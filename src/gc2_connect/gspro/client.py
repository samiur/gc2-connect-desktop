# ABOUTME: TCP client for GSPro Open Connect API v1.
# ABOUTME: Sends shot data to GSPro golf simulator and handles responses.
"""GSPro Open Connect API v1 client."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from collections.abc import Callable
from typing import Any

from gc2_connect.models import (
    GC2BallStatus,
    GC2ShotData,
    GSProResponse,
    GSProShotMessage,
    GSProShotOptions,
)

logger = logging.getLogger(__name__)


def _notify_callbacks(callbacks: list[Callable[..., None]], *args: Any) -> None:
    """Invoke all callbacks with the given arguments, logging any errors."""
    for callback in callbacks:
        try:
            callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 921
HEARTBEAT_INTERVAL_SECONDS = 6.0


class GSProClient:
    """Client for GSPro Open Connect API v1."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._socket: socket.socket | None = None
        self._connected = False
        self._shot_number = 0
        self._current_player: dict[str, Any] | None = None
        self._response_callbacks: list[Callable[[GSProResponse], None]] = []
        self._disconnect_callbacks: list[Callable[[], None]] = []

        # Reader loop callbacks for GSPro responses
        self._player_info_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._match_started_callbacks: list[Callable[[], None]] = []
        self._match_ended_callbacks: list[Callable[[], None]] = []

        # Reader loop state
        self._reader_task: asyncio.Task[None] | None = None
        self._reader_running = False

        # Match state tracking for heartbeat logic
        self._match_started = False
        self._hardware_ready = False
        self._heartbeat_task: asyncio.Task[None] | None = None

        # Register internal handlers for match state changes
        self._match_started_callbacks.append(self._on_match_started)
        self._match_ended_callbacks.append(self._on_match_ended)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def shot_number(self) -> int:
        return self._shot_number

    @property
    def current_player(self) -> dict[str, Any] | None:
        return self._current_player

    @property
    def match_started(self) -> bool:
        """Whether GSPro match is currently active."""
        return self._match_started

    @property
    def hardware_ready(self) -> bool:
        """Whether GC2 hardware is ready (green light)."""
        return self._hardware_ready

    @property
    def is_ready_to_report(self) -> bool:
        """Whether we should report LaunchMonitorIsReady=true.

        Only true when both:
        - GC2 hardware is ready (green light)
        - GSPro match is active
        """
        return self._hardware_ready and self._match_started

    def set_hardware_ready(self, ready: bool) -> None:
        """Update hardware ready state from GC2.

        Called when GC2 status changes (FLAGS in 0M message).
        """
        if self._hardware_ready != ready:
            self._hardware_ready = ready
            # Send status update if match is active
            if self._match_started:
                self.send_heartbeat()

    def add_response_callback(self, callback: Callable[[GSProResponse], None]) -> None:
        """Add a callback for GSPro responses."""
        self._response_callbacks.append(callback)

    def remove_response_callback(self, callback: Callable[[GSProResponse], None]) -> None:
        if callback in self._response_callbacks:
            self._response_callbacks.remove(callback)

    def _notify_response(self, response: GSProResponse) -> None:
        """Notify all callbacks of a response."""
        _notify_callbacks(self._response_callbacks, response)

    def add_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback for connection loss events."""
        self._disconnect_callbacks.append(callback)

    def remove_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """Remove a disconnect callback."""
        if callback in self._disconnect_callbacks:
            self._disconnect_callbacks.remove(callback)

    def _notify_disconnect(self) -> None:
        """Notify all callbacks of a disconnection."""
        _notify_callbacks(self._disconnect_callbacks)

    # -------------------------------------------------------------------------
    # Reader loop callback management
    # -------------------------------------------------------------------------

    def add_player_info_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Add callback for player info updates (code 201)."""
        self._player_info_callbacks.append(callback)

    def remove_player_info_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a player info callback."""
        if callback in self._player_info_callbacks:
            self._player_info_callbacks.remove(callback)

    def add_match_started_callback(self, callback: Callable[[], None]) -> None:
        """Add callback for match started events (code 202)."""
        self._match_started_callbacks.append(callback)

    def remove_match_started_callback(self, callback: Callable[[], None]) -> None:
        """Remove a match started callback."""
        if callback in self._match_started_callbacks:
            self._match_started_callbacks.remove(callback)

    def add_match_ended_callback(self, callback: Callable[[], None]) -> None:
        """Add callback for match ended events (code 203)."""
        self._match_ended_callbacks.append(callback)

    def remove_match_ended_callback(self, callback: Callable[[], None]) -> None:
        """Remove a match ended callback."""
        if callback in self._match_ended_callbacks:
            self._match_ended_callbacks.remove(callback)

    # -------------------------------------------------------------------------
    # Match state and heartbeat timer management
    # -------------------------------------------------------------------------

    def _on_match_started(self) -> None:
        """Handle match started event (code 202).

        Starts the heartbeat timer and sends current ready status.
        """
        if not self._match_started:
            self._match_started = True
            self._start_heartbeat_timer()
            self.send_heartbeat()

    def _on_match_ended(self) -> None:
        """Handle match ended event (code 203).

        Stops the heartbeat timer. Does not send "not ready" here;
        the disconnect sequence handles the final "not ready" message.
        """
        if self._match_started:
            self._match_started = False
            self._stop_heartbeat_timer()

    def _start_heartbeat_timer(self) -> None:
        """Start periodic heartbeat timer."""
        self._stop_heartbeat_timer()  # Stop any existing timer
        try:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("GSPro heartbeat timer started")
        except RuntimeError as e:
            # No running event loop - happens in sync-only contexts
            logger.debug(f"Could not start heartbeat timer (no event loop): {e}")

    def _stop_heartbeat_timer(self) -> None:
        """Stop the heartbeat timer."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
            logger.info("GSPro heartbeat timer stopped")

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats at regular intervals while match is active."""
        while self._connected and self._match_started:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            if self._connected and self._match_started:
                self.send_heartbeat()

    # -------------------------------------------------------------------------
    # Reader loop for receiving unsolicited GSPro messages
    # -------------------------------------------------------------------------

    def _handle_response(self, response_json: dict[str, Any]) -> None:
        """Handle a response from GSPro based on code.

        Handles response codes:
        - 201: Player info update (handedness, club, distance)
        - 202: GSPro is ready / match started
        - 203: GSPro round ended
        """
        code = response_json.get("Code", 0)

        if code == 201:
            player = response_json.get("Player", {})
            if player:
                logger.debug(f"Received player info: {player}")
                _notify_callbacks(self._player_info_callbacks, player)

        elif code == 202:
            logger.info("GSPro match started (code 202)")
            _notify_callbacks(self._match_started_callbacks)

        elif code == 203:
            message = response_json.get("Message", "")
            if "round ended" in message.lower():
                logger.info("GSPro match ended (code 203)")
                _notify_callbacks(self._match_ended_callbacks)

    async def _reader_loop(self) -> None:
        """Background task that continuously reads from GSPro socket.

        This loop handles unsolicited messages from GSPro such as:
        - Code 201: Player info updates
        - Code 202: Match started
        - Code 203: Match ended
        """
        buffer = ""
        logger.debug("GSPro reader loop started")

        while self._reader_running and self._connected and self._socket:
            try:
                # Set socket to non-blocking for async reads
                self._socket.setblocking(False)
                try:
                    data = self._socket.recv(4096)
                    if not data:
                        # Connection closed
                        logger.warning("GSPro connection closed (empty recv)")
                        break
                    buffer += data.decode("utf-8")

                    # Try to parse complete JSON objects
                    while buffer:
                        try:
                            decoder = json.JSONDecoder()
                            response_json, idx = decoder.raw_decode(buffer)
                            buffer = buffer[idx:].lstrip()
                            self._handle_response(response_json)
                        except json.JSONDecodeError:
                            # Incomplete JSON, wait for more data
                            break

                except BlockingIOError:
                    # No data available, wait a bit
                    await asyncio.sleep(0.1)
                finally:
                    if self._socket:
                        self._socket.setblocking(True)

            except OSError as e:
                logger.error(f"Reader loop socket error: {e}")
                break
            except Exception as e:
                logger.error(f"Reader loop error: {e}")
                break

        logger.info("GSPro reader loop ended")

    def _start_reader_loop(self) -> None:
        """Start the background reader loop.

        This attempts to create an async task for the reader loop. If no event
        loop is running (e.g., in synchronous-only contexts or tests), it will
        log a debug message and skip starting the reader.
        """
        if self._reader_task is not None and not self._reader_task.done():
            return  # Already running

        try:
            self._reader_running = True
            self._reader_task = asyncio.create_task(self._reader_loop())
            logger.debug("Started GSPro reader loop task")
        except RuntimeError as e:
            # No running event loop - this happens in sync-only contexts
            logger.debug(f"Could not start reader loop (no event loop): {e}")
            self._reader_running = False

    def _stop_reader_loop(self) -> None:
        """Stop the background reader loop."""
        self._reader_running = False
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
            logger.debug("Stopped GSPro reader loop task")

    # -------------------------------------------------------------------------
    # Connection management
    # -------------------------------------------------------------------------

    def connect(self) -> bool:
        """Connect to GSPro."""
        try:
            # Use create_connection for cleaner connection handling
            self._socket = socket.create_connection((self.host, self.port), timeout=5.0)
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

            # Start background reader loop for unsolicited GSPro messages
            self._start_reader_loop()

            return True
        except OSError as e:
            logger.error(f"Failed to connect to GSPro: {e}")
            self._socket = None
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Cleanly disconnect from GSPro.

        Following OpenSkyPlus2 reference implementation:
        1. Stop heartbeat timer (stop sending heartbeats)
        2. Stop reader loop (prevent any more reads)
        3. Send heartbeat with LaunchMonitorIsReady=false
        4. Wait 250ms for GSPro to process
        5. Close socket

        This tells GSPro the launch monitor is going offline gracefully
        instead of just disappearing. TCP_NODELAY ensures the heartbeat
        is sent immediately without buffering.
        """
        if not self._socket:
            self._connected = False
            return

        # Step 1: Stop the heartbeat timer
        self._stop_heartbeat_timer()
        self._match_started = False

        # Step 2: Stop the reader loop
        self._stop_reader_loop()

        # Step 3: Tell GSPro we're going offline
        try:
            self._send_shutdown_heartbeat()
        except Exception as e:
            logger.debug(f"Error sending shutdown heartbeat: {e}")

        # Step 4: Wait for GSPro to process the heartbeat
        time.sleep(0.250)

        # Step 5: Close socket
        try:
            self._socket.close()
        except Exception:
            pass

        # Step 6: Clear internal state
        self._socket = None
        self._connected = False
        self._shot_number = 0
        self._current_player = None
        logger.info("Disconnected from GSPro (clean shutdown)")

    def _send_shutdown_heartbeat(self) -> None:
        """Send final heartbeat indicating launch monitor is going offline.

        This is sent without waiting for a response since GSPro doesn't
        respond to heartbeats anyway.
        """
        if not self._socket:
            return

        message = GSProShotMessage(
            ShotNumber=self._shot_number,
            ShotDataOptions=GSProShotOptions(
                ContainsBallData=False,
                ContainsClubData=False,
                LaunchMonitorIsReady=False,  # Key: telling GSPro we're going offline
                IsHeartBeat=True,
            ),
        )
        json_data = json.dumps(message.to_dict())
        self._socket.sendall(json_data.encode("utf-8"))
        logger.debug("Sent shutdown heartbeat (LaunchMonitorIsReady=false)")

    async def disconnect_async(self) -> None:
        """Async version of disconnect for use in async contexts."""
        await asyncio.get_event_loop().run_in_executor(None, self.disconnect)

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

        Uses is_ready_to_report to determine LaunchMonitorIsReady value.
        This is true only when both GC2 hardware is ready AND match is active.

        Note: GSPro doesn't respond to heartbeat messages, so we don't wait for a response.
        """
        if not self._connected or not self._socket:
            return None

        message = GSProShotMessage(
            ShotNumber=self._shot_number,
            ShotDataOptions=GSProShotOptions(
                ContainsBallData=False,
                ContainsClubData=False,
                LaunchMonitorIsReady=self.is_ready_to_report,
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
        return await asyncio.get_event_loop().run_in_executor(None, self.send_status, status)

    def _send_message(
        self, message: GSProShotMessage, expect_response: bool = True
    ) -> GSProResponse | None:
        """Send a message and optionally receive response.

        Args:
            message: The message to send
            expect_response: If True, wait for and parse response. If False, just send.
        """
        if self._socket is None:
            logger.error("Cannot send message: socket is None")
            return None

        sock = self._socket  # Local reference for type narrowing

        try:
            # Clear any buffered data before sending (stale responses)
            sock.setblocking(False)
            try:
                while True:
                    stale = sock.recv(4096)
                    if stale:
                        logger.debug(f"Cleared {len(stale)} bytes of stale buffer data")
                    else:
                        break
            except BlockingIOError:
                pass  # No data to clear, good
            finally:
                sock.setblocking(True)

            # Send JSON message
            json_data = json.dumps(message.to_dict())
            encoded = json_data.encode("utf-8")
            sock.sendall(encoded)
            logger.debug(f"Sent {len(encoded)} bytes: {json_data}")

            if not expect_response:
                return None

            # Receive response
            sock.settimeout(5.0)
            logger.debug("Waiting for response...")
            response_data = sock.recv(4096)

            if not response_data:
                logger.warning("Empty response from GSPro")
                return None

            response_str = response_data.decode("utf-8")

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
            was_connected = self._connected
            self._connected = False
            if was_connected:
                logger.error("GSPro connection lost!")
                self._notify_disconnect()
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return None

    async def send_shot_async(self, shot: GC2ShotData) -> GSProResponse | None:
        """Async version of send_shot."""
        return await asyncio.get_event_loop().run_in_executor(None, self.send_shot, shot)
