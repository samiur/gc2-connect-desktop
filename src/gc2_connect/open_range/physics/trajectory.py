# ABOUTME: Golf ball trajectory simulation using RK4 integration.
# ABOUTME: Implements Nathan model with drag, lift (Magnus), and wind effects.
"""Golf ball trajectory simulation using 4th-order Runge-Kutta integration.

This module provides:
- FlightSimulator: Simulates ball flight from launch to landing
- SimulationState: Tracks ball state during simulation
- Unit conversion utilities

Based on:
- Professor Alan Nathan's trajectory calculator (UIUC)
- libgolf C++ reference implementation
- WSU Golf Ball Aerodynamics research
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gc2_connect.open_range.models import Conditions, Phase, TrajectoryPoint, Vec3
from gc2_connect.open_range.physics.aerodynamics import (
    calculate_air_density,
    calculate_reynolds,
    get_drag_coefficient,
    get_lift_coefficient,
)
from gc2_connect.open_range.physics.constants import (
    BALL_AREA_M2,
    BALL_MASS_KG,
    BALL_RADIUS_M,
    DT,
    GRAVITY_MS2,
    MAX_ITERATIONS,
    MAX_TIME,
    MAX_TRAJECTORY_POINTS,
    SPIN_DECAY_RATE,
)

# =============================================================================
# Unit Conversion Utilities
# =============================================================================


def mph_to_ms(mph: float) -> float:
    """Convert miles per hour to meters per second."""
    return mph * 0.44704


def ms_to_mph(ms: float) -> float:
    """Convert meters per second to miles per hour."""
    return ms / 0.44704


def meters_to_yards(meters: float) -> float:
    """Convert meters to yards."""
    return meters / 0.9144


def yards_to_meters(yards: float) -> float:
    """Convert yards to meters."""
    return yards * 0.9144


def meters_to_feet(meters: float) -> float:
    """Convert meters to feet."""
    return meters / 0.3048


def feet_to_meters(feet: float) -> float:
    """Convert feet to meters."""
    return feet * 0.3048


def rpm_to_rad_s(rpm: float) -> float:
    """Convert revolutions per minute to radians per second."""
    return rpm * 2.0 * math.pi / 60.0


def rad_s_to_rpm(rad_s: float) -> float:
    """Convert radians per second to revolutions per minute."""
    return rad_s * 60.0 / (2.0 * math.pi)


def deg_to_rad(deg: float) -> float:
    """Convert degrees to radians."""
    return deg * math.pi / 180.0


def rad_to_deg(rad: float) -> float:
    """Convert radians to degrees."""
    return rad * 180.0 / math.pi


# =============================================================================
# Simulation State
# =============================================================================


@dataclass
class SimulationState:
    """Current state of ball during simulation.

    All positions and velocities are in SI units (meters, m/s).
    Spin values are in RPM for consistency with input.
    """

    pos: Vec3
    vel: Vec3
    spin_back: float  # RPM
    spin_side: float  # RPM
    t: float  # seconds
    phase: Phase


def calculate_initial_velocity(
    ball_speed_mph: float,
    vla_deg: float,
    hla_deg: float,
) -> Vec3:
    """Calculate initial velocity vector from launch conditions.

    Args:
        ball_speed_mph: Ball speed in mph.
        vla_deg: Vertical launch angle in degrees.
        hla_deg: Horizontal launch angle in degrees (+ = right).

    Returns:
        Initial velocity vector in m/s (Vec3).
    """
    speed_ms = mph_to_ms(ball_speed_mph)
    vla_rad = deg_to_rad(vla_deg)
    hla_rad = deg_to_rad(hla_deg)

    # First get horizontal and vertical components
    horizontal_speed = speed_ms * math.cos(vla_rad)
    vertical_speed = speed_ms * math.sin(vla_rad)

    # Then split horizontal into forward (X) and lateral (Z)
    forward_speed = horizontal_speed * math.cos(hla_rad)
    lateral_speed = horizontal_speed * math.sin(hla_rad)

    return Vec3(x=forward_speed, y=vertical_speed, z=lateral_speed)


# =============================================================================
# Flight Simulator
# =============================================================================


class FlightSimulator:
    """Simulates golf ball flight phase (before first ground contact).

    Uses 4th-order Runge-Kutta integration for accuracy.
    Accounts for:
    - Gravity
    - Aerodynamic drag (with drag crisis model)
    - Magnus force (lift from spin)
    - Wind (logarithmic profile with height)
    - Spin decay over time
    """

    def __init__(self, conditions: Conditions, dt: float = DT):
        """Initialize flight simulator.

        Args:
            conditions: Environmental conditions.
            dt: Time step in seconds (default 0.01s / 10ms).
        """
        self.conditions = conditions
        self.dt = dt
        self.air_density = calculate_air_density(
            temp_f=conditions.temp_f,
            elevation_ft=conditions.elevation_ft,
            humidity_pct=conditions.humidity_pct,
        )

    def get_wind_at_height(self, height_m: float) -> Vec3:
        """Get wind velocity at given height using logarithmic profile.

        Wind speed increases with height due to reduced surface friction.
        Uses log profile: V(h) = V_ref × ln(h/z0) / ln(h_ref/z0)

        Args:
            height_m: Height above ground in meters.

        Returns:
            Wind velocity vector in m/s.
        """
        if self.conditions.wind_speed_mph < 0.1:
            return Vec3(x=0.0, y=0.0, z=0.0)

        height_ft = meters_to_feet(height_m)

        # Logarithmic wind profile constants
        z0 = 0.01  # Roughness length (short grass) in feet
        ref_height = 10.0  # Reference height in feet

        # Calculate height factor
        # At ground level (h <= z0), wind is near zero
        # At reference height, factor = 1.0
        # Above reference height, factor > 1.0
        if height_ft <= z0:
            factor = 0.0
        else:
            factor = math.log(height_ft / z0) / math.log(ref_height / z0)
            factor = max(0.0, min(factor, 2.0))  # Clamp to reasonable range

        wind_speed_ms = mph_to_ms(self.conditions.wind_speed_mph) * factor
        wind_dir_rad = deg_to_rad(self.conditions.wind_dir_deg)

        # Wind direction: 0° = from north (headwind), 90° = from east (left-to-right)
        # Headwind opposes forward motion (negative X)
        # Crosswind from east pushes right (positive Z)
        return Vec3(
            x=-wind_speed_ms * math.cos(wind_dir_rad),
            y=0.0,
            z=wind_speed_ms * math.sin(wind_dir_rad),
        )

    def _gravity_force(self) -> Vec3:
        """Calculate gravity force on ball.

        Returns:
            Gravity force vector in Newtons.
        """
        return Vec3(x=0.0, y=-BALL_MASS_KG * GRAVITY_MS2, z=0.0)

    def _drag_force(
        self,
        pos: Vec3,
        vel: Vec3,
        spin_back: float,
        spin_side: float,
    ) -> Vec3:
        """Calculate aerodynamic drag force.

        Drag opposes the relative velocity (ball velocity minus wind).
        Uses the drag crisis model with spin-dependent term.

        Args:
            pos: Ball position in meters.
            vel: Ball velocity in m/s.
            spin_back: Backspin in RPM.
            spin_side: Sidespin in RPM.

        Returns:
            Drag force vector in Newtons.
        """
        # Get wind at current height
        wind = self.get_wind_at_height(pos.y)

        # Relative velocity (ball velocity in wind frame)
        rel_vel = vel.sub(wind)
        speed = rel_vel.mag()

        if speed < 0.01:
            return Vec3(x=0.0, y=0.0, z=0.0)

        # Calculate spin factor for drag term
        omega_back = rpm_to_rad_s(abs(spin_back))
        omega_side = rpm_to_rad_s(abs(spin_side))
        omega_total = math.sqrt(omega_back * omega_back + omega_side * omega_side)
        spin_factor = (omega_total * BALL_RADIUS_M) / speed if speed > 0.1 else 0.0

        # Get drag coefficient
        reynolds = calculate_reynolds(speed, self.air_density)
        cd = get_drag_coefficient(reynolds, spin_factor)

        # Dynamic pressure: q = 0.5 × ρ × v²
        q = 0.5 * self.air_density * speed * speed

        # Drag magnitude: F = q × Cd × A
        drag_magnitude = q * cd * BALL_AREA_M2

        # Drag direction: opposes relative velocity
        drag_direction = rel_vel.normalize().neg()

        return drag_direction.scale(drag_magnitude)

    def _magnus_force(
        self,
        pos: Vec3,
        vel: Vec3,
        spin_back: float,
        spin_side: float,
    ) -> Vec3:
        """Calculate Magnus force (lift from spin).

        Magnus force is perpendicular to both spin axis and velocity.
        Uses the formula: F = (1/2) × ρ × Cl × A × V² in the direction ω × V

        For a golf ball:
        - Backspin creates upward lift (Magnus force in +Y direction)
        - Positive sidespin (slice) curves the ball right (+Z direction)
        - Negative sidespin (hook) curves the ball left (-Z direction)

        Args:
            pos: Ball position in meters.
            vel: Ball velocity in m/s.
            spin_back: Backspin in RPM (positive = backspin).
            spin_side: Sidespin in RPM (positive = slice/fade).

        Returns:
            Magnus force vector in Newtons.
        """
        # Get wind at current height
        wind = self.get_wind_at_height(pos.y)

        # Relative velocity
        rel_vel = vel.sub(wind)
        speed = rel_vel.mag()

        if speed < 0.01:
            return Vec3(x=0.0, y=0.0, z=0.0)

        # Convert spin to rad/s
        omega_back = rpm_to_rad_s(spin_back)
        omega_side = rpm_to_rad_s(spin_side)

        # Total spin rate for spin factor calculation
        omega_total = math.sqrt(omega_back * omega_back + omega_side * omega_side)

        if omega_total < 0.1:
            return Vec3(x=0.0, y=0.0, z=0.0)

        # Spin factor: S = (ω × r) / V
        spin_factor = (omega_total * BALL_RADIUS_M) / speed

        # Get lift coefficient
        cl = get_lift_coefficient(spin_factor)

        if cl < 0.001:
            return Vec3(x=0.0, y=0.0, z=0.0)

        # Dynamic pressure
        q = 0.5 * self.air_density * speed * speed

        # Magnus magnitude: F = q × Cl × A
        magnus_magnitude = q * cl * BALL_AREA_M2

        # Build the spin vector in the ball's reference frame
        # The spin axis orientation depends on the type of spin:
        #
        # For BACKSPIN:
        # - The ball rotates such that the top moves backward relative to flight
        # - The spin axis is horizontal, perpendicular to velocity direction
        # - For a ball moving forward (+X), the spin axis points in +Z direction
        # - Magnus force = spin × velocity gives upward (+Y) force
        #
        # For SIDESPIN:
        # - The ball rotates around a tilted axis
        # - For a slice (positive sidespin), the axis is tilted to produce rightward force
        # - The spin axis for sidespin is approximately vertical but tilted

        # Get velocity direction
        vel_dir = rel_vel.normalize()

        # For backspin, the spin axis is perpendicular to velocity in the horizontal plane
        # velocity_direction × UP gives the correct spin axis for backspin
        # (not UP × velocity, which gives the opposite direction)
        up = Vec3(x=0.0, y=1.0, z=0.0)

        # Backspin axis: vel_dir × UP
        # For forward motion (+X), this gives +Z direction
        # Then spin × velocity = (+Z) × (+X) = +Y (upward lift)
        backspin_axis = vel_dir.cross(up)
        if backspin_axis.mag() > 0.001:
            backspin_axis = backspin_axis.normalize()
        else:
            # Ball moving straight up/down - assume standard backspin axis
            backspin_axis = Vec3(x=0.0, y=0.0, z=1.0)

        # For sidespin, the spin axis is approximately vertical
        # Positive sidespin (slice): ball curves right
        # The spin axis is tilted from vertical toward the velocity direction
        # For simplicity, we use the UP vector for sidespin axis
        # Then spin × velocity = (+Y) × (+X) = -Z (leftward force for positive Y spin)
        # But we want positive sidespin to curve right (+Z), so we negate the axis
        sidespin_axis = Vec3(x=0.0, y=-1.0, z=0.0)  # Negative Y axis for positive sidespin

        # Build combined spin vector (in rad/s)
        # The relative contribution depends on the spin rates
        spin_vec = backspin_axis.scale(omega_back).add(sidespin_axis.scale(omega_side))

        # Magnus force direction: spin × velocity
        magnus_dir = spin_vec.cross(rel_vel)
        magnus_mag_vec = magnus_dir.mag()

        if magnus_mag_vec < 0.001:
            return Vec3(x=0.0, y=0.0, z=0.0)

        # Normalize and scale by the magnitude calculated from Cl
        magnus_dir = magnus_dir.scale(1.0 / magnus_mag_vec)

        return magnus_dir.scale(magnus_magnitude)

    def calculate_acceleration(
        self,
        pos: Vec3,
        vel: Vec3,
        spin_back: float,
        spin_side: float,
    ) -> Vec3:
        """Calculate total acceleration from all forces.

        Args:
            pos: Ball position in meters.
            vel: Ball velocity in m/s.
            spin_back: Backspin in RPM.
            spin_side: Sidespin in RPM.

        Returns:
            Total acceleration in m/s².
        """
        gravity = self._gravity_force()
        drag = self._drag_force(pos, vel, spin_back, spin_side)
        magnus = self._magnus_force(pos, vel, spin_back, spin_side)

        total_force = gravity.add(drag).add(magnus)

        # a = F / m
        return total_force.scale(1.0 / BALL_MASS_KG)

    def rk4_step(self, state: SimulationState) -> SimulationState:
        """Perform one 4th-order Runge-Kutta integration step.

        RK4 provides good accuracy with O(dt^5) local error.

        Args:
            state: Current simulation state.

        Returns:
            New simulation state after dt.
        """
        dt = self.dt
        pos = state.pos
        vel = state.vel
        spin_back = state.spin_back
        spin_side = state.spin_side

        # Apply spin decay for this step
        decay = 1.0 - SPIN_DECAY_RATE * dt
        new_spin_back = spin_back * decay
        new_spin_side = spin_side * decay

        # k1 = f(t, y)
        a1 = self.calculate_acceleration(pos, vel, spin_back, spin_side)
        k1_pos = vel
        k1_vel = a1

        # k2 = f(t + dt/2, y + dt/2 * k1)
        pos2 = pos.add(k1_pos.scale(dt / 2))
        vel2 = vel.add(k1_vel.scale(dt / 2))
        a2 = self.calculate_acceleration(pos2, vel2, spin_back, spin_side)
        k2_pos = vel2
        k2_vel = a2

        # k3 = f(t + dt/2, y + dt/2 * k2)
        pos3 = pos.add(k2_pos.scale(dt / 2))
        vel3 = vel.add(k2_vel.scale(dt / 2))
        a3 = self.calculate_acceleration(pos3, vel3, spin_back, spin_side)
        k3_pos = vel3
        k3_vel = a3

        # k4 = f(t + dt, y + dt * k3)
        pos4 = pos.add(k3_pos.scale(dt))
        vel4 = vel.add(k3_vel.scale(dt))
        a4 = self.calculate_acceleration(pos4, vel4, spin_back, spin_side)
        k4_pos = vel4
        k4_vel = a4

        # Combine: y_new = y + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
        new_pos = pos.add(
            k1_pos.add(k2_pos.scale(2)).add(k3_pos.scale(2)).add(k4_pos).scale(dt / 6)
        )
        new_vel = vel.add(
            k1_vel.add(k2_vel.scale(2)).add(k3_vel.scale(2)).add(k4_vel).scale(dt / 6)
        )

        return SimulationState(
            pos=new_pos,
            vel=new_vel,
            spin_back=new_spin_back,
            spin_side=new_spin_side,
            t=state.t + dt,
            phase=Phase.FLIGHT,
        )

    def simulate_flight(
        self,
        ball_speed_mph: float,
        vla_deg: float,
        hla_deg: float,
        backspin_rpm: float,
        sidespin_rpm: float,
    ) -> tuple[list[TrajectoryPoint], SimulationState]:
        """Simulate ball flight from launch until it hits the ground.

        Args:
            ball_speed_mph: Initial ball speed in mph.
            vla_deg: Vertical launch angle in degrees.
            hla_deg: Horizontal launch angle in degrees.
            backspin_rpm: Initial backspin in RPM.
            sidespin_rpm: Initial sidespin in RPM.

        Returns:
            Tuple of (trajectory points, final state at landing).
            Trajectory points are in output units (yards, feet).
        """
        trajectory: list[TrajectoryPoint] = []

        # Handle zero or negative ball speed
        if ball_speed_mph <= 0:
            initial_point = TrajectoryPoint(
                t=0.0,
                x=0.0,
                y=0.0,
                z=0.0,
                phase=Phase.FLIGHT,
            )
            trajectory.append(initial_point)
            final_state = SimulationState(
                pos=Vec3(x=0, y=0, z=0),
                vel=Vec3(x=0, y=0, z=0),
                spin_back=backspin_rpm,
                spin_side=sidespin_rpm,
                t=0.0,
                phase=Phase.FLIGHT,
            )
            return trajectory, final_state

        # Initialize state
        initial_vel = calculate_initial_velocity(ball_speed_mph, vla_deg, hla_deg)
        state = SimulationState(
            pos=Vec3(x=0.0, y=0.0, z=0.0),
            vel=initial_vel,
            spin_back=backspin_rpm,
            spin_side=sidespin_rpm,
            t=0.0,
            phase=Phase.FLIGHT,
        )

        # Add initial point
        trajectory.append(
            TrajectoryPoint(
                t=0.0,
                x=0.0,
                y=0.0,
                z=0.0,
                phase=Phase.FLIGHT,
            )
        )

        # Sampling rate for trajectory output (every N steps)
        sample_interval = max(1, int(0.02 / self.dt))  # Sample every 20ms
        step_count = 0

        # Main simulation loop
        iterations = 0
        while iterations < MAX_ITERATIONS:
            iterations += 1
            step_count += 1

            # Advance state
            new_state = self.rk4_step(state)

            # Check for landing (y <= 0 and was previously above ground)
            if new_state.pos.y <= 0 and state.pos.y > 0:
                # Interpolate to find exact landing position
                # Linear interpolation between state and new_state
                t_ratio = state.pos.y / (state.pos.y - new_state.pos.y)
                t_ratio = max(0.0, min(1.0, t_ratio))

                landing_pos = Vec3(
                    x=state.pos.x + t_ratio * (new_state.pos.x - state.pos.x),
                    y=0.0,
                    z=state.pos.z + t_ratio * (new_state.pos.z - state.pos.z),
                )
                landing_vel = Vec3(
                    x=state.vel.x + t_ratio * (new_state.vel.x - state.vel.x),
                    y=state.vel.y + t_ratio * (new_state.vel.y - state.vel.y),
                    z=state.vel.z + t_ratio * (new_state.vel.z - state.vel.z),
                )
                landing_t = state.t + t_ratio * self.dt

                final_state = SimulationState(
                    pos=landing_pos,
                    vel=landing_vel,
                    spin_back=new_state.spin_back,
                    spin_side=new_state.spin_side,
                    t=landing_t,
                    phase=Phase.FLIGHT,
                )

                # Add landing point to trajectory
                trajectory.append(
                    TrajectoryPoint(
                        t=landing_t,
                        x=meters_to_yards(landing_pos.x),
                        y=meters_to_feet(landing_pos.y),
                        z=meters_to_yards(landing_pos.z),
                        phase=Phase.FLIGHT,
                    )
                )

                return trajectory, final_state

            state = new_state

            # Check time limit
            if state.t >= MAX_TIME:
                break

            # Sample trajectory point
            if step_count >= sample_interval and len(trajectory) < MAX_TRAJECTORY_POINTS:
                trajectory.append(
                    TrajectoryPoint(
                        t=state.t,
                        x=meters_to_yards(state.pos.x),
                        y=meters_to_feet(state.pos.y),
                        z=meters_to_yards(state.pos.z),
                        phase=Phase.FLIGHT,
                    )
                )
                step_count = 0

        # Time limit reached - return current state
        return trajectory, state
