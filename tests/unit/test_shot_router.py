# ABOUTME: Unit tests for ShotRouter that routes shots between GSPro and Open Range.
# ABOUTME: Tests mode selection, shot routing, callbacks, and graceful mode switching.
"""Unit tests for the shot router module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from gc2_connect.models import GC2ShotData
from gc2_connect.services.shot_router import AppMode, ShotRouter


@pytest.fixture
def shot_router() -> ShotRouter:
    """Create a ShotRouter instance for testing."""
    return ShotRouter()


@pytest.fixture
def sample_shot() -> GC2ShotData:
    """Create a sample shot for testing."""
    return GC2ShotData(
        shot_id=1,
        ball_speed=145.0,
        launch_angle=12.0,
        horizontal_launch_angle=1.5,
        total_spin=2650,
        back_spin=2480,
        side_spin=-320,
    )


class TestAppModeEnum:
    """Tests for AppMode enum."""

    def test_gspro_mode_value(self) -> None:
        """Test GSPRO mode has correct value."""
        assert AppMode.GSPRO.value == "gspro"

    def test_open_range_mode_value(self) -> None:
        """Test OPEN_RANGE mode has correct value."""
        assert AppMode.OPEN_RANGE.value == "open_range"

    def test_mode_is_string_enum(self) -> None:
        """Test modes can be used as strings."""
        assert str(AppMode.GSPRO) == "AppMode.GSPRO"
        assert AppMode.GSPRO == "gspro"


class TestShotRouterInitialization:
    """Tests for ShotRouter initialization."""

    def test_default_mode_is_gspro(self, shot_router: ShotRouter) -> None:
        """Test that default mode is GSPro."""
        assert shot_router.mode == AppMode.GSPRO

    def test_gspro_client_initially_none(self, shot_router: ShotRouter) -> None:
        """Test that GSPro client is initially not set."""
        assert shot_router._gspro_client is None

    def test_open_range_engine_initially_none(self, shot_router: ShotRouter) -> None:
        """Test that Open Range engine is initially not set."""
        assert shot_router._open_range_engine is None

    def test_callbacks_initially_none(self, shot_router: ShotRouter) -> None:
        """Test that callbacks are initially not set."""
        assert shot_router._mode_change_callback is None
        assert shot_router._shot_result_callback is None


class TestModeSwitching:
    """Tests for mode switching functionality."""

    @pytest.mark.asyncio
    async def test_set_mode_to_open_range(self, shot_router: ShotRouter) -> None:
        """Test switching mode to Open Range."""
        await shot_router.set_mode(AppMode.OPEN_RANGE)
        assert shot_router.mode == AppMode.OPEN_RANGE

    @pytest.mark.asyncio
    async def test_set_mode_to_gspro(self, shot_router: ShotRouter) -> None:
        """Test switching mode to GSPro."""
        # First switch to open range
        await shot_router.set_mode(AppMode.OPEN_RANGE)
        # Then switch back to GSPro
        await shot_router.set_mode(AppMode.GSPRO)
        assert shot_router.mode == AppMode.GSPRO

    @pytest.mark.asyncio
    async def test_set_same_mode_is_noop(self, shot_router: ShotRouter) -> None:
        """Test that setting the same mode doesn't trigger callback."""
        callback = AsyncMock()
        shot_router.on_mode_change(callback)

        # Set to same mode
        await shot_router.set_mode(AppMode.GSPRO)

        # Callback should not be called
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_mode_change_callback_invoked(self, shot_router: ShotRouter) -> None:
        """Test that mode change callback is invoked on mode switch."""
        callback = AsyncMock()
        shot_router.on_mode_change(callback)

        await shot_router.set_mode(AppMode.OPEN_RANGE)

        callback.assert_called_once_with(AppMode.OPEN_RANGE)

    @pytest.mark.asyncio
    async def test_mode_change_callback_with_both_directions(self, shot_router: ShotRouter) -> None:
        """Test callback is invoked when switching in both directions."""
        callback = AsyncMock()
        shot_router.on_mode_change(callback)

        await shot_router.set_mode(AppMode.OPEN_RANGE)
        await shot_router.set_mode(AppMode.GSPRO)

        assert callback.call_count == 2
        callback.assert_any_call(AppMode.OPEN_RANGE)
        callback.assert_any_call(AppMode.GSPRO)


class TestClientConfiguration:
    """Tests for configuring clients/engines."""

    def test_set_gspro_client(self, shot_router: ShotRouter) -> None:
        """Test setting GSPro client."""
        mock_client = MagicMock()
        shot_router.set_gspro_client(mock_client)
        assert shot_router._gspro_client is mock_client

    def test_set_open_range_engine(self, shot_router: ShotRouter) -> None:
        """Test setting Open Range engine."""
        mock_engine = MagicMock()
        shot_router.set_open_range_engine(mock_engine)
        assert shot_router._open_range_engine is mock_engine

    def test_on_mode_change_registers_callback(self, shot_router: ShotRouter) -> None:
        """Test registering mode change callback."""
        callback = AsyncMock()
        shot_router.on_mode_change(callback)
        assert shot_router._mode_change_callback is callback

    def test_on_shot_result_registers_callback(self, shot_router: ShotRouter) -> None:
        """Test registering shot result callback."""
        callback = AsyncMock()
        shot_router.on_shot_result(callback)
        assert shot_router._shot_result_callback is callback


class TestShotRouting:
    """Tests for shot routing functionality."""

    @pytest.mark.asyncio
    async def test_route_shot_gspro_mode_calls_gspro(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that shots are routed to GSPro in GSPRO mode."""
        mock_client = MagicMock()
        mock_client.send_shot_async = AsyncMock()
        shot_router.set_gspro_client(mock_client)

        await shot_router.route_shot(sample_shot)

        mock_client.send_shot_async.assert_called_once_with(sample_shot)

    @pytest.mark.asyncio
    async def test_route_shot_open_range_mode_calls_engine(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that shots are routed to Open Range in OPEN_RANGE mode."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_engine.simulate_shot.return_value = mock_result
        shot_router.set_open_range_engine(mock_engine)

        await shot_router.set_mode(AppMode.OPEN_RANGE)
        await shot_router.route_shot(sample_shot)

        mock_engine.simulate_shot.assert_called_once_with(sample_shot)

    @pytest.mark.asyncio
    async def test_route_shot_open_range_invokes_result_callback(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that shot result callback is invoked in Open Range mode."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_engine.simulate_shot.return_value = mock_result
        shot_router.set_open_range_engine(mock_engine)

        result_callback = AsyncMock()
        shot_router.on_shot_result(result_callback)

        await shot_router.set_mode(AppMode.OPEN_RANGE)
        await shot_router.route_shot(sample_shot)

        result_callback.assert_called_once_with(mock_result)

    @pytest.mark.asyncio
    async def test_route_shot_gspro_no_client_raises(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that routing to GSPro without client raises error."""
        with pytest.raises(RuntimeError, match="GSPro client not configured"):
            await shot_router.route_shot(sample_shot)

    @pytest.mark.asyncio
    async def test_route_shot_open_range_no_engine_raises(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that routing to Open Range without engine raises error."""
        await shot_router.set_mode(AppMode.OPEN_RANGE)
        with pytest.raises(RuntimeError, match="Open Range engine not configured"):
            await shot_router.route_shot(sample_shot)


class TestGracefulModeTransitions:
    """Tests for graceful mode transitions."""

    @pytest.mark.asyncio
    async def test_gspro_connection_maintained_on_mode_switch(
        self, shot_router: ShotRouter
    ) -> None:
        """Test that GSPro connection stays open when switching to Open Range."""
        mock_client = MagicMock()
        mock_client.disconnect = MagicMock()
        mock_client.is_connected = True
        shot_router.set_gspro_client(mock_client)

        await shot_router.set_mode(AppMode.OPEN_RANGE)

        # GSPro client should NOT be disconnected
        mock_client.disconnect.assert_not_called()
        # Client should still be accessible
        assert shot_router._gspro_client is mock_client

    @pytest.mark.asyncio
    async def test_mode_switch_is_graceful_without_errors(self, shot_router: ShotRouter) -> None:
        """Test that mode switching doesn't raise errors."""
        # Switch multiple times - should not raise
        await shot_router.set_mode(AppMode.OPEN_RANGE)
        await shot_router.set_mode(AppMode.GSPRO)
        await shot_router.set_mode(AppMode.OPEN_RANGE)
        await shot_router.set_mode(AppMode.GSPRO)

        assert shot_router.mode == AppMode.GSPRO

    @pytest.mark.asyncio
    async def test_open_range_works_without_gspro_connection(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that Open Range works even without GSPro client configured."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_engine.simulate_shot.return_value = mock_result
        shot_router.set_open_range_engine(mock_engine)

        # No GSPro client configured, but Open Range should still work
        await shot_router.set_mode(AppMode.OPEN_RANGE)
        await shot_router.route_shot(sample_shot)

        mock_engine.simulate_shot.assert_called_once()


class TestShotCallbacks:
    """Tests for shot-related callbacks."""

    @pytest.mark.asyncio
    async def test_shot_result_callback_not_called_in_gspro_mode(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that shot result callback is not called in GSPro mode."""
        mock_client = MagicMock()
        mock_client.send_shot_async = AsyncMock()
        shot_router.set_gspro_client(mock_client)

        result_callback = AsyncMock()
        shot_router.on_shot_result(result_callback)

        await shot_router.route_shot(sample_shot)

        result_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_shot_result_callback_optional(
        self, shot_router: ShotRouter, sample_shot: GC2ShotData
    ) -> None:
        """Test that Open Range works without shot result callback."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_engine.simulate_shot.return_value = mock_result
        shot_router.set_open_range_engine(mock_engine)

        await shot_router.set_mode(AppMode.OPEN_RANGE)
        # No callback registered, should not raise
        await shot_router.route_shot(sample_shot)

        mock_engine.simulate_shot.assert_called_once()
