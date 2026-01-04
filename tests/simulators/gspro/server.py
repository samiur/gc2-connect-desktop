# ABOUTME: Mock GSPro server for integration testing.
# ABOUTME: Provides configurable TCP server with shot tracking.
"""Mock GSPro server for testing.

This module provides MockGSProServer, an async TCP server that simulates
GSPro's Open Connect API for testing without actual GSPro software.

Example:
    async with MockGSProServer() as server:
        # Connect client to server.address
        await client.connect(server.host, server.port)

        # After client sends shot, retrieve it
        shots = server.get_shots()
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from tests.simulators.gspro.config import MockGSProServerConfig, ResponseType


@dataclass
class ReceivedShot:
    """A shot received by the mock server.

    Attributes:
        shot_number: The shot number from the message.
        ball_data: Ball data from the message.
        club_data: Club data from the message.
        raw_message: The raw JSON message received.
        received_at: Timestamp when shot was received.
    """

    shot_number: int
    ball_data: dict[str, Any]
    club_data: dict[str, Any]
    raw_message: dict[str, Any]
    received_at: datetime = field(default_factory=datetime.now)


class MockGSProServer:
    """Mock GSPro server for testing.

    Simulates GSPro's Open Connect API with configurable behavior:
    - Response types: success, error, timeout, disconnect
    - Response delay for latency simulation
    - Shot tracking for verification

    Can be used as async context manager:
        async with MockGSProServer(config) as server:
            # server is running, use server.host and server.port
            pass
        # server stopped

    Or manually:
        server = MockGSProServer(config)
        await server.start()
        # use server
        await server.stop()
    """

    def __init__(self, config: MockGSProServerConfig | None = None) -> None:
        """Initialize the mock server.

        Args:
            config: Server configuration. Uses defaults if not provided.
        """
        self._config = config or MockGSProServerConfig()
        self._server: asyncio.Server | None = None
        self._shots: list[ReceivedShot] = []
        self._connections: list[asyncio.StreamWriter] = []
        self._running = False
        self._actual_port: int = 0

    @property
    def config(self) -> MockGSProServerConfig:
        """Get current server configuration."""
        return self._config

    @property
    def host(self) -> str:
        """Get server host address."""
        return self._config.host

    @property
    def port(self) -> int:
        """Get server port (actual port if system-assigned)."""
        return self._actual_port or self._config.port

    @property
    def address(self) -> tuple[str, int]:
        """Get server address as (host, port) tuple."""
        return (self.host, self.port)

    @property
    def is_running(self) -> bool:
        """Whether server is currently running."""
        return self._running

    def update_config(self, **kwargs: Any) -> None:
        """Update server configuration.

        Args:
            **kwargs: Configuration fields to update.
        """
        self._config = self._config.with_updated(**kwargs)

    def get_shots(self) -> list[ReceivedShot]:
        """Get all shots received by the server.

        Returns:
            List of received shots in order received.
        """
        return list(self._shots)

    def get_shot_count(self) -> int:
        """Get number of shots received.

        Returns:
            Number of shots received.
        """
        return len(self._shots)

    def clear_shots(self) -> None:
        """Clear recorded shots."""
        self._shots.clear()

    async def wait_for_shots(
        self,
        count: int,
        timeout: float = 5.0,
    ) -> list[ReceivedShot]:
        """Wait for a specific number of shots to be received.

        Args:
            count: Number of shots to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            List of received shots.

        Raises:
            asyncio.TimeoutError: If timeout expires before count reached.
        """
        deadline = asyncio.get_event_loop().time() + timeout

        while len(self._shots) < count:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"Timeout waiting for {count} shots, got {len(self._shots)}"
                )
            await asyncio.sleep(min(0.01, remaining))

        return list(self._shots[:count])

    async def start(self) -> None:
        """Start the server."""
        if self._running:
            return

        self._server = await asyncio.start_server(
            self._handle_client,
            self._config.host,
            self._config.port,
        )

        # Get actual port if system-assigned
        addrs = self._server.sockets[0].getsockname()
        self._actual_port = addrs[1]

        self._running = True
        asyncio.create_task(self._server.serve_forever())

    async def stop(self) -> None:
        """Stop the server."""
        if not self._running:
            return

        self._running = False

        # Close all client connections
        for writer in self._connections:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._connections.clear()

        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def __aenter__(self) -> MockGSProServer:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a client connection."""
        self._connections.append(writer)

        try:
            while self._running:
                try:
                    data = await asyncio.wait_for(reader.read(4096), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if not data:
                    break

                # Parse the message
                try:
                    message = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                # Record the shot
                shot = ReceivedShot(
                    shot_number=message.get("ShotNumber", 0),
                    ball_data=message.get("BallData", {}),
                    club_data=message.get("ClubData", {}),
                    raw_message=message,
                )
                self._shots.append(shot)

                # Check disconnect after shots
                if (
                    self._config.disconnect_after_shots > 0
                    and len(self._shots) >= self._config.disconnect_after_shots
                ):
                    break

                # Handle based on response type
                await self._send_response(writer, shot)

        except Exception:
            pass
        finally:
            if writer in self._connections:
                self._connections.remove(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        shot: ReceivedShot,
    ) -> None:
        """Send response based on configuration."""
        # Apply delay
        if self._config.response_delay_ms > 0:
            await asyncio.sleep(self._config.response_delay_ms / 1000.0)

        response_type = self._config.response_type

        if response_type == ResponseType.TIMEOUT:
            # Don't send anything
            return

        if response_type == ResponseType.DISCONNECT:
            # Close connection
            writer.close()
            return

        if response_type == ResponseType.INVALID_JSON:
            # Send malformed JSON
            writer.write(b"not valid json {{{")
            await writer.drain()
            return

        if response_type == ResponseType.ERROR:
            response = {
                "Code": self._config.error_code,
                "Message": self._config.error_message,
            }
        else:  # SUCCESS
            response = {
                "Code": 200,
                "Message": "Shot received successfully",
                "Player": {"Handed": "RH", "Club": "DR"},
            }

        writer.write(json.dumps(response).encode("utf-8"))
        await writer.drain()
