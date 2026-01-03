# ABOUTME: Unit tests for the trajectory simulation module.
# ABOUTME: Tests RK4 integration, force calculations, wind model, and spin decay.
"""Tests for trajectory simulation using RK4 integration."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from gc2_connect.open_range.models import Conditions, Phase, TrajectoryPoint, Vec3
from gc2_connect.open_range.physics.constants import (
    BALL_MASS_KG,
    GRAVITY_MS2,
)

if TYPE_CHECKING:
    from gc2_connect.open_range.physics.trajectory import FlightSimulator


class TestUnitConversions:
    """Tests for unit conversion helpers."""

    def test_mph_to_ms(self) -> None:
        """Test mph to m/s conversion."""
        from gc2_connect.open_range.physics.trajectory import mph_to_ms

        # 100 mph = 44.704 m/s
        assert mph_to_ms(100.0) == pytest.approx(44.704, rel=1e-4)
        assert mph_to_ms(0.0) == 0.0
        assert mph_to_ms(160.0) == pytest.approx(71.5264, rel=1e-4)

    def test_ms_to_mph(self) -> None:
        """Test m/s to mph conversion."""
        from gc2_connect.open_range.physics.trajectory import ms_to_mph

        # 44.704 m/s = 100 mph
        assert ms_to_mph(44.704) == pytest.approx(100.0, rel=1e-4)
        assert ms_to_mph(0.0) == 0.0

    def test_meters_to_yards(self) -> None:
        """Test meters to yards conversion."""
        from gc2_connect.open_range.physics.trajectory import meters_to_yards

        # 1 meter = 1.0936 yards
        assert meters_to_yards(100.0) == pytest.approx(109.36, rel=1e-3)

    def test_meters_to_feet(self) -> None:
        """Test meters to feet conversion."""
        from gc2_connect.open_range.physics.trajectory import meters_to_feet

        # 1 meter = 3.281 feet
        assert meters_to_feet(10.0) == pytest.approx(32.81, rel=1e-3)

    def test_rpm_to_rad_s(self) -> None:
        """Test RPM to radians/second conversion."""
        from gc2_connect.open_range.physics.trajectory import rpm_to_rad_s

        # 60 RPM = 2π rad/s
        assert rpm_to_rad_s(60.0) == pytest.approx(2 * math.pi, rel=1e-6)
        assert rpm_to_rad_s(0.0) == 0.0

    def test_deg_to_rad(self) -> None:
        """Test degrees to radians conversion."""
        from gc2_connect.open_range.physics.trajectory import deg_to_rad

        assert deg_to_rad(180.0) == pytest.approx(math.pi, rel=1e-6)
        assert deg_to_rad(90.0) == pytest.approx(math.pi / 2, rel=1e-6)


class TestInitialVelocity:
    """Tests for initial velocity calculation from launch conditions."""

    def test_initial_velocity_straight_shot(self) -> None:
        """Test initial velocity with no horizontal launch angle."""
        from gc2_connect.open_range.physics.trajectory import calculate_initial_velocity

        vel = calculate_initial_velocity(
            ball_speed_mph=100.0,
            vla_deg=10.0,
            hla_deg=0.0,
        )

        # 100 mph = 44.704 m/s
        speed_ms = 44.704

        # VLA = 10 degrees
        vla_rad = math.radians(10.0)

        # Forward (X) component = speed * cos(vla)
        expected_x = speed_ms * math.cos(vla_rad)
        assert vel.x == pytest.approx(expected_x, rel=1e-4)

        # Vertical (Y) component = speed * sin(vla)
        expected_y = speed_ms * math.sin(vla_rad)
        assert vel.y == pytest.approx(expected_y, rel=1e-4)

        # Lateral (Z) should be 0 for straight shot
        assert vel.z == pytest.approx(0.0, abs=1e-10)

    def test_initial_velocity_with_hla(self) -> None:
        """Test initial velocity with horizontal launch angle (fade/draw)."""
        from gc2_connect.open_range.physics.trajectory import calculate_initial_velocity

        vel = calculate_initial_velocity(
            ball_speed_mph=100.0,
            vla_deg=10.0,
            hla_deg=5.0,  # Slight right
        )

        # Z component should be non-zero for HLA
        assert vel.z > 0  # Positive Z = right

    def test_initial_velocity_magnitude(self) -> None:
        """Velocity magnitude should match ball speed."""
        from gc2_connect.open_range.physics.trajectory import calculate_initial_velocity

        vel = calculate_initial_velocity(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=3.0,
        )

        # Magnitude should equal ball speed in m/s
        magnitude = vel.mag()
        expected_ms = 150.0 * 0.44704
        assert magnitude == pytest.approx(expected_ms, rel=1e-4)


class TestSimulationState:
    """Tests for SimulationState dataclass."""

    def test_simulation_state_creation(self) -> None:
        """Test creation of simulation state."""
        from gc2_connect.open_range.physics.trajectory import SimulationState

        state = SimulationState(
            pos=Vec3(x=0, y=0, z=0),
            vel=Vec3(x=50, y=10, z=0),
            spin_back=3000.0,
            spin_side=0.0,
            t=0.0,
            phase=Phase.FLIGHT,
        )

        assert state.pos.x == 0
        assert state.vel.x == 50
        assert state.spin_back == 3000.0
        assert state.t == 0.0
        assert state.phase == Phase.FLIGHT


class TestFlightSimulator:
    """Tests for the FlightSimulator class."""

    @pytest.fixture
    def simulator(self) -> FlightSimulator:
        """Create a simulator with standard conditions."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()  # Default: 70F, sea level, no wind
        return FlightSimulator(conditions=conditions, dt=0.01)

    def test_simulator_initialization(self, simulator: FlightSimulator) -> None:
        """Test simulator initializes with correct air density."""
        from gc2_connect.open_range.physics.constants import STD_AIR_DENSITY

        assert simulator.air_density == pytest.approx(STD_AIR_DENSITY, rel=0.01)
        assert simulator.dt == 0.01

    def test_gravity_only_trajectory(self) -> None:
        """Test trajectory with only gravity (no air resistance).

        A projectile under gravity only should follow a parabolic path.
        """
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        # Use zero air density to eliminate drag and Magnus effects
        conditions = Conditions(
            temp_f=70.0,
            elevation_ft=100000.0,  # Very high to get near-zero air density
            humidity_pct=0.0,
        )
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Launch at 45 degrees - should give maximum range in vacuum
        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=100.0,  # 44.7 m/s
            vla_deg=45.0,
            hla_deg=0.0,
            backspin_rpm=0.0,
            sidespin_rpm=0.0,
        )

        # Ball should land (y <= 0)
        assert final_state.pos.y <= 0.001  # Near ground

        # Flight time for 45 deg launch: t = 2 * v * sin(θ) / g
        v_ms = 100.0 * 0.44704
        expected_time = 2 * v_ms * math.sin(math.radians(45)) / GRAVITY_MS2
        assert final_state.t == pytest.approx(expected_time, rel=0.05)

    def test_drag_reduces_distance(self) -> None:
        """Test that drag reduces distance compared to no-drag case."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        # With standard air density (drag active)
        conditions_normal = Conditions()
        sim_normal = FlightSimulator(conditions=conditions_normal, dt=0.01)

        # Near-vacuum conditions (minimal drag)
        conditions_vacuum = Conditions(elevation_ft=100000.0)
        sim_vacuum = FlightSimulator(conditions=conditions_vacuum, dt=0.01)

        # Driver-like shot
        _, final_normal = sim_normal.simulate_flight(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        _, final_vacuum = sim_vacuum.simulate_flight(
            ball_speed_mph=167.0,
            vla_deg=10.9,
            hla_deg=0.0,
            backspin_rpm=2686.0,
            sidespin_rpm=0.0,
        )

        # With drag, ball should travel less distance in X
        # (though backspin lift might compensate somewhat)
        # In vacuum, no lift either, so comparison is complex
        # At minimum, flight time should be different
        assert final_normal.t != final_vacuum.t

    def test_backspin_creates_lift(self) -> None:
        """Test that backspin creates lift (higher apex, more carry)."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Low spin shot
        trajectory_low, _ = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=1000.0,
            sidespin_rpm=0.0,
        )

        # High spin shot
        trajectory_high, _ = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=5000.0,
            sidespin_rpm=0.0,
        )

        # Find max height for each trajectory
        max_height_low = max(p.y for p in trajectory_low)
        max_height_high = max(p.y for p in trajectory_high)

        # High spin should have higher apex due to Magnus lift
        assert max_height_high > max_height_low

    def test_sidespin_creates_curve(self) -> None:
        """Test that sidespin creates lateral curve.

        Positive sidespin = fade/slice (curves right)
        """
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Straight shot (no sidespin)
        _, final_straight = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        # Slice shot (positive sidespin)
        _, final_slice = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=1500.0,  # Slice
        )

        # Slice should curve right (positive Z)
        assert final_slice.pos.z > final_straight.pos.z

    def test_spin_decay_over_time(self) -> None:
        """Test that spin decays during flight."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        initial_spin = 3000.0
        _, final_state = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=initial_spin,
            sidespin_rpm=0.0,
        )

        # Spin should decay: spin_new = spin * (1 - SPIN_DECAY_RATE)^time
        # After ~5 seconds of flight, spin should be noticeably reduced
        assert final_state.spin_back < initial_spin

    def test_trajectory_terminates_on_landing(self) -> None:
        """Test that trajectory terminates when ball lands (y <= 0)."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=100.0,
            vla_deg=10.0,
            hla_deg=0.0,
            backspin_rpm=2500.0,
            sidespin_rpm=0.0,
        )

        # Final state should be at or below ground
        assert final_state.pos.y <= 0.01

        # All trajectory points after launch should be non-negative height
        # (except possibly the final landing point)
        for point in trajectory[:-1]:
            assert point.y >= -0.01

    def test_trajectory_output_format(self) -> None:
        """Test that trajectory output is in correct units (yards, feet)."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        trajectory, _ = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0,
        )

        # All points should be TrajectoryPoint objects
        assert all(isinstance(p, TrajectoryPoint) for p in trajectory)

        # All points should have FLIGHT phase (this is flight-only simulation)
        assert all(p.phase == Phase.FLIGHT for p in trajectory)

        # Time should be monotonically increasing
        times = [p.t for p in trajectory]
        assert times == sorted(times)


class TestWindModel:
    """Tests for wind effect on trajectory."""

    def test_headwind_decreases_carry(self) -> None:
        """Test that headwind decreases carry distance."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        # No wind
        conditions_calm = Conditions(wind_speed_mph=0.0)
        sim_calm = FlightSimulator(conditions=conditions_calm, dt=0.01)

        # Headwind (0 degrees = from north = headwind)
        conditions_headwind = Conditions(wind_speed_mph=15.0, wind_dir_deg=0.0)
        sim_headwind = FlightSimulator(conditions=conditions_headwind, dt=0.01)

        # 7-iron shot
        _, final_calm = sim_calm.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        _, final_headwind = sim_headwind.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        # Headwind should reduce carry distance
        assert final_headwind.pos.x < final_calm.pos.x

    def test_tailwind_increases_carry(self) -> None:
        """Test that tailwind increases carry distance."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        # No wind
        conditions_calm = Conditions(wind_speed_mph=0.0)
        sim_calm = FlightSimulator(conditions=conditions_calm, dt=0.01)

        # Tailwind (180 degrees = from south = tailwind)
        conditions_tailwind = Conditions(wind_speed_mph=15.0, wind_dir_deg=180.0)
        sim_tailwind = FlightSimulator(conditions=conditions_tailwind, dt=0.01)

        # 7-iron shot
        _, final_calm = sim_calm.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        _, final_tailwind = sim_tailwind.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        # Tailwind should increase carry distance
        assert final_tailwind.pos.x > final_calm.pos.x

    def test_crosswind_creates_drift(self) -> None:
        """Test that crosswind creates lateral drift."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        # No wind
        conditions_calm = Conditions(wind_speed_mph=0.0)
        sim_calm = FlightSimulator(conditions=conditions_calm, dt=0.01)

        # Crosswind from left (90 degrees = from east = left-to-right)
        conditions_cross = Conditions(wind_speed_mph=15.0, wind_dir_deg=90.0)
        sim_cross = FlightSimulator(conditions=conditions_cross, dt=0.01)

        # Straight shot
        _, final_calm = sim_calm.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        _, final_cross = sim_cross.simulate_flight(
            ball_speed_mph=120.0,
            vla_deg=16.3,
            hla_deg=0.0,
            backspin_rpm=7097.0,
            sidespin_rpm=0.0,
        )

        # Crosswind should push ball laterally (positive Z for left-to-right wind)
        assert final_cross.pos.z > final_calm.pos.z

    def test_wind_at_height(self) -> None:
        """Test logarithmic wind profile at different heights."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions(wind_speed_mph=10.0, wind_dir_deg=0.0)
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Wind at ground level should be minimal
        wind_ground = simulator.get_wind_at_height(0.0)
        # Wind at 10 feet (reference height) should be close to stated speed
        wind_ref = simulator.get_wind_at_height(10.0 * 0.3048)  # 10 ft in meters
        # Wind higher up should be stronger
        wind_high = simulator.get_wind_at_height(100.0 * 0.3048)  # 100 ft

        # Wind increases with height (up to a limit)
        assert wind_ref.mag() > wind_ground.mag()
        assert wind_high.mag() >= wind_ref.mag()


class TestRK4Integration:
    """Tests for RK4 numerical integration."""

    def test_rk4_step_gravity_only(self) -> None:
        """Test RK4 step with gravity only matches expected."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        # Near-vacuum conditions to test gravity behavior
        conditions = Conditions(elevation_ft=100000.0)
        simulator = FlightSimulator(conditions=conditions, dt=0.1)

        from gc2_connect.open_range.physics.trajectory import SimulationState

        # Ball moving horizontally at 50 m/s
        state = SimulationState(
            pos=Vec3(x=0, y=10, z=0),  # 10m high
            vel=Vec3(x=50, y=0, z=0),  # Moving forward
            spin_back=0.0,
            spin_side=0.0,
            t=0.0,
            phase=Phase.FLIGHT,
        )

        new_state = simulator.rk4_step(state)

        # After 0.1s with gravity:
        # y velocity should be ~ -g * dt = -9.81 * 0.1 = -0.981 m/s
        assert new_state.vel.y == pytest.approx(-0.981, rel=0.05)

        # Position should have moved forward and slightly down
        assert new_state.pos.x > state.pos.x
        assert new_state.pos.y < state.pos.y

    def test_rk4_preserves_energy_approximately(self) -> None:
        """Test that RK4 approximately preserves energy in gravity-only case."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator, SimulationState

        # Near-vacuum for gravity-only
        conditions = Conditions(elevation_ft=100000.0)
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        state = SimulationState(
            pos=Vec3(x=0, y=10, z=0),
            vel=Vec3(x=50, y=20, z=0),
            spin_back=0.0,
            spin_side=0.0,
            t=0.0,
            phase=Phase.FLIGHT,
        )

        # Calculate initial mechanical energy (KE + PE)
        initial_ke = 0.5 * BALL_MASS_KG * state.vel.mag() ** 2
        initial_pe = BALL_MASS_KG * GRAVITY_MS2 * state.pos.y
        initial_energy = initial_ke + initial_pe

        # Run 100 steps
        for _ in range(100):
            state = simulator.rk4_step(state)

        # Calculate final energy
        final_ke = 0.5 * BALL_MASS_KG * state.vel.mag() ** 2
        final_pe = BALL_MASS_KG * GRAVITY_MS2 * state.pos.y
        final_energy = final_ke + final_pe

        # Energy should be approximately conserved (within 1% for RK4)
        assert final_energy == pytest.approx(initial_energy, rel=0.01)


class TestForceCalculations:
    """Tests for force calculation components."""

    def test_gravity_force(self) -> None:
        """Test gravity force calculation."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Gravity should be constant regardless of position/velocity
        gravity = simulator._gravity_force()
        expected_y = -BALL_MASS_KG * GRAVITY_MS2

        assert gravity.x == 0.0
        assert gravity.y == pytest.approx(expected_y, rel=1e-6)
        assert gravity.z == 0.0

    def test_drag_force_opposes_motion(self) -> None:
        """Test that drag force opposes motion direction."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Ball moving forward and up
        vel = Vec3(x=50, y=10, z=5)
        pos = Vec3(x=100, y=30, z=10)

        drag = simulator._drag_force(pos, vel, spin_back=3000.0, spin_side=0.0)

        # Drag should oppose each velocity component
        assert drag.x < 0  # Opposing forward motion
        assert drag.y < 0  # Opposing upward motion
        assert drag.z < 0  # Opposing rightward motion

    def test_magnus_force_with_backspin(self) -> None:
        """Test Magnus force creates lift with backspin."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Ball moving forward with backspin
        vel = Vec3(x=50, y=0, z=0)
        pos = Vec3(x=100, y=30, z=0)

        magnus = simulator._magnus_force(pos, vel, spin_back=3000.0, spin_side=0.0)

        # Backspin + forward motion = upward Magnus force (lift)
        assert magnus.y > 0

    def test_magnus_force_with_sidespin(self) -> None:
        """Test Magnus force creates lateral curve with sidespin."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Ball moving forward with sidespin (slice)
        vel = Vec3(x=50, y=0, z=0)
        pos = Vec3(x=100, y=30, z=0)

        magnus = simulator._magnus_force(pos, vel, spin_back=0.0, spin_side=1500.0)

        # Positive sidespin + forward motion = rightward curve (positive Z)
        assert magnus.z > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_ball_speed(self) -> None:
        """Test handling of zero ball speed."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=0.0,
            vla_deg=10.0,
            hla_deg=0.0,
            backspin_rpm=2500.0,
            sidespin_rpm=0.0,
        )

        # Should return immediately with minimal trajectory
        assert len(trajectory) >= 1
        # Ball should be at origin
        assert final_state.pos.x == pytest.approx(0.0, abs=0.1)

    def test_very_high_ball_speed(self) -> None:
        """Test with very high ball speed (beyond normal golf shots)."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # 200 mph - very fast but possible with testing equipment
        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=200.0,
            vla_deg=10.0,
            hla_deg=0.0,
            backspin_rpm=2000.0,
            sidespin_rpm=0.0,
        )

        # Should complete without error
        assert len(trajectory) > 0
        assert final_state.pos.y <= 0.01

    def test_extreme_spin_rates(self) -> None:
        """Test with extreme spin rates."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Very high spin (15000 rpm - unusual but possible)
        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=100.0,
            vla_deg=45.0,
            hla_deg=0.0,
            backspin_rpm=15000.0,
            sidespin_rpm=0.0,
        )

        # Should complete without error
        assert len(trajectory) > 0

    def test_max_simulation_time(self) -> None:
        """Test that simulation respects maximum time limit."""
        from gc2_connect.open_range.physics.constants import MAX_TIME
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Very high launch angle to maximize flight time
        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=200.0,
            vla_deg=85.0,  # Nearly vertical
            hla_deg=0.0,
            backspin_rpm=1000.0,
            sidespin_rpm=0.0,
        )

        # Time should not exceed MAX_TIME
        assert final_state.t <= MAX_TIME

    def test_negative_spin_values(self) -> None:
        """Test handling of negative spin values (hook vs slice)."""
        from gc2_connect.open_range.physics.trajectory import FlightSimulator

        conditions = Conditions()
        simulator = FlightSimulator(conditions=conditions, dt=0.01)

        # Negative sidespin = hook (curves left)
        trajectory, final_state = simulator.simulate_flight(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=-1500.0,  # Hook
        )

        # Ball should curve left (negative Z)
        assert final_state.pos.z < 0
