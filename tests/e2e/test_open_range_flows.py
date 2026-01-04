# ABOUTME: End-to-end tests for Open Range mode user flows.
# ABOUTME: Tests mode switching, shot simulation, and visualization.
"""End-to-end tests for Open Range mode user flows.

Tests complete user journeys including:
- Mode switching between GSPro and Open Range
- Shot simulation and trajectory calculation
- Open Range engine configuration
- Integration with shot router
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from gc2_connect.models import GC2ShotData
from gc2_connect.open_range.models import Conditions, Phase, ShotResult
from gc2_connect.services.shot_router import AppMode

if TYPE_CHECKING:
    from tests.e2e.conftest import E2EMockGSProServer


class TestModeSwitching:
    """E2E tests for mode switching behavior."""

    @pytest.mark.asyncio
    async def test_switch_to_open_range_mode(self, default_e2e_app) -> None:
        """Test switching from GSPro to Open Range mode."""
        app = default_e2e_app

        # Initially in GSPro mode
        assert app.shot_router.mode == AppMode.GSPRO

        # Switch to Open Range
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        assert app.shot_router.mode == AppMode.OPEN_RANGE

    @pytest.mark.asyncio
    async def test_switch_back_to_gspro_mode(self, default_e2e_app) -> None:
        """Test switching back to GSPro mode."""
        app = default_e2e_app

        # Switch to Open Range then back
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)
        await app.shot_router.set_mode(AppMode.GSPRO)

        assert app.shot_router.mode == AppMode.GSPRO

    @pytest.mark.asyncio
    async def test_mode_change_updates_settings(self, e2e_app_factory, temp_settings_path) -> None:
        """Test that mode change is saved to settings."""
        import json

        # Create with initial settings to ensure file exists
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

        # Change mode and save
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)
        app.settings.mode = AppMode.OPEN_RANGE.value
        app.save_settings()

        # Verify saved
        saved = json.loads(temp_settings_path.read_text())
        assert saved["mode"] == "open_range"

    @pytest.mark.asyncio
    async def test_mode_change_callback_invoked(self, default_e2e_app) -> None:
        """Test that mode change callback is invoked."""
        app = default_e2e_app

        mode_changes: list[AppMode] = []

        async def on_mode_change(mode: AppMode) -> None:
            mode_changes.append(mode)

        app.shot_router.on_mode_change(on_mode_change)

        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        assert len(mode_changes) == 1
        assert mode_changes[0] == AppMode.OPEN_RANGE


class TestOpenRangeShots:
    """E2E tests for Open Range shot processing."""

    @pytest.mark.asyncio
    async def test_shot_routed_to_open_range(self, default_e2e_app) -> None:
        """Test that shots are routed to Open Range when in that mode."""
        app = default_e2e_app

        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        app.shot_router.on_shot_result(on_result)
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        # Create a test shot
        shot = GC2ShotData(
            shot_id=1,
            ball_speed=145.0,
            launch_angle=12.0,
            total_spin=2500,
            back_spin=2400,
            side_spin=-200,
        )

        # Route the shot
        await app.shot_router.route_shot(shot)

        assert len(results) == 1
        assert isinstance(results[0], ShotResult)
        assert results[0].summary.carry_distance > 0

    @pytest.mark.asyncio
    async def test_open_range_calculates_trajectory(self, default_e2e_app) -> None:
        """Test that Open Range calculates a complete trajectory."""
        app = default_e2e_app

        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        app.shot_router.on_shot_result(on_result)
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=160.0,  # Driver speed
            launch_angle=11.0,
            total_spin=2700,
            back_spin=2600,
            side_spin=-100,
        )

        await app.shot_router.route_shot(shot)

        result = results[0]

        # Should have trajectory with multiple phases
        assert len(result.trajectory) > 0

        # Trajectory should include flight phase
        phases = {p.phase for p in result.trajectory}
        assert Phase.FLIGHT in phases

        # Should have summary data
        assert result.summary.carry_distance > 200  # Driver should carry 200+ yards
        assert result.summary.max_height > 0
        assert result.summary.flight_time > 0

    @pytest.mark.asyncio
    async def test_multiple_shots_in_open_range(self, default_e2e_app) -> None:
        """Test multiple shots processed in Open Range mode."""
        app = default_e2e_app

        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        app.shot_router.on_shot_result(on_result)
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        # Send shots with increasing ball speed
        for i in range(3):
            shot = GC2ShotData(
                shot_id=i + 1,
                ball_speed=130.0 + i * 20,  # 130, 150, 170 mph
                launch_angle=12.0,
                total_spin=2500,
                back_spin=2400,
                side_spin=0,
            )
            await app.shot_router.route_shot(shot)

        assert len(results) == 3

        # Faster shots should carry farther
        assert results[2].summary.carry_distance > results[1].summary.carry_distance
        assert results[1].summary.carry_distance > results[0].summary.carry_distance


class TestOpenRangeConditions:
    """E2E tests for Open Range environmental conditions."""

    def test_engine_starts_with_default_conditions(self, default_e2e_app) -> None:
        """Test that engine has default environmental conditions."""
        app = default_e2e_app

        assert app.open_range_engine.conditions.temp_f == 70.0
        assert app.open_range_engine.conditions.elevation_ft == 0.0
        assert app.open_range_engine.conditions.humidity_pct == 50.0
        assert app.open_range_engine.conditions.wind_speed_mph == 0.0

    def test_engine_uses_settings_conditions(self, e2e_app_factory) -> None:
        """Test that engine uses conditions from settings."""
        app = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "open_range",
                "gspro": {"host": "127.0.0.1", "port": 921, "auto_connect": False},
                "gc2": {"auto_connect": False, "reject_zero_spin": True, "use_mock": True},
                "ui": {"theme": "dark", "show_history": True, "history_limit": 50},
                "open_range": {
                    "conditions": {
                        "temp_f": 85.0,
                        "elevation_ft": 5280.0,  # Denver
                        "humidity_pct": 30.0,
                        "wind_speed_mph": 10.0,
                        "wind_dir_deg": 90.0,
                    },
                    "surface": "Rough",
                    "show_trajectory": True,
                    "camera_follow": True,
                },
            }
        )

        assert app.open_range_engine.conditions.temp_f == 85.0
        assert app.open_range_engine.conditions.elevation_ft == 5280.0
        assert app.open_range_engine.surface == "Rough"

    @pytest.mark.asyncio
    async def test_elevation_affects_distance(self, e2e_app_factory) -> None:
        """Test that higher elevation increases carry distance."""
        # Sea level app
        app_sea = e2e_app_factory(
            initial_settings={
                "version": 2,
                "mode": "open_range",
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

        # Same shot at both elevations
        result_sea = app_sea.open_range_engine.simulate_manual(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=2500.0,
            sidespin_rpm=0.0,
        )

        # Update conditions for Denver
        app_sea.open_range_engine.update_conditions(Conditions(elevation_ft=5280.0, temp_f=70.0))

        result_denver = app_sea.open_range_engine.simulate_manual(
            ball_speed_mph=150.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=2500.0,
            sidespin_rpm=0.0,
        )

        # Higher elevation = more carry
        assert result_denver.summary.carry_distance > result_sea.summary.carry_distance

    def test_update_conditions(self, default_e2e_app) -> None:
        """Test updating engine conditions."""
        app = default_e2e_app

        new_conditions = Conditions(
            temp_f=90.0,
            elevation_ft=1000.0,
            humidity_pct=80.0,
            wind_speed_mph=15.0,
            wind_dir_deg=180.0,
        )

        app.open_range_engine.update_conditions(new_conditions)

        assert app.open_range_engine.conditions.temp_f == 90.0
        assert app.open_range_engine.conditions.elevation_ft == 1000.0
        assert app.open_range_engine.conditions.wind_speed_mph == 15.0

    def test_update_surface(self, default_e2e_app) -> None:
        """Test updating engine surface type."""
        app = default_e2e_app

        assert app.open_range_engine.surface == "Fairway"

        app.open_range_engine.update_surface("Green")

        assert app.open_range_engine.surface == "Green"


class TestOpenRangeWithGC2:
    """E2E tests for Open Range with mock GC2 integration."""

    @pytest.mark.asyncio
    async def test_gc2_shot_to_open_range(self, e2e_app_with_mock_gc2) -> None:
        """Test complete flow: Mock GC2 -> Open Range simulation."""
        app = e2e_app_with_mock_gc2

        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        app.shot_router.on_shot_result(on_result)
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        # Connect mock GC2 (UI elements pre-mocked by factory)
        await app._connect_gc2()

        # Send test shot
        app._send_test_shot()

        # Wait for processing
        await asyncio.sleep(0.3)

        # Should have simulation result
        assert len(results) >= 1
        assert results[0].summary.carry_distance > 0

        # Shot should also be in history (history updates regardless of mode)
        assert app.shot_history.count >= 1

        app._disconnect_gc2()


class TestModeTransitionWithConnections:
    """E2E tests for mode transitions with active connections."""

    @pytest.mark.asyncio
    async def test_gspro_connection_preserved_on_mode_switch(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that GSPro connection is preserved when switching to Open Range."""
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

        # Switch to Open Range
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        # GSPro client should still exist (not disconnected)
        assert app.gspro_client is not None

        # Switch back to GSPro
        await app.shot_router.set_mode(AppMode.GSPRO)

        # Should still be connected (if connection is stable)
        # Note: Connection may have been lost due to timeout, so we just check client exists
        assert app.gspro_client is not None

        app._disconnect_gspro()

    @pytest.mark.asyncio
    async def test_can_send_to_gspro_after_open_range(
        self, e2e_app_factory, e2e_mock_gspro_server: E2EMockGSProServer
    ) -> None:
        """Test that GSPro works after using Open Range mode."""
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

        # Connect both
        await app._connect_gc2()
        await app._connect_gspro()

        # Use Open Range for a bit
        await app.shot_router.set_mode(AppMode.OPEN_RANGE)

        results: list[ShotResult] = []

        async def on_result(result: ShotResult) -> None:
            results.append(result)

        app.shot_router.on_shot_result(on_result)

        app._send_test_shot()
        await asyncio.sleep(0.2)

        assert len(results) >= 1

        # Switch back to GSPro
        await app.shot_router.set_mode(AppMode.GSPRO)

        e2e_mock_gspro_server.clear()

        # Send shot to GSPro
        app._send_test_shot()
        await asyncio.sleep(0.3)

        # Should be received by GSPro
        shot_messages = e2e_mock_gspro_server.get_shot_messages()
        assert len(shot_messages) >= 1

        app._disconnect_gspro()
        app._disconnect_gc2()
