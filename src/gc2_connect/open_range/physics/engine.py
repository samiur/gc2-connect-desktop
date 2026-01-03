# ABOUTME: Complete golf ball physics engine integrating flight and ground phases.
# ABOUTME: Provides single simulate() method for full shot trajectory from launch to rest.
"""Complete golf ball physics engine integrating flight, bounce, and roll phases.

This module provides:
- PhysicsEngine: Complete simulation from launch to rest
- Integration of FlightSimulator and GroundPhysics components
- ShotSummary calculation from trajectory data

Based on:
- Professor Alan Nathan's trajectory calculator (UIUC)
- libgolf C++ reference implementation
- docs/PHYSICS.md specifications
"""

from __future__ import annotations

from gc2_connect.open_range.models import (
    Conditions,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
    TrajectoryPoint,
)
from gc2_connect.open_range.physics.constants import (
    DT,
    MAX_BOUNCES,
    MAX_ITERATIONS,
    MAX_TRAJECTORY_POINTS,
)
from gc2_connect.open_range.physics.ground import GroundPhysics
from gc2_connect.open_range.physics.trajectory import (
    FlightSimulator,
    SimulationState,
    meters_to_feet,
    meters_to_yards,
)


class PhysicsEngine:
    """Complete physics simulation from launch to rest.

    Integrates FlightSimulator and GroundPhysics to provide:
    - FLIGHT: RK4 integration of ball trajectory through air
    - BOUNCE: Ground impact with COR and friction
    - ROLLING: Deceleration until stopped
    - STOPPED: Final resting position

    Example:
        engine = PhysicsEngine()
        result = engine.simulate(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=3000.0,
            sidespin_rpm=0.0
        )
        print(f"Carry: {result.summary.carry_distance:.1f} yards")
    """

    def __init__(
        self,
        conditions: Conditions | None = None,
        surface: str = "Fairway",
        dt: float = DT,
    ):
        """Initialize physics engine.

        Args:
            conditions: Environmental conditions (temperature, elevation, wind).
                       Defaults to standard conditions (70°F, sea level, no wind).
            surface: Ground surface type ("Fairway", "Green", "Rough").
                    Affects bounce and roll behavior.
            dt: Time step in seconds. Defaults to 0.01s (10ms).
        """
        self.conditions = conditions or Conditions()
        self.surface = surface
        self.dt = dt
        self.flight_sim = FlightSimulator(self.conditions, dt)
        self.ground = GroundPhysics(surface)

    def simulate(
        self,
        ball_speed_mph: float,
        vla_deg: float,
        hla_deg: float,
        backspin_rpm: float,
        sidespin_rpm: float,
    ) -> ShotResult:
        """Run complete simulation from launch to rest.

        Phases:
        1. FLIGHT: RK4 integration until ball hits ground (y <= 0)
        2. BOUNCE: Apply bounce physics, return to flight if speed > threshold
        3. ROLLING: Decelerate on ground until stopped
        4. STOPPED: Record final position

        Args:
            ball_speed_mph: Initial ball speed in mph.
            vla_deg: Vertical launch angle in degrees.
            hla_deg: Horizontal launch angle in degrees (+ = right).
            backspin_rpm: Backspin in RPM.
            sidespin_rpm: Sidespin in RPM (+ = slice/fade).

        Returns:
            ShotResult with full trajectory and summary metrics.
        """
        # Store launch data
        launch_data = LaunchData(
            ball_speed=ball_speed_mph,
            vla=vla_deg,
            hla=hla_deg,
            backspin=backspin_rpm,
            sidespin=sidespin_rpm,
        )

        # Handle edge case: zero or negative ball speed
        if ball_speed_mph <= 0:
            return self._create_stopped_result(launch_data)

        # Phase 1: Flight simulation
        flight_trajectory, landing_state = self.flight_sim.simulate_flight(
            ball_speed_mph=ball_speed_mph,
            vla_deg=vla_deg,
            hla_deg=hla_deg,
            backspin_rpm=backspin_rpm,
            sidespin_rpm=sidespin_rpm,
        )

        # Record carry position (first landing)
        carry_x = meters_to_yards(landing_state.pos.x)
        carry_z = meters_to_yards(landing_state.pos.z)
        flight_time = landing_state.t

        # Combined trajectory starts with flight
        trajectory: list[TrajectoryPoint] = list(flight_trajectory)

        # Phase 2 & 3: Bounce and roll
        state = landing_state
        bounce_count = 0
        iterations = 0
        sample_counter = 0
        sample_interval = max(1, int(0.05 / self.dt))  # Sample every 50ms for ground

        while state.phase != Phase.STOPPED and iterations < MAX_ITERATIONS:
            iterations += 1

            # Check if ball should bounce or roll
            if state.phase == Phase.FLIGHT or state.phase == Phase.BOUNCE:
                # Ball just landed - apply bounce
                if bounce_count < MAX_BOUNCES:
                    state = self.ground.bounce(state)
                    bounce_count += 1

                    # Add bounce point to trajectory
                    if len(trajectory) < MAX_TRAJECTORY_POINTS:
                        trajectory.append(
                            TrajectoryPoint(
                                t=state.t,
                                x=meters_to_yards(state.pos.x),
                                y=meters_to_feet(state.pos.y),
                                z=meters_to_yards(state.pos.z),
                                phase=Phase.BOUNCE,
                            )
                        )

                    # Check if should continue bouncing or transition to roll
                    if self.ground.should_continue_bouncing(state):
                        # Continue in flight (another bounce arc)
                        bounce_trajectory, bounce_landing = self.flight_sim.simulate_flight(
                            ball_speed_mph=state.vel.mag() / 0.44704,  # m/s to mph
                            vla_deg=self._calculate_launch_angle(state),
                            hla_deg=self._calculate_horizontal_angle(state),
                            backspin_rpm=state.spin_back,
                            sidespin_rpm=state.spin_side,
                        )

                        # Offset trajectory by current position
                        for pt in bounce_trajectory[1:]:  # Skip first (duplicate)
                            if len(trajectory) < MAX_TRAJECTORY_POINTS:
                                trajectory.append(
                                    TrajectoryPoint(
                                        t=state.t + pt.t,
                                        x=meters_to_yards(state.pos.x) + pt.x,
                                        y=pt.y,
                                        z=meters_to_yards(state.pos.z) + pt.z,
                                        phase=Phase.FLIGHT,
                                    )
                                )

                        # Update state to landing position
                        state = SimulationState(
                            pos=state.pos.add(bounce_landing.pos),
                            vel=bounce_landing.vel,
                            spin_back=bounce_landing.spin_back,
                            spin_side=bounce_landing.spin_side,
                            t=state.t + bounce_landing.t,
                            phase=Phase.FLIGHT,
                        )
                    else:
                        # Transition to rolling
                        state = SimulationState(
                            pos=state.pos,
                            vel=state.vel,
                            spin_back=state.spin_back,
                            spin_side=state.spin_side,
                            t=state.t,
                            phase=Phase.ROLLING,
                        )
                else:
                    # Max bounces reached, force roll
                    state = SimulationState(
                        pos=state.pos,
                        vel=state.vel,
                        spin_back=state.spin_back,
                        spin_side=state.spin_side,
                        t=state.t,
                        phase=Phase.ROLLING,
                    )

            elif state.phase == Phase.ROLLING:
                # Roll step
                state = self.ground.roll_step(state, self.dt)
                sample_counter += 1

                # Sample trajectory periodically during roll
                if sample_counter >= sample_interval and len(trajectory) < MAX_TRAJECTORY_POINTS:
                    trajectory.append(
                        TrajectoryPoint(
                            t=state.t,
                            x=meters_to_yards(state.pos.x),
                            y=meters_to_feet(state.pos.y),
                            z=meters_to_yards(state.pos.z),
                            phase=Phase.ROLLING,
                        )
                    )
                    sample_counter = 0

        # Add final stopped point
        if state.phase == Phase.STOPPED:
            trajectory.append(
                TrajectoryPoint(
                    t=state.t,
                    x=meters_to_yards(state.pos.x),
                    y=0.0,
                    z=meters_to_yards(state.pos.z),
                    phase=Phase.STOPPED,
                )
            )

        # Calculate summary
        summary = self._calculate_summary(
            trajectory=trajectory,
            carry_x=carry_x,
            carry_z=carry_z,
            flight_time=flight_time,
            total_time=state.t,
            bounce_count=bounce_count,
        )

        return ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=self.conditions,
        )

    def _calculate_launch_angle(self, state: SimulationState) -> float:
        """Calculate vertical launch angle from velocity vector.

        Args:
            state: Current simulation state.

        Returns:
            Vertical angle in degrees.
        """
        import math

        horizontal_speed = math.sqrt(state.vel.x * state.vel.x + state.vel.z * state.vel.z)
        if horizontal_speed < 0.01:
            return 90.0 if state.vel.y > 0 else -90.0
        return math.degrees(math.atan2(state.vel.y, horizontal_speed))

    def _calculate_horizontal_angle(self, state: SimulationState) -> float:
        """Calculate horizontal launch angle from velocity vector.

        Args:
            state: Current simulation state.

        Returns:
            Horizontal angle in degrees (+ = right).
        """
        import math

        if abs(state.vel.x) < 0.01:
            return 90.0 if state.vel.z > 0 else -90.0
        return math.degrees(math.atan2(state.vel.z, state.vel.x))

    def _calculate_summary(
        self,
        trajectory: list[TrajectoryPoint],
        carry_x: float,
        carry_z: float,
        flight_time: float,
        total_time: float,
        bounce_count: int,
    ) -> ShotSummary:
        """Calculate shot summary from trajectory data.

        Args:
            trajectory: List of trajectory points.
            carry_x: X position at first landing (yards).
            carry_z: Z position at first landing (yards).
            flight_time: Time to first landing (seconds).
            total_time: Total time to stop (seconds).
            bounce_count: Number of bounces.

        Returns:
            ShotSummary with all metrics.
        """
        import math

        if not trajectory:
            return ShotSummary()

        # Find max height and time to apex
        max_height = 0.0
        max_height_time = 0.0
        for pt in trajectory:
            if pt.y > max_height:
                max_height = pt.y
                max_height_time = pt.t

        # Final position
        final_point = trajectory[-1]
        total_x = final_point.x
        total_z = final_point.z

        # Calculate distances
        carry_distance = math.sqrt(carry_x * carry_x + carry_z * carry_z)
        total_distance = math.sqrt(total_x * total_x + total_z * total_z)
        roll_distance = total_distance - carry_distance

        # Offline is just the Z component (lateral distance)
        offline_distance = total_z

        return ShotSummary(
            carry_distance=carry_distance,
            total_distance=total_distance,
            roll_distance=roll_distance,
            offline_distance=offline_distance,
            max_height=max_height,
            max_height_time=max_height_time,
            flight_time=flight_time,
            total_time=total_time,
            bounce_count=bounce_count,
        )

    def _create_stopped_result(self, launch_data: LaunchData) -> ShotResult:
        """Create a result for zero/negative ball speed (duff).

        Args:
            launch_data: Original launch conditions.

        Returns:
            ShotResult with ball at origin, stopped.
        """
        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.STOPPED)
        ]
        summary = ShotSummary(
            carry_distance=0.0,
            total_distance=0.0,
            roll_distance=0.0,
            offline_distance=0.0,
            max_height=0.0,
            max_height_time=0.0,
            flight_time=0.0,
            total_time=0.0,
            bounce_count=0,
        )
        return ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=self.conditions,
        )
