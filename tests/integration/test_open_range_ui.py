# ABOUTME: Integration tests for Open Range UI components.
# ABOUTME: Tests mode selector, Open Range view, phase indicators, and shot data display.
"""Integration tests for Open Range UI components.

Tests the UI components that make up the Open Range view:
- ModeSelector: Toggle between GSPro and Open Range modes
- OpenRangeView: Main Open Range visualization panel
- Phase indicators with color coding
- Shot data display with metrics
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gc2_connect.open_range.models import (
    Conditions,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
    TrajectoryPoint,
)
from gc2_connect.services.shot_router import AppMode


# Test fixtures for Open Range UI tests
@pytest.fixture
def sample_trajectory() -> list[TrajectoryPoint]:
    """Create a sample trajectory for testing."""
    return [
        TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=0.5, x=50.0, y=30.0, z=1.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=1.0, x=100.0, y=50.0, z=2.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=2.0, x=200.0, y=40.0, z=3.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=3.0, x=270.0, y=5.0, z=4.0, phase=Phase.BOUNCE),
        TrajectoryPoint(t=3.5, x=285.0, y=0.0, z=4.0, phase=Phase.ROLLING),
        TrajectoryPoint(t=4.0, x=295.0, y=0.0, z=4.2, phase=Phase.STOPPED),
    ]


@pytest.fixture
def sample_shot_result(sample_trajectory: list[TrajectoryPoint]) -> ShotResult:
    """Create a sample shot result for testing."""
    return ShotResult(
        trajectory=sample_trajectory,
        summary=ShotSummary(
            carry_distance=270.0,
            total_distance=295.0,
            roll_distance=25.0,
            offline_distance=4.2,
            max_height=50.0,
            max_height_time=1.0,
            flight_time=3.0,
            total_time=4.0,
            bounce_count=1,
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


class TestModeSelector:
    """Tests for ModeSelector component."""

    def test_mode_selector_can_be_instantiated(self) -> None:
        """Test that ModeSelector can be created with a callback."""
        from gc2_connect.ui.components.mode_selector import ModeSelector

        callback = AsyncMock()
        selector = ModeSelector(on_change=callback)
        assert selector is not None
        assert selector.current_mode == AppMode.GSPRO

    def test_mode_selector_default_mode_is_gspro(self) -> None:
        """Test that default mode is GSPro."""
        from gc2_connect.ui.components.mode_selector import ModeSelector

        callback = AsyncMock()
        selector = ModeSelector(on_change=callback)
        assert selector.current_mode == AppMode.GSPRO

    def test_mode_selector_can_set_mode(self) -> None:
        """Test that mode can be changed programmatically."""
        from gc2_connect.ui.components.mode_selector import ModeSelector

        callback = AsyncMock()
        selector = ModeSelector(on_change=callback)

        # Set to Open Range mode
        selector.set_mode(AppMode.OPEN_RANGE)
        assert selector.current_mode == AppMode.OPEN_RANGE

        # Set back to GSPro
        selector.set_mode(AppMode.GSPRO)
        assert selector.current_mode == AppMode.GSPRO


class TestOpenRangeView:
    """Tests for OpenRangeView component."""

    def test_open_range_view_can_be_instantiated(self) -> None:
        """Test that OpenRangeView can be created."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        assert view is not None
        assert view.current_phase == Phase.STOPPED

    def test_open_range_view_initial_state(self) -> None:
        """Test OpenRangeView initial state."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        assert view.range_scene is None
        assert view.animator is None

    def test_open_range_view_phase_update(self) -> None:
        """Test that phase can be updated."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()

        # Initial phase is STOPPED
        assert view.current_phase == Phase.STOPPED

        # Update to FLIGHT
        view.update_phase(Phase.FLIGHT)
        assert view.current_phase == Phase.FLIGHT

        # Update to BOUNCE
        view.update_phase(Phase.BOUNCE)
        assert view.current_phase == Phase.BOUNCE


class TestPhaseIndicator:
    """Tests for phase indicator functionality."""

    def test_phase_colors_are_distinct(self) -> None:
        """Test that each phase has a distinct color."""
        from gc2_connect.ui.components.open_range_view import PHASE_COLORS

        colors = list(PHASE_COLORS.values())
        # All colors should be unique
        assert len(colors) == len(set(colors))

    def test_all_phases_have_colors(self) -> None:
        """Test that all phases have assigned colors."""
        from gc2_connect.ui.components.open_range_view import PHASE_COLORS

        assert Phase.FLIGHT in PHASE_COLORS
        assert Phase.BOUNCE in PHASE_COLORS
        assert Phase.ROLLING in PHASE_COLORS
        assert Phase.STOPPED in PHASE_COLORS

    def test_phase_colors_are_valid_tailwind_classes(self) -> None:
        """Test that phase colors are valid Tailwind CSS classes."""
        from gc2_connect.ui.components.open_range_view import PHASE_COLORS

        for color_class in PHASE_COLORS.values():
            # Should be a Tailwind text color class
            assert color_class.startswith("text-")


class TestShotDataDisplay:
    """Tests for shot data display panel."""

    def test_shot_data_display_values(self, sample_shot_result: ShotResult) -> None:
        """Test that shot data is formatted correctly."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        # Get formatted data
        data = view.format_shot_summary(sample_shot_result.summary)

        # Check key metrics are present
        assert "carry_distance" in data
        assert "total_distance" in data
        assert "roll_distance" in data
        assert "offline_distance" in data
        assert "max_height" in data

        # Verify values are numeric strings
        assert isinstance(data["carry_distance"], str)
        assert "270" in data["carry_distance"]

    def test_launch_data_display_values(self, sample_shot_result: ShotResult) -> None:
        """Test that launch data is formatted correctly."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        data = view.format_launch_data(sample_shot_result.launch_data)

        # Check key metrics are present
        assert "ball_speed" in data
        assert "vla" in data
        assert "hla" in data
        assert "backspin" in data
        assert "sidespin" in data

        # Verify ball speed value
        assert "167" in data["ball_speed"]

    def test_conditions_display_values(self, sample_shot_result: ShotResult) -> None:
        """Test that conditions data is formatted correctly."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        data = view.format_conditions(sample_shot_result.conditions)

        # Check key conditions are present
        assert "temp_f" in data
        assert "elevation_ft" in data
        assert "wind_speed_mph" in data

        # Verify default temperature
        assert "70" in data["temp_f"]


class TestModeIntegration:
    """Integration tests for mode switching."""

    @pytest.mark.asyncio
    async def test_mode_switch_callback_invoked(self) -> None:
        """Test that mode change callback is invoked on switch."""
        from gc2_connect.ui.components.mode_selector import ModeSelector

        callback = AsyncMock()
        selector = ModeSelector(on_change=callback)

        # Simulate mode change
        await selector._on_mode_changed(AppMode.OPEN_RANGE)

        callback.assert_called_once_with(AppMode.OPEN_RANGE)

    @pytest.mark.asyncio
    async def test_mode_switch_updates_state(self) -> None:
        """Test that mode switch updates internal state."""
        from gc2_connect.ui.components.mode_selector import ModeSelector

        callback = AsyncMock()
        selector = ModeSelector(on_change=callback)

        await selector._on_mode_changed(AppMode.OPEN_RANGE)
        assert selector.current_mode == AppMode.OPEN_RANGE

        await selector._on_mode_changed(AppMode.GSPRO)
        assert selector.current_mode == AppMode.GSPRO


class TestOpenRangeViewWithShot:
    """Tests for OpenRangeView shot display."""

    def test_update_shot_data_stores_result(self, sample_shot_result: ShotResult) -> None:
        """Test that shot result is stored when updated."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        view.update_shot_data(sample_shot_result)

        assert view.last_shot_result is not None
        assert view.last_shot_result.summary.carry_distance == 270.0

    def test_format_distance_with_units(self) -> None:
        """Test distance formatting with units."""
        from gc2_connect.ui.components.open_range_view import format_distance

        # Test basic formatting
        assert format_distance(275.5) == "275.5 yds"
        assert format_distance(100.0) == "100.0 yds"
        assert format_distance(0.0) == "0.0 yds"

    def test_format_height_with_units(self) -> None:
        """Test height formatting with units."""
        from gc2_connect.ui.components.open_range_view import format_height

        # Test basic formatting
        assert format_height(50.5) == "50.5 ft"
        assert format_height(100.0) == "100.0 ft"

    def test_format_offline_with_direction(self) -> None:
        """Test offline distance formatting with direction."""
        from gc2_connect.ui.components.open_range_view import format_offline

        # Positive = right
        assert "R" in format_offline(5.0) or "right" in format_offline(5.0).lower()
        # Negative = left
        assert "L" in format_offline(-5.0) or "left" in format_offline(-5.0).lower()
        # Zero = straight
        assert format_offline(0.0) == "0.0 yds"
