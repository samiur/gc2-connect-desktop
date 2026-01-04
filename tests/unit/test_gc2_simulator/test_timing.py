# ABOUTME: Unit tests for TimeController.
# ABOUTME: Tests deterministic timing for INSTANT, REAL, and STEPPED modes.
"""Tests for TimeController."""

from __future__ import annotations

import asyncio
import time

import pytest

from tests.simulators.timing import TimeController, TimeMode


class TestTimeMode:
    """Tests for TimeMode enum."""

    def test_modes_exist(self) -> None:
        """All three modes are defined."""
        assert TimeMode.REAL.value == "real"
        assert TimeMode.INSTANT.value == "instant"
        assert TimeMode.STEPPED.value == "stepped"


class TestTimeControllerInstantMode:
    """Tests for TimeController in INSTANT mode."""

    @pytest.fixture
    def controller(self) -> TimeController:
        """Create controller in INSTANT mode."""
        return TimeController(mode=TimeMode.INSTANT)

    def test_now_returns_start_time(self, controller: TimeController) -> None:
        """Initial now() returns start time."""
        assert controller.now() == 0.0

    def test_now_with_custom_start(self) -> None:
        """Can set custom start time."""
        controller = TimeController(mode=TimeMode.INSTANT, start_time=100.0)
        assert controller.now() == 100.0

    @pytest.mark.asyncio
    async def test_sleep_advances_time_instantly(self, controller: TimeController) -> None:
        """Sleep advances time but returns immediately."""
        start = time.monotonic()
        await controller.sleep(10.0)
        elapsed_real = time.monotonic() - start

        # Virtual time advanced
        assert controller.now() == 10.0
        # Real time was nearly instant (< 100ms)
        assert elapsed_real < 0.1

    @pytest.mark.asyncio
    async def test_multiple_sleeps_accumulate(self, controller: TimeController) -> None:
        """Multiple sleeps accumulate time."""
        await controller.sleep(5.0)
        await controller.sleep(3.0)
        await controller.sleep(2.0)
        assert controller.now() == 10.0

    def test_reset_clears_time(self, controller: TimeController) -> None:
        """Reset returns time to start."""
        controller._current_time = 100.0
        controller.reset()
        assert controller.now() == 0.0

    def test_reset_with_custom_start(self, controller: TimeController) -> None:
        """Reset can set new start time."""
        controller._current_time = 100.0
        controller.reset(start_time=50.0)
        assert controller.now() == 50.0


class TestTimeControllerRealMode:
    """Tests for TimeController in REAL mode."""

    @pytest.fixture
    def controller(self) -> TimeController:
        """Create controller in REAL mode."""
        return TimeController(mode=TimeMode.REAL)

    def test_now_returns_monotonic_time(self, controller: TimeController) -> None:
        """now() returns actual monotonic time."""
        before = time.monotonic()
        now = controller.now()
        after = time.monotonic()
        assert before <= now <= after

    @pytest.mark.asyncio
    async def test_sleep_uses_real_time(self, controller: TimeController) -> None:
        """Sleep actually waits in REAL mode."""
        start = time.monotonic()
        await controller.sleep(0.05)  # 50ms
        elapsed = time.monotonic() - start

        # Should have actually waited ~50ms
        assert elapsed >= 0.04  # Allow some tolerance


class TestTimeControllerSteppedMode:
    """Tests for TimeController in STEPPED mode."""

    @pytest.fixture
    def controller(self) -> TimeController:
        """Create controller in STEPPED mode."""
        return TimeController(mode=TimeMode.STEPPED)

    def test_now_returns_current_time(self, controller: TimeController) -> None:
        """now() returns current stepped time."""
        assert controller.now() == 0.0

    def test_advance_moves_time_forward(self, controller: TimeController) -> None:
        """advance() moves time forward."""
        controller.advance(5.0)
        assert controller.now() == 5.0

    def test_advance_accumulates(self, controller: TimeController) -> None:
        """Multiple advances accumulate."""
        controller.advance(2.0)
        controller.advance(3.0)
        assert controller.now() == 5.0

    def test_advance_to_sets_exact_time(self, controller: TimeController) -> None:
        """advance_to() sets exact time."""
        controller.advance_to(10.0)
        assert controller.now() == 10.0

    def test_advance_to_ignores_past_times(self, controller: TimeController) -> None:
        """advance_to() ignores times in the past."""
        controller.advance_to(10.0)
        controller.advance_to(5.0)  # Should be ignored
        assert controller.now() == 10.0

    @pytest.mark.asyncio
    async def test_sleep_waits_for_advance(self, controller: TimeController) -> None:
        """sleep() waits until advance() reaches target time."""
        woke_up = False

        async def sleeper() -> None:
            nonlocal woke_up
            await controller.sleep(5.0)
            woke_up = True

        # Start the sleeper
        task = asyncio.create_task(sleeper())
        await asyncio.sleep(0.01)  # Give it time to start

        # Should not be awake yet
        assert not woke_up

        # Advance time
        controller.advance(5.0)
        await asyncio.sleep(0.01)  # Let event loop process

        # Should now be awake
        assert woke_up
        await task

    @pytest.mark.asyncio
    async def test_multiple_waiters_wake_at_correct_times(self, controller: TimeController) -> None:
        """Multiple sleepers wake when time reaches their target."""
        woke_durations: list[float] = []

        async def sleeper(duration: float) -> None:
            await controller.sleep(duration)
            woke_durations.append(duration)

        # Start multiple sleepers
        task1 = asyncio.create_task(sleeper(2.0))
        task2 = asyncio.create_task(sleeper(5.0))
        task3 = asyncio.create_task(sleeper(3.0))
        await asyncio.sleep(0.01)

        # Advance to 3.0 - should wake 2.0 and 3.0 sleepers
        controller.advance_to(3.0)
        await asyncio.sleep(0.01)
        assert sorted(woke_durations) == [2.0, 3.0]

        # Advance to 5.0 - should wake 5.0 sleeper
        controller.advance_to(5.0)
        await asyncio.sleep(0.01)
        assert sorted(woke_durations) == [2.0, 3.0, 5.0]

        await asyncio.gather(task1, task2, task3)

    def test_advance_only_works_in_stepped_mode(self) -> None:
        """advance() raises error in non-STEPPED modes."""
        controller = TimeController(mode=TimeMode.INSTANT)
        with pytest.raises(RuntimeError, match="STEPPED mode"):
            controller.advance(1.0)

    def test_advance_to_only_works_in_stepped_mode(self) -> None:
        """advance_to() raises error in non-STEPPED modes."""
        controller = TimeController(mode=TimeMode.REAL)
        with pytest.raises(RuntimeError, match="STEPPED mode"):
            controller.advance_to(1.0)
