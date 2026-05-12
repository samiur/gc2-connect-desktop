# ABOUTME: TCP client for GSPro Open Connect API v1.
# ABOUTME: Sends shot data to GSPro golf simulator and handles responses.
"""GSPro Open Connect API v1 client (async)."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import sys
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
CONNECT_TIMEOUT_SECONDS = 5.0
SHUTDOWN_GRACE_SECONDS = 0.250
KEEPALIVE_IDLE_SECONDS = 30
KEEPALIVE_INTVL_SECONDS = 10
KEEPALIVE_CNT = 3


class GSProClient:
    """Async client for GSPro Open Connect API v1."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._shot_number = 0
        self._current_player: dict[str, Any] | None = None

        self._response_callbacks: list[Callable[[GSProResponse], None]] = []
        self._disconnect_callbacks: list[Callable[[], None]] = []

        # Reader loop callbacks for GSPro responses
        self._player_info_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._match_started_callbacks: list[Callable[[], None]] = []
        self._match_ended_callbacks: list[Callable[[], None]] = []

        self._reader_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

        # Match state tracking for heartbeat logic
        self._match_started = False
        self._hardware_ready = False

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
        if self._hardware_ready == ready:
            return
        self._hardware_ready = ready
        # Send status update if match is active
        if not self._match_started:
            return
        self._schedule_heartbeat()

    def _schedule_heartbeat(self) -> None:
        """Fire-and-forget a heartbeat from a sync context."""
        try:
            asyncio.create_task(self.send_heartbeat())
        except RuntimeError:
            logger.debug("No running loop; skipping heartbeat schedule")

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
        if self._match_started:
            return
        self._match_started = True
        self._start_heartbeat_timer()
        self._schedule_heartbeat()

    def _on_match_ended(self) -> None:
        """Handle match ended event (code 203).

        Stops the heartbeat timer. Does not send "not ready" here;
        the disconnect sequence handles the final "not ready" message.
        """
        if not self._match_started:
            return
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
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
            logger.info("GSPro heartbeat timer stopped")

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats at regular intervals while match is active."""
        try:
            while self._connected and self._match_started:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                if self._connected and self._match_started:
                    await self.send_heartbeat()
        except asyncio.CancelledError:
            pass

    # -------------------------------------------------------------------------
    # Socket configuration
    # -------------------------------------------------------------------------

    def _configure_socket(self, sock: socket.socket) -> None:
        """Configure socket options for TCP_NODELAY and SO_KEEPALIVE."""
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if sys.platform == "darwin" and hasattr(socket, "TCP_KEEPALIVE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, KEEPALIVE_IDLE_SECONDS)
        elif sys.platform.startswith("linux"):
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, KEEPALIVE_IDLE_SECONDS)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, KEEPALIVE_INTVL_SECONDS)
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, KEEPALIVE_CNT)

    # -------------------------------------------------------------------------
    # Connection management
    # -------------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to GSPro."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except (TimeoutError, asyncio.TimeoutError, OSError) as e:
            logger.error(f"Failed to connect to GSPro: {e}")
            self._reader = None
            self._writer = None
            self._connected = False
            return False

        assert self._writer is not None
        sock = self._writer.get_extra_info("socket")
        if sock is not None:
            self._configure_socket(sock)

        self._connected = True
        logger.info(f"Connected to GSPro at {self.host}:{self.port}")

        # Send initial heartbeat to register with GSPro
        logger.info("Sending initial heartbeat to GSPro...")
        await self.send_heartbeat()
        logger.info("Initial heartbeat sent")

        # Start background reader loop for unsolicited GSPro messages
        self._reader_task = asyncio.create_task(self._reader_loop())
        return True

    async def disconnect(self) -> None:
        """Cleanly disconnect from GSPro.

        Following OpenSkyPlus2 reference implementation:
        1. Stop heartbeat timer (stop sending heartbeats)
        2. Cancel reader task
        3. Send heartbeat with LaunchMonitorIsReady=false
        4. Wait 250ms for GSPro to process
        5. Close writer
        """
        if self._writer is None and not self._connected:
            return

        # Step 1: Stop the heartbeat timer
        self._stop_heartbeat_timer()
        self._match_started = False

        # Step 2: Cancel the reader task
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None

        # Step 3: Tell GSPro we're going offline
        if self._writer is not None and self._connected:
            try:
                await self._send_shutdown_heartbeat()
                await asyncio.sleep(SHUTDOWN_GRACE_SECONDS)
            except Exception as e:
                logger.debug(f"Error sending shutdown heartbeat: {e}")

        # Step 4: Close the writer
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

        # Step 5: Clear internal state
        self._reader = None
        self._writer = None
        self._connected = False
        self._shot_number = 0
        self._current_player = None
        logger.info("Disconnected from GSPro (clean shutdown)")

    async def _send_shutdown_heartbeat(self) -> None:
        """Send final heartbeat indicating launch monitor is going offline.

        This tells GSPro the launch monitor is going offline gracefully.
        """
        if self._writer is None:
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
        payload = json.dumps(message.to_dict()).encode("utf-8") + b"\n"
        self._writer.write(payload)
        await self._writer.drain()
        logger.debug("Sent shutdown heartbeat (LaunchMonitorIsReady=false)")

    # -------------------------------------------------------------------------
    # Send methods
    # -------------------------------------------------------------------------

    async def send_shot(self, shot: GC2ShotData) -> None:
        """Send a shot to GSPro.

        The GSPro ack arrives asynchronously via the reader loop's response callbacks.
        """
        if not self._connected or self._writer is None:
            logger.error("Not connected to GSPro")
            return
        self._shot_number += 1
        message = GSProShotMessage.from_gc2_shot(shot, self._shot_number)
        await self._send_message(message)

    async def send_heartbeat(self) -> None:
        """Send a heartbeat to GSPro.

        Uses is_ready_to_report to determine LaunchMonitorIsReady value.
        This is true only when both GC2 hardware is ready AND match is active.
        """
        if not self._connected or self._writer is None:
            return

        message = GSProShotMessage(
            ShotNumber=self._shot_number,
            ShotDataOptions=GSProShotOptions(
                ContainsBallData=False,
                ContainsClubData=False,
                LaunchMonitorIsReady=self.is_ready_to_report,
                IsHeartBeat=True,
            ),
        )
        await self._send_message(message)

    async def send_status(self, status: GC2BallStatus) -> None:
        """Send ball status update to GSPro.

        This sends a non-shot message to GSPro indicating:
        - Whether the launch monitor is ready (green light)
        - Whether a ball is detected
        """
        if not self._connected or self._writer is None:
            return

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
        await self._send_message(message)

    async def _send_message(self, message: GSProShotMessage) -> None:
        """Send a message with newline framing.

        Appends \\n to every outbound JSON write, matching the GsProApi.cs reference.
        """
        if self._writer is None:
            logger.error("Cannot send message: writer is None")
            return
        payload = json.dumps(message.to_dict()).encode("utf-8") + b"\n"
        try:
            self._writer.write(payload)
            await self._writer.drain()
            logger.debug(f"Sent {len(payload)} bytes: {payload[:200]!r}")
        except (ConnectionError, OSError) as e:
            logger.error(f"GSPro write failed: {e}")
            self._on_connection_lost()

    # -------------------------------------------------------------------------
    # Reader loop for receiving unsolicited GSPro messages
    # -------------------------------------------------------------------------

    async def _reader_loop(self) -> None:
        """Background task that continuously reads from GSPro stream.

        Handles unsolicited messages from GSPro such as:
        - Code 201: Player info updates
        - Code 202: Match started
        - Code 203: Match ended
        - Bare "GSPro ready" string (treated as code 202)
        """
        logger.debug("GSPro reader loop started")
        buffer = b""
        try:
            while self._connected and self._reader is not None:
                try:
                    chunk = await self._reader.read(4096)
                except (ConnectionError, OSError) as e:
                    logger.warning(f"GSPro reader socket error: {e}")
                    self._on_connection_lost()
                    return
                if not chunk:
                    logger.warning("GSPro connection closed (EOF)")
                    self._on_connection_lost()
                    return
                buffer = self._drain_buffer(buffer + chunk)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("GSPro reader loop ended")

    def _drain_buffer(self, buffer: bytes) -> bytes:
        """Parse and dispatch complete JSON objects from the buffer.

        Returns any remaining unparsed bytes.
        """
        text = buffer.decode("utf-8", errors="replace")
        decoder = json.JSONDecoder()

        while text:
            stripped = text.lstrip()
            if not stripped:
                return b""
            text = stripped

            if text.startswith("GSPro ready"):
                self._handle_response({"Code": 202, "Message": "GSPro ready"})
                newline = text.find("\n")
                if newline == -1:
                    return b""
                text = text[newline + 1 :]
                continue

            try:
                obj, end = decoder.raw_decode(text)
            except json.JSONDecodeError:
                return text.encode("utf-8")

            self._handle_response(obj)
            text = text[end:]

        return b""

    def _on_connection_lost(self) -> None:
        """Handle unexpected connection loss."""
        if not self._connected:
            return
        self._connected = False
        self._stop_heartbeat_timer()
        self._match_started = False
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass
        self._notify_disconnect()

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

        response = GSProResponse.from_dict(response_json)

        # Update player info if received
        if response.Code == 201 and response.Player:
            self._current_player = response.Player
            logger.info(f"Player info: {response.Player}")

        self._notify_response(response)
