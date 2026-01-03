# ABOUTME: Unit tests for Open Range settings and settings migration.
# ABOUTME: Tests ConditionsSettings, OpenRangeSettings, and v1 -> v2 migration.
"""Unit tests for Open Range settings."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


class TestConditionsSettings:
    """Tests for ConditionsSettings model."""

    def test_default_values(self) -> None:
        """Test ConditionsSettings has correct defaults."""
        from gc2_connect.config.settings import ConditionsSettings

        conditions = ConditionsSettings()
        assert conditions.temp_f == 70.0
        assert conditions.elevation_ft == 0.0
        assert conditions.humidity_pct == 50.0
        assert conditions.wind_speed_mph == 0.0
        assert conditions.wind_dir_deg == 0.0

    def test_custom_values(self) -> None:
        """Test creating ConditionsSettings with custom values."""
        from gc2_connect.config.settings import ConditionsSettings

        conditions = ConditionsSettings(
            temp_f=85.0,
            elevation_ft=5280.0,
            humidity_pct=30.0,
            wind_speed_mph=10.0,
            wind_dir_deg=180.0,
        )
        assert conditions.temp_f == 85.0
        assert conditions.elevation_ft == 5280.0
        assert conditions.humidity_pct == 30.0
        assert conditions.wind_speed_mph == 10.0
        assert conditions.wind_dir_deg == 180.0

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        from gc2_connect.config.settings import ConditionsSettings

        conditions = ConditionsSettings(temp_f=75.0, wind_speed_mph=5.0)
        result = conditions.model_dump()
        assert result == {
            "temp_f": 75.0,
            "elevation_ft": 0.0,
            "humidity_pct": 50.0,
            "wind_speed_mph": 5.0,
            "wind_dir_deg": 0.0,
        }


class TestOpenRangeSettings:
    """Tests for OpenRangeSettings model."""

    def test_default_values(self) -> None:
        """Test OpenRangeSettings has correct defaults."""
        from gc2_connect.config.settings import OpenRangeSettings

        or_settings = OpenRangeSettings()
        assert or_settings.surface == "Fairway"
        assert or_settings.show_trajectory is True
        assert or_settings.camera_follow is True
        # Check nested conditions defaults
        assert or_settings.conditions.temp_f == 70.0
        assert or_settings.conditions.elevation_ft == 0.0

    def test_custom_values(self) -> None:
        """Test creating OpenRangeSettings with custom values."""
        from gc2_connect.config.settings import ConditionsSettings, OpenRangeSettings

        conditions = ConditionsSettings(temp_f=80.0, elevation_ft=1000.0)
        or_settings = OpenRangeSettings(
            conditions=conditions,
            surface="Rough",
            show_trajectory=False,
            camera_follow=False,
        )
        assert or_settings.conditions.temp_f == 80.0
        assert or_settings.surface == "Rough"
        assert or_settings.show_trajectory is False
        assert or_settings.camera_follow is False

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        from gc2_connect.config.settings import OpenRangeSettings

        or_settings = OpenRangeSettings(surface="Green")
        result = or_settings.model_dump()
        assert result["surface"] == "Green"
        assert result["show_trajectory"] is True
        assert result["camera_follow"] is True
        assert result["conditions"]["temp_f"] == 70.0


class TestSettingsWithOpenRange:
    """Tests for Settings with Open Range extension."""

    def test_settings_has_open_range(self) -> None:
        """Test that Settings includes open_range field."""
        from gc2_connect.config.settings import Settings

        settings = Settings()
        assert hasattr(settings, "open_range")
        assert settings.open_range is not None

    def test_settings_has_mode(self) -> None:
        """Test that Settings includes mode field."""
        from gc2_connect.config.settings import Settings

        settings = Settings()
        assert hasattr(settings, "mode")
        assert settings.mode == "gspro"  # Default mode

    def test_settings_version_is_2(self) -> None:
        """Test that Settings version is now 2."""
        from gc2_connect.config.settings import Settings

        settings = Settings()
        assert settings.version == 2

    def test_settings_open_range_defaults(self) -> None:
        """Test that Settings.open_range has correct defaults."""
        from gc2_connect.config.settings import Settings

        settings = Settings()
        assert settings.open_range.surface == "Fairway"
        assert settings.open_range.conditions.temp_f == 70.0

    def test_settings_to_dict_includes_open_range(self) -> None:
        """Test that to_dict includes open_range and mode."""
        from gc2_connect.config.settings import Settings

        settings = Settings()
        result = settings.to_dict()
        assert "open_range" in result
        assert "mode" in result
        assert result["mode"] == "gspro"
        assert result["open_range"]["surface"] == "Fairway"

    def test_settings_save_load_roundtrip_with_open_range(self, tmp_path: Path) -> None:
        """Test save then load preserves open_range settings."""
        from gc2_connect.config.settings import (
            ConditionsSettings,
            OpenRangeSettings,
            Settings,
        )

        settings_path = tmp_path / "settings.json"

        original = Settings(
            mode="open_range",
            open_range=OpenRangeSettings(
                conditions=ConditionsSettings(
                    temp_f=85.0,
                    elevation_ft=5280.0,
                    wind_speed_mph=15.0,
                ),
                surface="Rough",
                show_trajectory=False,
            ),
        )

        with patch("gc2_connect.config.settings.get_settings_path", return_value=settings_path):
            original.save()
            loaded = Settings.load()

        assert loaded.mode == "open_range"
        assert loaded.open_range.conditions.temp_f == 85.0
        assert loaded.open_range.conditions.elevation_ft == 5280.0
        assert loaded.open_range.conditions.wind_speed_mph == 15.0
        assert loaded.open_range.surface == "Rough"
        assert loaded.open_range.show_trajectory is False


class TestSettingsMigration:
    """Tests for settings migration from v1 to v2."""

    def test_migrate_v1_to_v2_adds_open_range(self, tmp_path: Path) -> None:
        """Test that loading v1 settings adds open_range with defaults."""
        from gc2_connect.config.settings import Settings

        settings_path = tmp_path / "settings.json"
        # v1 settings without open_range or mode
        v1_data = {
            "version": 1,
            "gspro": {"host": "192.168.1.50", "port": 921, "auto_connect": True},
            "gc2": {"auto_connect": True, "reject_zero_spin": True, "use_mock": False},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
        }
        settings_path.write_text(json.dumps(v1_data))

        with patch("gc2_connect.config.settings.get_settings_path", return_value=settings_path):
            settings = Settings.load()

        # Should have open_range with defaults
        assert settings.open_range is not None
        assert settings.open_range.surface == "Fairway"
        assert settings.open_range.conditions.temp_f == 70.0
        # Should have mode defaulting to gspro
        assert settings.mode == "gspro"
        # Should preserve existing v1 settings
        assert settings.gspro.host == "192.168.1.50"
        assert settings.gspro.auto_connect is True
        assert settings.gc2.auto_connect is True

    def test_migrate_v1_preserves_gspro_settings(self, tmp_path: Path) -> None:
        """Test that migrating from v1 preserves GSPro settings."""
        from gc2_connect.config.settings import Settings

        settings_path = tmp_path / "settings.json"
        v1_data = {
            "version": 1,
            "gspro": {"host": "10.0.0.5", "port": 9000, "auto_connect": False},
            "gc2": {"auto_connect": False, "reject_zero_spin": False, "use_mock": True},
            "ui": {"theme": "light", "show_history": False, "history_limit": 100},
        }
        settings_path.write_text(json.dumps(v1_data))

        with patch("gc2_connect.config.settings.get_settings_path", return_value=settings_path):
            settings = Settings.load()

        assert settings.gspro.host == "10.0.0.5"
        assert settings.gspro.port == 9000
        assert settings.gspro.auto_connect is False
        assert settings.gc2.auto_connect is False
        assert settings.gc2.reject_zero_spin is False
        assert settings.gc2.use_mock is True
        assert settings.ui.theme == "light"
        assert settings.ui.show_history is False
        assert settings.ui.history_limit == 100

    def test_load_v2_settings_directly(self, tmp_path: Path) -> None:
        """Test that v2 settings load correctly without migration."""
        from gc2_connect.config.settings import Settings

        settings_path = tmp_path / "settings.json"
        v2_data = {
            "version": 2,
            "mode": "open_range",
            "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
            "gc2": {"auto_connect": True, "reject_zero_spin": True, "use_mock": False},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
            "open_range": {
                "conditions": {
                    "temp_f": 75.0,
                    "elevation_ft": 1000.0,
                    "humidity_pct": 40.0,
                    "wind_speed_mph": 5.0,
                    "wind_dir_deg": 90.0,
                },
                "surface": "Green",
                "show_trajectory": True,
                "camera_follow": False,
            },
        }
        settings_path.write_text(json.dumps(v2_data))

        with patch("gc2_connect.config.settings.get_settings_path", return_value=settings_path):
            settings = Settings.load()

        assert settings.version == 2
        assert settings.mode == "open_range"
        assert settings.open_range.conditions.temp_f == 75.0
        assert settings.open_range.conditions.elevation_ft == 1000.0
        assert settings.open_range.surface == "Green"
        assert settings.open_range.camera_follow is False

    def test_migration_saves_as_v2(self, tmp_path: Path) -> None:
        """Test that after migrating v1, saving creates v2 format."""
        from gc2_connect.config.settings import Settings

        settings_path = tmp_path / "settings.json"
        v1_data = {
            "version": 1,
            "gspro": {"host": "192.168.1.1", "port": 921, "auto_connect": True},
            "gc2": {"auto_connect": True, "reject_zero_spin": True, "use_mock": False},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
        }
        settings_path.write_text(json.dumps(v1_data))

        with patch("gc2_connect.config.settings.get_settings_path", return_value=settings_path):
            settings = Settings.load()
            settings.save()

        # Re-read the file
        saved_data = json.loads(settings_path.read_text())
        assert saved_data["version"] == 2
        assert "mode" in saved_data
        assert "open_range" in saved_data
        assert saved_data["open_range"]["surface"] == "Fairway"

    def test_partial_v1_settings_get_defaults(self, tmp_path: Path) -> None:
        """Test that partial v1 settings still work with defaults filled in."""
        from gc2_connect.config.settings import Settings

        settings_path = tmp_path / "settings.json"
        # Minimal v1 settings
        v1_data = {
            "version": 1,
            "gspro": {"host": "10.0.0.10", "port": 921, "auto_connect": False},
        }
        settings_path.write_text(json.dumps(v1_data))

        with patch("gc2_connect.config.settings.get_settings_path", return_value=settings_path):
            settings = Settings.load()

        # Custom gspro setting preserved
        assert settings.gspro.host == "10.0.0.10"
        # Defaults for gc2 and ui
        assert settings.gc2.auto_connect is True
        assert settings.ui.theme == "dark"
        # Defaults for open_range (added by migration)
        assert settings.open_range.surface == "Fairway"
        assert settings.mode == "gspro"
