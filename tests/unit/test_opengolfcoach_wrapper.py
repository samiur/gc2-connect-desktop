# ABOUTME: Unit tests for OpenGolfCoach library wrapper.
# ABOUTME: Tests input/output dataclasses, unit conversions, and calculation functions.
"""Tests for OpenGolfCoach wrapper module."""

from __future__ import annotations

import json
import math

import pytest


class TestOpenGolfCoachInput:
    """Tests for OpenGolfCoachInput dataclass."""

    def test_creation_with_defaults(self) -> None:
        """Test OpenGolfCoachInput creation with default values."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
        )

        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=72.0,
            vertical_launch_angle_degrees=12.0,
        )
        assert input_data.ball_speed_meters_per_second == 72.0
        assert input_data.vertical_launch_angle_degrees == 12.0
        assert input_data.horizontal_launch_angle_degrees == 0.0
        assert input_data.total_spin_rpm == 0.0
        assert input_data.spin_axis_degrees == 0.0

    def test_creation_with_all_fields(self) -> None:
        """Test OpenGolfCoachInput creation with all fields."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
        )

        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=72.0,
            vertical_launch_angle_degrees=12.0,
            horizontal_launch_angle_degrees=2.5,
            total_spin_rpm=2500.0,
            spin_axis_degrees=5.0,
        )
        assert input_data.ball_speed_meters_per_second == 72.0
        assert input_data.vertical_launch_angle_degrees == 12.0
        assert input_data.horizontal_launch_angle_degrees == 2.5
        assert input_data.total_spin_rpm == 2500.0
        assert input_data.spin_axis_degrees == 5.0

    def test_to_json_produces_valid_json(self) -> None:
        """Test to_json() produces valid JSON with all required fields."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
        )

        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=72.0,
            vertical_launch_angle_degrees=12.0,
            horizontal_launch_angle_degrees=2.5,
            total_spin_rpm=2500.0,
            spin_axis_degrees=5.0,
        )
        json_str = input_data.to_json()

        parsed = json.loads(json_str)
        assert parsed["ball_speed_meters_per_second"] == 72.0
        assert parsed["vertical_launch_angle_degrees"] == 12.0
        assert parsed["horizontal_launch_angle_degrees"] == 2.5
        assert parsed["total_spin_rpm"] == 2500.0
        assert parsed["spin_axis_degrees"] == 5.0

    def test_from_gc2_shot_converts_units(self) -> None:
        """Test from_gc2_shot() correctly converts mph to m/s."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,  # mph
            launch_angle=12.0,
            horizontal_launch_angle=2.5,
            back_spin=2490.0,
            side_spin=218.0,
        )

        input_data = OpenGolfCoachInput.from_gc2_shot(gc2_shot)

        # 161 mph * 0.44704 = ~71.97 m/s
        assert input_data.ball_speed_meters_per_second == pytest.approx(71.97, rel=0.01)
        assert input_data.vertical_launch_angle_degrees == 12.0
        assert input_data.horizontal_launch_angle_degrees == 2.5

        # Total spin from components: sqrt(2490^2 + 218^2) = ~2499.5
        expected_total_spin = math.sqrt(2490**2 + 218**2)
        assert input_data.total_spin_rpm == pytest.approx(expected_total_spin, rel=0.01)

    def test_from_gc2_shot_calculates_spin_axis(self) -> None:
        """Test from_gc2_shot() calculates spin axis from components."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=150.0,
            launch_angle=10.0,
            horizontal_launch_angle=0.0,
            back_spin=2000.0,
            side_spin=500.0,
        )

        input_data = OpenGolfCoachInput.from_gc2_shot(gc2_shot)

        # spin_axis = atan2(side_spin, back_spin) in degrees
        expected_axis = math.degrees(math.atan2(500, 2000))
        assert input_data.spin_axis_degrees == pytest.approx(expected_axis, rel=0.01)


class TestOpenGolfCoachResult:
    """Tests for OpenGolfCoachResult dataclass."""

    def test_creation(self) -> None:
        """Test OpenGolfCoachResult creation."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachResult,
        )

        result = OpenGolfCoachResult(
            carry_distance_meters=226.3,
            total_distance_meters=236.2,
            offline_distance_meters=15.9,
            backspin_rpm=2490.5,
            sidespin_rpm=217.9,
            club_speed_meters_per_second=48.4,
            smash_factor=1.488,
            club_path_degrees=0.48,
            club_face_to_target_degrees=2.27,
            club_face_to_path_degrees=1.79,
            shot_name="Straight Fade",
            shot_rank="A",
            shot_color_rgb="0x00D977",
        )
        assert result.carry_distance_meters == 226.3
        assert result.total_distance_meters == 236.2
        assert result.shot_name == "Straight Fade"
        assert result.shot_rank == "A"

    def test_carry_distance_yards_conversion(self) -> None:
        """Test carry_distance_yards property converts correctly."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachResult,
        )

        result = OpenGolfCoachResult(
            carry_distance_meters=226.3,
            total_distance_meters=236.2,
            offline_distance_meters=15.9,
            backspin_rpm=2490.0,
            sidespin_rpm=218.0,
            club_speed_meters_per_second=48.4,
            smash_factor=1.488,
            club_path_degrees=0.48,
            club_face_to_target_degrees=2.27,
            club_face_to_path_degrees=1.79,
            shot_name="Straight Fade",
            shot_rank="A",
            shot_color_rgb="0x00D977",
        )

        # 226.3 meters * 1.09361 = ~247.5 yards
        assert result.carry_distance_yards == pytest.approx(247.5, rel=0.01)

    def test_total_distance_yards_conversion(self) -> None:
        """Test total_distance_yards property converts correctly."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachResult,
        )

        result = OpenGolfCoachResult(
            carry_distance_meters=226.3,
            total_distance_meters=236.2,
            offline_distance_meters=15.9,
            backspin_rpm=2490.0,
            sidespin_rpm=218.0,
            club_speed_meters_per_second=48.4,
            smash_factor=1.488,
            club_path_degrees=0.48,
            club_face_to_target_degrees=2.27,
            club_face_to_path_degrees=1.79,
            shot_name="Straight Fade",
            shot_rank="A",
            shot_color_rgb="0x00D977",
        )

        # 236.2 meters * 1.09361 = ~258.3 yards
        assert result.total_distance_yards == pytest.approx(258.3, rel=0.01)

    def test_offline_distance_yards_conversion(self) -> None:
        """Test offline_distance_yards property converts correctly."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachResult,
        )

        result = OpenGolfCoachResult(
            carry_distance_meters=226.3,
            total_distance_meters=236.2,
            offline_distance_meters=15.9,
            backspin_rpm=2490.0,
            sidespin_rpm=218.0,
            club_speed_meters_per_second=48.4,
            smash_factor=1.488,
            club_path_degrees=0.48,
            club_face_to_target_degrees=2.27,
            club_face_to_path_degrees=1.79,
            shot_name="Straight Fade",
            shot_rank="A",
            shot_color_rgb="0x00D977",
        )

        # 15.9 meters * 1.09361 = ~17.4 yards
        assert result.offline_distance_yards == pytest.approx(17.4, rel=0.01)

    def test_club_speed_mph_conversion(self) -> None:
        """Test club_speed_mph property converts correctly."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachResult,
        )

        result = OpenGolfCoachResult(
            carry_distance_meters=226.3,
            total_distance_meters=236.2,
            offline_distance_meters=15.9,
            backspin_rpm=2490.0,
            sidespin_rpm=218.0,
            club_speed_meters_per_second=48.4,
            smash_factor=1.488,
            club_path_degrees=0.48,
            club_face_to_target_degrees=2.27,
            club_face_to_path_degrees=1.79,
            shot_name="Straight Fade",
            shot_rank="A",
            shot_color_rgb="0x00D977",
        )

        # 48.4 m/s * 2.23694 = ~108.3 mph
        assert result.club_speed_mph == pytest.approx(108.3, rel=0.01)

    def test_club_speed_mph_none_when_not_available(self) -> None:
        """Test club_speed_mph returns None when club_speed not available."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachResult,
        )

        result = OpenGolfCoachResult(
            carry_distance_meters=226.3,
            total_distance_meters=236.2,
            offline_distance_meters=15.9,
            backspin_rpm=2490.0,
            sidespin_rpm=218.0,
            club_speed_meters_per_second=None,
            smash_factor=None,
            club_path_degrees=None,
            club_face_to_target_degrees=None,
            club_face_to_path_degrees=None,
            shot_name="Unknown",
            shot_rank="D",
            shot_color_rgb="#808080",
        )

        assert result.club_speed_mph is None


class TestCalculateShot:
    """Tests for calculate_shot() function."""

    def test_calculate_shot_returns_valid_result(self) -> None:
        """Test calculate_shot() returns OpenGolfCoachResult for typical shot."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
            calculate_shot,
        )

        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=72.0,
            vertical_launch_angle_degrees=12.0,
            horizontal_launch_angle_degrees=2.0,
            total_spin_rpm=2500.0,
            spin_axis_degrees=5.0,
        )

        result = calculate_shot(input_data)

        assert result.carry_distance_meters > 200  # Should be ~226m for this shot
        assert result.total_distance_meters > result.carry_distance_meters
        assert result.shot_name != ""
        assert result.shot_rank in ["S+", "S", "A", "B", "C", "D", "E"]

    def test_calculate_shot_with_high_spin(self) -> None:
        """Test calculate_shot() handles high spin shots."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
            calculate_shot,
        )

        # Wedge-like shot with high spin
        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=40.0,  # ~90 mph
            vertical_launch_angle_degrees=30.0,
            horizontal_launch_angle_degrees=0.0,
            total_spin_rpm=9000.0,  # High spin
            spin_axis_degrees=0.0,
        )

        result = calculate_shot(input_data)

        assert result.carry_distance_meters > 50
        assert result.backspin_rpm > 0

    def test_calculate_shot_with_slice(self) -> None:
        """Test calculate_shot() identifies slice shots."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
            calculate_shot,
        )

        # Shot with significant sidespin (slice)
        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=65.0,
            vertical_launch_angle_degrees=11.0,
            horizontal_launch_angle_degrees=5.0,  # Starting right
            total_spin_rpm=3500.0,
            spin_axis_degrees=20.0,  # Heavy slice spin axis
        )

        result = calculate_shot(input_data)

        assert result.offline_distance_meters > 0  # Right of target


class TestCalculateShotFromGC2:
    """Tests for calculate_shot_from_gc2() convenience function."""

    def test_calculate_from_gc2_shot(self) -> None:
        """Test calculate_shot_from_gc2() processes GC2 shot data."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            calculate_shot_from_gc2,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,  # mph
            launch_angle=10.9,
            horizontal_launch_angle=1.5,
            back_spin=2686.0,
            side_spin=-250.0,
        )

        result = calculate_shot_from_gc2(gc2_shot)

        # Should get valid result
        assert result.carry_distance_yards > 200  # Driver carry
        assert result.shot_name != ""
        assert result.shot_rank in ["S+", "S", "A", "B", "C", "D", "E"]

    def test_calculate_from_gc2_7iron(self) -> None:
        """Test calculation for typical 7-iron shot."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            calculate_shot_from_gc2,
        )

        gc2_shot = GC2ShotData(
            shot_id=2,
            ball_speed=120.0,  # mph
            launch_angle=18.0,
            horizontal_launch_angle=0.0,
            back_spin=6000.0,
            side_spin=100.0,
        )

        result = calculate_shot_from_gc2(gc2_shot)

        # 7-iron should carry 140-170 yards
        assert 100 < result.carry_distance_yards < 200


class TestOpenGolfCoachAvailability:
    """Tests for library availability and graceful fallback."""

    def test_opengolfcoach_is_available(self) -> None:
        """Test that is_available() returns True when library installed."""
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        assert is_available() is True

    def test_can_import_directly(self) -> None:
        """Test direct import of opengolfcoach library works."""
        import opengolfcoach

        assert hasattr(opengolfcoach, "calculate_derived_values")


class TestOpenGolfCoachUnavailable:
    """Tests for behavior when OpenGolfCoach is not available."""

    def test_calculate_shot_raises_when_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test calculate_shot() raises RuntimeError when library unavailable."""
        import gc2_connect.open_range.physics.opengolfcoach_wrapper as wrapper

        # Mock the availability flag to simulate library not installed
        monkeypatch.setattr(wrapper, "_OPENGOLFCOACH_AVAILABLE", False)

        from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
            OpenGolfCoachInput,
            calculate_shot,
        )

        input_data = OpenGolfCoachInput(
            ball_speed_meters_per_second=72.0,
            vertical_launch_angle_degrees=12.0,
        )

        with pytest.raises(RuntimeError, match="not installed"):
            calculate_shot(input_data)

    def test_is_available_returns_false_when_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test is_available() returns False when library not installed."""
        import gc2_connect.open_range.physics.opengolfcoach_wrapper as wrapper

        # Mock the availability flag
        monkeypatch.setattr(wrapper, "_OPENGOLFCOACH_AVAILABLE", False)

        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        assert is_available() is False
