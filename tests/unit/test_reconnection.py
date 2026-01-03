# ABOUTME: Unit tests for the ReconnectionManager class.
# ABOUTME: Tests auto-reconnection logic including exponential backoff and callbacks.

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from gc2_connect.utils.reconnect import ReconnectionManager, ReconnectionState


class TestReconnectionState:
    """Tests for ReconnectionState enum."""

    def test_state_values(self) -> None:
        """Test that all expected states exist."""
        assert ReconnectionState.DISCONNECTED.value == "disconnected"
        assert ReconnectionState.CONNECTING.value == "connecting"
        assert ReconnectionState.CONNECTED.value == "connected"
        assert ReconnectionState.RECONNECTING.value == "reconnecting"
        assert ReconnectionState.FAILED.value == "failed"


class TestReconnectionManagerInit:
    """Tests for ReconnectionManager initialization."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        manager = ReconnectionManager()

        assert manager.max_retries == 5
        assert manager.base_delay == 1.0
        assert manager.max_delay == 16.0
        assert manager.state == ReconnectionState.DISCONNECTED
        assert manager.retry_count == 0

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        manager = ReconnectionManager(
            max_retries=10,
            base_delay=2.0,
            max_delay=60.0,
        )

        assert manager.max_retries == 10
        assert manager.base_delay == 2.0
        assert manager.max_delay == 60.0


class TestExponentialBackoff:
    """Tests for exponential backoff timing."""

    def test_backoff_sequence(self) -> None:
        """Test exponential backoff delay sequence: 1, 2, 4, 8, 16."""
        manager = ReconnectionManager(base_delay=1.0, max_delay=16.0)

        expected_delays = [1.0, 2.0, 4.0, 8.0, 16.0]
        for attempt, expected in enumerate(expected_delays):
            delay = manager.get_delay_for_attempt(attempt)
            assert delay == expected, f"Attempt {attempt}: expected {expected}, got {delay}"

    def test_backoff_max_cap(self) -> None:
        """Test that backoff delay is capped at max_delay."""
        manager = ReconnectionManager(base_delay=1.0, max_delay=16.0)

        # After 5+ attempts, should still be capped at 16
        for attempt in range(5, 10):
            delay = manager.get_delay_for_attempt(attempt)
            assert delay == 16.0, f"Attempt {attempt}: expected 16.0, got {delay}"

    def test_custom_backoff_sequence(self) -> None:
        """Test custom base delay produces correct sequence."""
        manager = ReconnectionManager(base_delay=2.0, max_delay=32.0)

        expected_delays = [2.0, 4.0, 8.0, 16.0, 32.0]
        for attempt, expected in enumerate(expected_delays):
            delay = manager.get_delay_for_attempt(attempt)
            assert delay == expected, f"Attempt {attempt}: expected {expected}, got {delay}"


class TestReconnectionCallbacks:
    """Tests for reconnection status callbacks."""

    def test_on_state_change_callback(self) -> None:
        """Test that state change callback is invoked."""
        manager = ReconnectionManager()
        states_received: list[ReconnectionState] = []

        def callback(state: ReconnectionState) -> None:
            states_received.append(state)

        manager.on_state_change(callback)
        manager._set_state(ReconnectionState.CONNECTING)
        manager._set_state(ReconnectionState.CONNECTED)

        assert states_received == [
            ReconnectionState.CONNECTING,
            ReconnectionState.CONNECTED,
        ]

    def test_on_attempt_callback(self) -> None:
        """Test that attempt callback is invoked with retry info."""
        manager = ReconnectionManager()
        attempts_received: list[tuple[int, float]] = []

        def callback(attempt: int, delay: float) -> None:
            attempts_received.append((attempt, delay))

        manager.on_attempt(callback)

        # Simulate attempt notifications
        manager._notify_attempt(0, 1.0)
        manager._notify_attempt(1, 2.0)

        assert attempts_received == [(0, 1.0), (1, 2.0)]

    def test_multiple_callbacks(self) -> None:
        """Test that multiple callbacks are all invoked."""
        manager = ReconnectionManager()
        results: list[str] = []

        manager.on_state_change(lambda s: results.append(f"cb1:{s.value}"))
        manager.on_state_change(lambda s: results.append(f"cb2:{s.value}"))

        manager._set_state(ReconnectionState.CONNECTED)

        assert results == ["cb1:connected", "cb2:connected"]


class TestReconnectionAttempt:
    """Tests for reconnection attempt logic."""

    @pytest.mark.asyncio
    async def test_successful_reconnect_first_attempt(self) -> None:
        """Test successful reconnection on first attempt."""
        manager = ReconnectionManager()
        connect_fn = AsyncMock(return_value=True)

        result = await manager.attempt_reconnect(connect_fn)

        assert result is True
        assert manager.state == ReconnectionState.CONNECTED
        assert manager.retry_count == 0
        connect_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_reconnect_after_failures(self) -> None:
        """Test successful reconnection after some failures."""
        manager = ReconnectionManager(base_delay=0.01)  # Fast delays for testing

        # Fail twice, then succeed
        connect_fn = AsyncMock(side_effect=[False, False, True])

        result = await manager.attempt_reconnect(connect_fn)

        assert result is True
        assert manager.state == ReconnectionState.CONNECTED
        assert connect_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Test that reconnection stops after max retries."""
        manager = ReconnectionManager(max_retries=3, base_delay=0.01)
        connect_fn = AsyncMock(return_value=False)

        result = await manager.attempt_reconnect(connect_fn)

        assert result is False
        assert manager.state == ReconnectionState.FAILED
        assert connect_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_state_transitions_during_reconnect(self) -> None:
        """Test correct state transitions during reconnection."""
        manager = ReconnectionManager(base_delay=0.01)
        states: list[ReconnectionState] = []

        manager.on_state_change(lambda s: states.append(s))

        # Fail once, then succeed
        connect_fn = AsyncMock(side_effect=[False, True])
        await manager.attempt_reconnect(connect_fn)

        assert ReconnectionState.RECONNECTING in states
        assert ReconnectionState.CONNECTED in states
        assert states[-1] == ReconnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_attempt_callback_invoked(self) -> None:
        """Test that attempt callbacks are invoked for each retry."""
        manager = ReconnectionManager(base_delay=0.01, max_delay=0.04)
        attempts: list[tuple[int, float]] = []

        manager.on_attempt(lambda a, d: attempts.append((a, d)))

        # Fail 3 times, then succeed
        connect_fn = AsyncMock(side_effect=[False, False, False, True])
        await manager.attempt_reconnect(connect_fn)

        # Should have 3 retry attempts (first connection doesn't count as retry)
        assert len(attempts) == 3
        assert attempts[0][0] == 1  # First retry is attempt #1
        assert attempts[1][0] == 2
        assert attempts[2][0] == 3


class TestReconnectionCancel:
    """Tests for cancellation of reconnection attempts."""

    @pytest.mark.asyncio
    async def test_cancel_stops_reconnection(self) -> None:
        """Test that cancel() stops ongoing reconnection."""
        manager = ReconnectionManager(base_delay=1.0)  # Longer delay to allow cancellation
        connect_fn = AsyncMock(return_value=False)
        states: list[ReconnectionState] = []
        manager.on_state_change(lambda s: states.append(s))

        # Start reconnection in background
        task = asyncio.create_task(manager.attempt_reconnect(connect_fn))

        # Allow first attempt to fail
        await asyncio.sleep(0.05)

        # Cancel while waiting for retry
        manager.cancel()

        # Wait for task to complete
        result = await task

        assert result is False
        assert manager.state == ReconnectionState.DISCONNECTED
        assert ReconnectionState.DISCONNECTED in states

    @pytest.mark.asyncio
    async def test_cancel_when_not_reconnecting(self) -> None:
        """Test that cancel() is safe when not reconnecting."""
        manager = ReconnectionManager()

        # Should not raise
        manager.cancel()
        assert manager.state == ReconnectionState.DISCONNECTED


class TestReconnectionReset:
    """Tests for resetting reconnection state."""

    def test_reset_clears_retry_count(self) -> None:
        """Test that reset() clears retry count."""
        manager = ReconnectionManager()
        manager.retry_count = 5

        manager.reset()

        assert manager.retry_count == 0

    def test_reset_sets_disconnected_state(self) -> None:
        """Test that reset() sets state to disconnected."""
        manager = ReconnectionManager()
        manager._set_state(ReconnectionState.FAILED)

        manager.reset()

        assert manager.state == ReconnectionState.DISCONNECTED

    def test_reset_preserves_callbacks(self) -> None:
        """Test that reset() preserves registered callbacks."""
        manager = ReconnectionManager()
        callback_called = [False]

        manager.on_state_change(lambda _: callback_called.__setitem__(0, True))
        manager.reset()

        # Verify callback is still registered
        manager._set_state(ReconnectionState.CONNECTING)
        assert callback_called[0] is True


class TestReconnectionWithConnectable:
    """Tests for integration with connectable objects (GC2/GSPro)."""

    @pytest.mark.asyncio
    async def test_reconnect_with_sync_connect_function(self) -> None:
        """Test reconnection with a sync connect function."""
        manager = ReconnectionManager(base_delay=0.01)

        # Sync function that returns True
        def sync_connect() -> bool:
            return True

        result = await manager.attempt_reconnect(sync_connect)

        assert result is True
        assert manager.state == ReconnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_reconnect_with_exception(self) -> None:
        """Test that exceptions are handled gracefully."""
        manager = ReconnectionManager(max_retries=2, base_delay=0.01)

        # Function that raises on first call, succeeds on second
        call_count = [0]

        def flaky_connect() -> bool:
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Connection failed")
            return True

        result = await manager.attempt_reconnect(flaky_connect)

        assert result is True
        assert call_count[0] == 2
