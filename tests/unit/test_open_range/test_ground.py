# ABOUTME: Unit tests for ground physics module (bounce and roll).
# ABOUTME: Tests bounce physics, roll deceleration, and surface types.
"""Tests for ground physics (bounce and roll behavior)."""

from __future__ import annotations

import pytest

from gc2_connect.open_range.models import Phase, Vec3
from gc2_connect.open_range.physics.constants import (
    SURFACES,
)


class TestGroundSurfaceProperties:
    """Tests for ground surface property definitions."""

    def test_fairway_surface_exists(self) -> None:
        """Test that Fairway surface is defined."""
        assert "Fairway" in SURFACES
        fairway = SURFACES["Fairway"]
        assert fairway.name == "Fairway"
        assert fairway.cor == 0.60
        assert fairway.rolling_resistance == 0.10
        assert fairway.friction == 0.50

    def test_green_surface_exists(self) -> None:
        """Test that Green surface is defined."""
        assert "Green" in SURFACES
        green = SURFACES["Green"]
        assert green.name == "Green"
        assert green.cor == 0.40
        assert green.rolling_resistance == 0.05
        assert green.friction == 0.30

    def test_rough_surface_exists(self) -> None:
        """Test that Rough surface is defined."""
        assert "Rough" in SURFACES
        rough = SURFACES["Rough"]
        assert rough.name == "Rough"
        assert rough.cor == 0.30
        assert rough.rolling_resistance == 0.30
        assert rough.friction == 0.70


class TestGroundPhysicsInitialization:
    """Tests for GroundPhysics class initialization."""

    def test_default_surface_is_fairway(self) -> None:
        """Test that default surface is Fairway."""
        from gc2_connect.open_range.physics.ground import GroundPhysics

        ground = GroundPhysics()
        assert ground.surface.name == "Fairway"

    def test_can_specify_surface(self) -> None:
        """Test that surface can be specified at initialization."""
        from gc2_connect.open_range.physics.ground import GroundPhysics

        ground = GroundPhysics(surface_name="Green")
        assert ground.surface.name == "Green"

    def test_unknown_surface_raises_error(self) -> None:
        """Test that unknown surface raises KeyError."""
        from gc2_connect.open_range.physics.ground import GroundPhysics

        with pytest.raises(KeyError):
            GroundPhysics(surface_name="Unknown")


class TestBouncePhysics:
    """Tests for bounce physics."""

    def test_bounce_reduces_vertical_velocity_by_cor(self) -> None:
        """Test that bounce reduces vertical velocity by COR."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")  # COR = 0.60

        # Ball coming down at 10 m/s vertically
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=20, y=-10, z=0),  # Moving forward and down
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state = ground.bounce(state)

        # Vertical velocity should reverse and be reduced by COR
        # -(-10) * 0.60 = 6 m/s upward
        assert new_state.vel.y == pytest.approx(6.0, rel=0.1)

    def test_bounce_reduces_tangential_velocity_by_friction(self) -> None:
        """Test that bounce reduces tangential velocity by friction."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")  # Friction = 0.50

        # Ball coming down at angle
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=20, y=-10, z=5),
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state = ground.bounce(state)

        # Tangential velocity (X, Z components) should be reduced
        # Using friction factor 0.3: vt_new = vt * (1 - friction * 0.3)
        # = vt * (1 - 0.50 * 0.3) = vt * 0.85
        expected_x = 20 * 0.85
        expected_z = 5 * 0.85
        assert new_state.vel.x == pytest.approx(expected_x, rel=0.1)
        assert new_state.vel.z == pytest.approx(expected_z, rel=0.1)

    def test_bounce_on_green_has_lower_cor(self) -> None:
        """Test that bouncing on green has lower COR than fairway."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground_fairway = GroundPhysics(surface_name="Fairway")  # COR = 0.60
        ground_green = GroundPhysics(surface_name="Green")  # COR = 0.40

        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=10, y=-10, z=0),
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state_fairway = ground_fairway.bounce(state)
        new_state_green = ground_green.bounce(state)

        # Green should have lower bounce height (lower COR)
        assert new_state_green.vel.y < new_state_fairway.vel.y

    def test_bounce_on_rough_has_lowest_cor(self) -> None:
        """Test that bouncing on rough has lowest COR."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground_rough = GroundPhysics(surface_name="Rough")  # COR = 0.30

        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=10, y=-10, z=0),
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state = ground_rough.bounce(state)

        # Rough COR = 0.30, so vertical velocity should be 3 m/s
        assert new_state.vel.y == pytest.approx(3.0, rel=0.1)

    def test_bounce_reduces_spin(self) -> None:
        """Test that spin is reduced on bounce."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        initial_spin = 3000.0
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=10, y=-10, z=0),
            spin_back=initial_spin,
            spin_side=500.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state = ground.bounce(state)

        # Spin should be reduced by 30% (multiplied by 0.7)
        assert new_state.spin_back == pytest.approx(initial_spin * 0.7, rel=0.01)
        assert new_state.spin_side == pytest.approx(500.0 * 0.7, rel=0.01)

    def test_bounce_ensures_ball_above_ground(self) -> None:
        """Test that ball position is set slightly above ground after bounce."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        # Ball at ground level
        state = SimulationState(
            pos=Vec3(x=100, y=-0.5, z=0),  # Slightly below ground
            vel=Vec3(x=10, y=-5, z=0),
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state = ground.bounce(state)

        # Ball should be set to just above ground
        assert new_state.pos.y >= 0.0
        assert new_state.pos.y <= 0.01  # Small positive value

    def test_steep_impact_angle_retains_less_forward_momentum(self) -> None:
        """Test that steep impact angle retains less forward momentum."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        # Steep impact (more vertical)
        state_steep = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=5, y=-20, z=0),  # Mostly vertical
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        # Shallow impact (more horizontal)
        state_shallow = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=20, y=-5, z=0),  # Mostly horizontal
            spin_back=2000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_steep = ground.bounce(state_steep)
        new_shallow = ground.bounce(state_shallow)

        # Shallow impact should retain more forward (X) velocity
        # because it has more tangential velocity to start with
        assert new_shallow.vel.x > new_steep.vel.x


class TestRollPhysics:
    """Tests for roll physics."""

    def test_roll_decelerates_on_fairway(self) -> None:
        """Test that rolling ball decelerates on fairway."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")  # resistance = 0.10

        # Ball rolling at 5 m/s
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=5, y=0, z=0),
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_state = ground.roll_step(state, dt=0.1)

        # Speed should decrease
        new_speed = new_state.vel.mag()
        assert new_speed < 5.0

    def test_roll_decelerates_more_on_rough(self) -> None:
        """Test that rolling ball decelerates more on rough."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground_fairway = GroundPhysics(surface_name="Fairway")  # resistance = 0.10
        ground_rough = GroundPhysics(surface_name="Rough")  # resistance = 0.30

        initial_speed = 5.0
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=initial_speed, y=0, z=0),
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_fairway = ground_fairway.roll_step(state, dt=0.1)
        new_rough = ground_rough.roll_step(state, dt=0.1)

        # Rough should decelerate more (lower speed after same time)
        assert new_rough.vel.mag() < new_fairway.vel.mag()

    def test_roll_decelerates_less_on_green(self) -> None:
        """Test that rolling ball decelerates less on green."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground_fairway = GroundPhysics(surface_name="Fairway")  # resistance = 0.10
        ground_green = GroundPhysics(surface_name="Green")  # resistance = 0.05

        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=5, y=0, z=0),
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_fairway = ground_fairway.roll_step(state, dt=0.1)
        new_green = ground_green.roll_step(state, dt=0.1)

        # Green should decelerate less (higher speed after same time)
        assert new_green.vel.mag() > new_fairway.vel.mag()

    def test_roll_stops_below_threshold(self) -> None:
        """Test that ball stops when speed drops below threshold."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        # Ball moving very slowly (below threshold)
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=0.05, y=0, z=0),  # Below STOPPED_THRESHOLD (0.1 m/s)
            spin_back=100.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_state = ground.roll_step(state, dt=0.1)

        # Ball should be stopped
        assert new_state.phase == Phase.STOPPED
        assert new_state.vel.mag() == 0.0

    def test_roll_updates_position(self) -> None:
        """Test that roll updates position based on velocity."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=10, y=0, z=2),  # Moving forward and right
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_state = ground.roll_step(state, dt=0.1)

        # Position should increase (ball moved forward)
        assert new_state.pos.x > state.pos.x
        assert new_state.pos.z > state.pos.z

    def test_roll_keeps_ball_on_ground(self) -> None:
        """Test that roll keeps ball on ground (y=0)."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        state = SimulationState(
            pos=Vec3(x=100, y=0.5, z=0),  # Slightly above ground (shouldn't happen but...)
            vel=Vec3(x=10, y=0, z=0),
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_state = ground.roll_step(state, dt=0.1)

        # Ball should be on ground
        assert new_state.pos.y == 0.0

    def test_roll_decays_spin(self) -> None:
        """Test that spin decays during roll."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        initial_spin = 1000.0
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=10, y=0, z=0),
            spin_back=initial_spin,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_state = ground.roll_step(state, dt=0.1)

        # Spin should decay (multiplied by 1 - 0.1 * dt)
        expected_spin = initial_spin * (1 - 0.1 * 0.1)
        assert new_state.spin_back == pytest.approx(expected_spin, rel=0.01)

    def test_roll_step_returns_rolling_phase(self) -> None:
        """Test that roll_step returns ROLLING phase when still moving."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=10, y=0, z=0),
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        new_state = ground.roll_step(state, dt=0.1)

        # Should still be rolling
        assert new_state.phase == Phase.ROLLING

    def test_roll_velocity_goes_to_zero_eventually(self) -> None:
        """Test that ball eventually stops after enough roll steps."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=5, y=0, z=0),
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        # Run many roll steps
        for _ in range(500):  # Should be more than enough
            state = ground.roll_step(state, dt=0.1)
            if state.phase == Phase.STOPPED:
                break

        # Ball should have stopped
        assert state.phase == Phase.STOPPED
        assert state.vel.mag() == 0.0


class TestShouldContinueBouncing:
    """Tests for bounce continuation logic."""

    def test_high_vertical_velocity_continues_bouncing(self) -> None:
        """Test that high vertical velocity continues bouncing."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        state = SimulationState(
            pos=Vec3(x=100, y=0.001, z=0),
            vel=Vec3(x=10, y=5, z=0),  # High vertical velocity
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.BOUNCE,
        )

        assert ground.should_continue_bouncing(state) is True

    def test_low_vertical_velocity_stops_bouncing(self) -> None:
        """Test that low vertical velocity stops bouncing (transitions to roll)."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        state = SimulationState(
            pos=Vec3(x=100, y=0.001, z=0),
            vel=Vec3(x=10, y=0.3, z=0),  # Low vertical velocity
            spin_back=1000.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.BOUNCE,
        )

        assert ground.should_continue_bouncing(state) is False


class TestRealisticBehaviors:
    """Tests for realistic golf ball ground behaviors."""

    def test_driver_landing_bounces_and_rolls(self) -> None:
        """Test that driver landing at typical angle bounces and rolls."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        # Driver typically lands at 40-50 degree angle
        # Velocity magnitude ~25-30 m/s at landing
        # Approximate: Vx=20, Vy=-20 (45 degree angle)
        state = SimulationState(
            pos=Vec3(x=200, y=0, z=0),
            vel=Vec3(x=20, y=-20, z=0),
            spin_back=2000.0,
            spin_side=0.0,
            t=6.0,
            phase=Phase.FLIGHT,
        )

        # After bounce, ball should still have significant velocity
        new_state = ground.bounce(state)
        assert new_state.vel.y > 1.0  # Still bouncing up
        assert new_state.vel.x > 5.0  # Still moving forward

    def test_wedge_landing_has_less_roll(self) -> None:
        """Test that wedge shot landing steep has less roll potential."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground = GroundPhysics(surface_name="Fairway")

        # Wedge lands steeper (60-70 degree angle)
        # More vertical, less horizontal velocity
        state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=5, y=-15, z=0),  # Steep landing
            spin_back=8000.0,  # High spin on wedge
            spin_side=0.0,
            t=5.0,
            phase=Phase.FLIGHT,
        )

        new_state = ground.bounce(state)

        # After bounce, forward velocity should be relatively low
        assert new_state.vel.x < 10.0

    def test_ball_on_green_rolls_farther_than_rough(self) -> None:
        """Test that ball on green rolls farther than on rough."""
        from gc2_connect.open_range.physics.ground import GroundPhysics
        from gc2_connect.open_range.physics.trajectory import SimulationState

        ground_green = GroundPhysics(surface_name="Green")
        ground_rough = GroundPhysics(surface_name="Rough")

        initial_state = SimulationState(
            pos=Vec3(x=100, y=0, z=0),
            vel=Vec3(x=5, y=0, z=0),
            spin_back=500.0,
            spin_side=0.0,
            t=5.0,
            phase=Phase.ROLLING,
        )

        # Simulate until stopped
        state_green = initial_state
        state_rough = initial_state

        for _ in range(200):
            state_green = ground_green.roll_step(state_green, dt=0.1)
            state_rough = ground_rough.roll_step(state_rough, dt=0.1)
            if state_green.phase == Phase.STOPPED and state_rough.phase == Phase.STOPPED:
                break

        # Green should roll farther
        assert state_green.pos.x > state_rough.pos.x
