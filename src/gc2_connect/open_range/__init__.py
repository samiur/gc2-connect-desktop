# ABOUTME: Open Range package - built-in driving range simulator.
# ABOUTME: Provides physics simulation and 3D visualization for practice shots.
"""Open Range driving range simulator with physics-accurate ball flight."""

from gc2_connect.open_range.engine import OpenRangeEngine
from gc2_connect.open_range.models import (
    Conditions,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
    TrajectoryPoint,
    Vec3,
)

__all__ = [
    "Conditions",
    "LaunchData",
    "OpenRangeEngine",
    "Phase",
    "ShotResult",
    "ShotSummary",
    "TrajectoryPoint",
    "Vec3",
]
