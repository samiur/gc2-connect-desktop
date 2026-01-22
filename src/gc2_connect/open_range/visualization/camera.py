# ABOUTME: Camera system with multiple view presets for Open Range visualization.
# ABOUTME: Provides CameraMode enum, presets, controller, and minimap calculations.
"""Camera system for Open Range visualization.

This module provides:
- CameraMode: Enum for available camera view presets
- CameraPreset: Dataclass for camera position/look-at configurations
- CameraController: Manages camera state and mode switching
- Minimap camera calculations for top-down view
- Smooth camera transition interpolation

Camera presets:
- BEHIND_BALL: Low angle behind the ball (aim view)
- TEE_BOX: Eye-level view from behind the tee
- FOLLOW: Dynamic camera that follows ball during flight
- OVERHEAD: Bird's eye view for dispersion patterns
- GREEN: View from the landing area looking back

Coordinate system (Scene/Three.js):
- X: Lateral movement (+ = right)
- Y: Vertical height
- Z: Forward toward targets (+ = away from camera)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from gc2_connect.open_range.models import Vec3


# Camera mode constants
class CameraMode(str, Enum):
    """Available camera view modes for Open Range."""

    BEHIND_BALL = "behind_ball"
    TEE_BOX = "tee_box"
    FOLLOW = "follow"
    OVERHEAD = "overhead"
    GREEN = "green"


# Follow camera constants (yards)
FOLLOW_CAMERA_DISTANCE: float = 40.0  # Distance behind ball
FOLLOW_CAMERA_HEIGHT: float = 20.0  # Height above ground
FOLLOW_CAMERA_LATERAL: float = 10.0  # Lateral offset for better view

# Overhead camera constants (yards)
OVERHEAD_CAMERA_HEIGHT: float = 80.0  # Height for bird's eye view

# Green camera constants (yards)
GREEN_CAMERA_DISTANCE: float = 15.0  # Distance from green center
GREEN_CAMERA_HEIGHT: float = 2.0  # Eye-level height
GREEN_TARGET_DISTANCE: float = 200.0  # Default target green distance

# Behind ball camera constants (yards)
BEHIND_BALL_DISTANCE: float = 3.0  # Close behind ball
BEHIND_BALL_HEIGHT: float = 1.7  # Eye level (~5'7")

# Tee box camera constants (yards)
TEE_BOX_DISTANCE: float = 20.0  # Distance behind tee
TEE_BOX_HEIGHT: float = 15.0  # Elevated view
TEE_BOX_LATERAL: float = 10.0  # Lateral offset

# Minimap configuration
MINIMAP_WIDTH: int = 200  # Pixels
MINIMAP_HEIGHT: int = 200  # Pixels
MINIMAP_CAMERA_HEIGHT: float = 200.0  # Yards above ground for top-down view
MINIMAP_MIN_ZOOM: float = 50.0  # Minimum zoom (tighter view)
MINIMAP_MAX_ZOOM: float = 150.0  # Maximum zoom (wider view)


@dataclass
class CameraPreset:
    """Camera preset configuration.

    Defines a camera position and look-at target for a specific view mode.

    Attributes:
        name: Human-readable name for the preset.
        position: Camera position in scene coordinates.
        look_at: Point the camera should look at.
        is_dynamic: Whether this preset updates based on ball position.
    """

    name: str
    position: Vec3
    look_at: Vec3
    is_dynamic: bool = False


# Predefined camera presets
_CAMERA_PRESETS: dict[CameraMode, CameraPreset] = {
    CameraMode.BEHIND_BALL: CameraPreset(
        name="Behind Ball",
        position=Vec3(x=0.0, y=BEHIND_BALL_HEIGHT, z=-BEHIND_BALL_DISTANCE),
        look_at=Vec3(x=0.0, y=0.0, z=100.0),
        is_dynamic=False,
    ),
    CameraMode.TEE_BOX: CameraPreset(
        name="Tee Box",
        position=Vec3(x=TEE_BOX_LATERAL, y=TEE_BOX_HEIGHT, z=-TEE_BOX_DISTANCE),
        look_at=Vec3(x=0.0, y=5.0, z=100.0),
        is_dynamic=False,
    ),
    CameraMode.FOLLOW: CameraPreset(
        name="Follow",
        position=Vec3(
            x=FOLLOW_CAMERA_LATERAL,
            y=FOLLOW_CAMERA_HEIGHT,
            z=-FOLLOW_CAMERA_DISTANCE,
        ),
        look_at=Vec3(x=0.0, y=5.0, z=100.0),
        is_dynamic=True,
    ),
    CameraMode.OVERHEAD: CameraPreset(
        name="Overhead",
        position=Vec3(x=0.0, y=OVERHEAD_CAMERA_HEIGHT, z=100.0),
        look_at=Vec3(x=0.0, y=0.0, z=100.0),
        is_dynamic=False,
    ),
    CameraMode.GREEN: CameraPreset(
        name="Green",
        position=Vec3(
            x=0.0,
            y=GREEN_CAMERA_HEIGHT,
            z=GREEN_TARGET_DISTANCE + GREEN_CAMERA_DISTANCE,
        ),
        look_at=Vec3(x=0.0, y=5.0, z=0.0),
        is_dynamic=False,
    ),
}


def get_camera_preset(mode: CameraMode) -> CameraPreset:
    """Get the camera preset for a given mode.

    Args:
        mode: The camera mode to get preset for.

    Returns:
        CameraPreset with position and look-at configuration.
    """
    return _CAMERA_PRESETS[mode]


def get_mode_display_name(mode: CameraMode) -> str:
    """Get a human-readable display name for a camera mode.

    Args:
        mode: The camera mode.

    Returns:
        Human-readable display name string.
    """
    preset = _CAMERA_PRESETS[mode]
    return preset.name


def calculate_follow_camera_position(
    ball_position: Vec3,
) -> tuple[Vec3, Vec3]:
    """Calculate follow camera position and look-at based on ball position.

    The follow camera stays behind the ball, maintaining a consistent
    distance and height offset while tracking its movement.

    Args:
        ball_position: Current ball position in scene coordinates.

    Returns:
        Tuple of (camera_position, look_at_position).
    """
    # Camera follows behind the ball, staying at a minimum distance back
    camera_z = max(ball_position.z - FOLLOW_CAMERA_DISTANCE, -FOLLOW_CAMERA_DISTANCE)

    camera_pos = Vec3(
        x=FOLLOW_CAMERA_LATERAL,
        y=FOLLOW_CAMERA_HEIGHT,
        z=camera_z,
    )

    # Look ahead of the ball
    look_at = Vec3(
        x=0.0,
        y=max(5.0, ball_position.y * 0.5),  # Look slightly above midpoint
        z=ball_position.z + 30.0,
    )

    return camera_pos, look_at


def calculate_overhead_camera_position(
    ball_position: Vec3,
) -> tuple[Vec3, Vec3]:
    """Calculate overhead camera position centered on ball/range.

    The overhead camera provides a bird's eye view, useful for
    seeing shot dispersion patterns.

    Args:
        ball_position: Current ball position in scene coordinates.

    Returns:
        Tuple of (camera_position, look_at_position).
    """
    # Center above the midpoint between tee and ball
    center_z = ball_position.z / 2.0 if ball_position.z > 0 else 100.0

    camera_pos = Vec3(
        x=0.0,
        y=OVERHEAD_CAMERA_HEIGHT,
        z=center_z,
    )

    look_at = Vec3(
        x=0.0,
        y=0.0,
        z=center_z,
    )

    return camera_pos, look_at


def interpolate_camera_position(
    start: Vec3,
    end: Vec3,
    t: float,
) -> Vec3:
    """Linearly interpolate between two camera positions.

    Args:
        start: Starting position.
        end: Ending position.
        t: Interpolation factor (0.0 to 1.0).

    Returns:
        Interpolated position.
    """
    # Clamp t to [0, 1]
    t = max(0.0, min(1.0, t))

    return Vec3(
        x=start.x + (end.x - start.x) * t,
        y=start.y + (end.y - start.y) * t,
        z=start.z + (end.z - start.z) * t,
    )


def calculate_minimap_center(
    ball_position: Vec3,
    target_position: Vec3,
) -> Vec3:
    """Calculate the center point for minimap view.

    Centers the minimap between the ball and target positions.

    Args:
        ball_position: Current ball position.
        target_position: Target/pin position.

    Returns:
        Center position for minimap camera.
    """
    return Vec3(
        x=(ball_position.x + target_position.x) / 2.0,
        y=0.0,  # Y is height, not relevant for top-down center
        z=(ball_position.z + target_position.z) / 2.0,
    )


def calculate_minimap_zoom(
    ball_position: Vec3,
    target_position: Vec3,
) -> float:
    """Calculate appropriate zoom level for minimap.

    Zoom scales based on distance between ball and target,
    ensuring both are visible with some margin.

    Args:
        ball_position: Current ball position.
        target_position: Target/pin position.

    Returns:
        Zoom level (larger = wider view).
    """
    # Calculate distance between ball and target
    dx = target_position.x - ball_position.x
    dz = target_position.z - ball_position.z
    distance = math.sqrt(dx * dx + dz * dz)

    # Zoom based on distance with padding
    zoom = distance / 2.0 + 30.0

    # Clamp to reasonable range
    return max(MINIMAP_MIN_ZOOM, min(MINIMAP_MAX_ZOOM, zoom))


class CameraController:
    """Controls camera mode and position for Open Range.

    Manages the active camera mode, handles mode switching,
    and provides camera positions for rendering.

    Example:
        controller = CameraController()
        controller.set_mode(CameraMode.FOLLOW)
        position, look_at = controller.get_camera_position(ball_pos)
    """

    def __init__(self) -> None:
        """Initialize the camera controller with default mode."""
        self._current_mode: CameraMode = CameraMode.TEE_BOX
        self._mode_order: list[CameraMode] = list(CameraMode)

    @property
    def current_mode(self) -> CameraMode:
        """Get the current camera mode."""
        return self._current_mode

    def set_mode(self, mode: CameraMode) -> None:
        """Set the camera mode.

        Args:
            mode: The camera mode to switch to.
        """
        self._current_mode = mode

    def cycle_mode(self) -> None:
        """Cycle to the next camera mode in sequence."""
        current_index = self._mode_order.index(self._current_mode)
        next_index = (current_index + 1) % len(self._mode_order)
        self._current_mode = self._mode_order[next_index]

    def get_camera_position(
        self,
        ball_position: Vec3 | None = None,
    ) -> tuple[Vec3, Vec3]:
        """Get the current camera position and look-at target.

        For dynamic modes (FOLLOW), the ball position is used to
        calculate the camera position. For static modes, the preset
        position is returned.

        Args:
            ball_position: Current ball position (used for dynamic modes).

        Returns:
            Tuple of (camera_position, look_at_position).
        """
        preset = _CAMERA_PRESETS[self._current_mode]

        if preset.is_dynamic and ball_position is not None:
            if self._current_mode == CameraMode.FOLLOW:
                return calculate_follow_camera_position(ball_position)
            elif self._current_mode == CameraMode.OVERHEAD:
                return calculate_overhead_camera_position(ball_position)

        return preset.position, preset.look_at

    def get_current_preset_name(self) -> str:
        """Get the display name of the current camera preset.

        Returns:
            Human-readable name of the current camera mode.
        """
        return get_mode_display_name(self._current_mode)
