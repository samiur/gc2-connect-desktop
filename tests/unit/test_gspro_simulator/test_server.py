# ABOUTME: Unit tests for MockGSProServer.
# ABOUTME: Tests server startup, shot tracking, and response behaviors.
"""Tests for MockGSProServer."""

from __future__ import annotations

import asyncio
import json

import pytest

from tests.simulators.gspro.config import (
    MockGSProServerConfig,
    ResponseType,
)
from tests.simulators.gspro.server import MockGSProServer, ReceivedShot


class TestServerLifecycle:
    """Tests for server startup and shutdown."""

    @pytest.mark.asyncio
    async def test_server_starts_and_stops(self) -> None:
        """Server can start and stop."""
        server = MockGSProServer()
        await server.start()

        assert server.is_running
        assert server.port > 0

        await server.stop()
        assert not server.is_running

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Can use as async context manager."""
        async with MockGSProServer() as server:
            assert server.is_running
            assert server.port > 0

        assert not server.is_running

    @pytest.mark.asyncio
    async def test_system_assigned_port(self) -> None:
        """Port 0 gets system-assigned port."""
        config = MockGSProServerConfig(port=0)
        async with MockGSProServer(config) as server:
            assert server.port > 0
            assert server.port != 0


class TestShotReceiving:
    """Tests for shot receiving and tracking."""

    @pytest.mark.asyncio
    async def test_receives_shot(self) -> None:
        """Server receives and records shot."""
        async with MockGSProServer() as server:
            # Connect and send shot
            reader, writer = await asyncio.open_connection(server.host, server.port)

            shot_message = {
                "ShotNumber": 1,
                "BallData": {"Speed": 145.0, "TotalSpin": 2500},
                "ClubData": {},
            }
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()

            # Wait for response
            await asyncio.wait_for(reader.read(1024), timeout=1.0)
            writer.close()
            await writer.wait_closed()

            # Verify shot was recorded
            shots = server.get_shots()
            assert len(shots) == 1
            assert shots[0].shot_number == 1
            assert shots[0].ball_data["Speed"] == 145.0

    @pytest.mark.asyncio
    async def test_get_shot_count(self) -> None:
        """get_shot_count returns correct count."""
        async with MockGSProServer() as server:
            assert server.get_shot_count() == 0

            # Send a shot
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()
            await asyncio.wait_for(reader.read(1024), timeout=1.0)
            writer.close()
            await writer.wait_closed()

            assert server.get_shot_count() == 1

    @pytest.mark.asyncio
    async def test_clear_shots(self) -> None:
        """clear_shots clears recorded shots."""
        async with MockGSProServer() as server:
            # Send a shot
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()
            await asyncio.wait_for(reader.read(1024), timeout=1.0)
            writer.close()
            await writer.wait_closed()

            assert server.get_shot_count() == 1

            server.clear_shots()
            assert server.get_shot_count() == 0

    @pytest.mark.asyncio
    async def test_wait_for_shots(self) -> None:
        """wait_for_shots waits for requested count."""
        async with MockGSProServer() as server:

            async def send_shot(num: int) -> None:
                reader, writer = await asyncio.open_connection(server.host, server.port)
                shot_message = {"ShotNumber": num, "BallData": {}, "ClubData": {}}
                writer.write(json.dumps(shot_message).encode())
                await writer.drain()
                await reader.read(1024)
                writer.close()
                await writer.wait_closed()

            # Send shots in background
            asyncio.create_task(send_shot(1))
            asyncio.create_task(send_shot(2))

            # Wait for them
            shots = await server.wait_for_shots(2, timeout=2.0)
            assert len(shots) == 2

    @pytest.mark.asyncio
    async def test_wait_for_shots_timeout(self) -> None:
        """wait_for_shots raises TimeoutError on timeout."""
        async with MockGSProServer() as server:
            with pytest.raises(asyncio.TimeoutError):
                await server.wait_for_shots(1, timeout=0.1)


class TestResponseTypes:
    """Tests for different response types."""

    @pytest.mark.asyncio
    async def test_success_response(self) -> None:
        """SUCCESS response sends 200 code."""
        config = MockGSProServerConfig(response_type=ResponseType.SUCCESS)
        async with MockGSProServer(config) as server:
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()

            response_data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
            response = json.loads(response_data.decode())

            assert response["Code"] == 200
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_error_response(self) -> None:
        """ERROR response sends configured error code."""
        config = MockGSProServerConfig(
            response_type=ResponseType.ERROR,
            error_code=501,
            error_message="Test error",
        )
        async with MockGSProServer(config) as server:
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()

            response_data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
            response = json.loads(response_data.decode())

            assert response["Code"] == 501
            assert response["Message"] == "Test error"
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_timeout_response(self) -> None:
        """TIMEOUT response sends nothing."""
        config = MockGSProServerConfig(response_type=ResponseType.TIMEOUT)
        async with MockGSProServer(config) as server:
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()

            # Should timeout waiting for response
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(reader.read(1024), timeout=0.5)

            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self) -> None:
        """INVALID_JSON response sends malformed JSON."""
        config = MockGSProServerConfig(response_type=ResponseType.INVALID_JSON)
        async with MockGSProServer(config) as server:
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()

            response_data = await asyncio.wait_for(reader.read(1024), timeout=1.0)

            # Should not parse as JSON
            with pytest.raises(json.JSONDecodeError):
                json.loads(response_data.decode())

            writer.close()
            await writer.wait_closed()


class TestResponseDelay:
    """Tests for response delay configuration."""

    @pytest.mark.asyncio
    async def test_response_delay(self) -> None:
        """Response is delayed by configured amount."""
        import time

        config = MockGSProServerConfig(response_delay_ms=200.0)
        async with MockGSProServer(config) as server:
            reader, writer = await asyncio.open_connection(server.host, server.port)
            shot_message = {"ShotNumber": 1, "BallData": {}, "ClubData": {}}

            start = time.monotonic()
            writer.write(json.dumps(shot_message).encode())
            await writer.drain()
            await reader.read(1024)
            elapsed = time.monotonic() - start

            # Should take at least 200ms
            assert elapsed >= 0.15  # Allow some tolerance

            writer.close()
            await writer.wait_closed()


class TestDisconnectAfterShots:
    """Tests for disconnect after N shots feature."""

    @pytest.mark.asyncio
    async def test_disconnect_after_shots(self) -> None:
        """Server disconnects after configured number of shots."""
        config = MockGSProServerConfig(disconnect_after_shots=2)
        async with MockGSProServer(config) as server:
            reader, writer = await asyncio.open_connection(server.host, server.port)

            # Send 2 shots and receive responses
            for i in range(2):
                shot_message = {"ShotNumber": i + 1, "BallData": {}, "ClubData": {}}
                writer.write(json.dumps(shot_message).encode())
                await writer.drain()
                # Read response (if any)
                try:
                    await asyncio.wait_for(reader.read(1024), timeout=0.5)
                except asyncio.TimeoutError:
                    pass

            # Give server time to close connection
            await asyncio.sleep(0.2)

            # Connection should be closed after 2nd shot - next read should be empty
            data = await reader.read(1024)
            assert data == b""  # Empty read indicates closed connection

            writer.close()
            await writer.wait_closed()


class TestDynamicConfig:
    """Tests for dynamic configuration updates."""

    @pytest.mark.asyncio
    async def test_update_config(self) -> None:
        """Can update config while running."""
        async with MockGSProServer() as server:
            assert server.config.response_type == ResponseType.SUCCESS

            server.update_config(response_type=ResponseType.ERROR)

            assert server.config.response_type == ResponseType.ERROR


class TestReceivedShot:
    """Tests for ReceivedShot dataclass."""

    def test_received_shot_creation(self) -> None:
        """ReceivedShot stores shot data."""
        shot = ReceivedShot(
            shot_number=1,
            ball_data={"Speed": 145.0},
            club_data={"Speed": 100.0},
            raw_message={"ShotNumber": 1},
        )

        assert shot.shot_number == 1
        assert shot.ball_data["Speed"] == 145.0
        assert shot.club_data["Speed"] == 100.0
        assert shot.raw_message["ShotNumber"] == 1

    def test_received_shot_has_timestamp(self) -> None:
        """ReceivedShot has timestamp."""
        shot = ReceivedShot(
            shot_number=1,
            ball_data={},
            club_data={},
            raw_message={},
        )

        assert shot.received_at is not None
