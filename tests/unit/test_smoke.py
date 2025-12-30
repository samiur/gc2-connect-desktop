# ABOUTME: Smoke test to verify the test infrastructure works correctly.
# ABOUTME: Includes basic import tests and fixture validation.

from typing import Any

from gc2_connect.models import GC2ShotData, GSProShotMessage


def test_smoke_imports_work() -> None:
    """Verify that the main modules can be imported."""
    from gc2_connect import models
    from gc2_connect.gc2 import usb_reader
    from gc2_connect.gspro import client

    assert models is not None
    assert usb_reader is not None
    assert client is not None


def test_gc2_shot_data_model_exists() -> None:
    """Verify that GC2ShotData model is defined."""
    assert GC2ShotData is not None
    assert hasattr(GC2ShotData, "ball_speed")
    assert hasattr(GC2ShotData, "from_gc2_dict")


def test_gspro_shot_message_model_exists() -> None:
    """Verify that GSProShotMessage model is defined."""
    assert GSProShotMessage is not None
    assert hasattr(GSProShotMessage, "from_gc2_shot")
    assert hasattr(GSProShotMessage, "to_dict")


def test_fixtures_load_correctly(valid_gc2_dict: dict[str, Any]) -> None:
    """Verify that fixtures from conftest.py are available."""
    assert valid_gc2_dict is not None
    assert "SPEED_MPH" in valid_gc2_dict
    assert "SHOT_ID" in valid_gc2_dict


def test_gc2_shot_fixture_creates_valid_shot(sample_gc2_shot: GC2ShotData) -> None:
    """Verify that sample_gc2_shot fixture creates a valid GC2ShotData."""
    assert sample_gc2_shot is not None
    assert sample_gc2_shot.ball_speed > 0
    assert sample_gc2_shot.is_valid()
