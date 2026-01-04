# ABOUTME: Open Range visualization module for 3D driving range display.
# ABOUTME: Provides scene setup, ball animation, trajectory trace, and camera controls.
"""Open Range visualization components.

This module provides:
- RangeScene: 3D driving range environment setup
- BallAnimator: Ball flight animation along trajectory
- TrajectoryTrace: Visible trace of ball flight path
- Camera utilities for following ball flight

The visualization uses NiceGUI's Three.js integration (ui.scene)
for WebGL-based 3D rendering.
"""

from gc2_connect.open_range.visualization.ball_animation import (
    CAMERA_FOLLOW_DISTANCE,
    PHASE_COLORS,
    BallAnimator,
    calculate_follow_camera,
    get_tee_box_camera,
)
from gc2_connect.open_range.visualization.range_scene import (
    AMBIENT_LIGHT_INTENSITY,
    BALL_COLOR,
    DIRECTIONAL_LIGHT_INTENSITY,
    DISTANCE_MARKERS,
    GROUND_COLOR,
    RANGE_LENGTH_YARDS,
    RANGE_WIDTH_YARDS,
    TARGET_GREENS,
    RangeScene,
    feet_to_scene,
    trajectory_to_scene_coords,
    yards_to_scene,
)
from gc2_connect.open_range.visualization.trajectory_trace import (
    TRACE_COLORS,
    TraceSegment,
    TrajectoryTrace,
    get_phase_color,
)

__all__ = [
    # RangeScene exports
    "RangeScene",
    "DISTANCE_MARKERS",
    "TARGET_GREENS",
    "RANGE_LENGTH_YARDS",
    "RANGE_WIDTH_YARDS",
    "AMBIENT_LIGHT_INTENSITY",
    "DIRECTIONAL_LIGHT_INTENSITY",
    "GROUND_COLOR",
    "BALL_COLOR",
    "yards_to_scene",
    "feet_to_scene",
    "trajectory_to_scene_coords",
    # BallAnimator exports
    "BallAnimator",
    "PHASE_COLORS",
    "CAMERA_FOLLOW_DISTANCE",
    "calculate_follow_camera",
    "get_tee_box_camera",
    # TrajectoryTrace exports
    "TrajectoryTrace",
    "TraceSegment",
    "TRACE_COLORS",
    "get_phase_color",
]
