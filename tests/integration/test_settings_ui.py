# ABOUTME: Integration tests for Settings integration with UI.
# ABOUTME: Tests that settings are loaded on startup and saved when changed.
"""Integration tests for Settings and UI integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from gc2_connect.ui.app import GC2ConnectApp


class TestSettingsLoadOnInit:
    """Tests for loading settings on app initialization."""

    def test_app_loads_settings_on_init(self, tmp_path: Path) -> None:
        """Test that GC2ConnectApp loads settings on initialization."""
        settings_path = tmp_path / "settings.json"
        settings_data = {
            "version": 1,
            "gspro": {"host": "10.0.0.50", "port": 8888, "auto_connect": True},
            "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
            "ui": {"theme": "light", "show_history": True, "history_limit": 100},
        }
        settings_path.write_text(json.dumps(settings_data))

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()

        assert app.settings is not None
        assert app.settings.gspro.host == "10.0.0.50"
        assert app.settings.gspro.port == 8888
        assert app.settings.gc2.use_mock is True
        assert app.settings.ui.history_limit == 100

    def test_app_uses_default_settings_if_file_missing(self, tmp_path: Path) -> None:
        """Test that app uses defaults if settings file doesn't exist."""
        settings_path = tmp_path / "nonexistent" / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()

        assert app.settings is not None
        assert app.settings.gspro.host == "127.0.0.1"
        assert app.settings.gspro.port == 921
        assert app.settings.gc2.use_mock is False

    def test_app_initializes_state_from_settings(self, tmp_path: Path) -> None:
        """Test that app state is initialized from loaded settings."""
        settings_path = tmp_path / "settings.json"
        settings_data = {
            "version": 1,
            "gspro": {"host": "192.168.1.200", "port": 5000, "auto_connect": False},
            "gc2": {"auto_connect": True, "reject_zero_spin": False, "use_mock": True},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 25},
        }
        settings_path.write_text(json.dumps(settings_data))

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()

        # State should match settings
        assert app.use_mock_gc2 is True
        assert app.history_limit == 25


class TestSettingsInputValues:
    """Tests for settings values being used in inputs."""

    def test_gspro_host_from_settings(self, tmp_path: Path) -> None:
        """Test that GSPro host input uses value from settings."""
        settings_path = tmp_path / "settings.json"
        settings_data = {
            "version": 1,
            "gspro": {"host": "custom.host.local", "port": 9999, "auto_connect": False},
            "gc2": {"auto_connect": True, "reject_zero_spin": True, "use_mock": False},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
        }
        settings_path.write_text(json.dumps(settings_data))

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()

        # The app should have the custom values ready for when build_ui is called
        assert app.settings.gspro.host == "custom.host.local"
        assert app.settings.gspro.port == 9999


class TestSettingsSave:
    """Tests for saving settings when changed."""

    def test_save_settings_persists_to_file(self, tmp_path: Path) -> None:
        """Test that save_settings writes to file."""
        settings_path = tmp_path / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()

            # Modify settings
            app.settings.gspro.host = "new.host.com"
            app.settings.gspro.port = 1234

            # Save settings
            app.save_settings()

        # Verify file was written
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert data["gspro"]["host"] == "new.host.com"
        assert data["gspro"]["port"] == 1234

    def test_update_gspro_settings_saves(self, tmp_path: Path) -> None:
        """Test that updating GSPro settings triggers save."""
        settings_path = tmp_path / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()
            app.update_gspro_host("updated.host.com")
            app.update_gspro_port(7777)

        # Verify saved values
        data = json.loads(settings_path.read_text())
        assert data["gspro"]["host"] == "updated.host.com"
        assert data["gspro"]["port"] == 7777

    def test_update_gc2_settings_saves(self, tmp_path: Path) -> None:
        """Test that updating GC2 settings triggers save."""
        settings_path = tmp_path / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()
            app.update_use_mock(True)

        # Verify saved values
        data = json.loads(settings_path.read_text())
        assert data["gc2"]["use_mock"] is True

    def test_update_history_limit_saves(self, tmp_path: Path) -> None:
        """Test that updating history limit triggers save."""
        settings_path = tmp_path / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()
            app.update_history_limit(75)

        # Verify saved values
        data = json.loads(settings_path.read_text())
        assert data["ui"]["history_limit"] == 75
        assert app.history_limit == 75


class TestSettingsRoundtrip:
    """Tests for settings persistence across app restarts."""

    def test_settings_persist_across_instances(self, tmp_path: Path) -> None:
        """Test that settings saved by one instance are loaded by another."""
        settings_path = tmp_path / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            # First instance - modify and save settings
            app1 = GC2ConnectApp()
            app1.update_gspro_host("persistent.host.com")
            app1.update_gspro_port(5555)
            app1.update_use_mock(True)
            app1.update_history_limit(99)

            # Second instance - should load saved settings
            app2 = GC2ConnectApp()

        assert app2.settings.gspro.host == "persistent.host.com"
        assert app2.settings.gspro.port == 5555
        assert app2.settings.gc2.use_mock is True
        assert app2.settings.ui.history_limit == 99
        assert app2.use_mock_gc2 is True
        assert app2.history_limit == 99


class TestSettingsPath:
    """Tests for settings file path display."""

    def test_get_settings_path_available(self, tmp_path: Path) -> None:
        """Test that app can provide settings path for display."""
        settings_path = tmp_path / "settings.json"

        with (
            patch(
                "gc2_connect.config.settings.get_settings_path",
                return_value=settings_path,
            ),
            patch("gc2_connect.ui.app.get_settings_path", return_value=settings_path),
        ):
            app = GC2ConnectApp()
            # Must call within the patch context
            assert app.get_settings_path() == settings_path
