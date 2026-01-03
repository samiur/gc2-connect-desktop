# ABOUTME: Ground interaction physics for golf ball bounce and roll.
# ABOUTME: Implements bounce physics (COR, friction) and roll physics (deceleration).
"""Ground interaction physics for golf ball bounce and roll behavior.

This module handles:
- Bounce physics: Coefficient of restitution and friction on impact
- Roll physics: Deceleration due to rolling resistance
- Surface types: Fairway, Green, Rough with different properties

Based on:
- Professor Alan Nathan's trajectory calculator (UIUC)
- libgolf C++ reference implementation
- docs/PHYSICS.md specifications
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gc2_connect.open_range.models import Phase, Vec3
from gc2_connect.open_range.physics.constants import (
    GRAVITY_MS2,
    STOPPED_THRESHOLD,
    SURFACES,
    GroundSurface,
)

if TYPE_CHECKING:
    from gc2_connect.open_range.physics.trajectory import SimulationState

# Minimum bounce velocity threshold to transition to rolling
MIN_BOUNCE_VELOCITY: float = 0.5  # m/s


class GroundPhysics:
    """Handles bounce and roll physics for golf ball ground interaction.

    This class simulates:
    1. Bounce: When ball impacts ground, vertical velocity is reversed and
       reduced by coefficient of restitution (COR). Tangential velocity is
       reduced by friction. Spin is also reduced.
    2. Roll: Ball decelerates due to rolling resistance until stopped.
    """

    def __init__(self, surface_name: str = "Fairway"):
        """Initialize ground physics with a surface type.

        Args:
            surface_name: Name of the surface type (Fairway, Green, Rough).
                         Defaults to Fairway.

        Raises:
            KeyError: If surface_name is not a valid surface type.
        """
        self.surface: GroundSurface = SURFACES[surface_name]

    def bounce(
        self,
        state: SimulationState,
    ) -> SimulationState:
        """Apply bounce physics at ground contact.

        Physics:
        - Normal velocity: v_n_new = -v_n * COR
        - Tangential velocity: v_t_new = v_t * (1 - friction * 0.3)
        - Spin: reduced by 30% on each bounce

        Args:
            state: Current simulation state at ground contact.

        Returns:
            New simulation state after bounce.
        """
        from gc2_connect.open_range.physics.trajectory import SimulationState

        pos = state.pos
        vel = state.vel

        # Decompose velocity into normal (vertical) and tangential (horizontal) components
        normal = Vec3(x=0.0, y=1.0, z=0.0)

        # Normal component (should be negative when hitting ground)
        vn = vel.dot(normal)  # Dot product gives scalar vertical component

        # Tangential components (horizontal)
        vt = Vec3(x=vel.x, y=0.0, z=vel.z)

        # Apply coefficient of restitution to normal component
        # Reverse direction and reduce by COR
        vn_new = -vn * self.surface.cor

        # Apply friction to tangential component
        # friction_factor = 0.3 is from the libgolf reference
        friction_factor = 0.3
        vt_new = vt.scale(1.0 - self.surface.friction * friction_factor)

        # Combine velocity components
        new_vel = Vec3(
            x=vt_new.x,
            y=vn_new,
            z=vt_new.z,
        )

        # Reduce spin on bounce (70% retained)
        spin_retention = 0.7
        new_spin_back = state.spin_back * spin_retention
        new_spin_side = state.spin_side * spin_retention

        # Ensure ball is above ground
        new_pos = Vec3(x=pos.x, y=0.001, z=pos.z)

        return SimulationState(
            pos=new_pos,
            vel=new_vel,
            spin_back=new_spin_back,
            spin_side=new_spin_side,
            t=state.t,
            phase=Phase.BOUNCE,
        )

    def roll_step(
        self,
        state: SimulationState,
        dt: float,
    ) -> SimulationState:
        """Simulate one step of rolling.

        Physics:
        - Deceleration = rolling_resistance * g (with minimum 0.5 m/s²)
        - Speed decreases by decel * dt
        - Position updates by velocity * dt
        - Ball stops when speed < STOPPED_THRESHOLD (0.1 m/s)
        - Spin decays at 10% per second

        Args:
            state: Current simulation state during rolling.
            dt: Time step in seconds.

        Returns:
            New simulation state after roll step.
        """
        from gc2_connect.open_range.physics.trajectory import SimulationState

        pos = state.pos
        vel = state.vel

        speed = vel.mag()

        # Check if ball has stopped
        if speed < STOPPED_THRESHOLD:
            return SimulationState(
                pos=Vec3(x=pos.x, y=0.0, z=pos.z),
                vel=Vec3(x=0.0, y=0.0, z=0.0),
                spin_back=0.0,
                spin_side=0.0,
                t=state.t + dt,
                phase=Phase.STOPPED,
            )

        # Calculate deceleration due to rolling resistance
        # decel = resistance * g, with minimum of 0.5 m/s² for realism
        decel = self.surface.rolling_resistance * GRAVITY_MS2
        decel = max(decel, 0.5)

        # Calculate new speed
        new_speed = speed - decel * dt

        # Check if speed goes below zero
        if new_speed <= 0:
            # Ball has stopped
            return SimulationState(
                pos=Vec3(x=pos.x, y=0.0, z=pos.z),
                vel=Vec3(x=0.0, y=0.0, z=0.0),
                spin_back=0.0,
                spin_side=0.0,
                t=state.t + dt,
                phase=Phase.STOPPED,
            )

        # Update velocity (same direction, reduced magnitude)
        direction = vel.normalize()
        new_vel = direction.scale(new_speed)

        # Update position
        # Use average velocity for more accurate position update
        avg_speed = (speed + new_speed) / 2.0
        new_pos = pos.add(direction.scale(avg_speed * dt))
        new_pos = Vec3(x=new_pos.x, y=0.0, z=new_pos.z)  # Keep on ground

        # Spin decay during roll (10% per second)
        spin_decay = 1.0 - 0.1 * dt
        new_spin_back = state.spin_back * spin_decay
        new_spin_side = state.spin_side * spin_decay

        return SimulationState(
            pos=new_pos,
            vel=new_vel,
            spin_back=new_spin_back,
            spin_side=new_spin_side,
            t=state.t + dt,
            phase=Phase.ROLLING,
        )

    def should_continue_bouncing(self, state: SimulationState) -> bool:
        """Check if ball has enough energy for another bounce.

        When vertical velocity drops below threshold, ball transitions to rolling.

        Args:
            state: Current simulation state after bounce.

        Returns:
            True if ball should continue bouncing, False to transition to roll.
        """
        # Check if vertical velocity is high enough to continue bouncing
        return abs(state.vel.y) >= MIN_BOUNCE_VELOCITY
