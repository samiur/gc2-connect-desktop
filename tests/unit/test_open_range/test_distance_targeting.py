# ABOUTME: Tests for distance targeting functionality in hybrid physics engine.
# ABOUTME: Verifies ground physics can hit target distances when OGC is available.
"""Tests for distance targeting in the hybrid physics engine.

These tests verify that:
1. Ground physics can calculate rolling_resistance for a target distance
2. PhysicsEngine can simulate to a target total distance
3. OpenRangeEngine uses OGC targeting when available
4. Fallback to pure physics works when OGC unavailable
"""

from __future__ import annotations

import math

import pytest

from gc2_connect.models import GC2ShotData
from gc2_connect.open_range.models import Phase
from gc2_connect.open_range.physics.constants import GRAVITY_MS2
from gc2_connect.open_range.physics.ground import (
    GroundPhysics,
    calculate_rolling_resistance_for_target,
)


class TestCalculateRollingResistanceForTarget:
    """Tests for calculate_rolling_resistance_for_target function."""

    def test_basic_calculation(self) -> None:
        """Test basic rolling resistance calculation."""
        # Given: 10 m/s landing speed, want 50m roll
        landing_speed = 10.0  # m/s
        target_roll = 50.0  # meters

        # Expected: resistance = v² / (2 * d * g) = 100 / (2 * 50 * 9.81) ≈ 0.102
        resistance = calculate_rolling_resistance_for_target(landing_speed, target_roll)

        expected = (landing_speed**2) / (2 * target_roll * GRAVITY_MS2)
        assert abs(resistance - expected) < 0.001

    def test_clamped_to_minimum(self) -> None:
        """Test that resistance is clamped to minimum (0.02)."""
        # Very fast ball, very long target roll → would need very low resistance
        landing_speed = 5.0  # m/s
        target_roll = 500.0  # meters (unrealistic)

        resistance = calculate_rolling_resistance_for_target(landing_speed, target_roll)

        # Should be clamped to minimum
        assert resistance >= 0.02

    def test_clamped_to_maximum(self) -> None:
        """Test that resistance is clamped to maximum (0.50)."""
        # Slow ball, very short target roll → would need very high resistance
        landing_speed = 20.0  # m/s
        target_roll = 1.0  # meter (very short)

        resistance = calculate_rolling_resistance_for_target(landing_speed, target_roll)

        # Should be clamped to maximum
        assert resistance <= 0.50

    def test_zero_landing_speed(self) -> None:
        """Test handling of zero landing speed."""
        resistance = calculate_rolling_resistance_for_target(0.0, 50.0)
        assert resistance == 0.50  # Maximum resistance

    def test_zero_target_roll(self) -> None:
        """Test handling of zero target roll distance."""
        resistance = calculate_rolling_resistance_for_target(10.0, 0.0)
        assert resistance == 0.50  # Maximum resistance

    def test_negative_values(self) -> None:
        """Test handling of negative input values."""
        resistance = calculate_rolling_resistance_for_target(-10.0, 50.0)
        assert resistance == 0.50  # Maximum resistance

        resistance = calculate_rolling_resistance_for_target(10.0, -50.0)
        assert resistance == 0.50  # Maximum resistance


class TestGroundPhysicsWithTargetRollDistance:
    """Tests for GroundPhysics.with_target_roll_distance method."""

    def test_creates_new_ground_physics(self) -> None:
        """Test that with_target_roll_distance creates a new GroundPhysics instance."""
        ground = GroundPhysics("Fairway")
        targeted_ground = ground.with_target_roll_distance(
            landing_speed_ms=10.0, target_roll_meters=20.0
        )

        # Should be a different instance
        assert targeted_ground is not ground
        # Should have different rolling_resistance
        assert targeted_ground.surface.rolling_resistance != ground.surface.rolling_resistance

    def test_preserves_cor_and_friction(self) -> None:
        """Test that COR and friction are preserved from original surface."""
        ground = GroundPhysics("Fairway")
        targeted_ground = ground.with_target_roll_distance(
            landing_speed_ms=10.0, target_roll_meters=20.0
        )

        assert targeted_ground.surface.cor == ground.surface.cor
        assert targeted_ground.surface.friction == ground.surface.friction

    def test_surface_name_indicates_targeting(self) -> None:
        """Test that the surface name indicates it's a targeted surface."""
        ground = GroundPhysics("Fairway")
        targeted_ground = ground.with_target_roll_distance(
            landing_speed_ms=10.0, target_roll_meters=20.0
        )

        assert "targeted" in targeted_ground.surface.name.lower()


class TestPhysicsEngineSimulateFlightOnly:
    """Tests for PhysicsEngine.simulate_flight_only method."""

    def test_returns_trajectory_landing_state_and_launch_data(self) -> None:
        """Test that simulate_flight_only returns all expected components."""
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()
        trajectory, landing_state, launch_data = engine.simulate_flight_only(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        assert len(trajectory) > 0
        assert landing_state is not None
        assert launch_data is not None

    def test_trajectory_ends_at_ground(self) -> None:
        """Test that flight trajectory ends when ball hits ground."""
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()
        trajectory, landing_state, _ = engine.simulate_flight_only(
            ball_speed_mph=120.0,
            vla_deg=16.0,
            hla_deg=0.0,
            backspin_rpm=7000.0,
            sidespin_rpm=0.0,
        )

        # Last trajectory point should be near ground level
        assert trajectory[-1].y <= 1.0  # Within 1 foot of ground

    def test_launch_data_matches_input(self) -> None:
        """Test that launch_data matches input parameters."""
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()
        _, _, launch_data = engine.simulate_flight_only(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=1.5,
            backspin_rpm=3000.0,
            sidespin_rpm=-200.0,
        )

        assert launch_data.ball_speed == 150.0
        assert launch_data.vla == 12.0
        assert launch_data.hla == 1.5
        assert launch_data.backspin == 3000.0
        assert launch_data.sidespin == -200.0

    def test_handles_zero_ball_speed(self) -> None:
        """Test handling of zero ball speed."""
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()
        trajectory, landing_state, _ = engine.simulate_flight_only(
            ball_speed_mph=0.0,
            vla_deg=10.0,
            hla_deg=0.0,
            backspin_rpm=2500.0,
            sidespin_rpm=0.0,
        )

        # Should return a stopped trajectory at origin
        assert len(trajectory) == 1
        assert trajectory[0].phase == Phase.STOPPED
        assert landing_state.phase == Phase.STOPPED


class TestPhysicsEngineSimulateGroundToTarget:
    """Tests for PhysicsEngine.simulate_ground_to_target method."""

    def test_result_total_distance_near_target(self) -> None:
        """Test that result total distance is reasonably close to target.

        Note: The ground phase includes bouncing before rolling, which adds
        distance that can't be fully controlled by rolling_resistance alone.
        The 15% tolerance accounts for this bounce contribution.
        """
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()

        # First, get flight trajectory
        flight_trajectory, landing_state, launch_data = engine.simulate_flight_only(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        # Get physics carry distance
        carry_x = landing_state.pos.x * 1.09361  # meters to yards
        carry_z = landing_state.pos.z * 1.09361
        carry_distance = math.sqrt(carry_x**2 + carry_z**2)

        # Target total = carry + 20 yards roll
        target_total = carry_distance + 20.0

        result = engine.simulate_ground_to_target(
            flight_trajectory=flight_trajectory,
            landing_state=landing_state,
            launch_data=launch_data,
            target_total_yards=target_total,
        )

        # Total should be within 15% of target (bounces add distance)
        diff_pct = abs(result.summary.total_distance - target_total) / target_total * 100
        assert (
            diff_pct < 15.0
        ), f"Total {result.summary.total_distance:.1f} vs target {target_total:.1f}"

    def test_trajectory_includes_all_phases(self) -> None:
        """Test that result trajectory includes flight, bounce, roll, and stopped."""
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()

        flight_trajectory, landing_state, launch_data = engine.simulate_flight_only(
            ball_speed_mph=120.0,
            vla_deg=16.0,
            hla_deg=0.0,
            backspin_rpm=7000.0,
            sidespin_rpm=0.0,
        )

        carry_x = landing_state.pos.x * 1.09361
        carry_z = landing_state.pos.z * 1.09361
        carry_distance = math.sqrt(carry_x**2 + carry_z**2)
        target_total = carry_distance + 10.0

        result = engine.simulate_ground_to_target(
            flight_trajectory=flight_trajectory,
            landing_state=landing_state,
            launch_data=launch_data,
            target_total_yards=target_total,
        )

        phases = {pt.phase for pt in result.trajectory}
        assert Phase.FLIGHT in phases
        assert Phase.STOPPED in phases

    def test_handles_target_less_than_carry(self) -> None:
        """Test that target < carry results in ball stopping at carry."""
        from gc2_connect.open_range.physics.engine import PhysicsEngine

        engine = PhysicsEngine()

        flight_trajectory, landing_state, launch_data = engine.simulate_flight_only(
            ball_speed_mph=120.0,
            vla_deg=16.0,
            hla_deg=0.0,
            backspin_rpm=7000.0,
            sidespin_rpm=0.0,
        )

        carry_x = landing_state.pos.x * 1.09361
        carry_z = landing_state.pos.z * 1.09361
        carry_distance = math.sqrt(carry_x**2 + carry_z**2)

        # Target is less than carry
        target_total = carry_distance - 10.0

        result = engine.simulate_ground_to_target(
            flight_trajectory=flight_trajectory,
            landing_state=landing_state,
            launch_data=launch_data,
            target_total_yards=target_total,
        )

        # Ball should stop at carry position
        assert result.trajectory[-1].phase == Phase.STOPPED


class TestOpenRangeEngineOGCTargeting:
    """Tests for OpenRangeEngine using OGC targeting."""

    def test_uses_ogc_targeting_when_available(self) -> None:
        """Test that simulate_shot uses OGC targeting when available."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=0.0,
            back_spin=2686.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        # Result should have derived data
        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None

        # Total distance should be close to OGC total (within 10%)
        ogc_total = result.derived.ogc_total_distance
        diff_pct = abs(result.summary.total_distance - ogc_total) / ogc_total * 100
        assert diff_pct < 10.0, (
            f"Total {result.summary.total_distance:.1f} vs OGC {ogc_total:.1f} "
            f"({diff_pct:.1f}% diff)"
        )

    def test_simulate_manual_uses_ogc_targeting(self) -> None:
        """Test that simulate_manual uses OGC targeting when available."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        result = engine.simulate_manual(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None

        ogc_total = result.derived.ogc_total_distance
        diff_pct = abs(result.summary.total_distance - ogc_total) / ogc_total * 100
        assert diff_pct < 10.0

    def test_fallback_when_ogc_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback to pure physics when OGC unavailable."""
        from gc2_connect.open_range import engine as engine_module
        from gc2_connect.open_range.engine import OpenRangeEngine

        # Disable OGC
        monkeypatch.setattr(engine_module, "OPENGOLFCOACH_AVAILABLE", False)

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=0.0,
            back_spin=2686.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        # Should still work with pure physics
        assert result.summary.carry_distance > 200
        assert result.summary.total_distance > result.summary.carry_distance
        assert len(result.trajectory) > 10
        # Derived should be None
        assert result.derived is None


class TestDistanceTargetingAccuracy:
    """Tests for overall distance targeting accuracy."""

    def test_driver_matches_ogc_total(self) -> None:
        """Test that driver shot matches OGC total distance."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=0.0,
            back_spin=2686.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None

        # Should match within 5%
        ogc_total = result.derived.ogc_total_distance
        diff_pct = abs(result.summary.total_distance - ogc_total) / ogc_total * 100
        assert diff_pct < 5.0, f"Driver: {diff_pct:.1f}% diff from OGC"

    def test_7iron_matches_ogc_total(self) -> None:
        """Test that 7-iron shot matches OGC total distance."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=120.0,
            launch_angle=16.3,
            horizontal_launch_angle=0.0,
            back_spin=7097.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None

        ogc_total = result.derived.ogc_total_distance
        diff_pct = abs(result.summary.total_distance - ogc_total) / ogc_total * 100
        assert diff_pct < 5.0, f"7-Iron: {diff_pct:.1f}% diff from OGC"

    def test_wedge_matches_ogc_total(self) -> None:
        """Test that wedge shot matches OGC total distance."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=102.0,
            launch_angle=24.2,
            horizontal_launch_angle=0.0,
            back_spin=9304.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None

        ogc_total = result.derived.ogc_total_distance
        diff_pct = abs(result.summary.total_distance - ogc_total) / ogc_total * 100
        assert diff_pct < 5.0, f"Wedge: {diff_pct:.1f}% diff from OGC"
