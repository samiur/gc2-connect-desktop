# ABOUTME: Singleton connection managers for GC2 and GSPro connections.
# ABOUTME: Persists connection state across NiceGUI page refreshes.
"""Singleton connection managers that survive UI lifecycle changes.

This module provides connection managers that persist across NiceGUI page
refreshes. When a user refreshes the native window, the UI is recreated but
the USB and network connections remain stable.

Key components:
- UICallbackRegistry: Token-based callback registration for UI updates
- GC2ConnectionManager: Singleton wrapper for GC2 USB reader
- GSProConnectionManager: Singleton wrapper for GSPro TCP client

Usage:
    from gc2_connect.services.connection_manager import (
        get_gc2_manager,
        get_gspro_manager,
        get_callback_registry,
    )

    # In UI code
    registry = get_callback_registry()
    registry.register_shot_callback(my_callback, client_token)

    # Connect to devices
    gc2 = get_gc2_manager()
    gc2.connect(use_mock=True)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from gc2_connect.gc2.usb_reader import GC2USBReader, MockGC2Reader
from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2BallStatus, GC2ShotData

if TYPE_CHECKING:
    from gc2_connect.gc2.usb_reader import PacketSource

logger = logging.getLogger(__name__)


@dataclass
class UICallbackRegistry:
    """Registry for UI callbacks that survive page refresh.

    Callbacks are registered with a token (typically the NiceGUI client ID)
    so they can be bulk-unregistered when a UI instance is destroyed.

    When a callback throws a "client deleted" error, it's automatically
    removed from the registry.
    """

    _shot_callbacks: dict[str, Callable[[GC2ShotData], None]] = field(default_factory=dict)
    _status_callbacks: dict[str, Callable[[GC2BallStatus], None]] = field(default_factory=dict)
    _gc2_connect_callbacks: dict[str, Callable[[bool], None]] = field(default_factory=dict)
    _gc2_disconnect_callbacks: dict[str, Callable[[], None]] = field(default_factory=dict)
    _gspro_connect_callbacks: dict[str, Callable[[bool], None]] = field(default_factory=dict)
    _gspro_disconnect_callbacks: dict[str, Callable[[], None]] = field(default_factory=dict)

    def register_shot_callback(self, callback: Callable[[GC2ShotData], None], token: str) -> None:
        """Register a callback for shot data, keyed by token."""
        self._shot_callbacks[token] = callback

    def register_status_callback(
        self, callback: Callable[[GC2BallStatus], None], token: str
    ) -> None:
        """Register a callback for ball status updates, keyed by token."""
        self._status_callbacks[token] = callback

    def register_gc2_connect_callback(self, callback: Callable[[bool], None], token: str) -> None:
        """Register a callback for GC2 connection events, keyed by token."""
        self._gc2_connect_callbacks[token] = callback

    def register_gc2_disconnect_callback(self, callback: Callable[[], None], token: str) -> None:
        """Register a callback for GC2 disconnection events, keyed by token."""
        self._gc2_disconnect_callbacks[token] = callback

    def register_gspro_connect_callback(self, callback: Callable[[bool], None], token: str) -> None:
        """Register a callback for GSPro connection events, keyed by token."""
        self._gspro_connect_callbacks[token] = callback

    def register_gspro_disconnect_callback(self, callback: Callable[[], None], token: str) -> None:
        """Register a callback for GSPro disconnection events, keyed by token."""
        self._gspro_disconnect_callbacks[token] = callback

    def unregister_all(self, token: str) -> None:
        """Remove all callbacks registered with the given token."""
        self._shot_callbacks.pop(token, None)
        self._status_callbacks.pop(token, None)
        self._gc2_connect_callbacks.pop(token, None)
        self._gc2_disconnect_callbacks.pop(token, None)
        self._gspro_connect_callbacks.pop(token, None)
        self._gspro_disconnect_callbacks.pop(token, None)
        logger.debug(f"Unregistered all callbacks for token: {token}")

    def notify_shot(self, shot: GC2ShotData) -> None:
        """Notify all registered shot callbacks."""
        self._notify_with_arg(self._shot_callbacks, shot)

    def notify_status(self, status: GC2BallStatus) -> None:
        """Notify all registered status callbacks."""
        self._notify_with_arg(self._status_callbacks, status)

    def notify_gc2_connect(self, success: bool) -> None:
        """Notify all registered GC2 connection callbacks."""
        self._notify_with_arg(self._gc2_connect_callbacks, success)

    def notify_gc2_disconnect(self) -> None:
        """Notify all registered GC2 disconnection callbacks."""
        self._notify_no_args(self._gc2_disconnect_callbacks)

    def notify_gspro_connect(self, success: bool) -> None:
        """Notify all registered GSPro connection callbacks."""
        self._notify_with_arg(self._gspro_connect_callbacks, success)

    def notify_gspro_disconnect(self) -> None:
        """Notify all registered GSPro disconnection callbacks."""
        self._notify_no_args(self._gspro_disconnect_callbacks)

    def _notify_with_arg(self, callbacks: dict[str, Callable[..., None]], arg: Any) -> None:
        """Notify callbacks with a single argument, removing dead ones."""
        dead_tokens: list[str] = []
        for token, callback in list(callbacks.items()):
            try:
                callback(arg)
            except Exception as e:
                if self._is_client_deleted_error(e):
                    dead_tokens.append(token)
                    logger.debug(f"Removed dead callback for token {token}")
                else:
                    logger.error(f"Callback error for token {token}: {e}")

        for token in dead_tokens:
            callbacks.pop(token, None)

    def _notify_no_args(self, callbacks: dict[str, Callable[[], None]]) -> None:
        """Notify callbacks with no arguments, removing dead ones."""
        dead_tokens: list[str] = []
        for token, callback in list(callbacks.items()):
            try:
                callback()
            except Exception as e:
                if self._is_client_deleted_error(e):
                    dead_tokens.append(token)
                    logger.debug(f"Removed dead callback for token {token}")
                else:
                    logger.error(f"Callback error for token {token}: {e}")

        for token in dead_tokens:
            callbacks.pop(token, None)

    def _is_client_deleted_error(self, error: Exception) -> bool:
        """Check if an error indicates a deleted NiceGUI client."""
        error_str = str(error).lower()
        return "client" in error_str and "deleted" in error_str


class GC2ConnectionManager:
    """Singleton manager for GC2 USB connection.

    Wraps GC2USBReader and persists connection state across page refreshes.
    The reader's callbacks are routed through the UICallbackRegistry.
    """

    def __init__(self, callback_registry: UICallbackRegistry) -> None:
        self._callback_registry = callback_registry
        self._reader: GC2USBReader | MockGC2Reader | None = None
        self._read_task: asyncio.Task[None] | None = None
        self._last_shot_id = 0
        self._use_mock = False

    @property
    def is_connected(self) -> bool:
        """Whether the GC2 is currently connected."""
        return self._reader is not None and self._reader.is_connected

    @property
    def is_running(self) -> bool:
        """Whether the read loop is currently running."""
        return self._reader is not None and self._reader.is_running

    @property
    def reader(self) -> GC2USBReader | MockGC2Reader | None:
        """Access to the underlying reader (for status queries, etc)."""
        return self._reader

    @property
    def last_shot_id(self) -> int:
        """The last shot ID received (persisted across reconnects)."""
        return self._last_shot_id

    @property
    def last_status(self) -> GC2BallStatus | None:
        """The last ball status received."""
        if self._reader is not None:
            return self._reader.last_status
        return None

    @property
    def use_mock(self) -> bool:
        """Whether mock mode is enabled."""
        return self._use_mock

    def connect(
        self,
        use_mock: bool = False,
        packet_source: PacketSource | None = None,
    ) -> bool:
        """Connect to GC2 (or mock).

        Args:
            use_mock: If True, use MockGC2Reader instead of real USB.
            packet_source: Optional packet source for testing (GC2USBReader only).

        Returns:
            True if connection succeeded, False otherwise.
        """
        if self._reader is not None:
            self.disconnect()

        self._use_mock = use_mock

        if use_mock:
            self._reader = MockGC2Reader()
        else:
            self._reader = GC2USBReader(packet_source=packet_source)

        # Register internal callbacks that route to the registry
        self._reader.add_shot_callback(self._on_shot)
        self._reader.add_status_callback(self._on_status)
        self._reader.add_disconnect_callback(self._on_disconnect)

        success = self._reader.connect()
        self._callback_registry.notify_gc2_connect(success)

        if success:
            logger.info("GC2 connected via connection manager")
        else:
            logger.warning("GC2 connection failed")
            self._reader = None

        return success

    async def start_read_loop(self) -> None:
        """Start the async read loop."""
        if self._reader is None:
            logger.warning("Cannot start read loop: not connected")
            return

        if self._read_task is not None and not self._read_task.done():
            logger.debug("Read loop already running")
            return

        self._read_task = asyncio.create_task(self._reader.read_loop())
        logger.info("GC2 read loop started")

    def disconnect(self) -> None:
        """Disconnect from GC2."""
        if self._read_task is not None:
            self._read_task.cancel()
            self._read_task = None

        if self._reader is not None:
            self._reader.disconnect()
            self._reader = None

        logger.info("GC2 disconnected via connection manager")

    def send_test_shot(self) -> None:
        """Send test shot (mock mode only)."""
        if isinstance(self._reader, MockGC2Reader):
            self._reader.send_test_shot()
        else:
            logger.warning("send_test_shot only works in mock mode")

    def _on_shot(self, shot: GC2ShotData) -> None:
        """Internal callback for shots from the reader."""
        self._last_shot_id = shot.shot_id
        self._callback_registry.notify_shot(shot)

    def _on_status(self, status: GC2BallStatus) -> None:
        """Internal callback for status from the reader."""
        self._callback_registry.notify_status(status)

    def _on_disconnect(self) -> None:
        """Internal callback for disconnection from the reader."""
        logger.warning("GC2 USB disconnection detected")
        self._callback_registry.notify_gc2_disconnect()


class GSProConnectionManager:
    """Singleton manager for GSPro TCP connection.

    Wraps GSProClient and persists connection state (including shot number)
    across page refreshes. The shot number is stored here rather than in
    the client, so it survives client recreation.
    """

    def __init__(self, callback_registry: UICallbackRegistry) -> None:
        self._callback_registry = callback_registry
        self._client: GSProClient | None = None
        self._shot_number = 0  # Persisted here, not in client
        self._host: str = ""
        self._port: int = 921

    @property
    def is_connected(self) -> bool:
        """Whether GSPro is currently connected."""
        return self._client is not None and self._client.is_connected

    @property
    def client(self) -> GSProClient | None:
        """Access to the underlying client (for advanced operations)."""
        return self._client

    @property
    def shot_number(self) -> int:
        """Current shot number (persisted across reconnects)."""
        # Sync from client if connected
        if self._client is not None:
            self._shot_number = self._client.shot_number
        return self._shot_number

    @property
    def host(self) -> str:
        """The GSPro host address."""
        return self._host

    @property
    def port(self) -> int:
        """The GSPro port."""
        return self._port

    async def connect(self, host: str, port: int) -> bool:
        """Connect to GSPro.

        Args:
            host: GSPro host address.
            port: GSPro port.

        Returns:
            True if connection succeeded, False otherwise.
        """
        if self._client is not None:
            self.disconnect()

        self._host = host
        self._port = port
        self._client = GSProClient(host=host, port=port)
        self._client.add_disconnect_callback(self._on_disconnect)

        # Restore shot number from our persistent storage
        self._client._shot_number = self._shot_number

        success = await self._client.connect_async()
        self._callback_registry.notify_gspro_connect(success)

        if success:
            logger.info(f"GSPro connected to {host}:{port} via connection manager")
        else:
            logger.warning(f"GSPro connection to {host}:{port} failed")
            self._client = None

        return success

    def disconnect(self) -> None:
        """Disconnect from GSPro."""
        if self._client is not None:
            # Save shot number before disconnect (client resets it)
            self._shot_number = self._client.shot_number
            self._client.disconnect()
            self._client = None

        logger.info("GSPro disconnected via connection manager")

    async def send_shot(self, shot: GC2ShotData) -> Any:
        """Send shot to GSPro.

        Args:
            shot: The shot data to send.

        Returns:
            Response from GSPro, or None if not connected.
        """
        if self._client is None or not self._client.is_connected:
            logger.warning("Cannot send shot: GSPro not connected")
            return None

        response = await self._client.send_shot_async(shot)
        # Keep our shot number in sync
        self._shot_number = self._client.shot_number
        return response

    def send_status(self, status: GC2BallStatus) -> None:
        """Send ball status to GSPro.

        Args:
            status: The ball status to send.
        """
        if self._client is not None and self._client.is_connected:
            self._client.send_status(status)

    def _on_disconnect(self) -> None:
        """Internal callback for disconnection from the client."""
        if self._client is not None:
            # Save shot number before it gets reset
            self._shot_number = self._client.shot_number
        logger.warning("GSPro TCP disconnection detected")
        self._callback_registry.notify_gspro_disconnect()


# Module-level singletons
_callback_registry: UICallbackRegistry | None = None
_gc2_manager: GC2ConnectionManager | None = None
_gspro_manager: GSProConnectionManager | None = None


def get_callback_registry() -> UICallbackRegistry:
    """Get or create the callback registry singleton."""
    global _callback_registry
    if _callback_registry is None:
        _callback_registry = UICallbackRegistry()
    return _callback_registry


def get_gc2_manager() -> GC2ConnectionManager:
    """Get or create the GC2 connection manager singleton."""
    global _gc2_manager
    if _gc2_manager is None:
        _gc2_manager = GC2ConnectionManager(get_callback_registry())
    return _gc2_manager


def get_gspro_manager() -> GSProConnectionManager:
    """Get or create the GSPro connection manager singleton."""
    global _gspro_manager
    if _gspro_manager is None:
        _gspro_manager = GSProConnectionManager(get_callback_registry())
    return _gspro_manager


def reset_all() -> None:
    """Reset all singletons. For testing only.

    This disconnects any active connections and clears the singleton
    references, allowing fresh instances to be created.
    """
    global _callback_registry, _gc2_manager, _gspro_manager

    if _gc2_manager is not None:
        _gc2_manager.disconnect()
    if _gspro_manager is not None:
        _gspro_manager.disconnect()

    _callback_registry = None
    _gc2_manager = None
    _gspro_manager = None

    logger.debug("Connection manager singletons reset")


def shutdown_all() -> None:
    """Clean shutdown of all connections.

    Unlike reset_all(), this doesn't clear the singletons - it just
    disconnects. Used during app shutdown.
    """
    if _gc2_manager is not None:
        _gc2_manager.disconnect()
    if _gspro_manager is not None:
        _gspro_manager.disconnect()

    logger.info("All connections shut down")
