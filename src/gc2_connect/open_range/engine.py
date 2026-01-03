# ABOUTME: High-level Open Range engine that processes GC2 shot data.
# ABOUTME: Converts launch monitor input to simulated trajectory output.
"""High-level Open Range engine for processing GC2 shots.

This module provides:
- OpenRangeEngine: Processes GC2ShotData through physics simulation
- Test shot generation for UI testing and demos

The OpenRangeEngine wraps the PhysicsEngine and provides a clean interface
for integrating with the GC2 Connect application.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from gc2_connect.open_range.models import Conditions, ShotResult
from gc2_connect.open_range.physics.engine import PhysicsEngine

if TYPE_CHECKING:
    from gc2_connect.models import GC2ShotData


# Typical club parameters for test shots
# Format: (ball_speed_mph, vla_deg, backspin_rpm, variance_pct)
CLUB_PROFILES: dict[str, tuple[float, float, float, float]] = {
    "Driver": (167.0, 10.9, 2686.0, 0.05),
    "3-Wood": (155.0, 12.0, 3200.0, 0.05),
    "5-Wood": (145.0, 14.0, 4000.0, 0.05),
    "Hybrid": (140.0, 14.5, 4200.0, 0.05),
    "4-Iron": (135.0, 14.0, 4500.0, 0.05),
    "5-Iron": (130.0, 14.5, 5000.0, 0.05),
    "6-Iron": (125.0, 15.0, 5500.0, 0.05),
    "7-Iron": (120.0, 16.3, 7097.0, 0.05),
    "8-Iron": (115.0, 18.0, 7500.0, 0.05),
    "9-Iron": (110.0, 20.0, 8000.0, 0.05),
    "PW": (102.0, 24.2, 9304.0, 0.05),
    "GW": (95.0, 27.0, 9500.0, 0.05),
    "SW": (85.0, 30.0, 10000.0, 0.06),
    "LW": (75.0, 34.0, 10500.0, 0.07),
}


class OpenRangeEngine:
    """Processes GC2 shots for Open Range visualization.

    This class provides the main entry point for Open Range functionality:
    - Takes GC2 shot data or manual launch parameters
    - Runs physics simulation for trajectory
    - Returns complete ShotResult with metrics

    Example:
        engine = OpenRangeEngine()
        result = engine.simulate_shot(gc2_shot_data)
        print(f"Carry: {result.summary.carry_distance:.1f} yards")
    """

    def __init__(
        self,
        conditions: Conditions | None = None,
        surface: str = "Fairway",
    ):
        """Initialize Open Range engine.

        Args:
            conditions: Environmental conditions. Defaults to standard
                       (70°F, sea level, no wind).
            surface: Ground surface type ("Fairway", "Green", "Rough").
        """
        self.conditions = conditions or Conditions()
        self.surface = surface
        self.physics = PhysicsEngine(self.conditions, surface)

    def update_conditions(self, conditions: Conditions) -> None:
        """Update environmental conditions.

        Args:
            conditions: New environmental conditions.
        """
        self.conditions = conditions
        self.physics = PhysicsEngine(self.conditions, self.surface)

    def update_surface(self, surface: str) -> None:
        """Update ground surface type.

        Args:
            surface: New surface type ("Fairway", "Green", "Rough").
        """
        self.surface = surface
        self.physics = PhysicsEngine(self.conditions, surface)

    def simulate_shot(self, shot: GC2ShotData) -> ShotResult:
        """Simulate a shot from GC2 data.

        Args:
            shot: GC2ShotData from launch monitor.

        Returns:
            ShotResult with trajectory and summary.
        """
        return self.physics.simulate(
            ball_speed_mph=shot.ball_speed,
            vla_deg=shot.launch_angle,
            hla_deg=shot.horizontal_launch_angle,
            backspin_rpm=shot.back_spin,
            sidespin_rpm=shot.side_spin,
        )

    def simulate_manual(
        self,
        ball_speed_mph: float,
        vla_deg: float,
        hla_deg: float,
        backspin_rpm: float,
        sidespin_rpm: float,
    ) -> ShotResult:
        """Simulate a shot with manual parameters.

        Args:
            ball_speed_mph: Ball speed in mph.
            vla_deg: Vertical launch angle in degrees.
            hla_deg: Horizontal launch angle in degrees.
            backspin_rpm: Backspin in RPM.
            sidespin_rpm: Sidespin in RPM.

        Returns:
            ShotResult with trajectory and summary.
        """
        return self.physics.simulate(
            ball_speed_mph=ball_speed_mph,
            vla_deg=vla_deg,
            hla_deg=hla_deg,
            backspin_rpm=backspin_rpm,
            sidespin_rpm=sidespin_rpm,
        )

    def simulate_test_shot(self, club: str = "Driver") -> ShotResult:
        """Generate a realistic test shot for given club.

        Adds small random variance to make shots feel realistic.

        Args:
            club: Club name (e.g., "Driver", "7-Iron", "PW").
                 Defaults to "Driver".

        Returns:
            ShotResult for a typical shot with that club.
        """
        # Get club profile or default to driver
        profile = CLUB_PROFILES.get(club, CLUB_PROFILES["Driver"])
        base_speed, base_vla, base_spin, variance = profile

        # Add random variance
        speed = base_speed * (1 + random.uniform(-variance, variance))
        vla = base_vla * (1 + random.uniform(-variance * 0.5, variance * 0.5))
        backspin = base_spin * (1 + random.uniform(-variance, variance))

        # Small random sidespin for realism
        sidespin = random.uniform(-300, 300)

        # Small random horizontal launch angle
        hla = random.uniform(-1.5, 1.5)

        return self.physics.simulate(
            ball_speed_mph=speed,
            vla_deg=vla,
            hla_deg=hla,
            backspin_rpm=backspin,
            sidespin_rpm=sidespin,
        )

    @staticmethod
    def get_available_clubs() -> list[str]:
        """Get list of available club profiles.

        Returns:
            List of club names that can be used with simulate_test_shot.
        """
        return list(CLUB_PROFILES.keys())
