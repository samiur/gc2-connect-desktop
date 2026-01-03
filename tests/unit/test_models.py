# ABOUTME: Unit tests for GC2 shot data and GSPro message models.
# ABOUTME: Tests parsing, validation, conversion, and serialization of shot data.
"""Unit tests for data models."""

import math
from typing import Any

import pytest

from gc2_connect.models import (
    GC2ShotData,
    GSProBallData,
    GSProClubData,
    GSProResponse,
    GSProShotMessage,
    GSProShotOptions,
)


class TestGC2ShotDataDefaults:
    """Tests for GC2ShotData default values."""

    def test_default_shot_id_is_zero(self) -> None:
        """Default shot_id should be 0."""
        shot = GC2ShotData()
        assert shot.shot_id == 0

    def test_default_ball_speed_is_zero(self) -> None:
        """Default ball_speed should be 0.0."""
        shot = GC2ShotData()
        assert shot.ball_speed == 0.0

    def test_default_total_spin_is_zero(self) -> None:
        """Default total_spin should be 0.0."""
        shot = GC2ShotData()
        assert shot.total_spin == 0.0

    def test_default_club_speed_is_none(self) -> None:
        """Default club_speed should be None (no HMT data)."""
        shot = GC2ShotData()
        assert shot.club_speed is None

    def test_default_has_hmt_is_false(self) -> None:
        """Default has_hmt should be False."""
        shot = GC2ShotData()
        assert shot.has_hmt is False

    def test_timestamp_is_set(self) -> None:
        """Timestamp should be set on creation."""
        shot = GC2ShotData()
        assert shot.timestamp is not None


class TestGC2ShotDataFromGC2Dict:
    """Tests for GC2ShotData.from_gc2_dict() parsing."""

    def test_parse_ball_data_only(self, valid_gc2_dict: dict[str, Any]) -> None:
        """Parse valid ball-only data from GC2."""
        shot = GC2ShotData.from_gc2_dict(valid_gc2_dict)

        assert shot.shot_id == 1
        assert shot.ball_speed == 145.2
        assert shot.launch_angle == 11.8
        assert shot.horizontal_launch_angle == 1.5
        assert shot.total_spin == 2650.0
        assert shot.back_spin == 2480.0
        assert shot.side_spin == -320.0

    def test_parse_with_hmt_data(self, valid_gc2_dict_with_hmt: dict[str, Any]) -> None:
        """Parse valid data with HMT (club) data from GC2."""
        shot = GC2ShotData.from_gc2_dict(valid_gc2_dict_with_hmt)

        # Ball data
        assert shot.shot_id == 2
        assert shot.ball_speed == 150.5
        assert shot.total_spin == 2800.0

        # Club data
        assert shot.club_speed == 105.2
        assert shot.swing_path == 3.1
        assert shot.angle_of_attack == -4.2
        assert shot.face_to_target == 1.5
        assert shot.lie == 0.5
        assert shot.dynamic_loft == 15.2
        assert shot.has_hmt is True

    def test_parse_empty_dict_returns_defaults(self) -> None:
        """Empty dict should return shot with default values."""
        shot = GC2ShotData.from_gc2_dict({})

        assert shot.shot_id == 0
        assert shot.ball_speed == 0.0
        assert shot.total_spin == 0.0
        assert shot.club_speed is None

    def test_parse_ignores_unknown_fields(self) -> None:
        """Unknown fields in dict should be ignored."""
        data = {
            "SHOT_ID": "1",
            "SPEED_MPH": "100.0",
            "UNKNOWN_FIELD": "some_value",
            "ANOTHER_UNKNOWN": "123",
        }
        shot = GC2ShotData.from_gc2_dict(data)

        assert shot.shot_id == 1
        assert shot.ball_speed == 100.0

    def test_parse_handles_invalid_numeric_values(self) -> None:
        """Invalid numeric values should be skipped (keep defaults)."""
        data = {
            "SHOT_ID": "not_a_number",
            "SPEED_MPH": "also_invalid",
            "SPIN_RPM": "2000",  # Valid
        }
        shot = GC2ShotData.from_gc2_dict(data)

        assert shot.shot_id == 0  # Default, parsing failed
        assert shot.ball_speed == 0.0  # Default, parsing failed
        assert shot.total_spin == 2000.0  # Parsed successfully

    def test_parse_hmt_flag_accepts_various_truthy_values(self) -> None:
        """HMT flag should accept 1, true, yes as truthy."""
        for truthy_value in ["1", "true", "yes", "TRUE", "Yes"]:
            data = {"HMT": truthy_value}
            shot = GC2ShotData.from_gc2_dict(data)
            assert shot.has_hmt is True, f"Failed for value: {truthy_value}"

    def test_parse_hmt_flag_rejects_falsy_values(self) -> None:
        """HMT flag should be False for 0, false, no."""
        for falsy_value in ["0", "false", "no", "FALSE", "No"]:
            data = {"HMT": falsy_value}
            shot = GC2ShotData.from_gc2_dict(data)
            assert shot.has_hmt is False, f"Failed for value: {falsy_value}"


class TestGC2ShotDataSpinAxis:
    """Tests for GC2ShotData.spin_axis property."""

    def test_spin_axis_with_zero_backspin_returns_zero(self) -> None:
        """Zero backspin should return 0 spin axis to avoid division by zero."""
        shot = GC2ShotData(back_spin=0, side_spin=100)
        assert shot.spin_axis == 0.0

    def test_spin_axis_positive_side_spin(self) -> None:
        """Positive side spin (fade/slice) should give positive axis."""
        shot = GC2ShotData(back_spin=2000, side_spin=500)
        # atan2(500, 2000) in degrees
        expected = math.degrees(math.atan2(500, 2000))
        assert abs(shot.spin_axis - expected) < 0.01

    def test_spin_axis_negative_side_spin(self) -> None:
        """Negative side spin (draw/hook) should give negative axis."""
        shot = GC2ShotData(back_spin=2000, side_spin=-500)
        expected = math.degrees(math.atan2(-500, 2000))
        assert abs(shot.spin_axis - expected) < 0.01

    def test_spin_axis_pure_backspin(self) -> None:
        """Pure backspin (no sidespin) should give 0 axis."""
        shot = GC2ShotData(back_spin=2500, side_spin=0)
        assert shot.spin_axis == 0.0


class TestGC2ShotDataValidation:
    """Tests for GC2ShotData.is_valid() method."""

    def test_valid_shot_passes_validation(self, sample_gc2_shot: GC2ShotData) -> None:
        """A normal valid shot should pass validation."""
        assert sample_gc2_shot.is_valid() is True

    def test_zero_spin_is_invalid(self, zero_spin_gc2_dict: dict[str, Any]) -> None:
        """Zero spin shots should be rejected as misreads."""
        shot = GC2ShotData.from_gc2_dict(zero_spin_gc2_dict)
        assert shot.is_valid() is False

    def test_low_ball_speed_chip_shot_is_valid(self) -> None:
        """Low ball speed chip shots should be valid if spin data is present."""
        shot = GC2ShotData(ball_speed=5.0, total_spin=2000, back_spin=1900, side_spin=100)
        assert shot.is_valid() is True

    def test_zero_ball_speed_is_invalid(self) -> None:
        """Zero ball speed should be invalid."""
        shot = GC2ShotData(ball_speed=0.0, total_spin=2000, back_spin=1900, side_spin=100)
        assert shot.is_valid() is False

    def test_minimum_valid_ball_speed(self) -> None:
        """Very low ball speed should be valid with spin data."""
        shot = GC2ShotData(ball_speed=1.0, total_spin=2000, back_spin=1900, side_spin=100)
        assert shot.is_valid() is True

    def test_high_ball_speed_is_invalid(self) -> None:
        """Ball speed above 250 mph should be invalid."""
        shot = GC2ShotData(ball_speed=260.0, total_spin=2000, back_spin=1900, side_spin=100)
        assert shot.is_valid() is False

    def test_maximum_valid_ball_speed(self) -> None:
        """Ball speed at 250 mph should be valid."""
        shot = GC2ShotData(ball_speed=250.0, total_spin=2000, back_spin=1900, side_spin=100)
        assert shot.is_valid() is True

    def test_2222_backspin_is_invalid(self) -> None:
        """2222 backspin is a known GC2 error code and should be rejected."""
        shot = GC2ShotData(ball_speed=150.0, total_spin=2222, back_spin=2222.0, side_spin=0)
        assert shot.is_valid() is False

    def test_zero_back_and_side_spin_is_invalid(self) -> None:
        """Zero back spin AND side spin indicates a misread."""
        shot = GC2ShotData(ball_speed=150.0, total_spin=0, back_spin=0.0, side_spin=0.0)
        assert shot.is_valid() is False

    def test_zero_back_spin_with_side_spin_is_valid(self) -> None:
        """Zero back spin but non-zero side spin should be valid."""
        shot = GC2ShotData(ball_speed=150.0, total_spin=500, back_spin=0.0, side_spin=500.0)
        assert shot.is_valid() is True

    def test_typical_driver_shot_is_valid(self) -> None:
        """A typical driver shot should be valid."""
        shot = GC2ShotData(ball_speed=165.0, total_spin=2800, back_spin=2500, side_spin=-300)
        assert shot.is_valid() is True

    def test_typical_wedge_shot_is_valid(self) -> None:
        """A typical wedge shot should be valid."""
        shot = GC2ShotData(ball_speed=85.0, total_spin=9000, back_spin=8800, side_spin=500)
        assert shot.is_valid() is True


class TestGC2ShotDataHasClubData:
    """Tests for GC2ShotData.has_club_data property."""

    def test_has_club_data_false_when_no_club_speed(self) -> None:
        """has_club_data should be False when club_speed is None."""
        shot = GC2ShotData(ball_speed=150.0, club_speed=None)
        assert shot.has_club_data is False

    def test_has_club_data_true_when_club_speed_set(self) -> None:
        """has_club_data should be True when club_speed is set."""
        shot = GC2ShotData(ball_speed=150.0, club_speed=105.0)
        assert shot.has_club_data is True

    def test_has_club_data_with_fixture(
        self, sample_gc2_shot: GC2ShotData, sample_gc2_shot_with_hmt: GC2ShotData
    ) -> None:
        """Test has_club_data with fixtures."""
        assert sample_gc2_shot.has_club_data is False
        assert sample_gc2_shot_with_hmt.has_club_data is True


class TestGSProShotMessageFromGC2Shot:
    """Tests for GSProShotMessage.from_gc2_shot() conversion."""

    def test_conversion_without_club_data(self, sample_gc2_shot: GC2ShotData) -> None:
        """Convert GC2 shot without club data to GSPro message."""
        message = GSProShotMessage.from_gc2_shot(sample_gc2_shot, shot_number=1)

        assert message.ShotNumber == 1
        assert message.DeviceID == "GC2 Connect"
        assert message.Units == "Yards"

        # Ball data should be populated (speed sent as mph directly)
        assert message.BallData.Speed == sample_gc2_shot.ball_speed
        assert message.BallData.TotalSpin == sample_gc2_shot.total_spin
        assert message.BallData.BackSpin == sample_gc2_shot.back_spin
        assert message.BallData.SideSpin == sample_gc2_shot.side_spin
        assert sample_gc2_shot.launch_angle == message.BallData.VLA
        assert sample_gc2_shot.horizontal_launch_angle == message.BallData.HLA

        # Club data should be empty
        assert message.ShotDataOptions.ContainsClubData is False

    def test_conversion_with_club_data(self, sample_gc2_shot_with_hmt: GC2ShotData) -> None:
        """Convert GC2 shot with HMT club data to GSPro message."""
        message = GSProShotMessage.from_gc2_shot(sample_gc2_shot_with_hmt, shot_number=5)

        assert message.ShotNumber == 5
        assert message.ShotDataOptions.ContainsClubData is True

        # Club data should be populated
        assert message.ClubData.Speed == sample_gc2_shot_with_hmt.club_speed
        assert message.ClubData.Path == sample_gc2_shot_with_hmt.swing_path
        assert message.ClubData.AngleOfAttack == sample_gc2_shot_with_hmt.angle_of_attack
        assert message.ClubData.FaceToTarget == sample_gc2_shot_with_hmt.face_to_target

    def test_spin_axis_is_calculated(self, sample_gc2_shot: GC2ShotData) -> None:
        """SpinAxis should be calculated from back/side spin."""
        message = GSProShotMessage.from_gc2_shot(sample_gc2_shot, shot_number=1)
        assert message.BallData.SpinAxis == sample_gc2_shot.spin_axis

    def test_shot_number_is_set_correctly(self, sample_gc2_shot: GC2ShotData) -> None:
        """Shot number should be set from parameter."""
        for shot_num in [1, 10, 100, 999]:
            message = GSProShotMessage.from_gc2_shot(sample_gc2_shot, shot_number=shot_num)
            assert message.ShotNumber == shot_num


class TestGSProShotMessageToDict:
    """Tests for GSProShotMessage.to_dict() serialization."""

    def test_to_dict_has_required_keys(self, sample_gspro_message: GSProShotMessage) -> None:
        """to_dict should include all required GSPro API keys."""
        result = sample_gspro_message.to_dict()

        assert "DeviceID" in result
        assert "Units" in result
        assert "ShotNumber" in result
        assert "APIversion" in result
        assert "BallData" in result
        assert "ClubData" in result
        assert "ShotDataOptions" in result

    def test_to_dict_ball_data_keys(self, sample_gspro_message: GSProShotMessage) -> None:
        """BallData should have all required keys."""
        result = sample_gspro_message.to_dict()
        ball_data = result["BallData"]

        expected_keys = [
            "Speed",
            "SpinAxis",
            "TotalSpin",
            "BackSpin",
            "SideSpin",
            "HLA",
            "VLA",
            "CarryDistance",
        ]
        for key in expected_keys:
            assert key in ball_data, f"Missing key: {key}"

    def test_to_dict_club_data_keys(self, sample_gspro_message: GSProShotMessage) -> None:
        """ClubData should have all required keys."""
        result = sample_gspro_message.to_dict()
        club_data = result["ClubData"]

        expected_keys = [
            "Speed",
            "AngleOfAttack",
            "FaceToTarget",
            "Lie",
            "Loft",
            "Path",
            "SpeedAtImpact",
            "VerticalFaceImpact",
            "HorizontalFaceImpact",
            "ClosureRate",
        ]
        for key in expected_keys:
            assert key in club_data, f"Missing key: {key}"

    def test_to_dict_shot_options_keys(self, sample_gspro_message: GSProShotMessage) -> None:
        """ShotDataOptions should have all required keys."""
        result = sample_gspro_message.to_dict()
        options = result["ShotDataOptions"]

        expected_keys = [
            "ContainsBallData",
            "ContainsClubData",
            "LaunchMonitorIsReady",
            "LaunchMonitorBallDetected",
            "IsHeartBeat",
        ]
        for key in expected_keys:
            assert key in options, f"Missing key: {key}"

    def test_to_dict_values_are_correct_types(self, sample_gspro_message: GSProShotMessage) -> None:
        """Values in to_dict should be correct types for JSON."""
        result = sample_gspro_message.to_dict()

        assert isinstance(result["DeviceID"], str)
        assert isinstance(result["ShotNumber"], int)
        assert isinstance(result["BallData"]["Speed"], float)
        assert isinstance(result["ShotDataOptions"]["ContainsBallData"], bool)


class TestGSProResponseFromDict:
    """Tests for GSProResponse.from_dict() parsing."""

    def test_parse_success_response(self) -> None:
        """Parse a success response from GSPro."""
        data = {
            "Code": 200,
            "Message": "Shot received",
            "Player": {"Name": "Player 1", "Club": "Driver"},
        }
        response = GSProResponse.from_dict(data)

        assert response.Code == 200
        assert response.Message == "Shot received"
        assert response.Player == {"Name": "Player 1", "Club": "Driver"}

    def test_parse_error_response(self) -> None:
        """Parse an error response from GSPro."""
        data = {"Code": 501, "Message": "Player not ready"}
        response = GSProResponse.from_dict(data)

        assert response.Code == 501
        assert response.Message == "Player not ready"
        assert response.Player is None

    def test_parse_empty_dict_returns_defaults(self) -> None:
        """Empty dict should return response with defaults."""
        response = GSProResponse.from_dict({})

        assert response.Code == 0
        assert response.Message == ""
        assert response.Player is None

    def test_parse_partial_data(self) -> None:
        """Partial data should fill in defaults for missing fields."""
        data = {"Code": 200}
        response = GSProResponse.from_dict(data)

        assert response.Code == 200
        assert response.Message == ""
        assert response.Player is None


class TestGSProResponseIsSuccess:
    """Tests for GSProResponse.is_success property."""

    def test_200_is_success(self) -> None:
        """Code 200 should be success."""
        response = GSProResponse(Code=200)
        assert response.is_success is True

    def test_201_is_success(self) -> None:
        """Code 201 should be success."""
        response = GSProResponse(Code=201)
        assert response.is_success is True

    def test_299_is_success(self) -> None:
        """Code 299 should be success (boundary)."""
        response = GSProResponse(Code=299)
        assert response.is_success is True

    def test_300_is_not_success(self) -> None:
        """Code 300 should not be success."""
        response = GSProResponse(Code=300)
        assert response.is_success is False

    def test_199_is_not_success(self) -> None:
        """Code 199 should not be success."""
        response = GSProResponse(Code=199)
        assert response.is_success is False

    def test_500_is_not_success(self) -> None:
        """Code 500 should not be success."""
        response = GSProResponse(Code=500)
        assert response.is_success is False

    def test_0_is_not_success(self) -> None:
        """Code 0 (default) should not be success."""
        response = GSProResponse()
        assert response.is_success is False

    @pytest.mark.parametrize("code", [400, 401, 404, 500, 501, 503])
    def test_error_codes_are_not_success(self, code: int) -> None:
        """Various error codes should not be success."""
        response = GSProResponse(Code=code)
        assert response.is_success is False


class TestGSProDataclassDefaults:
    """Tests for GSPro dataclass default values."""

    def test_gspro_ball_data_defaults(self) -> None:
        """GSProBallData should have zero defaults."""
        ball = GSProBallData()
        assert ball.Speed == 0.0
        assert ball.TotalSpin == 0.0
        assert ball.SpinAxis == 0.0

    def test_gspro_club_data_defaults(self) -> None:
        """GSProClubData should have zero defaults."""
        club = GSProClubData()
        assert club.Speed == 0.0
        assert club.AngleOfAttack == 0.0
        assert club.Path == 0.0

    def test_gspro_shot_options_defaults(self) -> None:
        """GSProShotOptions should have correct defaults."""
        options = GSProShotOptions()
        assert options.ContainsBallData is True
        assert options.ContainsClubData is False
        assert options.LaunchMonitorIsReady is True
        assert options.LaunchMonitorBallDetected is True
        assert options.IsHeartBeat is False

    def test_gspro_shot_message_defaults(self) -> None:
        """GSProShotMessage should have correct defaults."""
        message = GSProShotMessage()
        assert message.DeviceID == "GC2 Connect"
        assert message.Units == "Yards"
        assert message.ShotNumber == 1
        assert message.APIversion == "1"
