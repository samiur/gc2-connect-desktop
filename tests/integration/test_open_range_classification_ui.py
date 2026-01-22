# ABOUTME: Integration tests for Open Range shot classification UI.
# ABOUTME: Tests shot name, rank badge, color coding, and derived data display.
"""Integration tests for Open Range shot classification UI.

Tests the UI components that display shot classification data from OpenGolfCoach:
- Shot name display (e.g., "Straight", "Push Slice")
- Rank badge with color coding (S+, S, A, B, C, D, E)
- Graceful handling of missing derived data
"""

from __future__ import annotations

import pytest

from gc2_connect.open_range.models import (
    Conditions,
    DerivedShotData,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
    TrajectoryPoint,
)


# Test fixtures for classification UI tests
@pytest.fixture
def sample_trajectory() -> list[TrajectoryPoint]:
    """Create a sample trajectory for testing."""
    return [
        TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=1.0, x=100.0, y=50.0, z=2.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=2.0, x=200.0, y=30.0, z=3.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=3.0, x=270.0, y=0.0, z=4.0, phase=Phase.STOPPED),
    ]


@pytest.fixture
def sample_derived_data() -> DerivedShotData:
    """Create sample derived data with all fields populated."""
    return DerivedShotData(
        shot_name="Straight",
        shot_rank="A",
        shot_color_rgb="#22C55E",
        smash_factor=1.48,
        estimated_club_speed_mph=112.0,
        estimated_club_path_deg=0.5,
        estimated_face_angle_deg=0.3,
        ogc_carry_distance=268.5,
        ogc_total_distance=292.0,
    )


@pytest.fixture
def shot_result_with_derived(
    sample_trajectory: list[TrajectoryPoint],
    sample_derived_data: DerivedShotData,
) -> ShotResult:
    """Create a shot result with derived data for testing."""
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
        derived=sample_derived_data,
    )


@pytest.fixture
def shot_result_without_derived(sample_trajectory: list[TrajectoryPoint]) -> ShotResult:
    """Create a shot result without derived data for testing."""
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
        derived=None,
    )


class TestRankColors:
    """Tests for rank color mapping."""

    def test_rank_colors_exist(self) -> None:
        """Test that RANK_COLORS mapping exists."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        assert RANK_COLORS is not None
        assert isinstance(RANK_COLORS, dict)

    def test_all_ranks_have_colors(self) -> None:
        """Test that all ranks have assigned colors."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        expected_ranks = ["S+", "S", "A", "B", "C", "D", "E"]
        for rank in expected_ranks:
            assert rank in RANK_COLORS, f"Missing color for rank {rank}"

    def test_rank_colors_are_valid_tailwind_classes(self) -> None:
        """Test that rank colors are valid Tailwind CSS classes."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        for rank, color_class in RANK_COLORS.items():
            # Should be a Tailwind color class
            assert color_class.startswith("text-") or color_class.startswith(
                "bg-"
            ), f"Invalid color class for rank {rank}: {color_class}"

    def test_rank_colors_are_distinct(self) -> None:
        """Test that each rank has a distinct color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        colors = list(RANK_COLORS.values())
        assert len(colors) == len(set(colors)), "Rank colors should be distinct"


class TestShotClassificationDisplay:
    """Tests for shot classification display functionality."""

    def test_format_shot_classification_with_derived(
        self, shot_result_with_derived: ShotResult
    ) -> None:
        """Test that classification data is formatted correctly with derived data."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        classification = view.format_shot_classification(shot_result_with_derived.derived)

        assert classification is not None
        assert "shot_name" in classification
        assert "shot_rank" in classification
        assert classification["shot_name"] == "Straight"
        assert classification["shot_rank"] == "A"

    def test_format_shot_classification_without_derived(
        self, shot_result_without_derived: ShotResult
    ) -> None:
        """Test that classification returns None when derived data is missing."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        classification = view.format_shot_classification(shot_result_without_derived.derived)

        assert classification is None

    def test_get_rank_color_for_valid_ranks(self) -> None:
        """Test that get_rank_color returns correct colors for valid ranks."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()

        # Test each rank
        for rank in ["S+", "S", "A", "B", "C", "D", "E"]:
            color = view.get_rank_color(rank)
            assert color is not None
            assert color.startswith("text-") or color.startswith("bg-")

    def test_get_rank_color_for_unknown_rank(self) -> None:
        """Test that get_rank_color returns default for unknown rank."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        color = view.get_rank_color("Unknown")

        # Should return a default gray color
        assert color is not None
        assert "gray" in color.lower() or "400" in color


class TestShotClassificationPanel:
    """Tests for shot classification panel component."""

    def test_view_has_classification_labels(self) -> None:
        """Test that OpenRangeView has classification label references."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()

        # Should have classification-related label attributes
        assert hasattr(view, "_shot_name_label")
        assert hasattr(view, "_shot_rank_label")

    def test_update_shot_classification_with_derived(
        self, shot_result_with_derived: ShotResult
    ) -> None:
        """Test that classification is updated when shot has derived data."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        view.update_shot_data(shot_result_with_derived)

        # Derived data should be stored
        assert view.last_shot_result is not None
        assert view.last_shot_result.derived is not None
        assert view.last_shot_result.derived.shot_name == "Straight"
        assert view.last_shot_result.derived.shot_rank == "A"

    def test_update_shot_classification_without_derived(
        self, shot_result_without_derived: ShotResult
    ) -> None:
        """Test that classification handles missing derived data gracefully."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        view.update_shot_data(shot_result_without_derived)

        # Should not raise, derived should be None
        assert view.last_shot_result is not None
        assert view.last_shot_result.derived is None


class TestSmashFactorDisplay:
    """Tests for smash factor display."""

    def test_format_smash_factor_with_value(self, sample_derived_data: DerivedShotData) -> None:
        """Test that smash factor is formatted correctly when present."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        formatted = view.format_smash_factor(sample_derived_data.smash_factor)

        assert formatted is not None
        assert "1.48" in formatted

    def test_format_smash_factor_with_none(self) -> None:
        """Test that smash factor returns placeholder when None."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        formatted = view.format_smash_factor(None)

        assert formatted is not None
        assert "--" in formatted or "N/A" in formatted


class TestRankBadgeColors:
    """Tests for rank badge color coding specification."""

    def test_s_plus_is_gold_color(self) -> None:
        """Test that S+ rank has gold/yellow color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("S+", "")
        # Gold is typically yellow-500/600 or amber in Tailwind
        assert (
            "yellow" in color.lower() or "amber" in color.lower() or "gold" in color.lower()
        ), f"S+ should be gold-ish, got {color}"

    def test_s_is_silver_color(self) -> None:
        """Test that S rank has silver/gray color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("S", "")
        # Silver is typically gray/slate
        assert (
            "gray" in color.lower() or "slate" in color.lower() or "silver" in color.lower()
        ), f"S should be silver-ish, got {color}"

    def test_a_is_green_color(self) -> None:
        """Test that A rank has green color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("A", "")
        assert "green" in color.lower(), f"A should be green, got {color}"

    def test_b_is_blue_color(self) -> None:
        """Test that B rank has blue color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("B", "")
        assert "blue" in color.lower(), f"B should be blue, got {color}"

    def test_c_is_purple_color(self) -> None:
        """Test that C rank has purple color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("C", "")
        assert (
            "purple" in color.lower() or "violet" in color.lower()
        ), f"C should be purple, got {color}"

    def test_d_is_orange_color(self) -> None:
        """Test that D rank has orange color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("D", "")
        assert "orange" in color.lower(), f"D should be orange, got {color}"

    def test_e_is_red_color(self) -> None:
        """Test that E rank has red color."""
        from gc2_connect.ui.components.open_range_view import RANK_COLORS

        color = RANK_COLORS.get("E", "")
        assert "red" in color.lower(), f"E should be red, got {color}"


class TestClassificationReset:
    """Tests for resetting classification display."""

    def test_reset_clears_classification_state(self, shot_result_with_derived: ShotResult) -> None:
        """Test that reset clears classification data."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        # First update with shot data
        view.update_shot_data(shot_result_with_derived)
        assert view.last_shot_result is not None

        # Reset should clear
        view.reset()
        assert view.last_shot_result is None


class TestDerivedDataDisplay:
    """Tests for displaying all derived data fields."""

    def test_format_derived_summary_with_data(self, sample_derived_data: DerivedShotData) -> None:
        """Test that derived data summary is formatted correctly."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        summary = view.format_derived_summary(sample_derived_data)

        assert summary is not None
        assert "shot_name" in summary
        assert "shot_rank" in summary
        assert "smash_factor" in summary
        assert summary["shot_name"] == "Straight"
        assert summary["shot_rank"] == "A"
        assert "1.48" in summary["smash_factor"]

    def test_format_derived_summary_with_none(self) -> None:
        """Test that derived data summary handles None gracefully."""
        from gc2_connect.ui.components.open_range_view import OpenRangeView

        view = OpenRangeView()
        summary = view.format_derived_summary(None)

        assert summary is None
