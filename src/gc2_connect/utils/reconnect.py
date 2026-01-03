# ABOUTME: Auto-reconnection manager with exponential backoff for connections.
# ABOUTME: Handles reconnection logic for GC2 USB and GSPro network connections.

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ReconnectionState(str, Enum):
    """State of the reconnection manager."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ReconnectionManager:
    """Manages automatic reconnection with exponential backoff.

    This class provides a generic reconnection mechanism that can be used
    with any connection type (GC2 USB, GSPro network, etc.).

    Features:
    - Exponential backoff delay between attempts (1, 2, 4, 8, 16 seconds)
    - Configurable maximum retries
    - State change and attempt callbacks for UI updates
    - Cancellation support
    - Works with both sync and async connect functions
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 16.0,
    ) -> None:
        """Initialize the reconnection manager.

        Args:
            max_retries: Maximum number of reconnection attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        self._state = ReconnectionState.DISCONNECTED
        self._retry_count = 0
        self._cancelled = False

        # Callbacks
        self._state_callbacks: list[Callable[[ReconnectionState], None]] = []
        self._attempt_callbacks: list[Callable[[int, float], None]] = []

    @property
    def state(self) -> ReconnectionState:
        """Current reconnection state."""
        return self._state

    @property
    def retry_count(self) -> int:
        """Number of retry attempts made."""
        return self._retry_count

    @retry_count.setter
    def retry_count(self, value: int) -> None:
        """Set retry count (for testing)."""
        self._retry_count = value

    def get_delay_for_attempt(self, attempt: int) -> float:
        """Calculate delay for a given attempt number using exponential backoff.

        Args:
            attempt: Zero-based attempt number

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.base_delay * (2**attempt)
        return float(min(delay, self.max_delay))

    def on_state_change(self, callback: Callable[[ReconnectionState], None]) -> None:
        """Register a callback for state changes.

        Args:
            callback: Function called with new state when state changes
        """
        self._state_callbacks.append(callback)

    def on_attempt(self, callback: Callable[[int, float], None]) -> None:
        """Register a callback for reconnection attempts.

        Args:
            callback: Function called with (attempt_number, delay) before each retry
        """
        self._attempt_callbacks.append(callback)

    def _set_state(self, state: ReconnectionState) -> None:
        """Update state and notify callbacks."""
        self._state = state
        for callback in self._state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    def _notify_attempt(self, attempt: int, delay: float) -> None:
        """Notify callbacks of a reconnection attempt."""
        for callback in self._attempt_callbacks:
            try:
                callback(attempt, delay)
            except Exception as e:
                logger.error(f"Attempt callback error: {e}")

    async def attempt_reconnect(
        self,
        connect_fn: Callable[[], bool] | Callable[[], Awaitable[bool]],
    ) -> bool:
        """Attempt to reconnect using the provided connect function.

        This method will keep trying to connect until successful or max_retries
        is reached. Between attempts, it waits with exponential backoff.

        Args:
            connect_fn: Function that attempts connection, returns True on success.
                        Can be sync or async.

        Returns:
            True if connection succeeded, False if all retries exhausted
        """
        self._cancelled = False
        self._retry_count = 0
        self._set_state(ReconnectionState.CONNECTING)

        attempt = 0
        while attempt < self.max_retries and not self._cancelled:
            try:
                # Call connect function (handle both sync and async)
                result = connect_fn()
                if asyncio.iscoroutine(result):
                    success = await result
                else:
                    success = result

                if success:
                    self._set_state(ReconnectionState.CONNECTED)
                    logger.info("Reconnection successful")
                    return True

            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

            # Failed - calculate delay and wait
            attempt += 1
            self._retry_count = attempt

            if attempt < self.max_retries and not self._cancelled:
                delay = self.get_delay_for_attempt(attempt - 1)
                self._set_state(ReconnectionState.RECONNECTING)
                self._notify_attempt(attempt, delay)
                logger.info(
                    f"Reconnection attempt {attempt}/{self.max_retries}, waiting {delay:.1f}s..."
                )

                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    self._cancelled = True
                    break

        if self._cancelled:
            self._set_state(ReconnectionState.DISCONNECTED)
            logger.info("Reconnection cancelled")
            return False

        self._set_state(ReconnectionState.FAILED)
        logger.error(f"Reconnection failed after {self.max_retries} attempts")
        return False

    def cancel(self) -> None:
        """Cancel ongoing reconnection attempts."""
        self._cancelled = True
        if self._state == ReconnectionState.RECONNECTING:
            self._set_state(ReconnectionState.DISCONNECTED)
        logger.info("Reconnection cancelled by user")

    def reset(self) -> None:
        """Reset the manager to initial state."""
        self._retry_count = 0
        self._cancelled = False
        self._set_state(ReconnectionState.DISCONNECTED)
