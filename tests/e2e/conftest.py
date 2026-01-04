# ABOUTME: E2E test configuration and fixtures.
# ABOUTME: Sets up test environment for complete user flow testing.
"""End-to-end test configuration for GC2 Connect.

Provides fixtures for testing complete user flows without requiring
browser automation. Tests exercise the full app logic including
settings, connections, shot routing, and mode switching.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from gc2_connect.ui.app import GC2ConnectApp

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def mock_nicegui_ui():
    """Auto-use fixture to mock NiceGUI UI functions.

    This prevents RuntimeError from ui.notify() and other UI calls
    that require NiceGUI context.
    """
    with patch("gc2_connect.ui.app.ui") as mock_ui:
        # Mock ui.notify to do nothing
        mock_ui.notify = MagicMock()
        yield mock_ui


@dataclass
class E2EMockGSProServer:
    """Mock GSPro server for E2E testing.

    Runs in a background thread and tracks received shots.
    Provides configurable responses for testing various scenarios.
    """

    host: str
    port: int
    received_shots: list[dict[str, Any]] = dataclass_field(default_factory=list)
    _server: socket.socket | None = None
    _thread: threading.Thread | None = None
    _running: bool = False
    _conn: socket.socket | None = None
    error_mode: bool = False
    disconnect_after: int = -1  # Disconnect after N shots, -1 = never

    def get_shot_messages(self) -> list[dict[str, Any]]:
        """Get received shot messages (excluding heartbeats)."""
        return [
            shot
            for shot in self.received_shots
            if not shot.get("ShotDataOptions", {}).get("IsHeartBeat", False)
        ]

    def clear(self) -> None:
        """Clear received shots."""
        self.received_shots.clear()


def _run_e2e_server(server: E2EMockGSProServer) -> None:
    """Run the mock GSPro server in a background thread."""
    server._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server._server.settimeout(0.5)
    server._server.bind((server.host, server.port))
    server._server.listen(1)

    while server._running:
        try:
            conn, _addr = server._server.accept()
            server._conn = conn
            conn.settimeout(0.5)

            shot_count = 0
            while server._running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break

                    try:
                        message = json.loads(data.decode("utf-8"))
                        server.received_shots.append(message)

                        # Check for disconnect trigger
                        if not message.get("ShotDataOptions", {}).get("IsHeartBeat", False):
                            shot_count += 1
                            if (
                                server.disconnect_after > 0
                                and shot_count >= server.disconnect_after
                            ):
                                conn.close()
                                break

                        # Send response
                        if server.error_mode:
                            response = {"Code": 500, "Message": "Internal error"}
                        else:
                            response = {
                                "Code": 201,
                                "Message": "Shot received",
                                "Player": {"Handed": "RH", "Club": "DR"},
                            }
                        conn.sendall(json.dumps(response).encode("utf-8"))

                    except json.JSONDecodeError:
                        pass

                except TimeoutError:
                    continue
                except OSError:
                    break

            conn.close()
            server._conn = None

        except TimeoutError:
            continue
        except OSError:
            break

    if server._server:
        server._server.close()


@pytest.fixture
def e2e_mock_gspro_server() -> E2EMockGSProServer:
    """Fixture that runs a mock GSPro server for E2E tests.

    The server accepts shot data and returns success responses.
    Can be configured to simulate errors or disconnections.

    Yields:
        E2EMockGSProServer instance with host, port, and received_shots.
    """
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = E2EMockGSProServer(host="127.0.0.1", port=port)
    server._running = True
    server._thread = threading.Thread(target=_run_e2e_server, args=(server,), daemon=True)
    server._thread.start()

    time.sleep(0.1)

    yield server

    # Cleanup
    server._running = False
    if server._conn:
        try:
            server._conn.close()
        except Exception:
            pass
    if server._thread:
        server._thread.join(timeout=1.0)


@pytest.fixture
def temp_settings_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary settings file path.

    This prevents E2E tests from modifying user's real settings.

    Returns:
        Path to temporary settings file (doesn't exist yet).
    """
    return tmp_path / "gc2_connect" / "settings.json"


def _create_mock_ui_element() -> MagicMock:
    """Create a mock UI element with common attributes."""
    mock = MagicMock()
    mock.text = ""
    mock.value = ""
    mock.classes = MagicMock(return_value=mock)
    mock.clear = MagicMock()
    return mock


@pytest.fixture
def e2e_app_factory(temp_settings_path: Path):
    """Factory fixture for creating E2E app instances with isolated settings.

    Returns:
        Factory function that creates GC2ConnectApp instances.
    """
    from gc2_connect.ui.app import GC2ConnectApp

    apps_created: list[GC2ConnectApp] = []
    # Keep patches active so save_settings works
    patches: list[Any] = []

    def create_app(
        initial_settings: dict[str, Any] | None = None,
    ) -> GC2ConnectApp:
        """Create an app instance with optional initial settings.

        Args:
            initial_settings: Optional settings dict to pre-populate.

        Returns:
            GC2ConnectApp instance (not yet built UI).
        """
        # Always create the directory
        temp_settings_path.parent.mkdir(parents=True, exist_ok=True)

        if initial_settings:
            temp_settings_path.write_text(json.dumps(initial_settings))

        # Create patches but don't use context manager so they stay active
        p1 = patch(
            "gc2_connect.config.settings.get_settings_path",
            return_value=temp_settings_path,
        )
        p2 = patch("gc2_connect.ui.app.get_settings_path", return_value=temp_settings_path)

        p1.start()
        p2.start()
        patches.extend([p1, p2])

        app = GC2ConnectApp()
        apps_created.append(app)

        # Pre-mock common UI elements to prevent NoneType errors
        app.gc2_status_label = _create_mock_ui_element()
        app.gspro_status_label = _create_mock_ui_element()
        app.shot_display = _create_mock_ui_element()
        app.history_list = _create_mock_ui_element()
        app.history_count_label = _create_mock_ui_element()
        app.stats_avg_speed_label = _create_mock_ui_element()
        app.stats_avg_spin_label = _create_mock_ui_element()

        # Mock input elements with values from settings
        app.gspro_host_input = _create_mock_ui_element()
        app.gspro_host_input.value = app.settings.gspro.host
        app.gspro_port_input = _create_mock_ui_element()
        app.gspro_port_input.value = str(app.settings.gspro.port)

        return app

    yield create_app

    # Cleanup all created apps
    for app in apps_created:
        try:
            app.shutdown()
        except Exception:
            pass

    # Stop all patches
    for p in patches:
        try:
            p.stop()
        except Exception:
            pass


@pytest.fixture
def default_e2e_app(e2e_app_factory) -> GC2ConnectApp:
    """Fixture providing an E2E app instance with default settings.

    Returns:
        GC2ConnectApp instance with default settings.
    """
    return e2e_app_factory()


@pytest.fixture
def e2e_app_with_mock_gc2(e2e_app_factory) -> GC2ConnectApp:
    """Fixture providing an E2E app instance configured for mock GC2.

    Returns:
        GC2ConnectApp instance with mock GC2 enabled.
    """
    return e2e_app_factory(
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
