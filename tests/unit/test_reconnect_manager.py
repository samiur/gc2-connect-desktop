# ABOUTME: Unit tests for ReconnectionManager exponential-backoff reconnect helper.
# ABOUTME: Covers retry-count semantics, infinite-retry mode, cancellation, and delay calculation.
"""Unit tests for ReconnectionManager."""

from __future__ import annotations

import pytest

from gc2_connect.utils.reconnect import ReconnectionManager, ReconnectionState


class TestInfiniteRetries:
    """Test that max_retries=None means infinite retries."""

    @pytest.mark.asyncio
    async def test_infinite_retries_keeps_attempting_past_default_cap(self) -> None:
        """When max_retries=None the loop should keep attempting beyond any normal cap."""
        mgr = ReconnectionManager(max_retries=None, base_delay=0.0, max_delay=0.0)
        attempts = 0

        def fail_then_succeed() -> bool:
            nonlocal attempts
            attempts += 1
            return attempts >= 50  # success on the 50th attempt

        result = await mgr.attempt_reconnect(fail_then_succeed)
        assert result is True
        assert attempts == 50
        assert mgr.state == ReconnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_infinite_retries_stops_on_cancel(self) -> None:
        """When max_retries=None the loop should stop when cancel() is called."""
        mgr = ReconnectionManager(max_retries=None, base_delay=0.0, max_delay=0.0)
        attempts = 0

        def fail_and_cancel_after_3() -> bool:
            nonlocal attempts
            attempts += 1
            if attempts >= 3:
                mgr.cancel()
            return False

        result = await mgr.attempt_reconnect(fail_and_cancel_after_3)
        assert result is False
        assert mgr.state == ReconnectionState.DISCONNECTED
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_finite_retries_still_exits_at_max(self) -> None:
        """Confirm we did not regress the bounded-retry path: max_retries=3 still exits."""
        mgr = ReconnectionManager(max_retries=3, base_delay=0.0, max_delay=0.0)

        def always_fail() -> bool:
            return False

        result = await mgr.attempt_reconnect(always_fail)
        assert result is False
        assert mgr.state == ReconnectionState.FAILED
        assert mgr.retry_count == 3
