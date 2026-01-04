# ABOUTME: Trajectory trace visualization for Open Range ball flight paths.
# ABOUTME: Creates visible trace lines with phase-specific colors during ball animation.
"""Trajectory trace visualization for Open Range.

This module provides:
- TrajectoryTrace: Manages collection of trace segments
- TraceSegment: Individual line segment with phase-based coloring
- get_phase_color: Returns appropriate color for each phase

Trace colors by phase:
- FLIGHT: Green (#00ff88)
- BOUNCE: Orange (#ff8844)
- ROLLING: Blue (#00d4ff)
- STOPPED: Gray (#888888)

The trace is drawn progressively as the ball animates, showing the
complete flight path including bounces and roll. The trace remains
visible after the animation completes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from gc2_connect.open_range.models import Phase, Vec3

if TYPE_CHECKING:
    from gc2_connect.open_range.models import TrajectoryPoint


# Phase colors (match ball_animation.py colors)
TRACE_COLORS: dict[Phase, str] = {
    Phase.FLIGHT: "#00ff88",  # Green - ball in flight
    Phase.BOUNCE: "#ff8844",  # Orange - ground contact
    Phase.ROLLING: "#00d4ff",  # Blue - rolling
    Phase.STOPPED: "#888888",  # Gray - at rest
}

# Default maximum segments to prevent memory issues
DEFAULT_MAX_SEGMENTS: int = 500

# Trace line visual configuration
TRACE_SPHERE_RADIUS: float = 0.15  # Radius of breadcrumb spheres
TRACE_SPHERE_OPACITY: float = 0.9  # Opacity of trace spheres


def get_phase_color(phase: Phase) -> str:
    """Get the trace color for a phase.

    Args:
        phase: The trajectory phase.

    Returns:
        Hex color string for the phase.
    """
    return TRACE_COLORS.get(phase, TRACE_COLORS[Phase.STOPPED])


@dataclass
class TraceSegment:
    """Single segment of the trajectory trace.

    Represents a line segment between two points with a phase
    that determines its color.
    """

    start: Vec3
    end: Vec3
    phase: Phase
    scene_object: Any = None  # Reference to NiceGUI scene object

    @property
    def color(self) -> str:
        """Get the color for this segment based on phase."""
        return get_phase_color(self.phase)


@dataclass
class TrajectoryTrace:
    """Manages trajectory trace visualization.

    Collects trace segments as the ball moves and provides methods
    to draw them in the scene. Supports both batch building from
    a full trajectory and progressive point-by-point addition.

    The trace uses small spheres as "breadcrumbs" along the path
    since NiceGUI's scene doesn't have a direct line API.

    Example:
        trace = TrajectoryTrace()
        # Progressive mode during animation:
        trace.add_point(pos1, Phase.FLIGHT)
        trace.add_point(pos2, Phase.FLIGHT)
        # Or batch mode:
        trace.build_from_trajectory(trajectory_points)
    """

    max_segments: int = DEFAULT_MAX_SEGMENTS
    segments: list[TraceSegment] = field(default_factory=list)
    visible: bool = True
    _last_point: Vec3 | None = None
    _scene_objects: list[Any] = field(default_factory=list)

    def add_segment(self, start: Vec3, end: Vec3, phase: Phase) -> None:
        """Add a segment to the trace.

        Args:
            start: Start position in scene coordinates.
            end: End position in scene coordinates.
            phase: Phase of this segment (determines color).
        """
        if len(self.segments) >= self.max_segments:
            return

        segment = TraceSegment(start=start, end=end, phase=phase)
        self.segments.append(segment)

    def add_point(self, position: Vec3, phase: Phase) -> None:
        """Add a point progressively during animation.

        Creates a segment from the previous point to this point.
        Call this for each animation frame to build trace progressively.

        Args:
            position: Current ball position in scene coordinates.
            phase: Current phase of ball motion.
        """
        if self._last_point is not None:
            self.add_segment(self._last_point, position, phase)

        self._last_point = position

    def build_from_trajectory(
        self,
        trajectory: list[TrajectoryPoint],
        sample_interval: int = 1,
    ) -> None:
        """Build trace from complete trajectory.

        Creates segments connecting all trajectory points.
        Use sample_interval to reduce segment count for long trajectories.

        Args:
            trajectory: List of trajectory points.
            sample_interval: Sample every Nth point (default 1 = all points).
        """
        from gc2_connect.open_range.visualization.range_scene import (
            feet_to_scene,
            yards_to_scene,
        )

        self.clear()

        if len(trajectory) < 2:
            return

        # Sample points based on interval
        sampled = trajectory[::sample_interval]
        # Ensure last point is included
        if trajectory[-1] not in sampled:
            sampled.append(trajectory[-1])

        # Convert to scene coordinates and create segments
        for i in range(len(sampled) - 1):
            p1 = sampled[i]
            p2 = sampled[i + 1]

            # Convert physics coords to scene coords
            # Physics X (forward) -> Scene Z
            # Physics Y (height) -> Scene Y
            # Physics Z (lateral) -> Scene X (negated)
            start = Vec3(
                x=-yards_to_scene(p1.z),
                y=feet_to_scene(p1.y),
                z=yards_to_scene(p1.x),
            )
            end = Vec3(
                x=-yards_to_scene(p2.z),
                y=feet_to_scene(p2.y),
                z=yards_to_scene(p2.x),
            )

            # Use the end point's phase for the segment
            self.add_segment(start, end, p2.phase)

    def clear(self) -> None:
        """Clear all trace segments and remove from scene."""
        # Remove scene objects
        for obj in self._scene_objects:
            try:
                obj.delete()
            except Exception:
                pass

        self.segments = []
        self._scene_objects = []
        self._last_point = None

    def set_visible(self, visible: bool) -> None:
        """Set trace visibility.

        Args:
            visible: Whether trace should be visible.
        """
        self.visible = visible

    def draw_in_scene(self, scene: Any) -> None:
        """Draw all segments in the scene.

        Uses small spheres as "breadcrumbs" to visualize the path.
        This approach works with NiceGUI's scene API which doesn't
        have a direct line primitive.

        Args:
            scene: NiceGUI scene to draw in.
        """
        if scene is None or not self.visible:
            return

        try:
            from nicegui import ui

            with scene:
                for segment in self.segments:
                    if segment.scene_object is not None:
                        continue

                    # Draw a small sphere at the end point of each segment
                    sphere = (
                        ui.scene.sphere(radius=TRACE_SPHERE_RADIUS)
                        .material(segment.color)
                        .move(segment.end.x, segment.end.y, segment.end.z)
                    )
                    segment.scene_object = sphere
                    self._scene_objects.append(sphere)
        except ImportError:
            pass

    def draw_segment_in_scene(self, scene: Any, segment: TraceSegment) -> None:
        """Draw a single segment in the scene.

        Args:
            scene: NiceGUI scene to draw in.
            segment: The segment to draw.
        """
        if scene is None or not self.visible:
            return

        if segment.scene_object is not None:
            return

        try:
            from nicegui import ui

            with scene:
                sphere = (
                    ui.scene.sphere(radius=TRACE_SPHERE_RADIUS)
                    .material(segment.color)
                    .move(segment.end.x, segment.end.y, segment.end.z)
                )
                segment.scene_object = sphere
                self._scene_objects.append(sphere)
        except ImportError:
            pass
