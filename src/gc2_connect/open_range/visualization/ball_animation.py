# ABOUTME: Ball flight animation along trajectory path for Open Range.
# ABOUTME: Handles smooth animation with phase transitions and camera following.
"""Ball flight animation for Open Range visualization.

This module provides:
- BallAnimator: Animates ball along trajectory
- Phase indicators with color coding
- Camera following utilities with multiple camera modes
- Position interpolation

Animation phases:
- FLIGHT: Ball in air (green color)
- BOUNCE: Ground contact (orange color)
- ROLLING: Ball rolling (blue color)
- STOPPED: Ball at rest (gray color)

Camera modes:
- BEHIND_BALL: Low angle behind the ball
- TEE_BOX: Eye-level view from behind tee
- FOLLOW: Dynamic camera following ball during flight
- OVERHEAD: Bird's eye view for dispersion
- GREEN: View from landing area looking back
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gc2_connect.open_range.models import Phase, TrajectoryPoint, Vec3
from gc2_connect.open_range.visualization.camera import (
    FOLLOW_CAMERA_DISTANCE,
    FOLLOW_CAMERA_HEIGHT,
    FOLLOW_CAMERA_LATERAL,
    CameraController,
    CameraMode,
)

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

# Camera timing configuration
CAMERA_FOLLOW_DELAY: float = 0.5  # Seconds to wait before camera starts following
CAMERA_END_DELAY: float = 2.0  # Seconds to show final position before resetting

# Legacy camera constants (re-exported from camera module for backwards compatibility)
CAMERA_FOLLOW_DISTANCE: float = FOLLOW_CAMERA_DISTANCE
CAMERA_HEIGHT_OFFSET: float = FOLLOW_CAMERA_HEIGHT
CAMERA_LATERAL_OFFSET: float = FOLLOW_CAMERA_LATERAL

# Animation configuration
DEFAULT_TARGET_FPS: int = 60
DEFAULT_SPEED_MULTIPLIER: float = 1.0


@dataclass
class AnimationFrame:
    """Single frame of ball animation."""

    position: Vec3
    phase: Phase
    time: float


def get_tee_box_camera() -> tuple[Vec3, Vec3]:
    """Get the default tee box camera position and look-at.

    Returns:
        Tuple of (camera_position, look_at_position) for tee box view.
    """
    camera_pos = Vec3(
        x=CAMERA_LATERAL_OFFSET,  # Offset to the right
        y=CAMERA_HEIGHT_OFFSET,  # Above ground
        z=-CAMERA_FOLLOW_DISTANCE,  # Behind tee
    )
    look_at = Vec3(
        x=0.0,  # Center of range
        y=5.0,  # Slightly above ground
        z=100.0,  # Looking down range
    )
    return camera_pos, look_at


def calculate_follow_camera(ball_z: float, target_z: float) -> tuple[Vec3, Vec3]:
    """Calculate camera position and look-at to follow ball along range.

    The camera smoothly follows the ball, staying behind it and looking
    ahead. Uses fixed height and lateral position to prevent rotation.

    Scene coordinate system:
    - X: Lateral (+ = right)
    - Y: Height
    - Z: Forward (+ = away from tee)

    Args:
        ball_z: Ball's current Z position (forward distance) in scene units.
        target_z: Where to look at on the Z axis.

    Returns:
        Tuple of (camera_position, look_at_position) in scene coordinates.
    """
    # Camera follows behind the ball, but stays at a minimum distance back
    camera_z = max(ball_z - CAMERA_FOLLOW_DISTANCE, -CAMERA_FOLLOW_DISTANCE)

    camera_pos = Vec3(
        x=CAMERA_LATERAL_OFFSET,  # Fixed lateral offset
        y=CAMERA_HEIGHT_OFFSET,  # Fixed height
        z=camera_z,  # Follow the ball
    )

    # Look ahead of the ball position
    look_at = Vec3(
        x=0.0,  # Center of range
        y=5.0,  # Slightly above ground
        z=target_z + 30.0,  # Look ahead of target
    )

    return camera_pos, look_at


class BallAnimator:
    """Animates ball along trajectory path.

    Handles smooth animation of the golf ball from launch to rest,
    with phase transitions and configurable camera modes.

    The animator interpolates between trajectory points to create
    smooth 60fps animation from the sparse trajectory data.

    Camera behavior is controlled by the CameraController, which
    supports multiple view modes (tee box, follow, overhead, etc.).

    Example:
        animator = BallAnimator()
        animator.set_camera_mode(CameraMode.FOLLOW)
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
        self._camera_controller: CameraController = CameraController()

    @property
    def camera_mode(self) -> CameraMode:
        """Get current camera mode."""
        return self._camera_controller.current_mode

    def set_camera_mode(self, mode: CameraMode) -> None:
        """Set the camera mode.

        Args:
            mode: The camera mode to switch to.
        """
        self._camera_controller.set_mode(mode)

    def cycle_camera_mode(self) -> CameraMode:
        """Cycle to the next camera mode.

        Returns:
            The new camera mode after cycling.
        """
        self._camera_controller.cycle_mode()
        return self._camera_controller.current_mode

    def get_camera_mode_name(self) -> str:
        """Get the display name of the current camera mode.

        Returns:
            Human-readable name of current mode.
        """
        return self._camera_controller.get_current_preset_name()

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
        return self._camera_controller.get_camera_position(ball_position)

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
        draw_trace: bool = True,
        trace_sample_interval: int = 3,
    ) -> None:
        """Animate ball along trajectory with configurable camera and trace.

        Camera behavior depends on the current camera mode:
        - TEE_BOX/BEHIND_BALL: Static view from behind the tee
        - FOLLOW: Tracks ball during flight, returns to tee after
        - OVERHEAD: Bird's eye view, good for dispersion
        - GREEN: View from landing area looking back

        Trace behavior:
        - Trace is drawn progressively as ball moves
        - Each phase gets a different color (flight=green, bounce=orange, roll=blue)
        - Trace remains visible after animation completes

        Args:
            result: Shot result with trajectory data.
            scene: RangeScene to animate in (optional).
            speed: Animation speed multiplier.
            on_phase_change: Callback when phase changes.
            draw_trace: Whether to draw trajectory trace (default True).
            trace_sample_interval: Draw trace point every N frames (default 3).
        """
        self.trajectory = result.trajectory
        self.is_animating = True
        self.current_frame = 0
        self.current_phase = Phase.FLIGHT

        if not self.trajectory:
            self.is_animating = False
            return

        # Clear any existing trace before starting new animation
        if scene is not None and draw_trace:
            scene.clear_trajectory_line()

        # Calculate animation frames
        frames = self.calculate_animation_frames(self.trajectory, speed_multiplier=speed)

        # Frame timing
        frame_delay = (1.0 / DEFAULT_TARGET_FPS) / speed
        total_time = self.trajectory[-1].t

        # Calculate when camera should start following (in animation time)
        follow_start_time = CAMERA_FOLLOW_DELAY / speed

        # Set initial camera position based on current mode
        if scene is not None:
            initial_cam_pos, initial_cam_look = self._camera_controller.get_camera_position()
            scene.update_camera(initial_cam_pos, initial_cam_look)

        last_phase = Phase.FLIGHT

        for i, frame_pos in enumerate(frames):
            if not self.is_animating:
                break

            self.current_frame = i

            # Calculate time at this frame
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
                # Physics Z (lateral) -> Scene X (negated: physics +Z is right, scene -X is right)
                scene_pos = Vec3(
                    x=-yards_to_scene(frame_pos.z),  # Physics lateral -> Scene X (negated)
                    y=feet_to_scene(frame_pos.y),  # Height stays Y
                    z=yards_to_scene(frame_pos.x),  # Physics forward -> Scene Z
                )
                scene.update_ball_position(scene_pos)

                # Draw trace point progressively (every N frames for performance)
                if draw_trace and i % trace_sample_interval == 0:
                    scene.add_trajectory_point(scene_pos, current_phase)

                # Update camera based on current mode
                # For FOLLOW mode, camera tracks ball after initial delay
                # For other modes, camera stays static
                current_mode = self._camera_controller.current_mode
                if current_mode == CameraMode.FOLLOW and frame_time >= follow_start_time:
                    camera_pos, look_at = self._camera_controller.get_camera_position(
                        ball_position=scene_pos
                    )
                    scene.update_camera(camera_pos, look_at)
                elif current_mode in (CameraMode.TEE_BOX, CameraMode.BEHIND_BALL):
                    # Static modes - no update needed during animation
                    pass
                elif current_mode == CameraMode.OVERHEAD:
                    # For overhead, optionally track ball (center on ball)
                    camera_pos, look_at = self._camera_controller.get_camera_position(
                        ball_position=scene_pos
                    )
                    # Only update occasionally for overhead to avoid jitter
                    if i % 10 == 0:
                        scene.update_camera(camera_pos, look_at)

            # Wait for next frame
            await asyncio.sleep(frame_delay)

        # Hold on final position (trace remains visible)
        if scene is not None and self.is_animating:
            await asyncio.sleep(CAMERA_END_DELAY / speed)

            # Reset camera to initial mode position
            reset_cam_pos, reset_cam_look = self._camera_controller.get_camera_position()
            scene.update_camera(reset_cam_pos, reset_cam_look)

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
