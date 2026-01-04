# ABOUTME: End-to-end tests for complete user flows in GSPro mode.
# ABOUTME: Tests the full journey from app load to shot sending.
"""End-to-end tests for GSPro mode user flows.

Tests complete user journeys including:
- App initialization and settings loading
- GC2 connection (mock mode)
- GSPro connection and shot sending
- Shot history updates
- Settings persistence
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from gc2_connect.gc2.usb_reader import MockGC2Reader
from gc2_connect.models import GC2ShotData
from gc2_connect.services.shot_router import AppMode

if TYPE_CHECKING:
    from tests.e2e.conftest import E2EMockGSProServer


class TestAppStartup:
    """E2E tests for app startup behavior."""

    def test_app_loads_with_default_settings(self, default_e2e_app) -> None:
        """Test that app starts with default settings when none exist."""
        app = default_e2e_app

        assert app.settings is not None
        assert app.settings.gspro.host == "127.0.0.1"
        assert app.settings.gspro.port == 921
        assert app.settings.mode == "gspro"
        assert app.shot_router.mode == AppMode.GSPRO

    def test_app_loads_custom_settings(self, e2e_app_factory) -> None:
        """Test that app loads custom settings from file."""
        custom_settings = {
            "version": 2,
            "mode": "gspro",
            "gspro": {"host": "10.0.0.100", "port": 8000, "auto_connect": False},
            "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
            "ui": {"theme": "dark", "show_history": True, "history_limit": 75},
            "open_range": {
                "conditions": {
                    "temp_f": 75.0,
                    "elevation_ft": 1000.0,
                    "humidity_pct": 60.0,
                    "wind_speed_mph": 5.0,
                    "wind_dir_deg": 45.0,
                },
                "surface": "Fairway",
                "show_trajectory": True,
                "camera_follow": True,
            },
        }
        app = e2e_app_factory(initial_settings=custom_settings)

        assert app.settings.gspro.host == "10.0.0.100"
        assert app.settings.gspro.port == 8000
        assert app.settings.ui.history_limit == 75
        assert app.shot_history.limit == 75
        assert app.use_mock_gc2 is True

    def test_app_initializes_components(self, default_e2e_app) -> None:
        """Test that all required components are initialized."""
        app = default_e2e_app

        assert app.shot_router is not None
        assert app.open_range_engine is not None
        assert app.shot_history is not None
        assert app.gspro_client is None  # Not connected yet
        assert app.gc2_reader is None  # Not connected yet


class TestGC2ConnectionFlow:
    """E2E tests for GC2 connection flow."""

    @pytest.mark.asyncio
    async def test_connect_to_mock_gc2(self, e2e_app_with_mock_gc2) -> None:
        """Test connecting to mock GC2."""
        app = e2e_app_with_mock_gc2

        # Connect to mock GC2 (UI elements pre-mocked by factory)
        await app._connect_gc2()

        assert app.gc2_reader is not None
        assert isinstance(app.gc2_reader, MockGC2Reader)
        assert app.gc2_reader.is_connected is True

        # Cleanup
        app._disconnect_gc2()
        assert app.gc2_reader is None

    @pytest.mark.asyncio
    async def test_mock_gc2_sends_test_shot(self, e2e_app_with_mock_gc2) -> None:
        """Test that mock GC2 can send test shots."""
        app = e2e_app_with_mock_gc2

        shots_received: list[GC2ShotData] = []

        def on_shot(shot: GC2ShotData) -> None:
            shots_received.append(shot)

        await app._connect_gc2()
        app.gc2_reader.add_shot_callback(on_shot)  # type: ignore[union-attr]

        # Send test shot
        app._send_test_shot()

        # Wait for callback
        await asyncio.sleep(0.1)

        assert len(shots_received) == 1
        assert shots_received[0].ball_speed > 0
        assert shots_received[0].shot_id > 0

        app._disconnect_gc2()


class TestGSProConnectionFlow:
    """E2E tests for GSPro connection flow."""

    @pytest.mark.asyncio
    async def test_connect_to_gspro(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test connecting to GSPro server."""
        # Create app with server's port
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {
                    "host": e2e_mock_gspro_server.host,
                    "port": e2e_mock_gspro_server.port,
                    "auto_connect": False,
                },
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        # Set up inputs to match server address
        app.gspro_host_input.value = e2e_mock_gspro_server.host
        app.gspro_port_input.value = str(e2e_mock_gspro_server.port)

        # Connect to GSPro
        await app._connect_gspro()

        assert app.gspro_client is not None
        assert app.gspro_client.is_connected is True

        # Should have sent heartbeat
        await asyncio.sleep(0.2)
        assert len(e2e_mock_gspro_server.received_shots) >= 1

        app._disconnect_gspro()


class TestCompleteShotFlow:
    """E2E tests for complete shot flow from GC2 to GSPro."""

    @pytest.mark.asyncio
    async def test_shot_from_gc2_to_gspro(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test complete flow: GC2 shot -> App processing -> GSPro."""
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {
                    "host": e2e_mock_gspro_server.host,
                    "port": e2e_mock_gspro_server.port,
                    "auto_connect": False,
                },
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        # Set up inputs to match server address
        app.gspro_host_input.value = e2e_mock_gspro_server.host
        app.gspro_port_input.value = str(e2e_mock_gspro_server.port)

        # Connect both GC2 and GSPro
        await app._connect_gc2()
        await app._connect_gspro()

        assert app.gc2_reader is not None
        assert app.gspro_client is not None

        # Clear any initial messages
        e2e_mock_gspro_server.clear()

        # Send a test shot from mock GC2
        app._send_test_shot()

        # Wait for shot to be processed and sent
        await asyncio.sleep(0.3)

        # Verify shot was received by GSPro
        shot_messages = e2e_mock_gspro_server.get_shot_messages()
        assert len(shot_messages) >= 1

        # Verify shot has expected structure
        shot = shot_messages[0]
        assert "BallData" in shot
        assert shot["BallData"]["Speed"] > 0

        # Verify shot was added to history
        assert app.shot_history.count >= 1

        # Cleanup
        app._disconnect_gspro()
        app._disconnect_gc2()

    @pytest.mark.asyncio
    async def test_multiple_shots_in_sequence(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test multiple shots are sent and received correctly."""
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {
                    "host": e2e_mock_gspro_server.host,
                    "port": e2e_mock_gspro_server.port,
                    "auto_connect": False,
                },
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        # Set up inputs to match server address
        app.gspro_host_input.value = e2e_mock_gspro_server.host
        app.gspro_port_input.value = str(e2e_mock_gspro_server.port)

        await app._connect_gc2()
        await app._connect_gspro()

        e2e_mock_gspro_server.clear()

        # Send multiple shots
        for _ in range(3):
            app._send_test_shot()
            await asyncio.sleep(0.2)

        # Wait for all shots to be processed
        await asyncio.sleep(0.3)

        # Verify all shots were received
        shot_messages = e2e_mock_gspro_server.get_shot_messages()
        assert len(shot_messages) == 3

        # Verify shot history
        assert app.shot_history.count == 3

        # Cleanup
        app._disconnect_gspro()
        app._disconnect_gc2()


class TestShotHistory:
    """E2E tests for shot history functionality."""

    @pytest.mark.asyncio
    async def test_shot_history_updates_on_shot(self, e2e_app_with_mock_gc2) -> None:
        """Test that shot history updates when shot is received."""
        app = e2e_app_with_mock_gc2

        # UI elements are pre-mocked by the e2e_app_with_mock_gc2 fixture
        await app._connect_gc2()

        # Initially empty
        assert app.shot_history.count == 0

        # Send test shots
        for _ in range(5):
            app._send_test_shot()
            await asyncio.sleep(0.1)

        # Verify history updated
        assert app.shot_history.count == 5

        # Verify statistics are calculated
        stats = app.shot_history.get_statistics()
        assert stats["count"] == 5
        assert stats["avg_ball_speed"] > 0
        assert stats["avg_total_spin"] > 0

        app._disconnect_gc2()

    def test_shot_history_respects_limit(self, e2e_app_factory) -> None:
        """Test that shot history respects the configured limit."""
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 3},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        # Add more shots than limit
        for i in range(5):
            shot = GC2ShotData(
                shot_id=i + 1,
                ball_speed=140 + i,
                launch_angle=12.0,
                total_spin=2500,
                back_spin=2400,
                side_spin=100,
            )
            app.shot_history.add_shot(shot)

        # Should only have last 3
        assert app.shot_history.count == 3
        # Newest should be shot 5
        assert app.shot_history.shots[0].shot_id == 5

    def test_clear_history(self, default_e2e_app) -> None:
        """Test clearing shot history."""
        app = default_e2e_app

        # Add some shots
        for i in range(3):
            shot = GC2ShotData(
                shot_id=i + 1,
                ball_speed=140,
                launch_angle=12.0,
                total_spin=2500,
                back_spin=2400,
                side_spin=100,
            )
            app.shot_history.add_shot(shot)

        assert app.shot_history.count == 3

        # Clear history
        app.shot_history.clear()

        assert app.shot_history.count == 0


class TestSettingsPersistence:
    """E2E tests for settings persistence."""

    def test_settings_saved_on_host_change(self, e2e_app_factory, temp_settings_path: Path) -> None:
        """Test that changing GSPro host saves settings."""
        # Create with initial settings to ensure the directory exists
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        app.update_gspro_host("new-host.local")

        # Read saved settings
        saved = json.loads(temp_settings_path.read_text())
        assert saved["gspro"]["host"] == "new-host.local"

    def test_settings_saved_on_port_change(self, e2e_app_factory, temp_settings_path: Path) -> None:
        """Test that changing GSPro port saves settings."""
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        app.update_gspro_port(9999)

        saved = json.loads(temp_settings_path.read_text())
        assert saved["gspro"]["port"] == 9999

    def test_settings_saved_on_mock_toggle(self, e2e_app_factory, temp_settings_path: Path) -> None:
        """Test that toggling mock mode saves settings."""
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": False},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        app.update_use_mock(True)

        saved = json.loads(temp_settings_path.read_text())
        assert saved["gc2"]["use_mock"] is True

    def test_settings_persist_across_app_restart(
        self, e2e_app_factory, temp_settings_path: Path
    ) -> None:
        """Test that settings persist when app is restarted."""
        # First app instance - create with initial settings and change them
        app1 = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "gspro",
                "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 70.0,
                        "elevation_ft": 0.0,
                        "humidity_pct": 50.0,
                        "wind_speed_mph": 0.0,
                        "wind_dir_deg": 0.0,
                    },
                    "surface": "Fairway",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )
        app1.update_gspro_host("persistent-host.local")
        app1.update_gspro_port(7777)
        app1.update_history_limit(100)
        app1.shutdown()

        # Read the file to verify changes were saved
        saved = json.loads(temp_settings_path.read_text())
        assert saved["gspro"]["host"] == "persistent-host.local"
        assert saved["gspro"]["port"] == 7777
        assert saved["ui"]["history_limit"] == 100
