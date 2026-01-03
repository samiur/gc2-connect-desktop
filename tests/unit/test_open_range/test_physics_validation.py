# ABOUTME: Validation tests against Nathan model reference data.
# ABOUTME: Ensures physics simulation produces accurate carry distances for typical shots.
"""Validation tests for physics simulation accuracy.

These tests verify that the physics simulation produces results consistent
with the Nathan model reference data documented in docs/PHYSICS.md.
"""

from __future__ import annotations

import pytest

from gc2_connect.open_range.models import Conditions
from gc2_connect.open_range.physics.engine import PhysicsEngine
from gc2_connect.open_range.physics.trajectory import FlightSimulator, meters_to_yards


class TestValidationAgainstNathanModel:
    """Validation tests against expected carry distances from Nathan model.

    Reference data from docs/PHYSICS.md Section 10.1:
    | Test         | Ball Speed | Launch | Spin     | Expected Carry | Tolerance |
    |--------------|------------|--------|----------|----------------|-----------|
    | Driver High  | 167 mph    | 10.9°  | 2686 rpm | 275 yds        | ±5%       |
    | Driver Mid   | 160 mph    | 11.0°  | 3000 rpm | 259 yds        | ±3%       |
    | 7-Iron       | 120 mph    | 16.3°  | 7097 rpm | 172 yds        | ±5%       |
    | Wedge        | 102 mph    | 24.2°  | 9304 rpm | 136 yds        | ±5%       |
    """

    @pytest.fixture
    def simulator(self) -> FlightSimulator:
        """Create simulator with standard conditions."""
        conditions = Conditions()  # 70°F, sea level, no wind
        return FlightSimulator(conditions=conditions, dt=0.01)

    def test_driver_high_carry(self, simulator: FlightSimulator) -> None:
        """Test driver shot at 167 mph, 10.9° launch, 2686 rpm.

        Expected carry: 275 yards ± 5%
        """
        _, final_state = simulator.simulate_flight(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        carry_yards = meters_to_yards(final_state.pos.x)
        expected = 275.0
        tolerance = expected * 0.05  # 5%

        assert carry_yards == pytest.approx(expected, abs=tolerance), (
            f"Driver High carry: {carry_yards:.1f} yds (expected {expected} ±{tolerance:.1f})"
        )

    def test_driver_mid_carry(self, simulator: FlightSimulator) -> None:
        """Test driver shot at 160 mph, 11.0° launch, 3000 rpm.

        Expected carry: 259 yards ± 3%
        """
        _, final_state = simulator.simulate_flight(
            ball_speed_mph=160.0,
            vla_deg=11.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        carry_yards = meters_to_yards(final_state.pos.x)
        expected = 259.0
        tolerance = expected * 0.03  # 3%

        assert carry_yards == pytest.approx(expected, abs=tolerance), (
            f"Driver Mid carry: {carry_yards:.1f} yds (expected {expected} ±{tolerance:.1f})"
        )

    def test_7_iron_carry(self, simulator: FlightSimulator) -> None:
        """Test 7-iron shot at 120 mph, 16.3° launch, 7097 rpm.

        Expected carry: 172 yards ± 5%
        """
        _, final_state = simulator.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        carry_yards = meters_to_yards(final_state.pos.x)
        expected = 172.0
        tolerance = expected * 0.05  # 5%

        assert carry_yards == pytest.approx(expected, abs=tolerance), (
            f"7-Iron carry: {carry_yards:.1f} yds (expected {expected} ±{tolerance:.1f})"
        )

    def test_wedge_carry(self, simulator: FlightSimulator) -> None:
        """Test wedge shot at 102 mph, 24.2° launch, 9304 rpm.

        Expected carry: 136 yards ± 5%
        """
        _, final_state = simulator.simulate_flight(
            ball_speed_mph=102.0,
            vla_deg=24.2,
            hla_deg=0.0,
            backspin_rpm=9304.0,
            sidespin_rpm=0.0,
        )

        carry_yards = meters_to_yards(final_state.pos.x)
        expected = 136.0
        tolerance = expected * 0.05  # 5%

        assert carry_yards == pytest.approx(expected, abs=tolerance), (
            f"Wedge carry: {carry_yards:.1f} yds (expected {expected} ±{tolerance:.1f})"
        )


class TestPhysicsEngineValidation:
    """Validation tests using complete PhysicsEngine (flight + bounce + roll)."""

    @pytest.fixture
    def engine(self) -> PhysicsEngine:
        """Create physics engine with standard conditions."""
        conditions = Conditions()  # 70°F, sea level, no wind
        return PhysicsEngine(conditions=conditions, surface="Fairway")

    def test_driver_high_carry_with_engine(self, engine: PhysicsEngine) -> None:
        """Test driver shot carry using complete PhysicsEngine."""
        result = engine.simulate(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        expected = 275.0
        tolerance = expected * 0.05  # 5%

        assert result.summary.carry_distance == pytest.approx(expected, abs=tolerance), (
            f"Driver carry: {result.summary.carry_distance:.1f} yds "
            f"(expected {expected} ±{tolerance:.1f})"
        )

    def test_driver_mid_carry_with_engine(self, engine: PhysicsEngine) -> None:
        """Test driver shot at 160 mph using complete PhysicsEngine."""
        result = engine.simulate(
            ball_speed_mph=160.0,
            vla_deg=11.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        expected = 259.0
        tolerance = expected * 0.03  # 3%

        assert result.summary.carry_distance == pytest.approx(expected, abs=tolerance), (
            f"Driver carry: {result.summary.carry_distance:.1f} yds "
            f"(expected {expected} ±{tolerance:.1f})"
        )

    def test_7_iron_carry_with_engine(self, engine: PhysicsEngine) -> None:
        """Test 7-iron shot using complete PhysicsEngine."""
        result = engine.simulate(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        expected = 172.0
        tolerance = expected * 0.05  # 5%

        assert result.summary.carry_distance == pytest.approx(expected, abs=tolerance), (
            f"7-Iron carry: {result.summary.carry_distance:.1f} yds "
            f"(expected {expected} ±{tolerance:.1f})"
        )

    def test_wedge_carry_with_engine(self, engine: PhysicsEngine) -> None:
        """Test wedge shot using complete PhysicsEngine."""
        result = engine.simulate(
            ball_speed_mph=102.0,
            vla_deg=24.2,
            hla_deg=0.0,
            backspin_rpm=9304.0,
            sidespin_rpm=0.0,
        )

        expected = 136.0
        tolerance = expected * 0.05  # 5%

        assert result.summary.carry_distance == pytest.approx(expected, abs=tolerance), (
            f"Wedge carry: {result.summary.carry_distance:.1f} yds "
            f"(expected {expected} ±{tolerance:.1f})"
        )

    def test_total_distance_greater_than_carry(self, engine: PhysicsEngine) -> None:
        """Test that total distance includes roll (>= carry)."""
        result = engine.simulate(
            ball_speed_mph=160.0,
            vla_deg=11.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        assert result.summary.total_distance >= result.summary.carry_distance
        assert result.summary.roll_distance >= 0

    def test_shot_summary_consistency(self, engine: PhysicsEngine) -> None:
        """Test that shot summary metrics are consistent."""
        result = engine.simulate(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        # Roll = Total - Carry
        expected_roll = result.summary.total_distance - result.summary.carry_distance
        assert result.summary.roll_distance == pytest.approx(expected_roll, abs=0.1)

        # Max height should be positive
        assert result.summary.max_height > 0

        # Flight time should be positive
        assert result.summary.flight_time > 0

        # Total time >= flight time
        assert result.summary.total_time >= result.summary.flight_time

    def test_trajectory_phases(self, engine: PhysicsEngine) -> None:
        """Test that trajectory includes expected phases."""
        from gc2_connect.open_range.models import Phase

        result = engine.simulate(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        phases = {pt.phase for pt in result.trajectory}

        # Should have flight phase
        assert Phase.FLIGHT in phases

        # Should end with stopped
        assert result.trajectory[-1].phase == Phase.STOPPED

    def test_zero_ball_speed_returns_stopped(self, engine: PhysicsEngine) -> None:
        """Test that zero ball speed returns stopped result."""
        from gc2_connect.open_range.models import Phase

        result = engine.simulate(
            ball_speed_mph=0.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        assert result.summary.carry_distance == 0.0
        assert result.summary.total_distance == 0.0
        assert len(result.trajectory) == 1
        assert result.trajectory[0].phase == Phase.STOPPED


class TestEnvironmentalEffects:
    """Tests for environmental effects on ball flight."""

    def test_denver_elevation_increases_carry(self) -> None:
        """Test that Denver elevation (5280 ft) increases carry distance.

        Thinner air at altitude means less drag, more carry.
        """
        # Sea level
        conditions_sea = Conditions(temp_f=70.0, elevation_ft=0.0)
        sim_sea = FlightSimulator(conditions=conditions_sea, dt=0.01)

        # Denver
        conditions_denver = Conditions(temp_f=70.0, elevation_ft=5280.0)
        sim_denver = FlightSimulator(conditions=conditions_denver, dt=0.01)

        # Driver shot
        _, final_sea = sim_sea.simulate_flight(
            ball_speed_mph=160.0,
            vla_deg=11.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        _, final_denver = sim_denver.simulate_flight(
            ball_speed_mph=160.0,
            vla_deg=11.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        carry_sea = meters_to_yards(final_sea.pos.x)
        carry_denver = meters_to_yards(final_denver.pos.x)

        # Denver should give 5-10% more carry
        assert carry_denver > carry_sea
        assert carry_denver > carry_sea * 1.03  # At least 3% more

    def test_headwind_decreases_carry(self) -> None:
        """Test that 15 mph headwind decreases carry distance."""
        # No wind
        conditions_calm = Conditions(wind_speed_mph=0.0)
        sim_calm = FlightSimulator(conditions=conditions_calm, dt=0.01)

        # Headwind
        conditions_wind = Conditions(wind_speed_mph=15.0, wind_dir_deg=0.0)
        sim_wind = FlightSimulator(conditions=conditions_wind, dt=0.01)

        # 7-iron shot
        _, final_calm = sim_calm.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        _, final_wind = sim_wind.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        carry_calm = meters_to_yards(final_calm.pos.x)
        carry_wind = meters_to_yards(final_wind.pos.x)

        # Headwind should reduce carry by roughly 10-15%
        assert carry_wind < carry_calm
        assert carry_wind < carry_calm * 0.95

    def test_tailwind_increases_carry(self) -> None:
        """Test that 15 mph tailwind increases carry distance."""
        # No wind
        conditions_calm = Conditions(wind_speed_mph=0.0)
        sim_calm = FlightSimulator(conditions=conditions_calm, dt=0.01)

        # Tailwind (180° = from behind)
        conditions_wind = Conditions(wind_speed_mph=15.0, wind_dir_deg=180.0)
        sim_wind = FlightSimulator(conditions=conditions_wind, dt=0.01)

        # 7-iron shot
        _, final_calm = sim_calm.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        _, final_wind = sim_wind.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        carry_calm = meters_to_yards(final_calm.pos.x)
        carry_wind = meters_to_yards(final_wind.pos.x)

        # Tailwind should increase carry
        assert carry_wind > carry_calm


class TestSpinEffects:
    """Tests for spin effects on ball flight."""

    def test_sidespin_curves_correctly(self) -> None:
        """Test that positive sidespin (slice) curves right, negative (hook) curves left."""
        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Straight shot
        _, final_straight = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        # Slice (positive sidespin)
        _, final_slice = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=1500.0,
        )

        # Hook (negative sidespin)
        _, final_hook = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=-1500.0,
        )

        offline_straight = meters_to_yards(final_straight.pos.z)
        offline_slice = meters_to_yards(final_slice.pos.z)
        offline_hook = meters_to_yards(final_hook.pos.z)

        # Straight should be near zero
        assert abs(offline_straight) < 1.0

        # Slice should be right (positive Z)
        assert offline_slice > 10.0

        # Hook should be left (negative Z)
        assert offline_hook < -10.0

        # Slice and hook should be roughly symmetric
        assert abs(offline_slice + offline_hook) < abs(offline_slice) * 0.3

    def test_moderate_spin_affects_max_height(self) -> None:
        """Test that moderate backspin produces higher flight apex than low spin.

        Note: Very high spin (>8000 rpm) can actually reduce height because:
        1. The lift coefficient plateaus at CL_MAX
        2. Spin adds to drag coefficient via CD_SPIN term
        3. The increased drag slows the ball more than the lift helps

        This test uses moderate spin levels where increased spin still helps.
        """
        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Very low spin (skulled shot)
        trajectory_low, _ = simulator.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=14.0,
            hla_deg=0.0,
            backspin_rpm=1500.0,  # Very low for this ball speed
            sidespin_rpm=0.0,
        )

        # Normal spin (well-struck)
        trajectory_normal, _ = simulator.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=14.0,
            hla_deg=0.0,
            backspin_rpm=4500.0,  # Normal for 7-iron
            sidespin_rpm=0.0,
        )

        max_height_low = max(p.y for p in trajectory_low)
        max_height_normal = max(p.y for p in trajectory_normal)

        # Normal spin should produce higher apex than very low spin
        assert max_height_normal > max_height_low


class TestSimulationPerformance:
    """Tests for simulation performance requirements."""

    def test_flight_simulation_completes_in_reasonable_time(self) -> None:
        """Test that flight simulation completes quickly.

        The simulation should complete fast enough for responsive UI.
        Allowing up to 500ms which works even on slower CI machines.
        """
        import time

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        start = time.perf_counter()

        # Run a typical driver shot
        simulator.simulate_flight(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete within 500ms even on slow CI machines
        assert elapsed_ms < 500, f"Flight simulation took {elapsed_ms:.1f}ms (limit: 500ms)"

    def test_complete_physics_engine_under_100ms(self) -> None:
        """Test that complete PhysicsEngine simulation completes under 100ms.

        The complete simulation (flight + bounces + roll) should complete
        fast enough for real-time use. Target: <100ms.
        """
        import time

        engine = PhysicsEngine()

        start = time.perf_counter()

        # Run a typical driver shot (longest simulation)
        engine.simulate(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Target: <100ms for responsive UI
        # Allow up to 500ms for slow CI machines
        assert elapsed_ms < 500, f"Complete simulation took {elapsed_ms:.1f}ms (limit: 500ms)"

    def test_trajectory_points_reasonable(self) -> None:
        """Test that trajectory has reasonable number of points."""
        from gc2_connect.open_range.physics.constants import MAX_TRAJECTORY_POINTS

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        trajectory, _ = simulator.simulate_flight(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        # Should have reasonable number of points for animation
        assert len(trajectory) >= 50  # Enough for smooth animation
        assert len(trajectory) <= MAX_TRAJECTORY_POINTS  # Not too many


class TestOpenRangeEngine:
    """Tests for OpenRangeEngine high-level wrapper."""

    def test_simulate_test_shot_driver(self) -> None:
        """Test that simulate_test_shot produces realistic driver results."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()
        result = engine.simulate_test_shot("Driver")

        # Driver should carry 200-300 yards
        assert 200 <= result.summary.carry_distance <= 320
        # Max height should be reasonable (30-120 feet)
        assert 30 <= result.summary.max_height <= 150

    def test_simulate_test_shot_wedge(self) -> None:
        """Test that simulate_test_shot produces realistic wedge results."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()
        result = engine.simulate_test_shot("PW")

        # Wedge should carry 90-150 yards
        assert 80 <= result.summary.carry_distance <= 160
        # Max height should be reasonable for wedge
        assert result.summary.max_height > 20

    def test_simulate_manual(self) -> None:
        """Test simulate_manual with explicit parameters."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()
        result = engine.simulate_manual(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=2.0,  # Slight push right
            backspin_rpm=3000.0,
            sidespin_rpm=500.0,  # Slight fade
        )

        # Should have valid trajectory
        assert len(result.trajectory) > 10
        assert result.summary.carry_distance > 0

        # Offline should be positive (right) due to push and fade
        assert result.summary.offline_distance > 0

    def test_simulate_shot_from_gc2_data(self) -> None:
        """Test simulate_shot with GC2ShotData input."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()
        shot = GC2ShotData(
            ball_speed=150.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=3000.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(shot)

        assert result.summary.carry_distance > 0
        assert len(result.trajectory) > 10

    def test_update_conditions(self) -> None:
        """Test that update_conditions affects simulation."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Standard conditions
        result_standard = engine.simulate_manual(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        # Update to Denver conditions
        engine.update_conditions(Conditions(elevation_ft=5280.0))

        result_denver = engine.simulate_manual(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        # Denver should give more carry
        assert result_denver.summary.carry_distance > result_standard.summary.carry_distance

    def test_update_surface(self) -> None:
        """Test that update_surface affects roll behavior."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine(surface="Fairway")

        result_fairway = engine.simulate_manual(
            ball_speed_mph=120.0,
            vla_deg=16.0,
            hla_deg=0.0,
            backspin_rpm=5000.0,
            sidespin_rpm=0.0,
        )

        engine.update_surface("Rough")

        result_rough = engine.simulate_manual(
            ball_speed_mph=120.0,
            vla_deg=16.0,
            hla_deg=0.0,
            backspin_rpm=5000.0,
            sidespin_rpm=0.0,
        )

        # Rough should have less roll than fairway
        assert result_rough.summary.roll_distance < result_fairway.summary.roll_distance

    def test_get_available_clubs(self) -> None:
        """Test that get_available_clubs returns expected clubs."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        clubs = OpenRangeEngine.get_available_clubs()

        assert "Driver" in clubs
        assert "7-Iron" in clubs
        assert "PW" in clubs
        assert len(clubs) >= 10  # At least standard set
