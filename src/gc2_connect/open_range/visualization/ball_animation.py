# ABOUTME: Ball flight animation along trajectory path for Open Range.
# ABOUTME: Handles smooth animation with phase transitions and camera following.
"""Ball flight animation for Open Range visualization.

This module provides:
- BallAnimator: Animates ball along trajectory
- Phase indicators with color coding
- Camera following utilities
- Position interpolation

Animation phases:
- FLIGHT: Ball in air (green color)
- BOUNCE: Ground contact (orange color)
- ROLLING: Ball rolling (blue color)
- STOPPED: Ball at rest (gray color)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gc2_connect.open_range.models import Phase, TrajectoryPoint, Vec3

if TYPE_CHECKING:
    from gc2_connect.open_range.models import ShotResult
    from gc2_connect.open_range.visualization.range_scene import RangeScene


# Phase colors (hex strings for Three.js materials)
PHASE_COLORS: dict[Phase, str] = {
    Phase.FLIGHT: "#00ff88",  # Green - ball in flight
    Phase.BOUNCE: "#ff8844",  # Orange - ground contact
    Phase.ROLLING: "#00d4ff",  # Blue - rolling
    Phase.STOPPED: "#888888",  # Gray - at rest
}

# Camera configuration
CAMERA_FOLLOW_DISTANCE: float = 30.0  # Yards behind ball
CAMERA_HEIGHT_OFFSET: float = 15.0  # Feet above ball
CAMERA_LATERAL_OFFSET: float = 5.0  # Yards to side for better view

# Animation configuration
DEFAULT_TARGET_FPS: int = 60
DEFAULT_SPEED_MULTIPLIER: float = 1.0


@dataclass
class AnimationFrame:
    """Single frame of ball animation."""

    position: Vec3
    phase: Phase
    time: float


def calculate_camera_position(ball_z: float) -> Vec3:
    """Calculate camera position to track ball along the range.

    The camera stays at a fixed lateral position and height,
    moving only along the Z axis (forward) to track the ball.
    This prevents the scene from rotating during animation.

    Scene coordinate system:
    - X: Lateral (+ = right)
    - Y: Height
    - Z: Forward (+ = away from tee)

    Args:
        ball_z: Ball's Z position (forward distance) in scene coordinates.

    Returns:
        Camera position in scene coordinates.
    """
    return Vec3(
        x=CAMERA_LATERAL_OFFSET,  # Fixed lateral offset from center
        y=CAMERA_HEIGHT_OFFSET,  # Fixed height
        z=max(ball_z - CAMERA_FOLLOW_DISTANCE, -CAMERA_FOLLOW_DISTANCE),  # Behind the ball
    )


def calculate_camera_look_at(ball_z: float) -> Vec3:
    """Calculate where camera should look.

    Looks at a point along the center of the range at the ball's Z distance.
    This keeps the ground stable and prevents rotation.

    Args:
        ball_z: Ball's Z position (forward distance) in scene coordinates.

    Returns:
        Look-at position in scene coordinates.
    """
    return Vec3(
        x=0.0,  # Look at center of range
        y=5.0,  # Look slightly above ground
        z=ball_z + 50.0,  # Look ahead of ball
    )


class BallAnimator:
    """Animates ball along trajectory path.

    Handles smooth animation of the golf ball from launch to rest,
    with phase transitions and optional camera following.

    The animator interpolates between trajectory points to create
    smooth 60fps animation from the sparse trajectory data.

    Example:
        animator = BallAnimator()
        frames = animator.calculate_animation_frames(trajectory)
        await animator.animate_shot(result, scene)
    """

    def __init__(self) -> None:
        """Initialize the ball animator."""
        self.trajectory: list[TrajectoryPoint] = []
        self.current_frame: int = 0
        self.is_animating: bool = False
        self.current_phase: Phase = Phase.STOPPED
        self._animation_task: asyncio.Task[None] | None = None

    def calculate_animation_frames(
        self,
        trajectory: list[TrajectoryPoint],
        target_fps: int = DEFAULT_TARGET_FPS,
        speed_multiplier: float = DEFAULT_SPEED_MULTIPLIER,
    ) -> list[Vec3]:
        """Calculate interpolated animation frames.

        Converts sparse trajectory points into smooth animation frames
        at the target frame rate.

        Args:
            trajectory: Trajectory points from physics simulation.
            target_fps: Target frames per second for animation.
            speed_multiplier: Animation speed multiplier (2.0 = 2x speed).

        Returns:
            List of Vec3 positions for each animation frame.
        """
        if not trajectory:
            return []

        # Calculate total animation duration
        total_time = trajectory[-1].t
        if total_time <= 0:
            return [Vec3(x=trajectory[0].x, y=trajectory[0].y, z=trajectory[0].z)]

        # Calculate frame interval based on speed
        frame_interval = (1.0 / target_fps) * speed_multiplier

        # Generate frames at regular intervals
        frames: list[Vec3] = []
        current_time = 0.0

        while current_time <= total_time:
            pos = self._interpolate_position(trajectory, current_time)
            frames.append(pos)
            current_time += frame_interval

        # Ensure last frame matches end of trajectory
        if frames and frames[-1].x != trajectory[-1].x:
            frames.append(Vec3(x=trajectory[-1].x, y=trajectory[-1].y, z=trajectory[-1].z))

        return frames

    def _interpolate_position(self, trajectory: list[TrajectoryPoint], time: float) -> Vec3:
        """Interpolate position at a specific time.

        Args:
            trajectory: Trajectory points.
            time: Time to interpolate at.

        Returns:
            Interpolated position as Vec3.
        """
        if not trajectory:
            return Vec3(x=0.0, y=0.0, z=0.0)

        # Find surrounding points
        if time <= trajectory[0].t:
            return Vec3(x=trajectory[0].x, y=trajectory[0].y, z=trajectory[0].z)

        if time >= trajectory[-1].t:
            return Vec3(x=trajectory[-1].x, y=trajectory[-1].y, z=trajectory[-1].z)

        # Find the two points to interpolate between
        for i in range(len(trajectory) - 1):
            p1 = trajectory[i]
            p2 = trajectory[i + 1]

            if p1.t <= time <= p2.t:
                # Linear interpolation factor
                dt = p2.t - p1.t
                t = 0.0 if dt == 0 else (time - p1.t) / dt

                return Vec3(
                    x=p1.x + t * (p2.x - p1.x),
                    y=p1.y + t * (p2.y - p1.y),
                    z=p1.z + t * (p2.z - p1.z),
                )

        # Fallback to last point
        return Vec3(x=trajectory[-1].x, y=trajectory[-1].y, z=trajectory[-1].z)

    def get_phase_at_time(self, time: float) -> Phase:
        """Get the ball phase at a specific time.

        Args:
            time: Time in seconds since launch.

        Returns:
            Phase at the given time.
        """
        if not self.trajectory:
            return Phase.STOPPED

        # Find the point at or just before the given time
        for i in range(len(self.trajectory) - 1, -1, -1):
            if self.trajectory[i].t <= time:
                return self.trajectory[i].phase

        return self.trajectory[0].phase

    def get_position_at_time(self, time: float) -> Vec3:
        """Get the ball position at a specific time.

        Args:
            time: Time in seconds since launch.

        Returns:
            Position at the given time.
        """
        return self._interpolate_position(self.trajectory, time)

    async def animate_shot(
        self,
        result: ShotResult,
        scene: RangeScene | None = None,
        speed: float = DEFAULT_SPEED_MULTIPLIER,
        on_phase_change: Callable[[Phase], None] | None = None,
    ) -> None:
        """Animate ball along trajectory.

        Plays the complete ball animation from launch to rest,
        updating the scene and calling phase change callbacks.

        Args:
            result: Shot result with trajectory data.
            scene: RangeScene to animate in (optional).
            speed: Animation speed multiplier.
            on_phase_change: Callback when phase changes.
        """
        self.trajectory = result.trajectory
        self.is_animating = True
        self.current_frame = 0
        self.current_phase = Phase.FLIGHT

        if not self.trajectory:
            self.is_animating = False
            return

        # Calculate animation frames
        frames = self.calculate_animation_frames(self.trajectory, speed_multiplier=speed)

        # Frame timing
        frame_delay = (1.0 / DEFAULT_TARGET_FPS) / speed

        last_phase = Phase.FLIGHT
        for i, frame_pos in enumerate(frames):
            if not self.is_animating:
                break

            self.current_frame = i

            # Calculate time at this frame
            total_time = self.trajectory[-1].t
            frame_time = (i / len(frames)) * total_time

            # Get phase at this time
            current_phase = self.get_phase_at_time(frame_time)
            self.current_phase = current_phase

            # Notify phase change
            if current_phase != last_phase:
                if on_phase_change is not None:
                    on_phase_change(current_phase)
                last_phase = current_phase

            # Update scene
            if scene is not None:
                from gc2_connect.open_range.visualization.range_scene import (
                    feet_to_scene,
                    yards_to_scene,
                )

                # Convert physics coordinates to scene coordinates:
                # Physics X (forward) -> Scene Z
                # Physics Y (height) -> Scene Y
                # Physics Z (lateral) -> Scene X
                scene_pos = Vec3(
                    x=yards_to_scene(frame_pos.z),  # Physics lateral -> Scene X
                    y=feet_to_scene(frame_pos.y),  # Height stays Y
                    z=yards_to_scene(frame_pos.x),  # Physics forward -> Scene Z
                )
                scene.update_ball_position(scene_pos)

                # Update camera to track ball along range
                # Camera moves along Z axis, keeping stable view (no rotation)
                camera_pos = calculate_camera_position(scene_pos.z)
                look_at = calculate_camera_look_at(scene_pos.z)
                scene.update_camera(camera_pos, look_at)

            # Wait for next frame
            await asyncio.sleep(frame_delay)

        self.is_animating = False
        self.current_phase = Phase.STOPPED

    def stop(self) -> None:
        """Stop the current animation."""
        self.is_animating = False
        if self._animation_task is not None:
            self._animation_task.cancel()
            self._animation_task = None

    def reset(self) -> None:
        """Reset animation to initial state.

        Preserves trajectory data but resets frame counter
        and animation state.
        """
        self.current_frame = 0
        self.is_animating = False
        self.current_phase = Phase.STOPPED
        if self._animation_task is not None:
            self._animation_task.cancel()
            self._animation_task = None
