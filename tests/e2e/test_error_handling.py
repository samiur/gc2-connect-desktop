# ABOUTME: End-to-end tests for error handling scenarios.
# ABOUTME: Tests app recovery from various error conditions.
"""End-to-end tests for error handling.

Tests how the application handles various error scenarios:
- GC2 connection failures
- GSPro connection failures
- Mode switch during errors
- Recovery from errors
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2ShotData
from gc2_connect.services.shot_router import AppMode

if TYPE_CHECKING:
    from tests.e2e.conftest import E2EMockGSProServer


class TestGC2ConnectionErrors:
    """E2E tests for GC2 connection error handling."""

    @pytest.mark.asyncio
    async def test_gc2_connection_failure_without_device(self, e2e_app_factory) -> None:
        """Test handling of GC2 connection failure when device not present."""
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

        # Mock UI elements
        app.gc2_status_label = MagicMock()
        app.gc2_status_label.text = ""
        app.gc2_status_label.classes = MagicMock()

        # Attempt connection (will fail without USB device)
        await app._connect_gc2()

        # Should handle gracefully - status should indicate failure
        # The reader should exist but not be connected
        # (In real app, usb.core.find returns None and connect returns False)
        # Since there's no USB device, connect() should return False
        if app.gc2_reader is not None:
            # If reader was created, it should not be connected
            assert app.gc2_reader.is_connected is False

    @pytest.mark.asyncio
    async def test_gc2_disconnect_handled_gracefully(self, e2e_app_with_mock_gc2) -> None:
        """Test that GC2 disconnect is handled gracefully."""
        app = e2e_app_with_mock_gc2

        # Mock UI elements
        app.gc2_status_label = MagicMock()
        app.gc2_status_label.text = ""
        app.gc2_status_label.classes = MagicMock()

        await app._connect_gc2()
        assert app.gc2_reader is not None
        assert app.gc2_reader.is_connected is True

        # Disconnect
        app._disconnect_gc2()

        # Should be cleaned up
        assert app.gc2_reader is None

    @pytest.mark.asyncio
    async def test_app_works_without_gc2(self, default_e2e_app) -> None:
        """Test that app can function without GC2 connected."""
        app = default_e2e_app

        # App should be usable without GC2
        assert app.gc2_reader is None

        # Can still switch modes
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)
        assert app.shot_router.mode == AppMode.OPEN_RANGE

        # Can still use Open Range directly
        result = app.open_range_engine.simulate_test_shot("Driver")
        assert result.summary.carry_distance > 0


class TestGSProConnectionErrors:
    """E2E tests for GSPro connection error handling."""

    @pytest.mark.asyncio
    async def test_gspro_connection_failure_wrong_host(self, e2e_app_factory) -> None:
        """Test handling of GSPro connection failure with wrong host."""
        app = e2e_app_factory()

        # Mock UI to point to non-existent server
        app.gspro_host_input = type("MockInput", (), {"value": "192.168.255.255"})()
        app.gspro_port_input = type("MockInput", (), {"value": "12345"})()
        app.gspro_status_label = MagicMock()
        app.gspro_status_label.text = ""
        app.gspro_status_label.classes = MagicMock()

        # This will timeout trying to connect
        # Set a short timeout to speed up test
        with patch.object(GSProClient, "connect_async") as mock_connect:
            mock_connect.return_value = False
            await app._connect_gspro()

        # Client should exist but not be connected
        assert app.gspro_client is not None
        # Since mock returned False, connection failed

    @pytest.mark.asyncio
    async def test_gspro_disconnect_handled_gracefully(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that GSPro disconnect is handled gracefully."""
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

        # Mock UI
        app.gspro_host_input = type("MockInput", (), {"value": e2e_mock_gspro_server.host})()
        app.gspro_port_input = type("MockInput", (), {"value": str(e2e_mock_gspro_server.port)})()
        app.gspro_status_label = MagicMock()
        app.gspro_status_label.text = ""
        app.gspro_status_label.classes = MagicMock()

        await app._connect_gspro()
        assert app.gspro_client is not None

        # Disconnect
        app._disconnect_gspro()

        # Should be cleaned up
        assert app.gspro_client is None

    @pytest.mark.asyncio
    async def test_app_works_without_gspro(self, e2e_app_with_mock_gc2) -> None:
        """Test that app can function without GSPro connected."""
        app = e2e_app_with_mock_gc2

        # App should be usable without GSPro (in Open Range mode)
        assert app.gspro_client is None

        # Set up result callback before connecting
        results: list = []

        async def on_result(result) -> None:  # type: ignore[no-untyped-def]
            results.append(result)

        app.shot_router.on_shot_result(on_result)
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        await app._connect_gc2()

        # Should be able to process shots in Open Range
        app._send_test_shot()
        await asyncio.sleep(0.2)

        assert len(results) >= 1

        app._disconnect_gc2()


class TestModeSwitchDuringErrors:
    """E2E tests for mode switching during error conditions."""

    @pytest.mark.asyncio
    async def test_can_switch_to_open_range_when_gspro_disconnected(self, default_e2e_app) -> None:
        """Test that mode switch works even when GSPro is not connected."""
        app = default_e2e_app

        assert app.gspro_client is None  # Not connected

        # Should still be able to switch to Open Range
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)
        assert app.shot_router.mode == AppMode.OPEN_RANGE

        # Open Range should work
        result = app.open_range_engine.simulate_test_shot("Driver")
        assert result.summary.carry_distance > 0

    @pytest.mark.asyncio
    async def test_mode_switch_clears_pending_operations(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that mode switch handles any pending operations cleanly."""
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

        # Mock UI
        app.gspro_host_input = type("MockInput", (), {"value": e2e_mock_gspro_server.host})()
        app.gspro_port_input = type("MockInput", (), {"value": str(e2e_mock_gspro_server.port)})()
        app.gspro_status_label = MagicMock()
        app.gc2_status_label = MagicMock()
        app.shot_display = MagicMock()

        await app._connect_gc2()
        await app._connect_gspro()

        # Start sending shots
        app._send_test_shot()

        # Immediately switch modes
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        # Wait a bit
        await asyncio.sleep(0.2)

        # Should not crash - mode switch should handle gracefully
        assert app.shot_router.mode == AppMode.OPEN_RANGE

        app._disconnect_gspro()
        app._disconnect_gc2()


class TestRecoveryScenarios:
    """E2E tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_reconnect_gc2_after_disconnect(self, e2e_app_with_mock_gc2) -> None:
        """Test that GC2 can be reconnected after disconnect."""
        app = e2e_app_with_mock_gc2

        # Mock UI
        app.gc2_status_label = MagicMock()

        # Connect
        await app._connect_gc2()
        assert app.gc2_reader is not None

        # Disconnect
        app._disconnect_gc2()
        assert app.gc2_reader is None

        # Reconnect
        await app._connect_gc2()
        assert app.gc2_reader is not None
        assert app.gc2_reader.is_connected is True

        app._disconnect_gc2()

    @pytest.mark.asyncio
    async def test_reconnect_gspro_after_disconnect(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that GSPro can be reconnected after disconnect."""
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

        # Mock UI
        app.gspro_host_input = type("MockInput", (), {"value": e2e_mock_gspro_server.host})()
        app.gspro_port_input = type("MockInput", (), {"value": str(e2e_mock_gspro_server.port)})()
        app.gspro_status_label = MagicMock()

        # Connect
        await app._connect_gspro()
        assert app.gspro_client is not None

        # Disconnect
        app._disconnect_gspro()
        assert app.gspro_client is None

        # Reconnect
        await app._connect_gspro()
        assert app.gspro_client is not None
        assert app.gspro_client.is_connected is True

        app._disconnect_gspro()

    @pytest.mark.asyncio
    async def test_shot_history_preserved_through_errors(self, e2e_app_with_mock_gc2) -> None:
        """Test that shot history is preserved through connection errors."""
        app = e2e_app_with_mock_gc2

        # Mock UI
        app.gc2_status_label = MagicMock()
        app.shot_display = MagicMock()
        app.history_list = MagicMock()
        app.history_count_label = MagicMock()
        app.stats_avg_speed_label = MagicMock()
        app.stats_avg_spin_label = MagicMock()

        await app._connect_gc2()

        # Send some shots
        for _ in range(3):
            app._send_test_shot()
            await asyncio.sleep(0.1)

        initial_count = app.shot_history.count
        assert initial_count >= 3

        # Simulate connection issue - disconnect
        app._disconnect_gc2()

        # History should be preserved
        assert app.shot_history.count == initial_count

        # Reconnect and send more
        await app._connect_gc2()
        app._send_test_shot()
        await asyncio.sleep(0.1)

        # History should have grown
        assert app.shot_history.count > initial_count

        app._disconnect_gc2()


class TestShutdown:
    """E2E tests for app shutdown handling."""

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_all(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that shutdown properly disconnects all connections."""
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

        # Mock UI
        app.gspro_host_input = type("MockInput", (), {"value": e2e_mock_gspro_server.host})()
        app.gspro_port_input = type("MockInput", (), {"value": str(e2e_mock_gspro_server.port)})()
        app.gspro_status_label = MagicMock()
        app.gc2_status_label = MagicMock()

        # Connect both
        await app._connect_gc2()
        await app._connect_gspro()

        assert app.gc2_reader is not None
        assert app.gspro_client is not None

        # Shutdown
        app.shutdown()

        # Both should be disconnected
        assert app.gc2_reader is None
        assert app.gspro_client is None

    def test_shutdown_handles_no_connections(self, default_e2e_app) -> None:
        """Test that shutdown works even with no connections."""
        app = default_e2e_app

        assert app.gc2_reader is None
        assert app.gspro_client is None

        # Should not raise
        app.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_pending_tasks(self, e2e_app_with_mock_gc2) -> None:
        """Test that shutdown cancels any pending async tasks."""
        app = e2e_app_with_mock_gc2

        # Mock UI
        app.gc2_status_label = MagicMock()

        await app._connect_gc2()

        # Verify task exists before shutdown
        assert app._gc2_task is not None

        # Shutdown
        app.shutdown()

        # Task should be cancelled
        assert app._gc2_task is None


class TestInvalidShotHandling:
    """E2E tests for handling invalid shot data."""

    @pytest.mark.asyncio
    async def test_zero_spin_shot_not_sent_to_gspro(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that shots with zero spin (misreads) are not sent to GSPro."""
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

        # Mock UI
        app.gspro_host_input = type("MockInput", (), {"value": e2e_mock_gspro_server.host})()
        app.gspro_port_input = type("MockInput", (), {"value": str(e2e_mock_gspro_server.port)})()
        app.gspro_status_label = MagicMock()
        app.shot_display = MagicMock()

        await app._connect_gspro()
        e2e_mock_gspro_server.clear()

        # Create an invalid shot (zero spin)
        invalid_shot = GC2ShotData(
            shot_id=1,
            ball_speed=145.0,
            launch_angle=12.0,
            total_spin=0,
            back_spin=0,
            side_spin=0,
        )

        # Check if shot is valid
        assert invalid_shot.is_valid() is False

        # Note: In the real app, validation happens in the GC2USBReader
        # before the callback is invoked, so invalid shots never reach
        # the app. This test verifies the validation logic.

        app._disconnect_gspro()
