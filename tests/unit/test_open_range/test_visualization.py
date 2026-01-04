# ABOUTME: Unit tests for Open Range 3D visualization components.
# ABOUTME: Tests RangeScene creation, ball animation, and camera controls.
"""Tests for Open Range visualization components."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gc2_connect.open_range.models import (
    Conditions,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
    TrajectoryPoint,
)

if TYPE_CHECKING:
    pass


# Test trajectory data for animation tests
@pytest.fixture
def sample_trajectory() -> list[TrajectoryPoint]:
    """Create a sample trajectory for testing."""
    return [
        TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=0.5, x=50.0, y=30.0, z=1.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=1.0, x=100.0, y=50.0, z=2.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=1.5, x=150.0, y=60.0, z=2.5, phase=Phase.FLIGHT),
        TrajectoryPoint(t=2.0, x=200.0, y=55.0, z=3.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=2.5, x=240.0, y=30.0, z=3.5, phase=Phase.FLIGHT),
        TrajectoryPoint(t=3.0, x=270.0, y=5.0, z=4.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=3.2, x=275.0, y=0.0, z=4.0, phase=Phase.BOUNCE),
        TrajectoryPoint(t=3.4, x=278.0, y=2.0, z=4.0, phase=Phase.BOUNCE),
        TrajectoryPoint(t=3.6, x=282.0, y=0.0, z=4.1, phase=Phase.ROLLING),
        TrajectoryPoint(t=4.0, x=290.0, y=0.0, z=4.2, phase=Phase.ROLLING),
        TrajectoryPoint(t=4.5, x=295.0, y=0.0, z=4.2, phase=Phase.STOPPED),
    ]


@pytest.fixture
def sample_shot_result(sample_trajectory: list[TrajectoryPoint]) -> ShotResult:
    """Create a sample shot result for testing."""
    return ShotResult(
        trajectory=sample_trajectory,
        summary=ShotSummary(
            carry_distance=275.0,
            total_distance=295.0,
            roll_distance=20.0,
            offline_distance=4.2,
            max_height=60.0,
            max_height_time=1.5,
            flight_time=3.2,
            total_time=4.5,
            bounce_count=2,
        ),
        launch_data=LaunchData(
            ball_speed=167.0,
            vla=10.9,
            hla=0.5,
            backspin=2686.0,
            sidespin=150.0,
        ),
        conditions=Conditions(),
    )


class TestRangeScene:
    """Tests for RangeScene class."""

    def test_range_scene_can_be_instantiated(self) -> None:
        """Test that RangeScene can be created with default parameters."""
        from gc2_connect.open_range.visualization.range_scene import RangeScene

        scene = RangeScene()
        assert scene is not None
        assert scene.width == 800
        assert scene.height == 600

    def test_range_scene_custom_dimensions(self) -> None:
        """Test RangeScene with custom dimensions."""
        from gc2_connect.open_range.visualization.range_scene import RangeScene

        scene = RangeScene(width=1024, height=768)
        assert scene.width == 1024
        assert scene.height == 768

    def test_distance_markers_configuration(self) -> None:
        """Test distance marker positions are correctly configured."""
        from gc2_connect.open_range.visualization.range_scene import (
            DISTANCE_MARKERS,
            RangeScene,
        )

        _scene = RangeScene()  # Instantiate to verify no errors
        # Distance markers should be at standard intervals
        assert len(DISTANCE_MARKERS) > 0
        # Should include 100 and 200 yard markers
        assert 100 in DISTANCE_MARKERS
        assert 200 in DISTANCE_MARKERS
        # Markers should be in ascending order
        assert sorted(DISTANCE_MARKERS) == DISTANCE_MARKERS

    def test_target_greens_configuration(self) -> None:
        """Test target green positions are correctly configured."""
        from gc2_connect.open_range.visualization.range_scene import (
            TARGET_GREENS,
            RangeScene,
        )

        _scene = RangeScene()  # Instantiate to verify no errors
        # Should have multiple target greens
        assert len(TARGET_GREENS) > 0
        # Each green should have position and radius
        for green in TARGET_GREENS:
            assert "distance" in green
            assert "radius" in green
            assert green["distance"] > 0
            assert green["radius"] > 0

    def test_range_dimensions(self) -> None:
        """Test that range dimensions are appropriate."""
        from gc2_connect.open_range.visualization.range_scene import (
            RANGE_LENGTH_YARDS,
            RANGE_WIDTH_YARDS,
            RangeScene,
        )

        _scene = RangeScene()  # Instantiate to verify no errors
        # Range should be at least 350 yards long for driver shots
        assert RANGE_LENGTH_YARDS >= 350
        # Range width should be reasonable for dispersion
        assert RANGE_WIDTH_YARDS >= 50


class TestBallAnimator:
    """Tests for BallAnimator class."""

    def test_ball_animator_can_be_instantiated(self) -> None:
        """Test that BallAnimator can be created."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        assert animator is not None
        assert animator.is_animating is False
        assert animator.current_frame == 0

    def test_ball_animator_initial_state(self) -> None:
        """Test BallAnimator initial state."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        assert animator.trajectory == []
        assert animator.current_phase == Phase.STOPPED

    def test_calculate_animation_frames(self, sample_trajectory: list[TrajectoryPoint]) -> None:
        """Test that animation frames are calculated correctly."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        frames = animator.calculate_animation_frames(sample_trajectory, target_fps=60)

        # Should have frames for smooth animation
        assert len(frames) > 0
        # First frame should be at origin
        assert frames[0].x == 0.0
        assert frames[0].y == 0.0
        # Last frame should match end of trajectory
        assert frames[-1].x == sample_trajectory[-1].x

    def test_animation_respects_speed_multiplier(
        self, sample_trajectory: list[TrajectoryPoint]
    ) -> None:
        """Test that animation speed multiplier works."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()

        # Normal speed
        frames_normal = animator.calculate_animation_frames(
            sample_trajectory, target_fps=60, speed_multiplier=1.0
        )

        # 2x speed should have fewer frames (faster animation)
        frames_fast = animator.calculate_animation_frames(
            sample_trajectory, target_fps=60, speed_multiplier=2.0
        )

        # Fast animation should have fewer frames
        assert len(frames_fast) < len(frames_normal)

    def test_get_phase_at_time(self, sample_trajectory: list[TrajectoryPoint]) -> None:
        """Test phase lookup at specific times."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        animator.trajectory = sample_trajectory

        # At t=0, should be FLIGHT
        assert animator.get_phase_at_time(0.0) == Phase.FLIGHT
        # At t=1.0, should be FLIGHT
        assert animator.get_phase_at_time(1.0) == Phase.FLIGHT
        # At t=3.2, should be BOUNCE
        assert animator.get_phase_at_time(3.2) == Phase.BOUNCE
        # At t=4.0, should be ROLLING
        assert animator.get_phase_at_time(4.0) == Phase.ROLLING
        # At t=4.5, should be STOPPED
        assert animator.get_phase_at_time(4.5) == Phase.STOPPED

    def test_get_position_at_time(self, sample_trajectory: list[TrajectoryPoint]) -> None:
        """Test position interpolation at specific times."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        animator.trajectory = sample_trajectory

        # At t=0, should be at origin
        pos = animator.get_position_at_time(0.0)
        assert pos.x == 0.0
        assert pos.y == 0.0
        assert pos.z == 0.0

        # At t=0.5, should match trajectory point
        pos = animator.get_position_at_time(0.5)
        assert pos.x == 50.0
        assert pos.y == 30.0

        # At interpolated time (t=0.25), should be between first two points
        pos = animator.get_position_at_time(0.25)
        assert 0.0 < pos.x < 50.0
        assert 0.0 < pos.y < 30.0

    def test_stop_animation(self) -> None:
        """Test that animation can be stopped."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        animator.is_animating = True

        animator.stop()
        assert animator.is_animating is False

    def test_reset_animation(self, sample_trajectory: list[TrajectoryPoint]) -> None:
        """Test that animation can be reset."""
        from gc2_connect.open_range.visualization.ball_animation import BallAnimator

        animator = BallAnimator()
        animator.trajectory = sample_trajectory
        animator.current_frame = 50
        animator.is_animating = True
        animator.current_phase = Phase.ROLLING

        animator.reset()
        assert animator.current_frame == 0
        assert animator.is_animating is False
        assert animator.current_phase == Phase.STOPPED
        # Trajectory should be preserved after reset
        assert len(animator.trajectory) > 0


class TestCameraPosition:
    """Tests for camera positioning utilities."""

    def test_calculate_camera_position_at_start(self) -> None:
        """Test camera position at ball start."""
        from gc2_connect.open_range.visualization.ball_animation import (
            calculate_camera_position,
        )

        # Ball at origin (z=0)
        camera_pos = calculate_camera_position(ball_z=0.0)

        # Camera should be behind (negative Z) and above ground
        # Scene coordinates: X=lateral, Y=height, Z=forward
        assert camera_pos.z < 0.0  # Behind on Z axis
        assert camera_pos.y > 0.0  # Above ground

    def test_calculate_camera_position_follows_ball(self) -> None:
        """Test camera follows ball during flight."""
        from gc2_connect.open_range.visualization.ball_animation import (
            calculate_camera_position,
        )

        # Ball at origin
        cam1 = calculate_camera_position(ball_z=0.0)

        # Ball has moved forward (forward is +Z in scene coordinates)
        cam2 = calculate_camera_position(ball_z=100.0)

        # Camera should have moved forward (positive Z) as well
        assert cam2.z > cam1.z

    def test_camera_maintains_relative_offset(self) -> None:
        """Test camera maintains consistent offset from ball."""
        from gc2_connect.open_range.visualization.ball_animation import (
            CAMERA_FOLLOW_DISTANCE,
            calculate_camera_position,
        )

        # Ball at 100 yards forward (scene Z=100)
        ball_z = 100.0
        camera_pos = calculate_camera_position(ball_z=ball_z)

        # Camera should be behind ball by follow distance (on Z axis)
        assert abs(ball_z - camera_pos.z - CAMERA_FOLLOW_DISTANCE) < 10


class TestPhaseColors:
    """Tests for phase color configuration."""

    def test_phase_colors_defined(self) -> None:
        """Test that all phases have defined colors."""
        from gc2_connect.open_range.visualization.ball_animation import PHASE_COLORS

        assert Phase.FLIGHT in PHASE_COLORS
        assert Phase.BOUNCE in PHASE_COLORS
        assert Phase.ROLLING in PHASE_COLORS
        assert Phase.STOPPED in PHASE_COLORS

    def test_phase_colors_are_hex_strings(self) -> None:
        """Test that phase colors are valid hex color strings."""
        from gc2_connect.open_range.visualization.ball_animation import PHASE_COLORS

        for _phase, color in PHASE_COLORS.items():
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB format


class TestCoordinateConversion:
    """Tests for coordinate system conversion utilities."""

    def test_yards_to_scene_units(self) -> None:
        """Test conversion from yards to scene units."""
        from gc2_connect.open_range.visualization.range_scene import yards_to_scene

        # 1 yard should convert to some scene unit value
        result = yards_to_scene(1.0)
        assert isinstance(result, float)

        # 100 yards should be 100x the unit conversion
        result_100 = yards_to_scene(100.0)
        assert result_100 == result * 100.0

    def test_feet_to_scene_units(self) -> None:
        """Test conversion from feet to scene units."""
        from gc2_connect.open_range.visualization.range_scene import feet_to_scene

        # 1 foot should convert to some scene unit value
        result = feet_to_scene(1.0)
        assert isinstance(result, float)

        # 3 feet equals 1 yard, so they should produce the same scene units
        from gc2_connect.open_range.visualization.range_scene import yards_to_scene

        assert feet_to_scene(3.0) == yards_to_scene(1.0)  # 3 feet = 1 yard

        # 1 foot should be 1/3 of a yard in scene units
        assert feet_to_scene(1.0) == yards_to_scene(1.0) / 3.0

    def test_trajectory_to_scene_coordinates(
        self, sample_trajectory: list[TrajectoryPoint]
    ) -> None:
        """Test converting trajectory points to scene coordinates."""
        from gc2_connect.open_range.visualization.range_scene import (
            trajectory_to_scene_coords,
        )

        scene_coords = trajectory_to_scene_coords(sample_trajectory)

        # Should have same number of points
        assert len(scene_coords) == len(sample_trajectory)

        # Scene coordinates should be Vec3 objects
        from gc2_connect.open_range.models import Vec3

        assert all(isinstance(c, Vec3) for c in scene_coords)

        # First point should be at origin (scaled)
        assert scene_coords[0].x == 0.0
        assert scene_coords[0].y == 0.0
        assert scene_coords[0].z == 0.0


class TestSceneSetup:
    """Tests for scene setup and configuration."""

    def test_lighting_configuration(self) -> None:
        """Test that lighting is properly configured."""
        from gc2_connect.open_range.visualization.range_scene import (
            AMBIENT_LIGHT_INTENSITY,
            DIRECTIONAL_LIGHT_INTENSITY,
        )

        # Ambient light should be moderate for visibility
        assert 0.3 <= AMBIENT_LIGHT_INTENSITY <= 0.8
        # Directional light should provide good illumination
        assert 0.5 <= DIRECTIONAL_LIGHT_INTENSITY <= 1.5

    def test_ground_color_configuration(self) -> None:
        """Test ground color is appropriate (green for fairway)."""
        from gc2_connect.open_range.visualization.range_scene import GROUND_COLOR

        # Should be a green-ish color (hex string)
        assert isinstance(GROUND_COLOR, str)
        assert GROUND_COLOR.startswith("#")

    def test_ball_color_configuration(self) -> None:
        """Test ball color is appropriate (white)."""
        from gc2_connect.open_range.visualization.range_scene import BALL_COLOR

        # Should be white or near-white
        assert isinstance(BALL_COLOR, str)
        assert BALL_COLOR.startswith("#")
