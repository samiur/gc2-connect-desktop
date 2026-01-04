# ABOUTME: Time controller for deterministic timing in async tests.
# ABOUTME: Allows controlled time progression for testing timeouts and delays.
"""Time controller for deterministic testing.

This module provides a TimeController that allows tests to control time
progression for deterministic and repeatable testing of:

- Packet delivery timing
- Timeout behavior
- Two-phase transmission simulation

Modes:
- REAL: Uses actual time (asyncio.sleep) - for integration tests
- INSTANT: All sleeps complete immediately, time advances - for fast unit tests
- STEPPED: Time only advances via advance() calls - for precise timing tests
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum


class TimeMode(Enum):
    """Mode of time progression.

    Attributes:
        REAL: Use actual time (for integration tests)
        INSTANT: Time advances instantly on sleep (for fast unit tests)
        STEPPED: Time only advances via advance() calls (for precise timing)
    """

    REAL = "real"
    INSTANT = "instant"
    STEPPED = "stepped"


class TimeController:
    """Controls virtual time for deterministic testing.

    Allows tests to control time progression for deterministic and
    repeatable testing of timing-sensitive code.

    Example (INSTANT mode - fast unit tests):
        controller = TimeController(mode=TimeMode.INSTANT)
        await controller.sleep(10.0)  # Returns immediately
        assert controller.now() == 10.0  # But time advanced

    Example (STEPPED mode - precise timing tests):
        controller = TimeController(mode=TimeMode.STEPPED)
        task = asyncio.create_task(some_timed_operation())
        controller.advance(5.0)  # Move time forward
        await asyncio.sleep(0)  # Let waiters process
    """

    def __init__(
        self,
        mode: TimeMode = TimeMode.INSTANT,
        start_time: float = 0.0,
    ) -> None:
        """Initialize the time controller.

        Args:
            mode: Time progression mode.
            start_time: Initial virtual time (ignored in REAL mode).
        """
        self._mode = mode
        self._current_time = start_time
        self._waiters: list[tuple[float, asyncio.Event]] = []

    @property
    def mode(self) -> TimeMode:
        """Get the current time mode."""
        return self._mode

    def now(self) -> float:
        """Get current time in seconds.

        Returns:
            Current time - virtual time in INSTANT/STEPPED modes,
            or actual monotonic time in REAL mode.
        """
        if self._mode == TimeMode.REAL:
            return time.monotonic()
        return self._current_time

    async def sleep(self, duration: float) -> None:
        """Sleep for specified duration.

        Behavior depends on mode:
        - REAL: Actual async sleep
        - INSTANT: Returns immediately, advances virtual time
        - STEPPED: Waits for advance() to reach target time

        Args:
            duration: Sleep duration in seconds.
        """
        if duration <= 0:
            return

        if self._mode == TimeMode.REAL:
            await asyncio.sleep(duration)
            return

        if self._mode == TimeMode.INSTANT:
            self._current_time += duration
            return

        # STEPPED mode: wait for advance() to reach target time
        target = self._current_time + duration
        event = asyncio.Event()
        self._waiters.append((target, event))

        # Check if already past target (race condition handling)
        if self._current_time >= target:
            event.set()

        await event.wait()

    def advance(self, duration: float) -> None:
        """Advance time by duration (STEPPED mode only).

        Wakes any waiters whose target time has been reached.

        Args:
            duration: Duration to advance in seconds.

        Raises:
            RuntimeError: If not in STEPPED mode.
        """
        if self._mode != TimeMode.STEPPED:
            raise RuntimeError("advance() only works in STEPPED mode")

        self._current_time += duration
        self._wake_ready_waiters()

    def advance_to(self, target: float) -> None:
        """Advance time to specific point (STEPPED mode only).

        Args:
            target: Target time in seconds.

        Raises:
            RuntimeError: If not in STEPPED mode.
        """
        if self._mode != TimeMode.STEPPED:
            raise RuntimeError("advance_to() only works in STEPPED mode")

        if target <= self._current_time:
            return

        self._current_time = target
        self._wake_ready_waiters()

    def _wake_ready_waiters(self) -> None:
        """Wake waiters whose target time has been reached."""
        ready = [(t, e) for t, e in self._waiters if t <= self._current_time]
        for target, event in ready:
            event.set()
            self._waiters.remove((target, event))

    def reset(self, start_time: float = 0.0) -> None:
        """Reset time and clear all waiters.

        Args:
            start_time: New start time (ignored in REAL mode).
        """
        self._current_time = start_time
        # Wake all waiters so they can exit cleanly
        for _, event in self._waiters:
            event.set()
        self._waiters.clear()
