# ABOUTME: Minimap component for Open Range with top-down orthographic view.
# ABOUTME: Displays ball position, target, and landing markers for shot dispersion.
"""Minimap component for Open Range visualization.

This module provides:
- MinimapRenderer: Manages minimap state and coordinate conversion
- Landing marker tracking for shot dispersion visualization
- Dynamic zoom based on ball-to-target distance
- World-to-screen coordinate conversion

The minimap shows a top-down orthographic view of the driving range,
centered between the ball and target positions. It dynamically adjusts
zoom level to keep both positions visible.

Coordinate system:
- World: X=lateral, Y=height, Z=forward (yards)
- Minimap: X=lateral (pixels), Y=forward mapped to vertical (pixels)
"""

from __future__ import annotations

from dataclasses import dataclass

from gc2_connect.open_range.models import Vec3
from gc2_connect.open_range.visualization.camera import (
    MINIMAP_CAMERA_HEIGHT,
    MINIMAP_HEIGHT,
    MINIMAP_WIDTH,
    calculate_minimap_center,
    calculate_minimap_zoom,
)

# Minimap styling constants
MINIMAP_BACKGROUND_COLOR: str = "rgba(0, 0, 0, 0.7)"  # Semi-transparent black
MINIMAP_BORDER_COLOR: str = "rgba(255, 255, 255, 0.3)"  # Light border
MINIMAP_BALL_COLOR: str = "#ffffff"  # White ball marker
MINIMAP_TARGET_COLOR: str = "#ff4444"  # Red target/flag marker
MINIMAP_LANDING_MARKER_COLOR: str = "#ffff00"  # Yellow landing spots
MINIMAP_FAIRWAY_COLOR: str = "#3d8c40"  # Green fairway

# Landing marker configuration
MAX_LANDING_MARKERS: int = 50  # Maximum shots to show in dispersion


@dataclass
class ScreenPosition:
    """Position in screen/minimap pixel coordinates.

    Attributes:
        x: Horizontal position in pixels.
        y: Vertical position in pixels.
    """

    x: float
    y: float


class MinimapRenderer:
    """Minimap renderer for top-down range visualization.

    Manages the minimap display state, coordinate conversion, and
    marker tracking. The minimap dynamically centers and zooms based
    on ball and target positions.

    Example:
        minimap = MinimapRenderer()
        minimap.update_ball_position(Vec3(x=0, y=10, z=150))
        minimap.update_target_position(Vec3(x=0, y=0, z=275))
        screen_pos = minimap.world_to_minimap(ball_pos)
    """

    def __init__(
        self,
        width: int = MINIMAP_WIDTH,
        height: int = MINIMAP_HEIGHT,
    ) -> None:
        """Initialize the minimap renderer.

        Args:
            width: Minimap width in pixels.
            height: Minimap height in pixels.
        """
        self._width = width
        self._height = height
        self._camera_height = MINIMAP_CAMERA_HEIGHT
        self._visible = True

        # Default positions
        self._ball_position = Vec3(x=0.0, y=0.0, z=0.0)
        self._target_position = Vec3(x=0.0, y=0.0, z=200.0)

        # Landing markers for dispersion visualization
        self._landing_markers: list[Vec3] = []

    @property
    def width(self) -> int:
        """Get minimap width in pixels."""
        return self._width

    @property
    def height(self) -> int:
        """Get minimap height in pixels."""
        return self._height

    @property
    def camera_height(self) -> float:
        """Get camera height for top-down view."""
        return self._camera_height

    @property
    def ball_position(self) -> Vec3:
        """Get current ball position."""
        return self._ball_position

    @property
    def target_position(self) -> Vec3:
        """Get current target position."""
        return self._target_position

    @property
    def visible(self) -> bool:
        """Get minimap visibility state."""
        return self._visible

    @property
    def landing_markers(self) -> list[Vec3]:
        """Get list of landing marker positions."""
        return self._landing_markers.copy()

    def update_ball_position(self, position: Vec3) -> None:
        """Update the ball position for minimap.

        Args:
            position: New ball position in world coordinates.
        """
        self._ball_position = position

    def update_target_position(self, position: Vec3) -> None:
        """Update the target position for minimap.

        Args:
            position: New target position in world coordinates.
        """
        self._target_position = position

    def set_visible(self, visible: bool) -> None:
        """Set minimap visibility.

        Args:
            visible: Whether the minimap should be visible.
        """
        self._visible = visible

    def get_camera_center(self) -> Vec3:
        """Calculate the camera center position for minimap view.

        Returns:
            Center position between ball and target.
        """
        return calculate_minimap_center(self._ball_position, self._target_position)

    def get_zoom_level(self) -> float:
        """Calculate the appropriate zoom level for current positions.

        Returns:
            Zoom level (larger = wider view).
        """
        return calculate_minimap_zoom(self._ball_position, self._target_position)

    def world_to_minimap(self, world_pos: Vec3) -> ScreenPosition:
        """Convert world coordinates to minimap screen coordinates.

        Maps world X (lateral) to screen X, and world Z (forward) to
        screen Y (with inversion so forward is down).

        Args:
            world_pos: Position in world coordinates.

        Returns:
            ScreenPosition with pixel coordinates.
        """
        center = self.get_camera_center()
        zoom = self.get_zoom_level()

        # Calculate relative position from center
        rel_x = world_pos.x - center.x
        rel_z = world_pos.z - center.z

        # Scale to screen coordinates
        # X: positive world X = positive screen X (right)
        # Z: positive world Z = positive screen Y (down, forward on range)
        scale = self._width / (zoom * 2.0)

        screen_x = self._width / 2.0 + rel_x * scale
        screen_y = self._height / 2.0 + rel_z * scale

        # Clamp to minimap bounds
        screen_x = max(0.0, min(float(self._width), screen_x))
        screen_y = max(0.0, min(float(self._height), screen_y))

        return ScreenPosition(x=screen_x, y=screen_y)

    def add_landing_marker(self, position: Vec3) -> None:
        """Add a landing marker for shot dispersion visualization.

        If the maximum number of markers is reached, the oldest
        marker is removed.

        Args:
            position: Landing position in world coordinates.
        """
        self._landing_markers.append(position)

        # Limit to maximum markers
        if len(self._landing_markers) > MAX_LANDING_MARKERS:
            self._landing_markers = self._landing_markers[-MAX_LANDING_MARKERS:]

    def clear_landing_markers(self) -> None:
        """Clear all landing markers."""
        self._landing_markers.clear()

    def get_css_styles(self) -> dict[str, str]:
        """Get CSS styles for minimap container.

        Returns:
            Dictionary of CSS property names to values.
        """
        return {
            "width": f"{self._width}px",
            "height": f"{self._height}px",
            "position": "fixed",
            "bottom": "20px",
            "right": "20px",
            "background-color": MINIMAP_BACKGROUND_COLOR,
            "border": f"2px solid {MINIMAP_BORDER_COLOR}",
            "border-radius": "8px",
            "z-index": "1000",
        }
