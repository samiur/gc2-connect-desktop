# ABOUTME: Unit tests for the ShotHistoryManager class.
# ABOUTME: Tests history storage, ordering, limits, statistics, and export functionality.
"""Tests for the shot history manager."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gc2_connect.models import GC2ShotData
from gc2_connect.services.history import ShotHistoryManager


@pytest.fixture
def manager() -> ShotHistoryManager:
    """Create a ShotHistoryManager with default limit."""
    return ShotHistoryManager(limit=50)


@pytest.fixture
def small_manager() -> ShotHistoryManager:
    """Create a ShotHistoryManager with small limit for testing."""
    return ShotHistoryManager(limit=5)


@pytest.fixture
def sample_shot() -> GC2ShotData:
    """Create a sample shot for testing."""
    return GC2ShotData(
        shot_id=1,
        timestamp=datetime.now(),
        ball_speed=150.0,
        launch_angle=12.0,
        horizontal_launch_angle=1.5,
        total_spin=2800.0,
        back_spin=2650.0,
        side_spin=-350.0,
    )


@pytest.fixture
def sample_shots() -> list[GC2ShotData]:
    """Create a list of sample shots for testing."""
    base_time = datetime.now()
    shots = []
    for i in range(10):
        shots.append(
            GC2ShotData(
                shot_id=i + 1,
                timestamp=base_time + timedelta(seconds=i),
                ball_speed=140.0 + i * 2,  # 140-158 mph
                launch_angle=10.0 + i * 0.5,  # 10-14.5 degrees
                horizontal_launch_angle=float(i % 3 - 1),  # -1, 0, 1
                total_spin=2500.0 + i * 100,  # 2500-3400 rpm
                back_spin=2400.0 + i * 90,  # 2400-3210 rpm
                side_spin=-200.0 + i * 40,  # -200 to 160 rpm
            )
        )
    return shots


class TestShotHistoryManagerInit:
    """Tests for ShotHistoryManager initialization."""

    def test_default_limit(self) -> None:
        """Test default limit is 50."""
        manager = ShotHistoryManager()
        assert manager.limit == 50

    def test_custom_limit(self) -> None:
        """Test custom limit is set correctly."""
        manager = ShotHistoryManager(limit=100)
        assert manager.limit == 100

    def test_initial_count_is_zero(self, manager: ShotHistoryManager) -> None:
        """Test that count starts at zero."""
        assert manager.count == 0

    def test_initial_shots_is_empty(self, manager: ShotHistoryManager) -> None:
        """Test that shots list starts empty."""
        assert manager.shots == []


class TestShotHistoryManagerAddShot:
    """Tests for adding shots to history."""

    def test_add_shot_increments_count(
        self, manager: ShotHistoryManager, sample_shot: GC2ShotData
    ) -> None:
        """Test adding a shot increments the count."""
        manager.add_shot(sample_shot)
        assert manager.count == 1

    def test_add_shot_stores_shot(
        self, manager: ShotHistoryManager, sample_shot: GC2ShotData
    ) -> None:
        """Test adding a shot stores it in the list."""
        manager.add_shot(sample_shot)
        assert len(manager.shots) == 1
        assert manager.shots[0] == sample_shot

    def test_newest_shot_is_first(
        self, manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test that newest shot is at index 0 (newest first ordering)."""
        for shot in sample_shots:
            manager.add_shot(shot)

        # Last added should be first in list
        assert manager.shots[0].shot_id == 10
        assert manager.shots[-1].shot_id == 1


class TestShotHistoryManagerLimit:
    """Tests for history limit enforcement."""

    def test_respects_limit(
        self, small_manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test that history respects the limit."""
        # Add 10 shots to manager with limit of 5
        for shot in sample_shots:
            small_manager.add_shot(shot)

        assert small_manager.count == 5
        assert len(small_manager.shots) == 5

    def test_oldest_removed_when_over_limit(
        self, small_manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test that oldest shots are removed when over limit."""
        for shot in sample_shots:
            small_manager.add_shot(shot)

        # Should have shots 6-10 (newest)
        shot_ids = [s.shot_id for s in small_manager.shots]
        assert 1 not in shot_ids
        assert 10 in shot_ids

    def test_update_limit_trims_history(
        self, manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test that updating limit trims existing history."""
        for shot in sample_shots:
            manager.add_shot(shot)

        assert manager.count == 10

        manager.limit = 3
        assert manager.count == 3
        assert manager.shots[0].shot_id == 10  # Newest kept

    def test_can_handle_100_plus_shots(self, manager: ShotHistoryManager) -> None:
        """Test that manager handles 100+ shots efficiently."""
        manager.limit = 150

        base_time = datetime.now()
        for i in range(150):
            shot = GC2ShotData(
                shot_id=i + 1,
                timestamp=base_time + timedelta(seconds=i),
                ball_speed=150.0,
                launch_angle=12.0,
                total_spin=2800.0,
                back_spin=2650.0,
                side_spin=-350.0,
            )
            manager.add_shot(shot)

        assert manager.count == 150
        assert manager.shots[0].shot_id == 150


class TestShotHistoryManagerClear:
    """Tests for clearing history."""

    def test_clear_removes_all_shots(
        self, manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test that clear removes all shots."""
        for shot in sample_shots:
            manager.add_shot(shot)

        manager.clear()
        assert manager.count == 0
        assert manager.shots == []


class TestShotHistoryManagerStatistics:
    """Tests for session statistics."""

    def test_stats_empty_when_no_shots(self, manager: ShotHistoryManager) -> None:
        """Test statistics return zeros when no shots."""
        stats = manager.get_statistics()
        assert stats["count"] == 0
        assert stats["avg_ball_speed"] == 0.0
        assert stats["avg_launch_angle"] == 0.0
        assert stats["avg_total_spin"] == 0.0

    def test_stats_with_single_shot(
        self, manager: ShotHistoryManager, sample_shot: GC2ShotData
    ) -> None:
        """Test statistics with single shot."""
        manager.add_shot(sample_shot)
        stats = manager.get_statistics()

        assert stats["count"] == 1
        assert stats["avg_ball_speed"] == 150.0
        assert stats["avg_launch_angle"] == 12.0
        assert stats["avg_total_spin"] == 2800.0

    def test_stats_averages_correctly(
        self, manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test statistics averages are calculated correctly."""
        for shot in sample_shots:
            manager.add_shot(shot)

        stats = manager.get_statistics()

        # Expected averages from sample_shots fixture
        # ball_speed: 140, 142, 144, 146, 148, 150, 152, 154, 156, 158 -> avg = 149.0
        # launch_angle: 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5 -> avg = 12.25
        # total_spin: 2500-3400 in 100 increments -> avg = 2950.0
        assert stats["count"] == 10
        assert stats["avg_ball_speed"] == pytest.approx(149.0, abs=0.1)
        assert stats["avg_launch_angle"] == pytest.approx(12.25, abs=0.1)
        assert stats["avg_total_spin"] == pytest.approx(2950.0, abs=0.1)

    def test_stats_includes_max_values(
        self, manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test statistics include max values."""
        for shot in sample_shots:
            manager.add_shot(shot)

        stats = manager.get_statistics()

        assert stats["max_ball_speed"] == 158.0
        assert stats["max_total_spin"] == 3400.0


class TestShotHistoryManagerExport:
    """Tests for exporting shots."""

    def test_to_dict_list_empty(self, manager: ShotHistoryManager) -> None:
        """Test exporting empty history returns empty list."""
        result = manager.to_dict_list()
        assert result == []

    def test_to_dict_list_structure(
        self, manager: ShotHistoryManager, sample_shot: GC2ShotData
    ) -> None:
        """Test exported dict has correct structure."""
        manager.add_shot(sample_shot)
        result = manager.to_dict_list()

        assert len(result) == 1
        shot_dict = result[0]

        # Check required fields
        assert "shot_id" in shot_dict
        assert "timestamp" in shot_dict
        assert "ball_speed" in shot_dict
        assert "launch_angle" in shot_dict
        assert "horizontal_launch_angle" in shot_dict
        assert "total_spin" in shot_dict
        assert "back_spin" in shot_dict
        assert "side_spin" in shot_dict
        assert "spin_axis" in shot_dict

    def test_to_dict_list_values(
        self, manager: ShotHistoryManager, sample_shot: GC2ShotData
    ) -> None:
        """Test exported dict has correct values."""
        manager.add_shot(sample_shot)
        result = manager.to_dict_list()

        shot_dict = result[0]
        assert shot_dict["shot_id"] == 1
        assert shot_dict["ball_speed"] == 150.0
        assert shot_dict["launch_angle"] == 12.0
        assert shot_dict["total_spin"] == 2800.0

    def test_to_dict_list_includes_club_data_when_present(
        self, manager: ShotHistoryManager
    ) -> None:
        """Test exported dict includes club data when available."""
        shot_with_club = GC2ShotData(
            shot_id=1,
            ball_speed=150.0,
            launch_angle=12.0,
            total_spin=2800.0,
            back_spin=2650.0,
            side_spin=-350.0,
            club_speed=105.0,
            swing_path=2.5,
            face_to_target=1.0,
            angle_of_attack=-3.5,
        )
        manager.add_shot(shot_with_club)
        result = manager.to_dict_list()

        shot_dict = result[0]
        assert shot_dict["club_speed"] == 105.0
        assert shot_dict["swing_path"] == 2.5
        assert shot_dict["face_to_target"] == 1.0
        assert shot_dict["angle_of_attack"] == -3.5


class TestShotHistoryManagerFormatting:
    """Tests for formatted output."""

    def test_format_count_display_empty(self, manager: ShotHistoryManager) -> None:
        """Test count display when empty."""
        assert manager.format_count_display() == "Shots: 0/50"

    def test_format_count_display_with_shots(
        self, manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test count display with shots."""
        for shot in sample_shots:
            manager.add_shot(shot)

        assert manager.format_count_display() == "Shots: 10/50"

    def test_format_count_display_at_limit(
        self, small_manager: ShotHistoryManager, sample_shots: list[GC2ShotData]
    ) -> None:
        """Test count display when at limit."""
        for shot in sample_shots:
            small_manager.add_shot(shot)

        assert small_manager.format_count_display() == "Shots: 5/5"
