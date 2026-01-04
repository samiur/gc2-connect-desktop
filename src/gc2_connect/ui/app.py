# ABOUTME: NiceGUI web-based user interface for GC2 Connect.
# ABOUTME: Displays connection status, shot data, history, and provides manual controls.
"""GC2 Connect - NiceGUI Application."""

from __future__ import annotations

import asyncio
import atexit
import logging
import os
import signal
from pathlib import Path
from typing import Any

from nicegui import app, ui

from gc2_connect.config.settings import Settings, get_settings_path
from gc2_connect.gc2.usb_reader import GC2USBReader, MockGC2Reader
from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2BallStatus, GC2ShotData
from gc2_connect.open_range.engine import OpenRangeEngine
from gc2_connect.open_range.models import Conditions, ShotResult
from gc2_connect.services.export import export_to_csv, generate_export_filename
from gc2_connect.services.history import ShotHistoryManager
from gc2_connect.services.shot_router import AppMode, ShotRouter
from gc2_connect.ui.components.mode_selector import ModeSelector
from gc2_connect.ui.components.open_range_view import OpenRangeView
from gc2_connect.utils.reconnect import ReconnectionManager, ReconnectionState

# Configure logging (set GC2_DEBUG=1 for verbose USB debugging)
log_level = logging.DEBUG if os.environ.get("GC2_DEBUG") else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GC2ConnectApp:
    """Main application class."""

    def __init__(self) -> None:
        # Load settings
        self.settings = Settings.load()
        logger.info(f"Settings loaded from {get_settings_path()}")

        # State (initialized from settings)
        self.gc2_reader: GC2USBReader | MockGC2Reader | None = None
        self.gspro_client: GSProClient | None = None
        self.shot_history = ShotHistoryManager(limit=self.settings.ui.history_limit)
        self.auto_send = True
        self.use_mock_gc2 = self.settings.gc2.use_mock

        # Shot router and Open Range components
        self.shot_router = ShotRouter()
        self.open_range_engine = OpenRangeEngine(
            conditions=Conditions(
                temp_f=self.settings.open_range.conditions.temp_f,
                elevation_ft=self.settings.open_range.conditions.elevation_ft,
                humidity_pct=self.settings.open_range.conditions.humidity_pct,
                wind_speed_mph=self.settings.open_range.conditions.wind_speed_mph,
                wind_dir_deg=self.settings.open_range.conditions.wind_dir_deg,
            ),
            surface=self.settings.open_range.surface,
        )
        self.shot_router.set_open_range_engine(self.open_range_engine)
        self.shot_router.on_mode_change(self._on_mode_change)
        self.shot_router.on_shot_result(self._on_open_range_result)

        # UI component instances
        self.mode_selector: ModeSelector | None = None
        self.open_range_view: OpenRangeView | None = None

        # UI references (typed as Any due to NiceGUI's dynamic nature)
        self.gc2_status_label: Any = None
        self.gc2_ready_indicator: Any = None
        self.gc2_ball_indicator: Any = None
        self.gspro_status_label: Any = None
        self.shot_display: Any = None
        self.history_list: Any = None
        self.gspro_host_input: Any = None
        self.gspro_port_input: Any = None
        self.history_limit_input: Any = None
        self.settings_path_label: Any = None
        self.history_count_label: Any = None
        self.stats_avg_speed_label: Any = None
        self.stats_avg_spin_label: Any = None

        # Container references for mode-specific visibility
        self._gspro_panel: Any = None
        self._open_range_container: Any = None
        self._gspro_content_column: Any = None

        # Ball status state
        self.send_status_to_gspro = True

        # Reconnection managers
        self._gc2_reconnect_mgr = ReconnectionManager(max_retries=5, base_delay=1.0)
        self._gspro_reconnect_mgr = ReconnectionManager(max_retries=5, base_delay=1.0)
        self._setup_reconnection_callbacks()

        # Tasks
        self._gc2_task: asyncio.Task[None] | None = None
        self._gc2_reconnect_task: asyncio.Task[None] | None = None
        self._gspro_reconnect_task: asyncio.Task[None] | None = None

    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            self.settings.save()
            logger.info("Settings saved")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            ui.notify(f"Failed to save settings: {e}", type="negative")

    def _setup_reconnection_callbacks(self) -> None:
        """Set up callbacks for reconnection managers."""
        # GC2 reconnection state changes
        self._gc2_reconnect_mgr.on_state_change(self._on_gc2_reconnect_state_change)
        self._gc2_reconnect_mgr.on_attempt(self._on_gc2_reconnect_attempt)

        # GSPro reconnection state changes
        self._gspro_reconnect_mgr.on_state_change(self._on_gspro_reconnect_state_change)
        self._gspro_reconnect_mgr.on_attempt(self._on_gspro_reconnect_attempt)

    def _on_gc2_reconnect_state_change(self, state: ReconnectionState) -> None:
        """Handle GC2 reconnection state changes."""
        if self.gc2_status_label is None:
            return

        if state == ReconnectionState.RECONNECTING:
            self.gc2_status_label.text = "Reconnecting..."
            self.gc2_status_label.classes(
                remove="text-red-500 text-green-500", add="text-yellow-500"
            )
        elif state == ReconnectionState.CONNECTED:
            self.gc2_status_label.text = "Connected"
            self.gc2_status_label.classes(
                remove="text-red-500 text-yellow-500", add="text-green-500"
            )
            ui.notify("GC2 Reconnected!", type="positive")
        elif state == ReconnectionState.FAILED:
            self.gc2_status_label.text = "Reconnection Failed"
            self.gc2_status_label.classes(
                remove="text-green-500 text-yellow-500", add="text-red-500"
            )
            ui.notify("GC2 reconnection failed after max retries", type="negative")
        elif state == ReconnectionState.DISCONNECTED:
            self.gc2_status_label.text = "Disconnected"
            self.gc2_status_label.classes(
                remove="text-green-500 text-yellow-500", add="text-red-500"
            )

    def _on_gc2_reconnect_attempt(self, attempt: int, delay: float) -> None:
        """Handle GC2 reconnection attempt notification."""
        if self.gc2_status_label is None:
            return

        self.gc2_status_label.text = f"Reconnecting... ({attempt}/5, {delay:.0f}s)"
        ui.notify(f"GC2 reconnecting in {delay:.0f}s (attempt {attempt})", type="info")

    def _on_gspro_reconnect_state_change(self, state: ReconnectionState) -> None:
        """Handle GSPro reconnection state changes."""
        if self.gspro_status_label is None:
            return

        if state == ReconnectionState.RECONNECTING:
            self.gspro_status_label.text = "Reconnecting..."
            self.gspro_status_label.classes(
                remove="text-red-500 text-green-500", add="text-yellow-500"
            )
        elif state == ReconnectionState.CONNECTED:
            host = self.gspro_host_input.value if self.gspro_host_input else "GSPro"
            port = self.gspro_port_input.value if self.gspro_port_input else "921"
            self.gspro_status_label.text = f"Connected to {host}:{port}"
            self.gspro_status_label.classes(
                remove="text-red-500 text-yellow-500", add="text-green-500"
            )
            ui.notify("GSPro Reconnected!", type="positive")
        elif state == ReconnectionState.FAILED:
            self.gspro_status_label.text = "Reconnection Failed"
            self.gspro_status_label.classes(
                remove="text-green-500 text-yellow-500", add="text-red-500"
            )
            ui.notify("GSPro reconnection failed after max retries", type="negative")
        elif state == ReconnectionState.DISCONNECTED:
            self.gspro_status_label.text = "Disconnected"
            self.gspro_status_label.classes(
                remove="text-green-500 text-yellow-500", add="text-red-500"
            )

    def _on_gspro_reconnect_attempt(self, attempt: int, delay: float) -> None:
        """Handle GSPro reconnection attempt notification."""
        if self.gspro_status_label is None:
            return

        self.gspro_status_label.text = f"Reconnecting... ({attempt}/5, {delay:.0f}s)"
        ui.notify(f"GSPro reconnecting in {delay:.0f}s (attempt {attempt})", type="info")

    def _on_gc2_disconnect(self) -> None:
        """Handle GC2 disconnect event - trigger reconnection."""
        logger.warning("GC2 disconnected - starting auto-reconnection")

        if self.gc2_status_label:
            self.gc2_status_label.text = "Connection Lost"
            self.gc2_status_label.classes(remove="text-green-500", add="text-red-500")

        ui.notify("GC2 connection lost - attempting to reconnect...", type="warning")

        # Start reconnection in background
        self._gc2_reconnect_task = asyncio.create_task(self._reconnect_gc2())

    def _on_gspro_disconnect(self) -> None:
        """Handle GSPro disconnect event - trigger reconnection."""
        logger.warning("GSPro disconnected - starting auto-reconnection")

        if self.gspro_status_label:
            self.gspro_status_label.text = "Connection Lost"
            self.gspro_status_label.classes(remove="text-green-500", add="text-red-500")

        ui.notify("GSPro connection lost - attempting to reconnect...", type="warning")

        # Start reconnection in background
        self._gspro_reconnect_task = asyncio.create_task(self._reconnect_gspro())

    async def _reconnect_gc2(self) -> None:
        """Attempt to reconnect to GC2."""
        # Clean up existing reader
        if self._gc2_task:
            self._gc2_task.cancel()
            self._gc2_task = None

        if self.gc2_reader:
            try:
                self.gc2_reader.disconnect()
            except Exception:
                pass
            self.gc2_reader = None

        # Create new reader
        if self.use_mock_gc2:
            self.gc2_reader = MockGC2Reader()
        else:
            self.gc2_reader = GC2USBReader()

        self.gc2_reader.add_shot_callback(self._on_shot_received)
        self.gc2_reader.add_status_callback(self._on_status_received)
        self.gc2_reader.add_disconnect_callback(self._on_gc2_disconnect)

        # Attempt reconnection
        success = await self._gc2_reconnect_mgr.attempt_reconnect(self.gc2_reader.connect)

        if success:
            # Start read loop
            self._gc2_task = asyncio.create_task(self.gc2_reader.read_loop())

    async def _reconnect_gspro(self) -> None:
        """Attempt to reconnect to GSPro."""
        # Clean up existing client
        if self.gspro_client:
            try:
                self.gspro_client.disconnect()
            except Exception:
                pass
            self.gspro_client = None

        # Get connection parameters
        host = self.gspro_host_input.value if self.gspro_host_input else self.settings.gspro.host
        port = (
            int(self.gspro_port_input.value) if self.gspro_port_input else self.settings.gspro.port
        )

        # Create new client
        self.gspro_client = GSProClient(host=host, port=port)
        self.gspro_client.add_disconnect_callback(self._on_gspro_disconnect)

        # Attempt reconnection
        await self._gspro_reconnect_mgr.attempt_reconnect(self.gspro_client.connect)

    def get_settings_path(self) -> Path:
        """Get the path to the settings file."""
        return get_settings_path()

    def update_gspro_host(self, host: str) -> None:
        """Update GSPro host and save settings."""
        self.settings.gspro.host = host
        self.save_settings()

    def update_gspro_port(self, port: int) -> None:
        """Update GSPro port and save settings."""
        self.settings.gspro.port = port
        self.save_settings()

    def update_use_mock(self, use_mock: bool) -> None:
        """Update use_mock setting and save."""
        self.use_mock_gc2 = use_mock
        self.settings.gc2.use_mock = use_mock
        self.save_settings()

    def update_history_limit(self, limit: int) -> None:
        """Update history limit and save settings."""
        self.shot_history.limit = limit
        self.settings.ui.history_limit = limit
        self.save_settings()
        # Only refresh if UI has been built
        if self.history_list is not None:
            self._refresh_history()

    def build_ui(self) -> None:
        """Build the NiceGUI interface."""
        # Apply theme from settings
        if self.settings.ui.theme == "dark":
            ui.dark_mode().enable()
        else:
            ui.dark_mode().disable()

        with ui.header().classes("bg-blue-900"):
            ui.label("GC2 Connect").classes("text-2xl font-bold")
            ui.space()

            # Mode selector in header
            self.mode_selector = ModeSelector(
                on_change=self._handle_mode_selector_change,
                initial_mode=AppMode(self.settings.mode),
            )
            self.mode_selector.build()

            ui.space()
            with ui.row().classes("items-center"):
                ui.label("Auto-send:").classes("text-sm")
                ui.switch(value=True, on_change=lambda e: setattr(self, "auto_send", e.value))

        # Main content area
        with ui.row().classes("w-full gap-4 p-4"):
            # Left column - GC2 Connection (always visible)
            with ui.column().classes("w-64 flex-shrink-0"):
                self._build_gc2_panel()
                self._build_settings_panel()

            # GSPro mode content
            with ui.column().classes("flex-grow") as gspro_content:
                self._gspro_content_column = gspro_content
                with ui.row().classes("w-full gap-4"):
                    # GSPro connection panel
                    with ui.column().classes("w-72"):
                        self._build_gspro_panel()

                    # Center column - Current Shot
                    with ui.column().classes("flex-grow"):
                        self._build_shot_display()

                    # Right column - Shot History
                    with ui.column().classes("w-80"):
                        self._build_history_panel()

            # Open Range mode content (initially hidden)
            with ui.column().classes("flex-grow hidden") as open_range_container:
                self._open_range_container = open_range_container
                self.open_range_view = OpenRangeView()
                self.open_range_view.build()

        # Set initial mode visibility
        initial_mode = AppMode(self.settings.mode)
        if initial_mode == AppMode.OPEN_RANGE:
            self._show_open_range_ui()
        else:
            self._show_gspro_ui()

    def _build_gc2_panel(self) -> None:
        """Build the GC2 connection panel."""
        with ui.card().classes("w-full"):
            ui.label("GC2 Launch Monitor").classes("text-lg font-bold")
            ui.separator()

            with ui.row().classes("items-center gap-2"):
                self.gc2_status_label = ui.label("Disconnected").classes("text-red-500")
                ui.badge("USB").classes("bg-gray-600")

            # Ball status indicators
            with ui.row().classes("items-center gap-4 mt-2"):
                with ui.row().classes("items-center gap-1"):
                    self.gc2_ready_indicator = ui.icon("circle").classes("text-gray-500 text-sm")
                    ui.label("Ready").classes("text-sm text-gray-400")
                with ui.row().classes("items-center gap-1"):
                    self.gc2_ball_indicator = ui.icon("sports_golf").classes(
                        "text-gray-500 text-sm"
                    )
                    ui.label("Ball").classes("text-sm text-gray-400")

            with ui.row().classes("gap-2 mt-4"):
                ui.button("Connect", on_click=self._connect_gc2).classes("bg-green-600")
                ui.button("Disconnect", on_click=self._disconnect_gc2).classes("bg-red-600")

            with ui.row().classes("items-center gap-2 mt-2"):
                ui.checkbox(
                    "Use Mock GC2",
                    value=self.use_mock_gc2,
                    on_change=lambda e: self.update_use_mock(e.value),
                )
                ui.button("Send Test Shot", on_click=self._send_test_shot).props("flat")

    def _build_gspro_panel(self) -> None:
        """Build the GSPro connection panel."""
        with ui.card().classes("w-full mt-4"):
            ui.label("GSPro Connection").classes("text-lg font-bold")
            ui.separator()

            with ui.row().classes("items-center gap-2"):
                self.gspro_status_label = ui.label("Disconnected").classes("text-red-500")

            with ui.column().classes("gap-2 mt-2"):
                self.gspro_host_input = ui.input(
                    label="GSPro IP Address",
                    value=self.settings.gspro.host,
                    placeholder="e.g., 192.168.1.100",
                    on_change=lambda e: self.update_gspro_host(e.value),
                ).classes("w-full")

                self.gspro_port_input = ui.input(
                    label="Port",
                    value=str(self.settings.gspro.port),
                    placeholder="921",
                    on_change=lambda e: self._on_port_change(e.value),
                ).classes("w-32")

            with ui.row().classes("gap-2 mt-4"):
                ui.button("Connect", on_click=self._connect_gspro).classes("bg-green-600")
                ui.button("Disconnect", on_click=self._disconnect_gspro).classes("bg-red-600")

    def _on_port_change(self, value: str) -> None:
        """Handle port input change with validation."""
        try:
            port = int(value)
            if port > 0:
                self.update_gspro_port(port)
        except ValueError:
            pass  # Ignore invalid port values

    def _build_settings_panel(self) -> None:
        """Build the settings panel with collapsible section."""
        with ui.expansion("Settings", icon="settings").classes("w-full mt-4"):  # noqa: SIM117
            with ui.card().classes("w-full"):  # Card must be inside expansion for NiceGUI
                # History settings
                ui.label("History Settings").classes("text-md font-semibold")
                with ui.row().classes("items-center gap-2 mt-2"):
                    ui.label("History Limit:")
                    self.history_limit_input = ui.number(
                        value=self.shot_history.limit,
                        min=10,
                        max=500,
                        step=10,
                        on_change=lambda e: self._on_history_limit_change(e.value),
                    ).classes("w-24")

                ui.separator().classes("my-4")

                # Auto-connect settings
                ui.label("Auto-Connect").classes("text-md font-semibold")
                with ui.column().classes("gap-2 mt-2"):
                    ui.checkbox(
                        "Auto-connect GC2 on startup",
                        value=self.settings.gc2.auto_connect,
                        on_change=lambda e: self._on_gc2_auto_connect_change(e.value),
                    )
                    ui.checkbox(
                        "Auto-connect GSPro on startup",
                        value=self.settings.gspro.auto_connect,
                        on_change=lambda e: self._on_gspro_auto_connect_change(e.value),
                    )

                ui.separator().classes("my-4")

                # Settings file location
                ui.label("Settings File").classes("text-md font-semibold")
                self.settings_path_label = ui.label(str(get_settings_path())).classes(
                    "text-xs text-gray-400 break-all mt-1"
                )

                # Save button
                with ui.row().classes("mt-4"):
                    ui.button(
                        "Save Settings", on_click=self._on_save_settings_click, icon="save"
                    ).props("flat")

    def _on_history_limit_change(self, value: float | None) -> None:
        """Handle history limit change."""
        if value is not None and value > 0:
            self.update_history_limit(int(value))

    def _on_gc2_auto_connect_change(self, value: bool) -> None:
        """Handle GC2 auto-connect change."""
        self.settings.gc2.auto_connect = value
        self.save_settings()

    def _on_gspro_auto_connect_change(self, value: bool) -> None:
        """Handle GSPro auto-connect change."""
        self.settings.gspro.auto_connect = value
        self.save_settings()

    def _on_save_settings_click(self) -> None:
        """Handle explicit save settings button click."""
        self.save_settings()
        ui.notify("Settings saved!", type="positive")

    def _build_shot_display(self) -> None:
        """Build the current shot display panel."""
        with ui.card().classes("w-full h-full"):
            ui.label("Current Shot").classes("text-lg font-bold")
            ui.separator()

            self.shot_display = ui.column().classes("w-full")

            with self.shot_display:
                ui.label("No shot data yet").classes("text-gray-500 italic")

    def _build_history_panel(self) -> None:
        """Build the shot history panel."""
        with ui.card().classes("w-full h-full"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Shot History").classes("text-lg font-bold")
                self.history_count_label = ui.label(
                    self.shot_history.format_count_display()
                ).classes("text-sm text-gray-400")
                with ui.row().classes("gap-1"):
                    ui.button("Export CSV", on_click=self._export_csv, icon="download").props(
                        "flat size=sm"
                    )
                    ui.button("Clear", on_click=self._clear_history).props("flat size=sm")

            ui.separator()

            # Session statistics
            with ui.row().classes("w-full gap-4 mb-2"):
                with ui.column().classes("flex-1"):
                    ui.label("Avg Speed").classes("text-xs text-gray-400")
                    self.stats_avg_speed_label = ui.label("-- mph").classes("text-sm font-semibold")
                with ui.column().classes("flex-1"):
                    ui.label("Avg Spin").classes("text-xs text-gray-400")
                    self.stats_avg_spin_label = ui.label("-- rpm").classes("text-sm font-semibold")

            ui.separator()

            self.history_list = ui.column().classes("w-full max-h-80 overflow-y-auto")

    def _update_shot_display(self, shot: GC2ShotData) -> None:
        """Update the shot display with new data."""
        self.shot_display.clear()

        with self.shot_display:
            # Ball Data Section
            ui.label("Ball Data").classes("text-md font-semibold text-blue-400")

            with ui.grid(columns=2).classes("gap-2 w-full"):
                self._stat_card("Ball Speed", f"{shot.ball_speed:.1f}", "mph")
                self._stat_card("Launch Angle", f"{shot.launch_angle:.1f}", "°")
                self._stat_card("H. Launch", f"{shot.horizontal_launch_angle:.1f}", "°")
                self._stat_card("Total Spin", f"{shot.total_spin:.0f}", "RPM")
                self._stat_card("Back Spin", f"{shot.back_spin:.0f}", "RPM")
                self._stat_card("Side Spin", f"{shot.side_spin:.0f}", "RPM")
                self._stat_card("Spin Axis", f"{shot.spin_axis:.1f}", "°")

            # Club Data Section (if available)
            if shot.has_club_data:
                ui.separator().classes("my-2")
                ui.label("Club Data (HMT)").classes("text-md font-semibold text-green-400")

                with ui.grid(columns=2).classes("gap-2 w-full"):
                    if shot.club_speed:
                        self._stat_card("Club Speed", f"{shot.club_speed:.1f}", "mph")
                    if shot.swing_path is not None:
                        self._stat_card("Path", f"{shot.swing_path:.1f}", "°")
                    if shot.face_to_target is not None:
                        self._stat_card("Face", f"{shot.face_to_target:.1f}", "°")
                    if shot.angle_of_attack is not None:
                        self._stat_card("Attack", f"{shot.angle_of_attack:.1f}", "°")

    def _stat_card(self, label: str, value: str, unit: str) -> None:
        """Create a stat display card."""
        with ui.column().classes("bg-gray-800 rounded p-2"):
            ui.label(label).classes("text-xs text-gray-400")
            with ui.row().classes("items-baseline"):
                ui.label(value).classes("text-xl font-bold")
                ui.label(unit).classes("text-sm text-gray-400 ml-1")

    def _add_to_history(self, shot: GC2ShotData) -> None:
        """Add a shot to the history list."""
        self.shot_history.add_shot(shot)
        self._refresh_history()

    def _refresh_history(self) -> None:
        """Refresh the history list display."""
        self.history_list.clear()

        # Update count display
        if self.history_count_label:
            self.history_count_label.text = self.shot_history.format_count_display()

        # Update statistics
        stats = self.shot_history.get_statistics()
        if self.stats_avg_speed_label:
            if stats["count"] > 0:
                self.stats_avg_speed_label.text = f"{stats['avg_ball_speed']:.1f} mph"
            else:
                self.stats_avg_speed_label.text = "-- mph"
        if self.stats_avg_spin_label:
            if stats["count"] > 0:
                self.stats_avg_spin_label.text = f"{stats['avg_total_spin']:.0f} rpm"
            else:
                self.stats_avg_spin_label.text = "-- rpm"

        # Render shot list (limit to 20 for performance but use full history for stats)
        with self.history_list:
            for shot in self.shot_history.shots[:20]:
                with ui.row().classes("w-full bg-gray-800 rounded p-2 mb-1 items-center"):
                    ui.label(f"#{shot.shot_id}").classes("text-sm text-gray-400 w-12")
                    ui.label(f"{shot.ball_speed:.1f} mph").classes("text-sm font-bold w-20")
                    ui.label(f"{shot.launch_angle:.1f}°").classes("text-sm w-12")
                    ui.label(f"{shot.total_spin:.0f} rpm").classes("text-sm w-20")
                    ui.label(shot.timestamp.strftime("%H:%M:%S")).classes("text-xs text-gray-500")

    def _clear_history(self) -> None:
        """Clear the shot history."""
        self.shot_history.clear()
        self._refresh_history()

    async def _export_csv(self) -> None:
        """Export shot history to CSV file.

        Opens a file download dialog for the user to save the CSV file.
        The default filename includes a timestamp.
        """
        if self.shot_history.count == 0:
            ui.notify("No shots to export", type="warning")
            return

        try:
            # Generate filename with timestamp
            filename = generate_export_filename()

            # Get platform-appropriate downloads directory
            downloads_dir = Path.home() / "Downloads"
            if not downloads_dir.exists():
                downloads_dir = Path.home()

            filepath = downloads_dir / filename

            # Export the shots
            export_to_csv(self.shot_history.shots, filepath)

            ui.notify(f"Exported {self.shot_history.count} shots to {filename}", type="positive")
            logger.info(f"Shot history exported to {filepath}")

        except OSError as e:
            ui.notify(f"Failed to export: {e}", type="negative")
            logger.error(f"Failed to export shot history: {e}")

    async def _connect_gc2(self) -> None:
        """Connect to the GC2."""
        # Reset reconnection state
        self._gc2_reconnect_mgr.reset()

        if self.use_mock_gc2:
            self.gc2_reader = MockGC2Reader()
        else:
            self.gc2_reader = GC2USBReader()

        self.gc2_reader.add_shot_callback(self._on_shot_received)
        self.gc2_reader.add_status_callback(self._on_status_received)
        self.gc2_reader.add_disconnect_callback(self._on_gc2_disconnect)

        if self.gc2_reader.connect():
            self.gc2_status_label.text = "Connected"
            self.gc2_status_label.classes(
                remove="text-red-500 text-yellow-500", add="text-green-500"
            )

            # Start read loop
            self._gc2_task = asyncio.create_task(self.gc2_reader.read_loop())
            ui.notify("GC2 Connected!", type="positive")
        else:
            self.gc2_status_label.text = "Connection Failed"
            ui.notify("Failed to connect to GC2", type="negative")

    def _disconnect_gc2(self) -> None:
        """Disconnect from the GC2."""
        # Cancel any pending reconnection
        self._gc2_reconnect_mgr.cancel()
        if self._gc2_reconnect_task:
            self._gc2_reconnect_task.cancel()
            self._gc2_reconnect_task = None

        if self._gc2_task:
            self._gc2_task.cancel()
            self._gc2_task = None

        if self.gc2_reader:
            self.gc2_reader.disconnect()
            self.gc2_reader = None

        self.gc2_status_label.text = "Disconnected"
        self.gc2_status_label.classes(remove="text-green-500 text-yellow-500", add="text-red-500")

        # Reset status indicators
        if self.gc2_ready_indicator:
            self.gc2_ready_indicator.classes(
                remove="text-green-500 text-red-500", add="text-gray-500"
            )
        if self.gc2_ball_indicator:
            self.gc2_ball_indicator.classes(remove="text-blue-400", add="text-gray-500")

        ui.notify("GC2 Disconnected", type="info")

    async def _connect_gspro(self) -> None:
        """Connect to GSPro."""
        # Reset reconnection state
        self._gspro_reconnect_mgr.reset()

        host = self.gspro_host_input.value
        port = int(self.gspro_port_input.value)

        self.gspro_client = GSProClient(host=host, port=port)
        self.gspro_client.add_disconnect_callback(self._on_gspro_disconnect)

        if await self.gspro_client.connect_async():
            self.gspro_status_label.text = f"Connected to {host}:{port}"
            self.gspro_status_label.classes(
                remove="text-red-500 text-yellow-500", add="text-green-500"
            )
            ui.notify("GSPro Connected!", type="positive")
        else:
            self.gspro_status_label.text = "Connection Failed"
            ui.notify("Failed to connect to GSPro", type="negative")

    def _disconnect_gspro(self) -> None:
        """Disconnect from GSPro."""
        # Cancel any pending reconnection
        self._gspro_reconnect_mgr.cancel()
        if self._gspro_reconnect_task:
            self._gspro_reconnect_task.cancel()
            self._gspro_reconnect_task = None

        if self.gspro_client:
            self.gspro_client.disconnect()
            self.gspro_client = None

        self.gspro_status_label.text = "Disconnected"
        self.gspro_status_label.classes(remove="text-green-500 text-yellow-500", add="text-red-500")
        ui.notify("GSPro Disconnected", type="info")

    def _on_shot_received(self, shot: GC2ShotData) -> None:
        """Handle a new shot from the GC2."""
        logger.info(f"Shot received: #{shot.shot_id}")

        # Always update history regardless of mode
        self._add_to_history(shot)

        # Route shot based on current mode
        if self.auto_send:
            # Create async task for shot routing
            asyncio.create_task(self._route_shot(shot))

    async def _route_shot(self, shot: GC2ShotData) -> None:
        """Route shot to appropriate destination based on mode."""
        try:
            if self.shot_router.mode == AppMode.GSPRO:
                # Update display for GSPro mode
                self._update_shot_display(shot)

                # Send to GSPro if connected
                if self.gspro_client and self.gspro_client.is_connected:
                    self.shot_router.set_gspro_client(self.gspro_client)
                    await self.shot_router.route_shot(shot)
                    ui.notify(f"Shot #{shot.shot_id} sent to GSPro", type="positive")
                else:
                    ui.notify("GSPro not connected", type="warning")
            else:
                # Open Range mode - route to physics engine
                await self.shot_router.route_shot(shot)
        except Exception as e:
            logger.error(f"Error routing shot: {e}")
            ui.notify(f"Shot routing error: {e}", type="negative")

    def _on_status_received(self, status: GC2BallStatus) -> None:
        """Handle ball status update from the GC2."""
        logger.debug(f"Ball status: ready={status.is_ready}, ball={status.ball_detected}")

        # Update UI indicators
        if self.gc2_ready_indicator:
            if status.is_ready:
                self.gc2_ready_indicator.classes(
                    remove="text-gray-500 text-red-500", add="text-green-500"
                )
            else:
                self.gc2_ready_indicator.classes(
                    remove="text-gray-500 text-green-500", add="text-red-500"
                )

        if self.gc2_ball_indicator:
            if status.ball_detected:
                self.gc2_ball_indicator.classes(remove="text-gray-500", add="text-blue-400")
            else:
                self.gc2_ball_indicator.classes(remove="text-blue-400", add="text-gray-500")

        # Send status to GSPro if connected
        if self.send_status_to_gspro and self.gspro_client and self.gspro_client.is_connected:
            self.gspro_client.send_status(status)

    def _send_test_shot(self) -> None:
        """Send a test shot (mock mode only)."""
        if isinstance(self.gc2_reader, MockGC2Reader):
            self.gc2_reader.send_test_shot()
        else:
            ui.notify("Enable Mock GC2 mode to send test shots", type="info")

    # Mode switching methods

    async def _handle_mode_selector_change(self, mode: AppMode) -> None:
        """Handle mode change from ModeSelector UI component."""
        await self.shot_router.set_mode(mode)

    async def _on_mode_change(self, mode: AppMode) -> None:
        """Handle mode change from shot router (callback)."""
        logger.info(f"Mode changed to: {mode.value}")

        # Update settings
        self.settings.mode = mode.value
        self.save_settings()

        # Update UI visibility
        if mode == AppMode.GSPRO:
            self._show_gspro_ui()
        else:
            self._show_open_range_ui()

        ui.notify(f"Switched to {mode.value.replace('_', ' ').title()} mode", type="info")

    async def _on_open_range_result(self, result: ShotResult) -> None:
        """Handle shot result from Open Range simulation."""
        logger.debug(
            f"Open Range result: carry={result.summary.carry_distance:.1f}yds, "
            f"total={result.summary.total_distance:.1f}yds"
        )

        # Display the shot in Open Range view
        if self.open_range_view is not None:
            await self.open_range_view.show_shot(result)

        ui.notify(
            f"Shot simulated: {result.summary.carry_distance:.0f}yds carry, "
            f"{result.summary.total_distance:.0f}yds total",
            type="positive",
        )

    def _show_gspro_ui(self) -> None:
        """Show GSPro mode UI, hide Open Range UI."""
        if self._gspro_content_column is not None:
            self._gspro_content_column.classes(remove="hidden")
        if self._open_range_container is not None:
            self._open_range_container.classes(add="hidden")

    def _show_open_range_ui(self) -> None:
        """Show Open Range mode UI, hide GSPro UI."""
        if self._gspro_content_column is not None:
            self._gspro_content_column.classes(add="hidden")
        if self._open_range_container is not None:
            self._open_range_container.classes(remove="hidden")

    def shutdown(self) -> None:
        """Clean shutdown of all connections.

        This method is called when the application is shutting down.
        It ensures all connections are properly closed before exit.
        """
        logger.info("Shutting down GC2 Connect...")

        # Cancel reconnection managers and tasks first
        self._gc2_reconnect_mgr.cancel()
        self._gspro_reconnect_mgr.cancel()

        if self._gc2_reconnect_task:
            logger.debug("Cancelling GC2 reconnection task...")
            self._gc2_reconnect_task.cancel()
            self._gc2_reconnect_task = None

        if self._gspro_reconnect_task:
            logger.debug("Cancelling GSPro reconnection task...")
            self._gspro_reconnect_task.cancel()
            self._gspro_reconnect_task = None

        # Cancel GC2 read task
        if self._gc2_task:
            logger.debug("Cancelling GC2 read task...")
            self._gc2_task.cancel()
            self._gc2_task = None

        # Disconnect from GC2
        if self.gc2_reader:
            logger.info("Disconnecting from GC2...")
            try:
                self.gc2_reader.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from GC2: {e}")
            self.gc2_reader = None

        # Disconnect from GSPro
        if self.gspro_client:
            logger.info("Disconnecting from GSPro...")
            try:
                self.gspro_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from GSPro: {e}")
            self.gspro_client = None

        logger.info("Shutdown complete")


# Global reference to the app instance for shutdown handling
_app_instance: GC2ConnectApp | None = None


def create_app() -> GC2ConnectApp:
    """Create and configure the application."""
    global _app_instance

    gc2_app = GC2ConnectApp()
    gc2_app.build_ui()
    _app_instance = gc2_app

    # Register shutdown handler for clean disconnection
    app.on_shutdown(gc2_app.shutdown)

    return gc2_app


def _atexit_handler() -> None:
    """Fallback shutdown handler called at interpreter exit."""
    global _app_instance
    if _app_instance is not None:
        logger.debug("atexit handler triggered")
        _app_instance.shutdown()
        _app_instance = None


def _signal_handler(signum: int, _frame: object) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, initiating shutdown...")

    global _app_instance
    if _app_instance is not None:
        _app_instance.shutdown()
        _app_instance = None

    # Re-raise to allow default behavior (exit)
    raise SystemExit(0)


@ui.page("/")
def main_page() -> None:
    """Main page."""
    create_app()


def main() -> None:
    """Entry point."""
    # Register atexit handler as fallback
    atexit.register(_atexit_handler)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    ui.run(
        title="GC2 Connect",
        port=8080,
        reload=False,
        show=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
