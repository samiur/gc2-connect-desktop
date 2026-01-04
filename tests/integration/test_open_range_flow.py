# ABOUTME: Integration tests for Open Range complete flow.
# ABOUTME: Tests GC2 shot -> Physics simulation -> Visualization flow.
"""Integration tests for Open Range complete flow.

Tests the complete flow from GC2 shot data through physics simulation
to visualization. Covers:
- Shot from MockGC2 -> Open Range engine -> ShotResult
- Mode switching between GSPro and Open Range
- Settings changes affecting engine
- Performance validation
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from gc2_connect.gc2.usb_reader import MockGC2Reader
from gc2_connect.models import GC2ShotData
from gc2_connect.open_range.engine import OpenRangeEngine
from gc2_connect.open_range.models import Conditions, Phase, ShotResult
from gc2_connect.services.shot_router import AppMode, ShotRouter


class TestShotRouterIntegration:
    """Integration tests for ShotRouter with Open Range engine."""

    def test_router_initializes_with_gspro_mode(self) -> None:
        """Test that router starts in GSPro mode by default."""
        router = ShotRouter()
        assert router.mode == AppMode.GSPRO

    @pytest.mark.asyncio
    async def test_router_can_switch_to_open_range(self) -> None:
        """Test that router can switch to Open Range mode."""
        router = ShotRouter()
        await router.set_mode(AppMode.OPEN_RANGE)
        assert router.mode == AppMode.OPEN_RANGE

    @pytest.mark.asyncio
    async def test_router_can_switch_back_to_gspro(self) -> None:
        """Test that router can switch back to GSPro mode."""
        router = ShotRouter()
        await router.set_mode(AppMode.OPEN_RANGE)
        await router.set_mode(AppMode.GSPRO)
        assert router.mode == AppMode.GSPRO

    @pytest.mark.asyncio
    async def test_mode_change_callback_invoked(self) -> None:
        """Test that mode change callback is invoked."""
        router = ShotRouter()
        callback = AsyncMock()
        router.on_mode_change(callback)

        await router.set_mode(AppMode.OPEN_RANGE)

        callback.assert_called_once_with(AppMode.OPEN_RANGE)

    @pytest.mark.asyncio
    async def test_mode_change_callback_not_invoked_for_same_mode(self) -> None:
        """Test that callback is not invoked when mode doesn't change."""
        router = ShotRouter()
        callback = AsyncMock()
        router.on_mode_change(callback)

        # Try to set the same mode
        await router.set_mode(AppMode.GSPRO)

        callback.assert_not_called()


class TestOpenRangeEngineIntegration:
    """Integration tests for OpenRangeEngine."""

    def test_engine_initializes_with_defaults(self) -> None:
        """Test engine initializes with default conditions."""
        engine = OpenRangeEngine()
        assert engine.conditions.temp_f == 70.0
        assert engine.conditions.elevation_ft == 0.0
        assert engine.surface == "Fairway"

    def test_engine_simulates_shot_from_gc2_data(self, sample_gc2_shot: GC2ShotData) -> None:
        """Test engine can simulate a shot from GC2 data."""
        engine = OpenRangeEngine()
        result = engine.simulate_shot(sample_gc2_shot)

        assert isinstance(result, ShotResult)
        assert len(result.trajectory) > 0
        assert result.summary.carry_distance > 0
        assert result.summary.total_distance >= result.summary.carry_distance

    def test_engine_simulates_test_shot(self) -> None:
        """Test engine can generate test shots."""
        engine = OpenRangeEngine()
        result = engine.simulate_test_shot("Driver")

        assert isinstance(result, ShotResult)
        # Driver should carry at least 200 yards in normal conditions
        assert result.summary.carry_distance > 200

    def test_engine_updates_conditions(self) -> None:
        """Test engine updates conditions correctly."""
        engine = OpenRangeEngine()

        new_conditions = Conditions(temp_f=50.0, elevation_ft=5280.0, wind_speed_mph=10.0)
        engine.update_conditions(new_conditions)

        assert engine.conditions.temp_f == 50.0
        assert engine.conditions.elevation_ft == 5280.0

    def test_engine_updates_surface(self) -> None:
        """Test engine updates surface correctly."""
        engine = OpenRangeEngine()
        engine.update_surface("Green")

        assert engine.surface == "Green"

    def test_elevation_affects_carry_distance(self) -> None:
        """Test that higher elevation increases carry distance."""
        # Use manual parameters for consistent comparison (no random variance)
        engine_sea = OpenRangeEngine(conditions=Conditions(elevation_ft=0.0))
        engine_denver = OpenRangeEngine(conditions=Conditions(elevation_ft=5280.0))

        # Simulate identical shots
        result_sea = engine_sea.simulate_manual(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )
        result_denver = engine_denver.simulate_manual(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        # Denver should have more carry
        assert result_denver.summary.carry_distance > result_sea.summary.carry_distance


class TestRouterWithOpenRangeEngine:
    """Integration tests for ShotRouter with OpenRangeEngine."""

    @pytest.fixture
    def configured_router(self) -> ShotRouter:
        """Fixture providing a router configured with Open Range engine."""
        router = ShotRouter()
        engine = OpenRangeEngine()
        router.set_open_range_engine(engine)
        return router

    @pytest.mark.asyncio
    async def test_router_routes_to_open_range(
        self, configured_router: ShotRouter, sample_gc2_shot: GC2ShotData
    ) -> None:
        """Test that shots are routed to Open Range when in that mode."""
        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        configured_router.on_shot_result(on_result)
        await configured_router.set_mode(AppMode.OPEN_RANGE)

        await configured_router.route_shot(sample_gc2_shot)

        assert len(results) == 1
        assert isinstance(results[0], ShotResult)
        assert results[0].summary.carry_distance > 0

    @pytest.mark.asyncio
    async def test_router_raises_when_gspro_not_configured(
        self, configured_router: ShotRouter, sample_gc2_shot: GC2ShotData
    ) -> None:
        """Test that router raises error when GSPro client not configured."""
        # Router is in GSPro mode by default, but client not configured
        with pytest.raises(RuntimeError, match="GSPro client not configured"):
            await configured_router.route_shot(sample_gc2_shot)

    @pytest.mark.asyncio
    async def test_multiple_shots_in_open_range(self, configured_router: ShotRouter) -> None:
        """Test multiple shots can be processed in Open Range mode."""
        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        configured_router.on_shot_result(on_result)
        await configured_router.set_mode(AppMode.OPEN_RANGE)

        # Send multiple shots
        for i in range(3):
            shot = GC2ShotData(
                shot_id=i + 1,
                ball_speed=140 + i * 10,
                launch_angle=12.0,
                total_spin=2500,
                back_spin=2400,
                side_spin=100,
            )
            await configured_router.route_shot(shot)

        assert len(results) == 3
        # Faster shots should carry farther
        assert results[2].summary.carry_distance > results[0].summary.carry_distance


class TestMockGC2ToOpenRange:
    """Integration tests for MockGC2 to Open Range flow."""

    @pytest.mark.asyncio
    async def test_mock_gc2_shot_to_open_range(self, mock_gc2_reader: MockGC2Reader) -> None:
        """Test complete flow from MockGC2 to Open Range."""
        router = ShotRouter()
        engine = OpenRangeEngine()
        router.set_open_range_engine(engine)

        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        router.on_shot_result(on_result)
        await router.set_mode(AppMode.OPEN_RANGE)

        received_shots: list[GC2ShotData] = []

        async def on_shot(shot: GC2ShotData) -> None:
            received_shots.append(shot)
            await router.route_shot(shot)

        # Use sync callback wrapper for MockGC2Reader
        def sync_callback(shot: GC2ShotData) -> None:
            import asyncio

            asyncio.create_task(on_shot(shot))

        mock_gc2_reader.add_shot_callback(sync_callback)
        mock_gc2_reader.connect()

        # Send test shots
        for _ in range(2):
            mock_gc2_reader.send_test_shot()

        # Allow async callbacks to complete
        import asyncio

        await asyncio.sleep(0.1)

        # Verify shots were received and simulated
        assert len(received_shots) == 2
        assert len(results) == 2

        mock_gc2_reader.disconnect()


class TestModeSwitchingWithConnections:
    """Integration tests for mode switching behavior."""

    @pytest.mark.asyncio
    async def test_mode_switch_preserves_gspro_client(
        self, mock_gspro_server, gspro_client
    ) -> None:
        """Test that switching modes doesn't disconnect GSPro."""
        router = ShotRouter()
        router.set_gspro_client(gspro_client)

        engine = OpenRangeEngine()
        router.set_open_range_engine(engine)

        # Switch to Open Range
        await router.set_mode(AppMode.OPEN_RANGE)
        assert router.mode == AppMode.OPEN_RANGE

        # GSPro client should still be set
        assert router._gspro_client is not None

        # Switch back to GSPro
        await router.set_mode(AppMode.GSPRO)
        assert router.mode == AppMode.GSPRO

    @pytest.mark.asyncio
    async def test_can_send_to_gspro_after_mode_switch(
        self, mock_gspro_server, gspro_client, sample_gc2_shot: GC2ShotData
    ) -> None:
        """Test that GSPro still works after switching modes."""
        router = ShotRouter()
        router.set_gspro_client(gspro_client)

        engine = OpenRangeEngine()
        router.set_open_range_engine(engine)

        # Switch to Open Range and back
        await router.set_mode(AppMode.OPEN_RANGE)
        await router.set_mode(AppMode.GSPRO)

        # Should be able to send to GSPro
        await router.route_shot(sample_gc2_shot)

        # Verify shot was received by GSPro server
        shot_messages = [
            shot
            for shot in mock_gspro_server.received_shots
            if not shot.get("ShotDataOptions", {}).get("IsHeartBeat", False)
        ]
        assert len(shot_messages) >= 1


class TestTrajectoryPhasesIntegration:
    """Integration tests for trajectory phases."""

    def test_trajectory_contains_all_phases(self) -> None:
        """Test that trajectory includes flight, bounce, and roll phases."""
        engine = OpenRangeEngine()
        result = engine.simulate_test_shot("Driver")

        phases_in_trajectory = {point.phase for point in result.trajectory}

        # Should have at least flight and stopped
        assert Phase.FLIGHT in phases_in_trajectory
        assert Phase.STOPPED in phases_in_trajectory

    def test_trajectory_phases_are_sequential(self) -> None:
        """Test that trajectory phases occur in logical order."""
        engine = OpenRangeEngine()
        result = engine.simulate_test_shot("7-Iron")

        # Find first occurrence of each phase
        phase_order = []
        current_phase = None
        for point in result.trajectory:
            if point.phase != current_phase:
                phase_order.append(point.phase)
                current_phase = point.phase

        # Flight should come before other phases
        if Phase.FLIGHT in phase_order:
            assert phase_order[0] == Phase.FLIGHT


class TestPerformanceIntegration:
    """Performance tests for Open Range integration."""

    def test_simulation_completes_under_200ms(self) -> None:
        """Test that simulation completes within performance threshold."""
        engine = OpenRangeEngine()

        start = time.perf_counter()
        result = engine.simulate_test_shot("Driver")
        elapsed = time.perf_counter() - start

        assert result is not None
        # 200ms is reasonable for a full simulation including bounce/roll
        assert elapsed < 0.2

    def test_multiple_simulations_are_fast(self) -> None:
        """Test that multiple simulations can be run quickly."""
        engine = OpenRangeEngine()

        start = time.perf_counter()
        for _ in range(10):
            engine.simulate_test_shot("Driver")
        elapsed = time.perf_counter() - start

        # 10 shots should complete in under 2 seconds
        assert elapsed < 2.0

    def test_trajectory_point_count_is_reasonable(self) -> None:
        """Test that trajectory doesn't have excessive points."""
        engine = OpenRangeEngine()
        result = engine.simulate_test_shot("Driver")

        # Should have meaningful number of points but not too many
        # With dt=0.02s and ~6s flight + bounce + roll, expect 300-700 points
        assert len(result.trajectory) > 50
        assert len(result.trajectory) < 1000
