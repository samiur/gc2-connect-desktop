# ABOUTME: TCP client for GSPro Open Connect API v1.
# ABOUTME: Sends shot data to GSPro golf simulator and handles responses.
"""GSPro Open Connect API v1 client."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from collections.abc import Callable

from gc2_connect.models import GC2BallStatus, GC2ShotData, GSProResponse, GSProShotMessage

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 921


class GSProClient:
    """Client for GSPro Open Connect API v1."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._socket: socket.socket | None = None
        self._connected = False
        self._shot_number = 0
        self._current_player: dict | None = None
        self._response_callbacks: list[Callable[[GSProResponse], None]] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def shot_number(self) -> int:
        return self._shot_number

    @property
    def current_player(self) -> dict | None:
        return self._current_player

    def add_response_callback(self, callback: Callable[[GSProResponse], None]):
        """Add a callback for GSPro responses."""
        self._response_callbacks.append(callback)

    def remove_response_callback(self, callback: Callable[[GSProResponse], None]):
        if callback in self._response_callbacks:
            self._response_callbacks.remove(callback)

    def _notify_response(self, response: GSProResponse):
        """Notify all callbacks of a response."""
        for callback in self._response_callbacks:
            try:
                callback(response)
            except Exception as e:
                logger.error(f"Response callback error: {e}")

    def connect(self) -> bool:
        """Connect to GSPro."""
        try:
            # Use create_connection for cleaner connection handling
            self._socket = socket.create_connection(
                (self.host, self.port),
                timeout=5.0
            )
            # Set TCP_NODELAY to disable Nagle's algorithm for immediate sends
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._socket.settimeout(5.0)
            self._connected = True
            logger.info(f"Connected to GSPro at {self.host}:{self.port}")

            # Send initial heartbeat to register with GSPro
            # Note: GSPro doesn't respond to heartbeats, so we just send it
            logger.info("Sending initial heartbeat to GSPro...")
            self.send_heartbeat()
            logger.info("Initial heartbeat sent")

            return True
        except OSError as e:
            logger.error(f"Failed to connect to GSPro: {e}")
            self._socket = None
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from GSPro."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._connected = False
        logger.info("Disconnected from GSPro")

    async def connect_async(self) -> bool:
        """Async version of connect."""
        return await asyncio.get_event_loop().run_in_executor(None, self.connect)

    def send_shot(self, shot: GC2ShotData) -> GSProResponse | None:
        """Send a shot to GSPro."""
        if not self._connected or not self._socket:
            logger.error("Not connected to GSPro")
            return None

        self._shot_number += 1
        message = GSProShotMessage.from_gc2_shot(shot, self._shot_number)

        return self._send_message(message)

    def send_heartbeat(self) -> GSProResponse | None:
        """Send a heartbeat to GSPro.

        Note: GSPro doesn't respond to heartbeat messages, so we don't wait for a response.
        """
        if not self._connected or not self._socket:
            return None

        message = GSProShotMessage(
            ShotNumber=self._shot_number,
            ShotDataOptions=GSProShotOptions(
                ContainsBallData=False,
                ContainsClubData=False,
                LaunchMonitorIsReady=True,
                IsHeartBeat=True,
            ),
        )

        return self._send_message(message, expect_response=False)

    def send_status(self, status: GC2BallStatus) -> GSProResponse | None:
        """Send ball status update to GSPro.

        This sends a non-shot message to GSPro indicating:
        - Whether the launch monitor is ready (green light)
        - Whether a ball is detected

        This helps GSPro know when to expect shot data.

        Note: GSPro doesn't respond to status messages, so we don't wait for a response.
        """
        if not self._connected or not self._socket:
            return None

        message = GSProShotMessage(
            ShotNumber=self._shot_number,
            ShotDataOptions=GSProShotOptions(
                ContainsBallData=False,
                ContainsClubData=False,
                LaunchMonitorIsReady=status.is_ready,
                LaunchMonitorBallDetected=status.ball_detected,
                IsHeartBeat=False,
            ),
        )

        logger.debug(
            f"Sending status: ready={status.is_ready}, ball_detected={status.ball_detected}"
        )
        return self._send_message(message, expect_response=False)

    async def send_status_async(self, status: GC2BallStatus) -> GSProResponse | None:
        """Async version of send_status."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.send_status, status
        )

    def _send_message(
        self, message: GSProShotMessage, expect_response: bool = True
    ) -> GSProResponse | None:
        """Send a message and optionally receive response.

        Args:
            message: The message to send
            expect_response: If True, wait for and parse response. If False, just send.
        """
        try:
            # Clear any buffered data before sending (stale responses)
            self._socket.setblocking(False)
            try:
                while True:
                    stale = self._socket.recv(4096)
                    if stale:
                        logger.debug(f"Cleared {len(stale)} bytes of stale buffer data")
                    else:
                        break
            except BlockingIOError:
                pass  # No data to clear, good
            finally:
                self._socket.setblocking(True)

            # Send JSON message
            json_data = json.dumps(message.to_dict())
            encoded = json_data.encode('utf-8')
            self._socket.sendall(encoded)
            logger.debug(f"Sent {len(encoded)} bytes: {json_data}")

            if not expect_response:
                return None

            # Receive response
            self._socket.settimeout(5.0)
            logger.debug("Waiting for response...")
            response_data = self._socket.recv(4096)

            if not response_data:
                logger.warning("Empty response from GSPro")
                return None

            response_str = response_data.decode('utf-8')

            # Parse only the first JSON object (handle concatenated responses)
            decoder = json.JSONDecoder()
            response_json, _ = decoder.raw_decode(response_str)
            response = GSProResponse.from_dict(response_json)

            logger.debug(f"Received: {response_json}")

            # Update player info if received
            if response.Code == 201 and response.Player:
                self._current_player = response.Player
                logger.info(f"Player info: {response.Player}")

            self._notify_response(response)
            return response

        except TimeoutError:
            logger.warning("Timeout waiting for GSPro response")
            return None
        except OSError as e:
            logger.error(f"Socket error: {e}")
            self._connected = False
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return None

    async def send_shot_async(self, shot: GC2ShotData) -> GSProResponse | None:
        """Async version of send_shot."""
        return await asyncio.get_event_loop().run_in_executor(None, self.send_shot, shot)


class GSProShotOptions:
    """Helper class for shot options."""
    def __init__(
        self,
        ContainsBallData: bool = True,
        ContainsClubData: bool = False,
        LaunchMonitorIsReady: bool = True,
        LaunchMonitorBallDetected: bool = True,
        IsHeartBeat: bool = False,
    ):
        self.ContainsBallData = ContainsBallData
        self.ContainsClubData = ContainsClubData
        self.LaunchMonitorIsReady = LaunchMonitorIsReady
        self.LaunchMonitorBallDetected = LaunchMonitorBallDetected
        self.IsHeartBeat = IsHeartBeat
