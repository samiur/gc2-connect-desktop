# ABOUTME: Wrapper module for OpenGolfCoach library integration.
# ABOUTME: Provides Python-friendly interface to the Rust/WASM physics calculations.
"""Wrapper module for OpenGolfCoach library.

This module provides a Python-friendly interface to the OpenGolfCoach library,
which is a Rust/WebAssembly library with Python bindings. It calculates derived
shot values including shot classification, ranking, distances, and estimated
club data from ball data.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

try:
    import opengolfcoach

    _OPENGOLFCOACH_AVAILABLE = True
except ImportError:
    _OPENGOLFCOACH_AVAILABLE = False

if TYPE_CHECKING:
    from gc2_connect.models import GC2ShotData


def is_available() -> bool:
    """Check if OpenGolfCoach library is available.

    Returns:
        True if the library is installed and can be imported.
    """
    return _OPENGOLFCOACH_AVAILABLE


@dataclass
class OpenGolfCoachInput:
    """Input parameters for OpenGolfCoach calculation."""

    ball_speed_meters_per_second: float
    vertical_launch_angle_degrees: float
    horizontal_launch_angle_degrees: float = 0.0
    total_spin_rpm: float = 0.0
    spin_axis_degrees: float = 0.0

    def to_json(self) -> str:
        """Convert to JSON string for OpenGolfCoach.

        Returns:
            JSON string with all input parameters.
        """
        return json.dumps(
            {
                "ball_speed_meters_per_second": self.ball_speed_meters_per_second,
                "vertical_launch_angle_degrees": self.vertical_launch_angle_degrees,
                "horizontal_launch_angle_degrees": self.horizontal_launch_angle_degrees,
                "total_spin_rpm": self.total_spin_rpm,
                "spin_axis_degrees": self.spin_axis_degrees,
            }
        )

    @classmethod
    def from_gc2_shot(cls, shot: GC2ShotData) -> OpenGolfCoachInput:
        """Create input from GC2ShotData.

        Args:
            shot: GC2 shot data from launch monitor.

        Returns:
            OpenGolfCoachInput with converted units.
        """
        # Convert mph to m/s (1 mph = 0.44704 m/s)
        ball_speed_ms = shot.ball_speed * 0.44704

        # Calculate total spin from back_spin and side_spin
        total_spin = math.sqrt(shot.back_spin**2 + shot.side_spin**2)

        # Calculate spin axis from components (using GC2ShotData.spin_axis property)
        spin_axis = shot.spin_axis

        return cls(
            ball_speed_meters_per_second=ball_speed_ms,
            vertical_launch_angle_degrees=shot.launch_angle,
            horizontal_launch_angle_degrees=shot.horizontal_launch_angle,
            total_spin_rpm=total_spin,
            spin_axis_degrees=spin_axis,
        )


@dataclass
class OpenGolfCoachResult:
    """Output from OpenGolfCoach calculation."""

    # Distance metrics (in meters from library)
    carry_distance_meters: float
    total_distance_meters: float
    offline_distance_meters: float

    # Spin components
    backspin_rpm: float
    sidespin_rpm: float

    # Performance metrics
    club_speed_meters_per_second: float | None
    smash_factor: float | None
    club_path_degrees: float | None
    club_face_to_target_degrees: float | None
    club_face_to_path_degrees: float | None

    # Shot classification
    shot_name: str
    shot_rank: str
    shot_color_rgb: str

    @property
    def carry_distance_yards(self) -> float:
        """Carry distance converted to yards."""
        return self.carry_distance_meters * 1.09361

    @property
    def total_distance_yards(self) -> float:
        """Total distance converted to yards."""
        return self.total_distance_meters * 1.09361

    @property
    def offline_distance_yards(self) -> float:
        """Offline distance converted to yards."""
        return self.offline_distance_meters * 1.09361

    @property
    def club_speed_mph(self) -> float | None:
        """Club speed converted to mph, or None if not available."""
        if self.club_speed_meters_per_second is None:
            return None
        return self.club_speed_meters_per_second * 2.23694


def calculate_shot(input_data: OpenGolfCoachInput) -> OpenGolfCoachResult:
    """Calculate derived values using OpenGolfCoach library.

    Args:
        input_data: Shot input parameters.

    Returns:
        OpenGolfCoachResult with calculated values.

    Raises:
        RuntimeError: If OpenGolfCoach library is not available.
        ValueError: If calculation fails or returns invalid data.
    """
    if not _OPENGOLFCOACH_AVAILABLE:
        raise RuntimeError("OpenGolfCoach library is not installed")

    json_input = input_data.to_json()
    json_output = opengolfcoach.calculate_derived_values(json_input)
    result = json.loads(json_output)

    # Extract values from the nested 'open_golf_coach' key
    ogc = result.get("open_golf_coach", {})

    return OpenGolfCoachResult(
        carry_distance_meters=ogc.get("carry_distance_meters", 0.0),
        total_distance_meters=ogc.get("total_distance_meters", 0.0),
        offline_distance_meters=ogc.get("offline_distance_meters", 0.0),
        backspin_rpm=ogc.get("backspin_rpm", 0.0),
        sidespin_rpm=ogc.get("sidespin_rpm", 0.0),
        club_speed_meters_per_second=ogc.get("club_speed_meters_per_second"),
        smash_factor=ogc.get("smash_factor"),
        club_path_degrees=ogc.get("club_path_degrees"),
        club_face_to_target_degrees=ogc.get("club_face_to_target_degrees"),
        club_face_to_path_degrees=ogc.get("club_face_to_path_degrees"),
        shot_name=ogc.get("shot_name", "Unknown"),
        shot_rank=ogc.get("shot_rank", "D"),
        shot_color_rgb=ogc.get("shot_color_rgb", "#808080"),
    )


def calculate_shot_from_gc2(shot: GC2ShotData) -> OpenGolfCoachResult:
    """Calculate derived values directly from GC2ShotData.

    Args:
        shot: GC2 shot data from launch monitor.

    Returns:
        OpenGolfCoachResult with calculated values.

    Raises:
        RuntimeError: If OpenGolfCoach library is not available.
    """
    input_data = OpenGolfCoachInput.from_gc2_shot(shot)
    return calculate_shot(input_data)
