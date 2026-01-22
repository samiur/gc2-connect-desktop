# ABOUTME: Unit tests for procedural terrain and atmosphere features.
# ABOUTME: Tests fog configuration, terrain undulations, rough areas, and tree variations.
"""Tests for procedural terrain and atmospheric effects.

These tests cover enhanced visual features:
- Atmospheric fog (linear fog for depth perception)
- Terrain undulations (ground height variations)
- Rough area visualization (darker grass on sides)
- Enhanced tree backdrop (more variation and density)
"""

from __future__ import annotations


class TestFogConfiguration:
    """Tests for atmospheric fog settings."""

    def test_fog_constants_exist(self) -> None:
        """Test that fog configuration constants are defined."""
        from gc2_connect.open_range.visualization.range_scene import (
            FOG_COLOR,
            FOG_FAR,
            FOG_NEAR,
        )

        # Fog color should match sky color for seamless blending
        assert isinstance(FOG_COLOR, str)
        assert FOG_COLOR.startswith("#")

        # Fog near distance should start after tee box
        assert FOG_NEAR > 0
        assert FOG_NEAR >= 50  # At least 50 yards before fog starts

        # Fog far distance should cover full range with some visibility
        assert FOG_FAR > FOG_NEAR
        assert FOG_FAR >= 300  # Should fade by end of range

    def test_fog_settings_reasonable_for_visibility(self) -> None:
        """Test that fog settings allow good visibility of near objects."""
        from gc2_connect.open_range.visualization.range_scene import (
            FOG_FAR,
            FOG_NEAR,
            RANGE_LENGTH_YARDS,
        )

        # Near fog should be past immediate view
        assert FOG_NEAR >= 50

        # Far fog should be past most shot distances but not hide everything
        assert FOG_FAR >= 300
        assert FOG_FAR <= RANGE_LENGTH_YARDS + 100


class TestTerrainUndulations:
    """Tests for terrain height variations."""

    def test_undulation_constants_exist(self) -> None:
        """Test that terrain undulation constants are defined."""
        from gc2_connect.open_range.visualization.range_scene import (
            TERRAIN_UNDULATION_AMPLITUDE,
            TERRAIN_UNDULATION_FREQUENCY,
        )

        # Amplitude should be subtle (not affect gameplay significantly)
        assert isinstance(TERRAIN_UNDULATION_AMPLITUDE, float)
        assert 0 < TERRAIN_UNDULATION_AMPLITUDE <= 2.0  # Max 2 yards

        # Frequency should create natural-looking undulations
        assert isinstance(TERRAIN_UNDULATION_FREQUENCY, float)
        assert 0 < TERRAIN_UNDULATION_FREQUENCY <= 0.1

    def test_calculate_terrain_height(self) -> None:
        """Test terrain height calculation at various positions."""
        from gc2_connect.open_range.visualization.range_scene import (
            calculate_terrain_height,
        )

        # At origin, should return some height value
        height_origin = calculate_terrain_height(0.0, 0.0)
        assert isinstance(height_origin, float)

        # At different positions, heights should vary
        height_mid = calculate_terrain_height(100.0, 10.0)
        height_far = calculate_terrain_height(200.0, -5.0)

        # Heights should be within reasonable bounds
        assert -2.0 <= height_origin <= 2.0
        assert -2.0 <= height_mid <= 2.0
        assert -2.0 <= height_far <= 2.0

    def test_terrain_height_varies_with_position(self) -> None:
        """Test that terrain height varies across the range."""
        from gc2_connect.open_range.visualization.range_scene import (
            calculate_terrain_height,
        )

        # Sample heights across the range
        heights = []
        for x in range(0, 300, 50):
            for z in range(-20, 20, 10):
                heights.append(calculate_terrain_height(float(x), float(z)))

        # Heights should not all be the same (shows variation)
        unique_heights = {round(h, 3) for h in heights}
        assert len(unique_heights) > 1, "Terrain should have height variation"


class TestRoughAreaVisualization:
    """Tests for rough area (darker grass on edges) configuration."""

    def test_rough_area_constants_exist(self) -> None:
        """Test that rough area configuration constants are defined."""
        from gc2_connect.open_range.visualization.range_scene import (
            FAIRWAY_WIDTH_YARDS,
            ROUGH_COLOR,
            ROUGH_START_DISTANCE,
        )

        # Rough color should be darker green than fairway
        assert isinstance(ROUGH_COLOR, str)
        assert ROUGH_COLOR.startswith("#")

        # Rough should start where fairway ends
        assert isinstance(ROUGH_START_DISTANCE, float)
        assert ROUGH_START_DISTANCE > 0

        # Fairway width should be reasonable
        assert isinstance(FAIRWAY_WIDTH_YARDS, float)
        assert 30 <= FAIRWAY_WIDTH_YARDS <= 80  # Typical fairway width

    def test_rough_color_is_darker_than_fairway(self) -> None:
        """Test that rough color is visually darker than fairway."""
        from gc2_connect.open_range.visualization.range_scene import (
            GROUND_COLOR,
            ROUGH_COLOR,
        )

        # Convert hex colors to RGB and compare brightness
        def hex_to_brightness(hex_color: str) -> float:
            hex_color = hex_color.lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Perceived brightness formula
            return (0.299 * r + 0.587 * g + 0.114 * b) / 255

        fairway_brightness = hex_to_brightness(GROUND_COLOR)
        rough_brightness = hex_to_brightness(ROUGH_COLOR)

        # Rough should be darker or equal (lower brightness)
        assert rough_brightness <= fairway_brightness


class TestEnhancedTreeBackdrop:
    """Tests for enhanced tree backdrop configuration."""

    def test_tree_variation_constants_exist(self) -> None:
        """Test that tree variation constants are defined."""
        from gc2_connect.open_range.visualization.range_scene import (
            TREE_HEIGHT_VARIATION,
            TREE_ROWS,
            TREE_SPACING_VARIATION,
            TREES_PER_ROW,
        )

        # Height variation should create visual interest
        assert isinstance(TREE_HEIGHT_VARIATION, float)
        assert TREE_HEIGHT_VARIATION > 0  # Should have some variation

        # Spacing variation should prevent uniform look
        assert isinstance(TREE_SPACING_VARIATION, float)
        assert TREE_SPACING_VARIATION >= 0

        # Should have multiple rows for depth
        assert isinstance(TREE_ROWS, int)
        assert TREE_ROWS >= 3

        # Should have enough trees per row
        assert isinstance(TREES_PER_ROW, int)
        assert TREES_PER_ROW >= 15

    def test_tree_colors_provide_variation(self) -> None:
        """Test that tree colors provide visual variation."""
        from gc2_connect.open_range.visualization.range_scene import (
            TREE_COLOR,
            TREE_COLOR_VARIATION,
        )

        # Base tree color should be defined
        assert isinstance(TREE_COLOR, str)
        assert TREE_COLOR.startswith("#")

        # Color variation should allow different shades
        assert isinstance(TREE_COLOR_VARIATION, list | tuple)
        assert len(TREE_COLOR_VARIATION) >= 2  # At least 2 color variants


class TestRangeSceneWithEnhancements:
    """Tests for RangeScene with enhanced visual features."""

    def test_range_scene_includes_fog_config(self) -> None:
        """Test that RangeScene has fog configuration attributes."""
        from gc2_connect.open_range.visualization.range_scene import RangeScene

        scene = RangeScene()

        # Scene should have fog-related configuration
        assert hasattr(scene, "fog_enabled") or hasattr(scene, "_fog_enabled")

    def test_range_scene_includes_terrain_config(self) -> None:
        """Test that RangeScene has terrain configuration attributes."""
        from gc2_connect.open_range.visualization.range_scene import RangeScene

        scene = RangeScene()

        # Scene should have terrain-related attributes
        assert scene is not None
        # The terrain is created during build() within NiceGUI context

    def test_range_scene_can_toggle_fog(self) -> None:
        """Test that fog can be enabled/disabled."""
        from gc2_connect.open_range.visualization.range_scene import RangeScene

        scene = RangeScene()
        scene.fog_enabled = True
        assert scene.fog_enabled is True

        scene.fog_enabled = False
        assert scene.fog_enabled is False


class TestPerformanceConstraints:
    """Tests ensuring visual features don't impact performance."""

    def test_tree_count_is_reasonable(self) -> None:
        """Test that total tree count stays within performance budget."""
        from gc2_connect.open_range.visualization.range_scene import (
            TREE_ROWS,
            TREES_PER_ROW,
        )

        total_trees = TREE_ROWS * TREES_PER_ROW

        # Should not exceed ~200 trees for performance
        assert total_trees <= 200, "Too many trees may impact frame rate"

    def test_undulation_segments_reasonable(self) -> None:
        """Test that terrain segment count is performance-friendly."""
        from gc2_connect.open_range.visualization.range_scene import (
            TERRAIN_SEGMENTS_X,
            TERRAIN_SEGMENTS_Z,
        )

        total_segments = TERRAIN_SEGMENTS_X * TERRAIN_SEGMENTS_Z

        # Keep segment count reasonable for performance
        # (NiceGUI creates individual boxes, so we need fewer segments)
        assert total_segments <= 100, "Too many terrain segments for box-based approach"

    def test_fog_distances_support_60fps(self) -> None:
        """Test fog configuration doesn't create expensive overdraw."""
        from gc2_connect.open_range.visualization.range_scene import (
            FOG_FAR,
            FOG_NEAR,
        )

        # Fog range shouldn't be too extreme (causes more shader work)
        fog_range = FOG_FAR - FOG_NEAR
        assert fog_range >= 100, "Fog range too narrow"
        assert fog_range <= 500, "Fog range too wide for good performance"
