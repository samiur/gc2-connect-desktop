# ABOUTME: Pytest configuration and shared fixtures for all tests.
# ABOUTME: Contains fixtures for GC2 shot data, GSPro messages, and mock objects.

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from gc2_connect.models import GC2ShotData, GSProShotMessage


@pytest.fixture(autouse=True)
def reset_connection_managers():
    """Reset connection manager singletons before each test.

    This ensures test isolation - each test gets fresh singleton instances.
    Without this, state from one test could leak into another.
    """
    from gc2_connect.services.connection_manager import reset_all

    reset_all()
    yield
    reset_all()


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
    """Fixture providing a mock socket for GSPro client testing.

    The mock properly handles:
    - setblocking() to track blocking mode
    - recv() raises BlockingIOError when in non-blocking mode (simulates empty buffer)
    - settimeout() to set timeout
    """
    mock = MagicMock()
    mock.connect.return_value = None
    mock.sendall.return_value = None
    mock.close.return_value = None
    mock.setblocking.return_value = None
    mock.settimeout.return_value = None
    mock.setsockopt.return_value = None

    # Track blocking mode state
    mock._blocking = True

    def setblocking(blocking: bool):
        mock._blocking = blocking

    def recv_side_effect(_size: int):
        # In non-blocking mode, raise BlockingIOError to simulate empty buffer
        if not mock._blocking:
            raise BlockingIOError("Resource temporarily unavailable")
        # In blocking mode, return whatever is configured via return_value
        return mock.recv.return_value

    mock.setblocking.side_effect = setblocking
    mock.recv.side_effect = recv_side_effect

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


# Integration test fixtures


@pytest.fixture
async def mock_gspro_server():
    """Fixture that runs a mock GSPro server for testing.

    The server accepts shot data and returns success responses.
    Use `server.received_shots` to inspect what was received.

    Yields:
        MockGSProServer instance with host, port, and received_shots attributes.
    """
    from tests.simulators.gspro.config import MockGSProServerConfig, ResponseType
    from tests.simulators.gspro.server import MockGSProServer

    class _ServerAdapter:
        """Adapter exposing received_shots as a list of raw dicts for test compatibility."""

        def __init__(self, server: MockGSProServer) -> None:
            self._server = server

        @property
        def host(self) -> str:
            return self._server.host

        @property
        def port(self) -> int:
            return self._server.port

        @property
        def received_shots(self) -> list[dict[str, Any]]:
            """Return all received messages as raw dicts."""
            return [s.raw_message for s in self._server.get_shots()]

    config = MockGSProServerConfig(
        host="127.0.0.1",
        port=0,
        response_type=ResponseType.SUCCESS,
    )
    # Override the response to use Code 201 with player info (what tests expect)
    server = MockGSProServer(config)

    # Patch the response to send Code 201 instead of 200
    import gc2_connect  # noqa: F401

    async def _send_response_201(writer, _shot):  # type: ignore[no-untyped-def]
        response = {
            "Code": 201,
            "Message": "Shot received with player info",
            "Player": {"Handed": "RH", "Club": "DR"},
        }
        try:
            writer.write(json.dumps(response).encode("utf-8"))
            await writer.drain()
        except Exception:
            pass

    server._send_response = _send_response_201  # type: ignore[method-assign]

    await server.start()
    adapter = _ServerAdapter(server)

    yield adapter

    await server.stop()


@pytest.fixture
def mock_gc2_reader():
    """Fixture providing a MockGC2Reader instance."""
    from gc2_connect.gc2.usb_reader import MockGC2Reader

    reader = MockGC2Reader()
    yield reader
    if reader.is_connected:
        reader.disconnect()


@pytest.fixture
async def gspro_client(mock_gspro_server):
    """Fixture providing a GSProClient connected to the mock server."""
    from gc2_connect.gspro.client import GSProClient

    client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)
    connected = await client.connect()
    assert connected, "Failed to connect to mock GSPro server"

    await asyncio.sleep(0.05)

    try:
        yield client
    finally:
        if client.is_connected:
            await client.disconnect()
