# ABOUTME: Unit tests for Open Range minimap component.
# ABOUTME: Tests minimap configuration, rendering setup, and position tracking.
"""Tests for Open Range minimap component."""

from __future__ import annotations

import pytest

from gc2_connect.open_range.models import Vec3


class TestMinimapRenderer:
    """Tests for MinimapRenderer class."""

    def test_minimap_renderer_can_be_instantiated(self) -> None:
        """Test that MinimapRenderer can be created."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        assert renderer is not None

    def test_minimap_renderer_default_dimensions(self) -> None:
        """Test MinimapRenderer has appropriate default dimensions."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        assert renderer.width == 200
        assert renderer.height == 200

    def test_minimap_renderer_custom_dimensions(self) -> None:
        """Test MinimapRenderer with custom dimensions."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer(width=250, height=250)
        assert renderer.width == 250
        assert renderer.height == 250

    def test_minimap_renderer_has_camera_position(self) -> None:
        """Test MinimapRenderer has camera position configured."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        # Should have a high camera for top-down view
        assert renderer.camera_height >= 150.0

    def test_minimap_renderer_update_ball_position(self) -> None:
        """Test updating ball position for minimap."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        ball_pos = Vec3(x=5.0, y=10.0, z=150.0)

        renderer.update_ball_position(ball_pos)
        assert renderer.ball_position == ball_pos

    def test_minimap_renderer_update_target_position(self) -> None:
        """Test updating target position for minimap."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        target_pos = Vec3(x=0.0, y=0.0, z=275.0)

        renderer.update_target_position(target_pos)
        assert renderer.target_position == target_pos


class TestMinimapCameraCalculations:
    """Tests for minimap camera position calculations."""

    def test_get_camera_center(self) -> None:
        """Test getting camera center position for minimap."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        renderer.update_ball_position(Vec3(x=0.0, y=0.0, z=50.0))
        renderer.update_target_position(Vec3(x=0.0, y=0.0, z=250.0))

        center = renderer.get_camera_center()
        # Should be centered between ball and target on Z axis
        assert center.z == pytest.approx(150.0, abs=1.0)

    def test_get_zoom_level_close_shot(self) -> None:
        """Test zoom level for close distance shots."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        renderer.update_ball_position(Vec3(x=0.0, y=0.0, z=0.0))
        renderer.update_target_position(Vec3(x=0.0, y=0.0, z=100.0))

        zoom = renderer.get_zoom_level()
        assert zoom >= 50.0  # Minimum zoom

    def test_get_zoom_level_far_shot(self) -> None:
        """Test zoom level for long distance shots."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        renderer.update_ball_position(Vec3(x=0.0, y=0.0, z=0.0))
        renderer.update_target_position(Vec3(x=0.0, y=0.0, z=300.0))

        zoom = renderer.get_zoom_level()
        assert zoom <= 150.0  # Maximum zoom

    def test_zoom_scales_with_distance(self) -> None:
        """Test that zoom level scales with ball-to-target distance."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()

        # Short distance
        renderer.update_ball_position(Vec3(x=0.0, y=0.0, z=0.0))
        renderer.update_target_position(Vec3(x=0.0, y=0.0, z=100.0))
        zoom_short = renderer.get_zoom_level()

        # Long distance
        renderer.update_target_position(Vec3(x=0.0, y=0.0, z=300.0))
        zoom_long = renderer.get_zoom_level()

        # Longer distance should have larger zoom (wider view)
        assert zoom_long > zoom_short


class TestMinimapStyling:
    """Tests for minimap visual styling configuration."""

    def test_minimap_has_background_color(self) -> None:
        """Test minimap has background color configured."""
        from gc2_connect.open_range.visualization.minimap import (
            MINIMAP_BACKGROUND_COLOR,
        )

        assert isinstance(MINIMAP_BACKGROUND_COLOR, str)
        # Should be a valid color specification
        assert len(MINIMAP_BACKGROUND_COLOR) > 0

    def test_minimap_has_border_color(self) -> None:
        """Test minimap has border color configured."""
        from gc2_connect.open_range.visualization.minimap import MINIMAP_BORDER_COLOR

        assert isinstance(MINIMAP_BORDER_COLOR, str)

    def test_minimap_has_ball_marker_color(self) -> None:
        """Test minimap has ball marker color configured."""
        from gc2_connect.open_range.visualization.minimap import MINIMAP_BALL_COLOR

        assert isinstance(MINIMAP_BALL_COLOR, str)
        # Should be a hex color
        assert MINIMAP_BALL_COLOR.startswith("#")

    def test_minimap_has_target_marker_color(self) -> None:
        """Test minimap has target marker color configured."""
        from gc2_connect.open_range.visualization.minimap import MINIMAP_TARGET_COLOR

        assert isinstance(MINIMAP_TARGET_COLOR, str)


class TestMinimapMarkerPositions:
    """Tests for converting positions to minimap coordinates."""

    def test_world_to_minimap_coordinates(self) -> None:
        """Test converting world coordinates to minimap pixel coordinates."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer(width=200, height=200)
        renderer.update_ball_position(Vec3(x=0.0, y=0.0, z=0.0))
        renderer.update_target_position(Vec3(x=0.0, y=0.0, z=200.0))

        # Ball at origin should be at top of minimap (near Z=0)
        ball_screen = renderer.world_to_minimap(renderer.ball_position)
        assert 0 <= ball_screen.x <= 200
        assert 0 <= ball_screen.y <= 200

    def test_world_to_minimap_ball_and_target_different(self) -> None:
        """Test ball and target have different minimap positions."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer(width=200, height=200)
        ball_pos = Vec3(x=0.0, y=0.0, z=50.0)
        target_pos = Vec3(x=0.0, y=0.0, z=250.0)

        renderer.update_ball_position(ball_pos)
        renderer.update_target_position(target_pos)

        ball_screen = renderer.world_to_minimap(ball_pos)
        target_screen = renderer.world_to_minimap(target_pos)

        # They should be at different Y positions (Z maps to Y on minimap)
        assert ball_screen.y != target_screen.y


class TestMinimapVisibility:
    """Tests for minimap visibility controls."""

    def test_minimap_visible_by_default(self) -> None:
        """Test minimap is visible by default."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        assert renderer.visible is True

    def test_minimap_can_be_hidden(self) -> None:
        """Test minimap visibility can be toggled."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        renderer.set_visible(False)
        assert renderer.visible is False

        renderer.set_visible(True)
        assert renderer.visible is True


class TestMinimapTrajectoryMarkers:
    """Tests for trajectory landing markers on minimap."""

    def test_add_landing_marker(self) -> None:
        """Test adding a landing marker to minimap."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        landing_pos = Vec3(x=5.0, y=0.0, z=275.0)

        renderer.add_landing_marker(landing_pos)
        assert len(renderer.landing_markers) == 1
        assert renderer.landing_markers[0] == landing_pos

    def test_add_multiple_landing_markers(self) -> None:
        """Test adding multiple landing markers for dispersion view."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()

        for i in range(5):
            pos = Vec3(x=float(i - 2), y=0.0, z=270.0 + i * 2)
            renderer.add_landing_marker(pos)

        assert len(renderer.landing_markers) == 5

    def test_clear_landing_markers(self) -> None:
        """Test clearing all landing markers."""
        from gc2_connect.open_range.visualization.minimap import MinimapRenderer

        renderer = MinimapRenderer()
        renderer.add_landing_marker(Vec3(x=0.0, y=0.0, z=275.0))
        renderer.add_landing_marker(Vec3(x=2.0, y=0.0, z=280.0))

        renderer.clear_landing_markers()
        assert len(renderer.landing_markers) == 0

    def test_landing_marker_limit(self) -> None:
        """Test that landing markers have a maximum count."""
        from gc2_connect.open_range.visualization.minimap import (
            MAX_LANDING_MARKERS,
            MinimapRenderer,
        )

        renderer = MinimapRenderer()

        # Add more than the limit
        for i in range(MAX_LANDING_MARKERS + 10):
            renderer.add_landing_marker(Vec3(x=0.0, y=0.0, z=200.0 + i))

        # Should be capped at maximum
        assert len(renderer.landing_markers) <= MAX_LANDING_MARKERS
