# ABOUTME: Unit tests for Open Range camera system with multiple view presets.
# ABOUTME: Tests camera modes, presets, transitions, and minimap configuration.
"""Tests for Open Range camera system components."""

from __future__ import annotations

import pytest

from gc2_connect.open_range.models import Vec3


class TestCameraMode:
    """Tests for CameraMode enum."""

    def test_camera_mode_enum_exists(self) -> None:
        """Test that CameraMode enum is defined with expected values."""
        from gc2_connect.open_range.visualization.camera import CameraMode

        # Should have at least 5 camera modes
        modes = list(CameraMode)
        assert len(modes) >= 5

    def test_camera_mode_has_behind_ball(self) -> None:
        """Test that BEHIND_BALL mode exists."""
        from gc2_connect.open_range.visualization.camera import CameraMode

        assert hasattr(CameraMode, "BEHIND_BALL")

    def test_camera_mode_has_tee_box(self) -> None:
        """Test that TEE_BOX mode exists."""
        from gc2_connect.open_range.visualization.camera import CameraMode

        assert hasattr(CameraMode, "TEE_BOX")

    def test_camera_mode_has_follow(self) -> None:
        """Test that FOLLOW mode exists."""
        from gc2_connect.open_range.visualization.camera import CameraMode

        assert hasattr(CameraMode, "FOLLOW")

    def test_camera_mode_has_overhead(self) -> None:
        """Test that OVERHEAD mode exists."""
        from gc2_connect.open_range.visualization.camera import CameraMode

        assert hasattr(CameraMode, "OVERHEAD")

    def test_camera_mode_has_green(self) -> None:
        """Test that GREEN mode exists."""
        from gc2_connect.open_range.visualization.camera import CameraMode

        assert hasattr(CameraMode, "GREEN")


class TestCameraPreset:
    """Tests for CameraPreset dataclass."""

    def test_camera_preset_dataclass_exists(self) -> None:
        """Test that CameraPreset dataclass is defined."""
        from gc2_connect.open_range.visualization.camera import CameraPreset

        preset = CameraPreset(
            name="Test",
            position=Vec3(x=0.0, y=10.0, z=-20.0),
            look_at=Vec3(x=0.0, y=0.0, z=100.0),
            is_dynamic=False,
        )
        assert preset.name == "Test"
        assert preset.position.y == 10.0
        assert preset.look_at.z == 100.0
        assert preset.is_dynamic is False

    def test_camera_preset_has_required_fields(self) -> None:
        """Test that CameraPreset has all required fields."""
        from gc2_connect.open_range.visualization.camera import CameraPreset

        preset = CameraPreset(
            name="Test",
            position=Vec3(x=0.0, y=10.0, z=-20.0),
            look_at=Vec3(x=0.0, y=0.0, z=100.0),
            is_dynamic=True,
        )
        assert hasattr(preset, "name")
        assert hasattr(preset, "position")
        assert hasattr(preset, "look_at")
        assert hasattr(preset, "is_dynamic")


class TestCameraPresets:
    """Tests for predefined camera presets."""

    def test_get_preset_for_behind_ball(self) -> None:
        """Test getting the behind ball camera preset."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_camera_preset,
        )

        preset = get_camera_preset(CameraMode.BEHIND_BALL)
        assert preset is not None
        assert preset.name == "Behind Ball"
        # Should be behind the ball (negative Z in scene coords)
        assert preset.position.z < 0

    def test_get_preset_for_tee_box(self) -> None:
        """Test getting the tee box camera preset."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_camera_preset,
        )

        preset = get_camera_preset(CameraMode.TEE_BOX)
        assert preset is not None
        assert preset.name == "Tee Box"
        # Should be at eye level height (around 1.5-2 yards)
        assert 1.0 <= preset.position.y <= 25.0

    def test_get_preset_for_follow(self) -> None:
        """Test getting the follow camera preset."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_camera_preset,
        )

        preset = get_camera_preset(CameraMode.FOLLOW)
        assert preset is not None
        assert preset.name == "Follow"
        # Follow camera should be dynamic
        assert preset.is_dynamic is True

    def test_get_preset_for_overhead(self) -> None:
        """Test getting the overhead camera preset."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_camera_preset,
        )

        preset = get_camera_preset(CameraMode.OVERHEAD)
        assert preset is not None
        assert preset.name == "Overhead"
        # Should be high above the ground
        assert preset.position.y >= 50.0

    def test_get_preset_for_green(self) -> None:
        """Test getting the green camera preset."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_camera_preset,
        )

        preset = get_camera_preset(CameraMode.GREEN)
        assert preset is not None
        assert preset.name == "Green"
        # Should be positioned forward (positive Z) looking back
        assert preset.position.z > 0
        assert preset.look_at.z < preset.position.z

    def test_all_modes_have_presets(self) -> None:
        """Test that all camera modes have associated presets."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_camera_preset,
        )

        for mode in CameraMode:
            preset = get_camera_preset(mode)
            assert preset is not None, f"Mode {mode} has no preset"


class TestCameraController:
    """Tests for CameraController class."""

    def test_camera_controller_can_be_instantiated(self) -> None:
        """Test that CameraController can be created."""
        from gc2_connect.open_range.visualization.camera import CameraController

        controller = CameraController()
        assert controller is not None

    def test_camera_controller_initial_mode(self) -> None:
        """Test CameraController initial mode is TEE_BOX."""
        from gc2_connect.open_range.visualization.camera import (
            CameraController,
            CameraMode,
        )

        controller = CameraController()
        assert controller.current_mode == CameraMode.TEE_BOX

    def test_camera_controller_set_mode(self) -> None:
        """Test setting camera mode."""
        from gc2_connect.open_range.visualization.camera import (
            CameraController,
            CameraMode,
        )

        controller = CameraController()
        controller.set_mode(CameraMode.OVERHEAD)
        assert controller.current_mode == CameraMode.OVERHEAD

    def test_camera_controller_cycle_mode(self) -> None:
        """Test cycling through camera modes."""
        from gc2_connect.open_range.visualization.camera import (
            CameraController,
            CameraMode,
        )

        controller = CameraController()
        initial_mode = controller.current_mode

        # Cycle through all modes
        modes_seen = {initial_mode}
        for _ in range(len(CameraMode)):
            controller.cycle_mode()
            modes_seen.add(controller.current_mode)

        # Should have cycled through all modes
        assert len(modes_seen) == len(CameraMode)

    def test_camera_controller_get_current_position(self) -> None:
        """Test getting current camera position."""
        from gc2_connect.open_range.visualization.camera import (
            CameraController,
            CameraMode,
        )

        controller = CameraController()
        controller.set_mode(CameraMode.TEE_BOX)

        position, look_at = controller.get_camera_position()
        assert isinstance(position, Vec3)
        assert isinstance(look_at, Vec3)

    def test_camera_controller_get_position_for_follow_mode(self) -> None:
        """Test getting camera position for follow mode with ball position."""
        from gc2_connect.open_range.visualization.camera import (
            CameraController,
            CameraMode,
        )

        controller = CameraController()
        controller.set_mode(CameraMode.FOLLOW)

        # Without ball position, should use default
        pos1, _ = controller.get_camera_position()

        # With ball position, should follow the ball
        ball_pos = Vec3(x=0.0, y=20.0, z=150.0)
        pos2, look_at2 = controller.get_camera_position(ball_position=ball_pos)

        # Follow camera should look at or near the ball
        assert look_at2.z >= 0  # Looking forward

    def test_camera_controller_get_preset_name(self) -> None:
        """Test getting human-readable preset name."""
        from gc2_connect.open_range.visualization.camera import (
            CameraController,
            CameraMode,
        )

        controller = CameraController()
        controller.set_mode(CameraMode.OVERHEAD)

        name = controller.get_current_preset_name()
        assert name == "Overhead"


class TestDynamicCameraCalculation:
    """Tests for dynamic camera position calculations."""

    def test_calculate_follow_camera_position(self) -> None:
        """Test follow camera calculation follows the ball."""
        from gc2_connect.open_range.visualization.camera import (
            calculate_follow_camera_position,
        )

        # Ball at origin
        ball_pos1 = Vec3(x=0.0, y=10.0, z=0.0)
        cam1, _ = calculate_follow_camera_position(ball_pos1)

        # Ball moved forward
        ball_pos2 = Vec3(x=0.0, y=10.0, z=100.0)
        cam2, _ = calculate_follow_camera_position(ball_pos2)

        # Camera should move forward with ball
        assert cam2.z > cam1.z

    def test_calculate_follow_camera_maintains_height(self) -> None:
        """Test follow camera maintains consistent height above ball."""
        from gc2_connect.open_range.visualization.camera import (
            calculate_follow_camera_position,
        )

        ball_pos = Vec3(x=0.0, y=10.0, z=100.0)
        cam_pos, _ = calculate_follow_camera_position(ball_pos)

        # Camera should be above the ball
        assert cam_pos.y > ball_pos.y

    def test_calculate_follow_camera_behind_ball(self) -> None:
        """Test follow camera stays behind the ball."""
        from gc2_connect.open_range.visualization.camera import (
            calculate_follow_camera_position,
        )

        ball_pos = Vec3(x=0.0, y=10.0, z=100.0)
        cam_pos, _ = calculate_follow_camera_position(ball_pos)

        # Camera Z should be less than ball Z (behind it)
        assert cam_pos.z < ball_pos.z

    def test_calculate_overhead_camera_position(self) -> None:
        """Test overhead camera position calculation."""
        from gc2_connect.open_range.visualization.camera import (
            calculate_overhead_camera_position,
        )

        ball_pos = Vec3(x=5.0, y=10.0, z=150.0)
        cam_pos, look_at = calculate_overhead_camera_position(ball_pos)

        # Camera should be directly above, looking down
        assert cam_pos.y > 50.0  # High up
        # Look at should be below camera
        assert look_at.y < cam_pos.y


class TestCameraSmoothTransition:
    """Tests for smooth camera transitions."""

    def test_interpolate_camera_position(self) -> None:
        """Test camera position interpolation."""
        from gc2_connect.open_range.visualization.camera import (
            interpolate_camera_position,
        )

        start = Vec3(x=0.0, y=10.0, z=-20.0)
        end = Vec3(x=0.0, y=50.0, z=100.0)

        # At t=0, should be at start
        result = interpolate_camera_position(start, end, t=0.0)
        assert result.x == start.x
        assert result.y == start.y
        assert result.z == start.z

        # At t=1, should be at end
        result = interpolate_camera_position(start, end, t=1.0)
        assert result.x == end.x
        assert result.y == end.y
        assert result.z == end.z

        # At t=0.5, should be midpoint
        result = interpolate_camera_position(start, end, t=0.5)
        assert result.y == pytest.approx(30.0, abs=0.1)
        assert result.z == pytest.approx(40.0, abs=0.1)

    def test_interpolate_clamps_t_value(self) -> None:
        """Test that interpolation clamps t value to [0, 1]."""
        from gc2_connect.open_range.visualization.camera import (
            interpolate_camera_position,
        )

        start = Vec3(x=0.0, y=0.0, z=0.0)
        end = Vec3(x=10.0, y=10.0, z=10.0)

        # t < 0 should clamp to start
        result = interpolate_camera_position(start, end, t=-0.5)
        assert result.x == start.x

        # t > 1 should clamp to end
        result = interpolate_camera_position(start, end, t=1.5)
        assert result.x == end.x


class TestMinimapConfiguration:
    """Tests for minimap configuration constants."""

    def test_minimap_dimensions(self) -> None:
        """Test minimap has appropriate dimensions."""
        from gc2_connect.open_range.visualization.camera import (
            MINIMAP_HEIGHT,
            MINIMAP_WIDTH,
        )

        # Minimap should be square-ish and reasonably sized
        assert 150 <= MINIMAP_WIDTH <= 300
        assert 150 <= MINIMAP_HEIGHT <= 300

    def test_minimap_camera_height(self) -> None:
        """Test minimap camera height is sufficient for top-down view."""
        from gc2_connect.open_range.visualization.camera import MINIMAP_CAMERA_HEIGHT

        # Camera should be high enough to see the entire range
        assert MINIMAP_CAMERA_HEIGHT >= 150.0

    def test_minimap_zoom_range(self) -> None:
        """Test minimap zoom configuration."""
        from gc2_connect.open_range.visualization.camera import (
            MINIMAP_MAX_ZOOM,
            MINIMAP_MIN_ZOOM,
        )

        # Min zoom should be less than max
        assert MINIMAP_MIN_ZOOM < MINIMAP_MAX_ZOOM
        # Reasonable zoom range for golf distances
        assert MINIMAP_MIN_ZOOM >= 30
        assert MINIMAP_MAX_ZOOM <= 200


class TestMinimapCameraCalculation:
    """Tests for minimap camera calculations."""

    def test_calculate_minimap_center(self) -> None:
        """Test minimap center calculation between ball and target."""
        from gc2_connect.open_range.visualization.camera import calculate_minimap_center

        ball_pos = Vec3(x=0.0, y=0.0, z=50.0)
        target_pos = Vec3(x=0.0, y=0.0, z=200.0)

        center = calculate_minimap_center(ball_pos, target_pos)

        # Center should be midpoint on X and Z
        assert center.x == pytest.approx(0.0, abs=0.1)
        assert center.z == pytest.approx(125.0, abs=0.1)

    def test_calculate_minimap_zoom(self) -> None:
        """Test minimap zoom scales with distance."""
        from gc2_connect.open_range.visualization.camera import calculate_minimap_zoom

        # Close shot - tighter zoom
        ball_pos_close = Vec3(x=0.0, y=0.0, z=50.0)
        target_close = Vec3(x=0.0, y=0.0, z=100.0)
        zoom_close = calculate_minimap_zoom(ball_pos_close, target_close)

        # Far shot - wider zoom
        ball_pos_far = Vec3(x=0.0, y=0.0, z=50.0)
        target_far = Vec3(x=0.0, y=0.0, z=300.0)
        zoom_far = calculate_minimap_zoom(ball_pos_far, target_far)

        # Far shot should have larger zoom (wider view)
        assert zoom_far > zoom_close


class TestCameraConstants:
    """Tests for camera system constants."""

    def test_follow_camera_constants(self) -> None:
        """Test follow camera constants are reasonable."""
        from gc2_connect.open_range.visualization.camera import (
            FOLLOW_CAMERA_DISTANCE,
            FOLLOW_CAMERA_HEIGHT,
            FOLLOW_CAMERA_LATERAL,
        )

        # Distance behind ball
        assert 20.0 <= FOLLOW_CAMERA_DISTANCE <= 60.0
        # Height above ground
        assert 10.0 <= FOLLOW_CAMERA_HEIGHT <= 40.0
        # Lateral offset
        assert 0.0 <= FOLLOW_CAMERA_LATERAL <= 20.0

    def test_overhead_camera_constants(self) -> None:
        """Test overhead camera constants are reasonable."""
        from gc2_connect.open_range.visualization.camera import OVERHEAD_CAMERA_HEIGHT

        # Should be high enough for bird's eye view
        assert OVERHEAD_CAMERA_HEIGHT >= 60.0

    def test_green_camera_constants(self) -> None:
        """Test green camera constants are reasonable."""
        from gc2_connect.open_range.visualization.camera import (
            GREEN_CAMERA_DISTANCE,
            GREEN_CAMERA_HEIGHT,
        )

        # Distance from green center
        assert GREEN_CAMERA_DISTANCE > 0.0
        # Height above ground (eye level for view from green)
        assert 1.0 <= GREEN_CAMERA_HEIGHT <= 10.0


class TestCameraModeNames:
    """Tests for camera mode display names."""

    def test_get_mode_display_name(self) -> None:
        """Test getting display names for camera modes."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_mode_display_name,
        )

        # Each mode should have a human-readable display name
        for mode in CameraMode:
            name = get_mode_display_name(mode)
            assert isinstance(name, str)
            assert len(name) > 0

    def test_mode_display_names_are_unique(self) -> None:
        """Test that all mode display names are unique."""
        from gc2_connect.open_range.visualization.camera import (
            CameraMode,
            get_mode_display_name,
        )

        names = [get_mode_display_name(mode) for mode in CameraMode]
        assert len(names) == len(set(names))
