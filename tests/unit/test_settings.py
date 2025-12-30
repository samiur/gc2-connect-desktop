# ABOUTME: Unit tests for the Settings module.
# ABOUTME: Tests settings persistence, platform paths, and load/save functionality.
"""Unit tests for Settings module."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from gc2_connect.config.settings import (
    GC2Settings,
    GSProSettings,
    Settings,
    UISettings,
    get_settings_path,
)


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_settings_has_version(self) -> None:
        """Test that settings has a version field."""
        settings = Settings()
        assert settings.version == 1

    def test_gspro_default_host(self) -> None:
        """Test default GSPro host."""
        settings = Settings()
        assert settings.gspro.host == "127.0.0.1"

    def test_gspro_default_port(self) -> None:
        """Test default GSPro port."""
        settings = Settings()
        assert settings.gspro.port == 921

    def test_gspro_default_auto_connect(self) -> None:
        """Test default GSPro auto_connect is False."""
        settings = Settings()
        assert settings.gspro.auto_connect is False

    def test_gc2_default_auto_connect(self) -> None:
        """Test default GC2 auto_connect is True."""
        settings = Settings()
        assert settings.gc2.auto_connect is True

    def test_gc2_default_reject_zero_spin(self) -> None:
        """Test default GC2 reject_zero_spin is True."""
        settings = Settings()
        assert settings.gc2.reject_zero_spin is True

    def test_gc2_default_use_mock(self) -> None:
        """Test default GC2 use_mock is False."""
        settings = Settings()
        assert settings.gc2.use_mock is False

    def test_ui_default_theme(self) -> None:
        """Test default UI theme is dark."""
        settings = Settings()
        assert settings.ui.theme == "dark"

    def test_ui_default_show_history(self) -> None:
        """Test default UI show_history is True."""
        settings = Settings()
        assert settings.ui.show_history is True

    def test_ui_default_history_limit(self) -> None:
        """Test default UI history_limit is 50."""
        settings = Settings()
        assert settings.ui.history_limit == 50


class TestGSProSettings:
    """Tests for GSProSettings model."""

    def test_create_with_custom_values(self) -> None:
        """Test creating GSProSettings with custom values."""
        gspro = GSProSettings(host="192.168.1.100", port=9000, auto_connect=True)
        assert gspro.host == "192.168.1.100"
        assert gspro.port == 9000
        assert gspro.auto_connect is True

    def test_port_must_be_positive(self) -> None:
        """Test that port must be a positive integer."""
        gspro = GSProSettings(port=1)
        assert gspro.port == 1

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        gspro = GSProSettings(host="10.0.0.1", port=8080, auto_connect=True)
        result = gspro.model_dump()
        assert result == {"host": "10.0.0.1", "port": 8080, "auto_connect": True}


class TestGC2Settings:
    """Tests for GC2Settings model."""

    def test_create_with_custom_values(self) -> None:
        """Test creating GC2Settings with custom values."""
        gc2 = GC2Settings(auto_connect=False, reject_zero_spin=False, use_mock=True)
        assert gc2.auto_connect is False
        assert gc2.reject_zero_spin is False
        assert gc2.use_mock is True

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        gc2 = GC2Settings(auto_connect=False, reject_zero_spin=True, use_mock=True)
        result = gc2.model_dump()
        assert result == {
            "auto_connect": False,
            "reject_zero_spin": True,
            "use_mock": True,
        }


class TestUISettings:
    """Tests for UISettings model."""

    def test_create_with_custom_values(self) -> None:
        """Test creating UISettings with custom values."""
        ui = UISettings(theme="light", show_history=False, history_limit=100)
        assert ui.theme == "light"
        assert ui.show_history is False
        assert ui.history_limit == 100

    def test_history_limit_must_be_positive(self) -> None:
        """Test that history_limit must be positive."""
        ui = UISettings(history_limit=1)
        assert ui.history_limit == 1

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        ui = UISettings(theme="light", show_history=False, history_limit=25)
        result = ui.model_dump()
        assert result == {"theme": "light", "show_history": False, "history_limit": 25}


class TestGetSettingsPath:
    """Tests for get_settings_path function."""

    def test_macos_path(self) -> None:
        """Test settings path on macOS."""
        with (
            patch.object(sys, "platform", "darwin"),
            patch("pathlib.Path.home", return_value=Path("/Users/testuser")),
        ):
            path = get_settings_path()
            assert path == Path(
                "/Users/testuser/Library/Application Support/GC2 Connect/settings.json"
            )

    def test_linux_path(self) -> None:
        """Test settings path on Linux."""
        with (
            patch.object(sys, "platform", "linux"),
            patch("pathlib.Path.home", return_value=Path("/home/testuser")),
        ):
            path = get_settings_path()
            assert path == Path("/home/testuser/.config/gc2-connect/settings.json")

    def test_unknown_platform_uses_linux_style(self) -> None:
        """Test that unknown platforms default to Linux-style path."""
        with (
            patch.object(sys, "platform", "freebsd"),
            patch("pathlib.Path.home", return_value=Path("/home/testuser")),
        ):
            path = get_settings_path()
            assert path == Path("/home/testuser/.config/gc2-connect/settings.json")


class TestSettingsLoad:
    """Tests for Settings.load() method."""

    def test_load_creates_defaults_if_file_not_exists(self, tmp_path: Path) -> None:
        """Test that load returns defaults if file doesn't exist."""
        settings_path = tmp_path / "nonexistent" / "settings.json"
        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings = Settings.load()
            assert settings.version == 1
            assert settings.gspro.host == "127.0.0.1"
            assert settings.gc2.auto_connect is True

    def test_load_reads_existing_file(self, tmp_path: Path) -> None:
        """Test that load reads existing settings file."""
        settings_path = tmp_path / "settings.json"
        settings_data = {
            "version": 1,
            "gspro": {"host": "192.168.1.50", "port": 9999, "auto_connect": True},
            "gc2": {"auto_connect": False, "reject_zero_spin": False, "use_mock": True},
            "ui": {"theme": "light", "show_history": False, "history_limit": 25},
        }
        settings_path.write_text(json.dumps(settings_data))

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings = Settings.load()
            assert settings.gspro.host == "192.168.1.50"
            assert settings.gspro.port == 9999
            assert settings.gspro.auto_connect is True
            assert settings.gc2.auto_connect is False
            assert settings.gc2.use_mock is True
            assert settings.ui.theme == "light"
            assert settings.ui.history_limit == 25

    def test_load_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test that load returns defaults on invalid JSON."""
        settings_path = tmp_path / "settings.json"
        settings_path.write_text("not valid json {{{")

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings = Settings.load()
            # Should return defaults
            assert settings.version == 1
            assert settings.gspro.host == "127.0.0.1"

    def test_load_handles_partial_data(self, tmp_path: Path) -> None:
        """Test that load handles partial settings data."""
        settings_path = tmp_path / "settings.json"
        # Only provide gspro settings
        settings_data = {
            "version": 1,
            "gspro": {"host": "10.0.0.1", "port": 5000, "auto_connect": False},
        }
        settings_path.write_text(json.dumps(settings_data))

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings = Settings.load()
            # Custom gspro values
            assert settings.gspro.host == "10.0.0.1"
            assert settings.gspro.port == 5000
            # Default gc2 and ui values
            assert settings.gc2.auto_connect is True
            assert settings.ui.theme == "dark"

    def test_load_with_custom_path(self, tmp_path: Path) -> None:
        """Test loading from a custom path."""
        custom_path = tmp_path / "custom" / "my_settings.json"
        custom_path.parent.mkdir(parents=True)
        settings_data = {
            "version": 1,
            "gspro": {"host": "custom.host", "port": 1234, "auto_connect": True},
            "gc2": {"auto_connect": True, "reject_zero_spin": True, "use_mock": False},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
        }
        custom_path.write_text(json.dumps(settings_data))

        settings = Settings.load(custom_path)
        assert settings.gspro.host == "custom.host"
        assert settings.gspro.port == 1234


class TestSettingsSave:
    """Tests for Settings.save() method."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test that save creates settings file."""
        settings_path = tmp_path / "settings.json"
        settings = Settings()

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings.save()

        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert data["version"] == 1
        assert data["gspro"]["host"] == "127.0.0.1"

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that save creates parent directories if needed."""
        settings_path = tmp_path / "nested" / "dirs" / "settings.json"
        settings = Settings()

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings.save()

        assert settings_path.exists()
        assert settings_path.parent.exists()

    def test_save_with_custom_values(self, tmp_path: Path) -> None:
        """Test saving custom settings values."""
        settings_path = tmp_path / "settings.json"
        settings = Settings(
            gspro=GSProSettings(host="192.168.1.200", port=8000, auto_connect=True),
            gc2=GC2Settings(auto_connect=False, reject_zero_spin=False, use_mock=True),
            ui=UISettings(theme="light", show_history=False, history_limit=100),
        )

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            settings.save()

        data = json.loads(settings_path.read_text())
        assert data["gspro"]["host"] == "192.168.1.200"
        assert data["gspro"]["port"] == 8000
        assert data["gc2"]["use_mock"] is True
        assert data["ui"]["theme"] == "light"
        assert data["ui"]["history_limit"] == 100

    def test_save_with_custom_path(self, tmp_path: Path) -> None:
        """Test saving to a custom path."""
        custom_path = tmp_path / "custom_settings.json"
        settings = Settings(
            gspro=GSProSettings(host="custom.save", port=5555, auto_connect=False)
        )

        settings.save(custom_path)

        assert custom_path.exists()
        data = json.loads(custom_path.read_text())
        assert data["gspro"]["host"] == "custom.save"


class TestSettingsRoundtrip:
    """Tests for save then load roundtrip."""

    def test_roundtrip_preserves_all_values(self, tmp_path: Path) -> None:
        """Test that save then load preserves all settings."""
        settings_path = tmp_path / "settings.json"

        original = Settings(
            gspro=GSProSettings(host="roundtrip.host", port=7777, auto_connect=True),
            gc2=GC2Settings(auto_connect=False, reject_zero_spin=False, use_mock=True),
            ui=UISettings(theme="light", show_history=False, history_limit=75),
        )

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            original.save()
            loaded = Settings.load()

        assert loaded.version == original.version
        assert loaded.gspro.host == original.gspro.host
        assert loaded.gspro.port == original.gspro.port
        assert loaded.gspro.auto_connect == original.gspro.auto_connect
        assert loaded.gc2.auto_connect == original.gc2.auto_connect
        assert loaded.gc2.reject_zero_spin == original.gc2.reject_zero_spin
        assert loaded.gc2.use_mock == original.gc2.use_mock
        assert loaded.ui.theme == original.ui.theme
        assert loaded.ui.show_history == original.ui.show_history
        assert loaded.ui.history_limit == original.ui.history_limit

    def test_multiple_save_load_cycles(self, tmp_path: Path) -> None:
        """Test multiple save/load cycles work correctly."""
        settings_path = tmp_path / "settings.json"

        with patch(
            "gc2_connect.config.settings.get_settings_path", return_value=settings_path
        ):
            # Cycle 1
            s1 = Settings(gspro=GSProSettings(host="host1", port=1111, auto_connect=False))
            s1.save()
            loaded1 = Settings.load()
            assert loaded1.gspro.host == "host1"

            # Cycle 2 - modify and save again
            s2 = Settings(gspro=GSProSettings(host="host2", port=2222, auto_connect=True))
            s2.save()
            loaded2 = Settings.load()
            assert loaded2.gspro.host == "host2"
            assert loaded2.gspro.port == 2222


class TestSettingsToDict:
    """Tests for Settings.to_dict() method."""

    def test_to_dict_structure(self) -> None:
        """Test that to_dict returns correct structure."""
        settings = Settings()
        result = settings.to_dict()

        assert "version" in result
        assert "gspro" in result
        assert "gc2" in result
        assert "ui" in result

    def test_to_dict_values(self) -> None:
        """Test that to_dict contains correct values."""
        settings = Settings(
            gspro=GSProSettings(host="test.host", port=1000, auto_connect=True),
            gc2=GC2Settings(auto_connect=False, reject_zero_spin=True, use_mock=True),
            ui=UISettings(theme="light", show_history=False, history_limit=30),
        )
        result = settings.to_dict()

        assert result["version"] == 1
        assert result["gspro"]["host"] == "test.host"
        assert result["gspro"]["port"] == 1000
        assert result["gc2"]["use_mock"] is True
        assert result["ui"]["theme"] == "light"
