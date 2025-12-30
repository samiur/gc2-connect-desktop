# ABOUTME: Pytest configuration and shared fixtures for all tests.
# ABOUTME: Contains fixtures for GC2 shot data, GSPro messages, and mock objects.

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from gc2_connect.models import GC2ShotData, GSProShotMessage


@pytest.fixture
def valid_gc2_dict() -> dict[str, Any]:
    """Fixture providing valid GC2 shot data as a dictionary."""
    return {
        "SHOT_ID": "1",
        "SPEED_MPH": "145.2",
        "ELEVATION_DEG": "11.8",
        "AZIMUTH_DEG": "1.5",
        "SPIN_RPM": "2650",
        "BACK_RPM": "2480",
        "SIDE_RPM": "-320",
    }


@pytest.fixture
def valid_gc2_dict_with_hmt() -> dict[str, Any]:
    """Fixture providing valid GC2 shot data with HMT (club) data."""
    return {
        "SHOT_ID": "2",
        "SPEED_MPH": "150.5",
        "ELEVATION_DEG": "12.3",
        "AZIMUTH_DEG": "2.1",
        "SPIN_RPM": "2800",
        "BACK_RPM": "2650",
        "SIDE_RPM": "-400",
        "CLUBSPEED_MPH": "105.2",
        "HPATH_DEG": "3.1",
        "VPATH_DEG": "-4.2",
        "FACE_T_DEG": "1.5",
        "LIE_DEG": "0.5",
        "LOFT_DEG": "15.2",
        "HMT": "1",
    }


@pytest.fixture
def zero_spin_gc2_dict() -> dict[str, Any]:
    """Fixture providing invalid GC2 shot data with zero spin (misread)."""
    return {
        "SHOT_ID": "3",
        "SPEED_MPH": "145.0",
        "ELEVATION_DEG": "12.0",
        "AZIMUTH_DEG": "0.0",
        "SPIN_RPM": "0",
        "BACK_RPM": "0",
        "SIDE_RPM": "0",
    }


@pytest.fixture
def sample_gc2_shot(valid_gc2_dict: dict[str, Any]) -> GC2ShotData:
    """Fixture providing a valid GC2ShotData instance."""
    return GC2ShotData.from_gc2_dict(valid_gc2_dict)


@pytest.fixture
def sample_gc2_shot_with_hmt(valid_gc2_dict_with_hmt: dict[str, Any]) -> GC2ShotData:
    """Fixture providing a valid GC2ShotData instance with HMT data."""
    return GC2ShotData.from_gc2_dict(valid_gc2_dict_with_hmt)


@pytest.fixture
def sample_gspro_message(sample_gc2_shot: GC2ShotData) -> GSProShotMessage:
    """Fixture providing a GSProShotMessage instance."""
    return GSProShotMessage.from_gc2_shot(sample_gc2_shot, shot_number=1)


@pytest.fixture
def mock_socket():
    """Fixture providing a mock socket for GSPro client testing."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.sendall.return_value = None
    mock.close.return_value = None
    return mock


@pytest.fixture
def mock_socket_with_success_response(mock_socket):
    """Fixture providing a mock socket that returns a success response."""
    response = {"Code": 200, "Message": "OK"}
    mock_socket.recv.return_value = json.dumps(response).encode("utf-8")
    return mock_socket


@pytest.fixture
def mock_socket_with_player_response(mock_socket):
    """Fixture providing a mock socket that returns a player info response."""
    response = {
        "Code": 201,
        "Message": "Player info",
        "Player": {
            "Handed": "RH",
            "Club": "DR",
            "DistanceToTarget": 450,
        },
    }
    mock_socket.recv.return_value = json.dumps(response).encode("utf-8")
    return mock_socket


@pytest.fixture
def gspro_success_response_dict() -> dict[str, Any]:
    """Fixture providing a successful GSPro response dictionary."""
    return {"Code": 200, "Message": "OK"}


@pytest.fixture
def gspro_player_response_dict() -> dict[str, Any]:
    """Fixture providing a GSPro response with player info."""
    return {
        "Code": 201,
        "Message": "Player info",
        "Player": {
            "Handed": "RH",
            "Club": "DR",
            "DistanceToTarget": 450,
        },
    }


@pytest.fixture
def gspro_error_response_dict() -> dict[str, Any]:
    """Fixture providing a GSPro error response dictionary."""
    return {"Code": 500, "Message": "Internal error"}
