# ABOUTME: Unit tests for the GSPro client TCP communication.
# ABOUTME: Tests initialization, connection state, message formatting, and response parsing.
"""Unit tests for GSProClient."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gc2_connect.gspro.client import DEFAULT_HOST, DEFAULT_PORT, GSProClient
from gc2_connect.models import GC2ShotData, GSProResponse


class TestGSProClientInitialization:
    """Tests for GSProClient initialization."""

    def test_default_host_and_port(self):
        """Test that client uses default host and port."""
        client = GSProClient()
        assert client.host == DEFAULT_HOST
        assert client.port == DEFAULT_PORT

    def test_custom_host_and_port(self):
        """Test that client accepts custom host and port."""
        client = GSProClient(host="192.168.1.100", port=9000)
        assert client.host == "192.168.1.100"
        assert client.port == 9000

    def test_initial_state(self):
        """Test that client initializes with correct state."""
        client = GSProClient()
        assert client.is_connected is False
        assert client.shot_number == 0
        assert client.current_player is None


class TestGSProClientConnectionState:
    """Tests for GSProClient connection state."""

    def test_is_connected_when_not_connected(self):
        """Test is_connected property returns False initially."""
        client = GSProClient()
        assert client.is_connected is False

    def test_shot_number_starts_at_zero(self):
        """Test that shot_number starts at 0."""
        client = GSProClient()
        assert client.shot_number == 0

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        client = GSProClient()
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        mock_writer.get_extra_info = MagicMock(return_value=None)

        with (
            patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)),
            patch.object(client, "_reader_loop", new=AsyncMock()),
        ):
            result = await client.connect()

        assert result is True
        assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test failed connection."""
        client = GSProClient()
        with patch("asyncio.open_connection", side_effect=OSError("Connection refused")):
            result = await client.connect()

        assert result is False
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnect resets state."""
        client = GSProClient()
        client._connected = True
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        client._writer = writer

        with patch.object(client, "_send_shutdown_heartbeat", new=AsyncMock()):
            await client.disconnect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected does not error."""
        client = GSProClient()
        await client.disconnect()
        assert client.is_connected is False


class TestGSProClientMessageFormatting:
    """Tests for GSProClient message formatting."""

    @pytest.mark.asyncio
    async def test_send_shot_increments_shot_number(self, sample_gc2_shot: GC2ShotData):
        """Test that send_shot increments the shot number."""
        client = GSProClient()
        client._connected = True
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        client._writer = writer

        assert client.shot_number == 0

        await client.send_shot(sample_gc2_shot)
        assert client.shot_number == 1

        await client.send_shot(sample_gc2_shot)
        assert client.shot_number == 2

    @pytest.mark.asyncio
    async def test_send_shot_when_not_connected(self, sample_gc2_shot: GC2ShotData):
        """Test that send_shot returns None when not connected."""
        client = GSProClient()
        result = await client.send_shot(sample_gc2_shot)
        assert result is None
        assert client.shot_number == 0

    @pytest.mark.asyncio
    async def test_send_shot_message_structure(self, sample_gc2_shot: GC2ShotData):
        """Test that send_shot sends correctly formatted JSON."""
        client = GSProClient()
        client._connected = True
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        client._writer = writer

        await client.send_shot(sample_gc2_shot)

        # Verify write was called with valid JSON + newline
        writer.write.assert_called()
        sent_bytes = writer.write.call_args[0][0]
        assert sent_bytes.endswith(b"\n")
        message = json.loads(sent_bytes[:-1].decode("utf-8"))

        # Verify message structure
        assert "DeviceID" in message
        assert "ShotNumber" in message
        assert "BallData" in message
        assert "ShotDataOptions" in message
        assert message["ShotNumber"] == 1
        # Ball speed is sent as mph directly to GSPro
        assert message["BallData"]["Speed"] == sample_gc2_shot.ball_speed

    @pytest.mark.asyncio
    async def test_heartbeat_message_structure(self):
        """Test that heartbeat sends correctly formatted message."""
        client = GSProClient()
        client._connected = True
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        client._writer = writer

        await client.send_heartbeat()

        # Verify write was called with valid JSON + newline
        writer.write.assert_called_once()
        sent_bytes = writer.write.call_args[0][0]
        assert sent_bytes.endswith(b"\n")
        message = json.loads(sent_bytes[:-1].decode("utf-8"))

        # Verify heartbeat message
        assert message["ShotDataOptions"]["IsHeartBeat"] is True
        assert message["ShotDataOptions"]["ContainsBallData"] is False
        assert message["ShotDataOptions"]["ContainsClubData"] is False

    @pytest.mark.asyncio
    async def test_send_heartbeat_when_not_connected(self):
        """Test that send_heartbeat returns None when not connected."""
        client = GSProClient()
        result = await client.send_heartbeat()
        assert result is None

    @pytest.mark.asyncio
    async def test_send_heartbeat_returns_none(self):
        """Test that send_heartbeat returns None (GSPro doesn't respond to heartbeats)."""
        client = GSProClient()
        client._connected = True
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        client._writer = writer

        result = await client.send_heartbeat()
        assert result is None


class TestGSProClientResponseParsing:
    """Tests for GSProClient response parsing via _drain_buffer and _handle_response."""

    def test_handle_response_code_200_fires_response_callback(self):
        """Test that code 200 fires response callbacks."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        client._handle_response({"Code": 200, "Message": "Shot received"})

        assert len(responses) == 1
        assert responses[0].Code == 200
        assert responses[0].is_success is True

    def test_handle_response_code_201_updates_player(self):
        """Test that code 201 updates current_player."""
        client = GSProClient()
        player_data = {"Handed": "RH", "Club": "DR"}

        client._handle_response({"Code": 201, "Player": player_data, "Message": "Player info"})

        assert client.current_player is not None
        assert client.current_player["Handed"] == "RH"

    def test_handle_response_error_code(self):
        """Test that error codes fire response callbacks."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        client._handle_response({"Code": 500, "Message": "Internal error"})

        assert len(responses) == 1
        assert responses[0].Code == 500
        assert responses[0].is_success is False
        assert responses[0].Message == "Internal error"

    def test_drain_buffer_parses_json(self):
        """Test that _drain_buffer correctly parses a JSON object."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        data = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8")
        remainder = client._drain_buffer(data)

        assert len(responses) == 1
        assert responses[0].Code == 200
        assert remainder == b""

    def test_drain_buffer_handles_multiple_objects(self):
        """Test that _drain_buffer handles multiple JSON objects."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        data = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8") + json.dumps(
            {"Code": 201, "Message": "Player info", "Player": {}}
        ).encode("utf-8")
        remainder = client._drain_buffer(data)

        assert len(responses) == 2
        assert remainder == b""

    def test_drain_buffer_returns_incomplete(self):
        """Test that _drain_buffer returns incomplete JSON."""
        client = GSProClient()
        incomplete = b'{"Code": 200, "Mes'
        remainder = client._drain_buffer(incomplete)
        assert remainder == incomplete

    def test_drain_buffer_handles_gspro_ready(self):
        """Test that _drain_buffer handles bare 'GSPro ready' string."""
        client = GSProClient()
        match_started_events = []
        client.add_match_started_callback(lambda: match_started_events.append(True))

        with (
            patch.object(client, "_start_heartbeat_timer"),
            patch.object(client, "_schedule_heartbeat"),
        ):
            remainder = client._drain_buffer(b"GSPro ready\n")

        assert client.match_started is True
        assert remainder == b""

    @pytest.mark.asyncio
    async def test_send_shot_returns_none(self, sample_gc2_shot: GC2ShotData):
        """Test that send_shot returns None (ack arrives via callback)."""
        client = GSProClient()
        client._connected = True
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        client._writer = writer

        result = await client.send_shot(sample_gc2_shot)
        assert result is None


class TestGSProClientCallbacks:
    """Tests for GSProClient response callbacks."""

    def test_add_response_callback(self):
        """Test adding a response callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_response_callback(callback)
        assert callback in client._response_callbacks

    def test_remove_response_callback(self):
        """Test removing a response callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_response_callback(callback)
        client.remove_response_callback(callback)
        assert callback not in client._response_callbacks

    def test_remove_nonexistent_callback(self):
        """Test removing a callback that was never added."""
        client = GSProClient()
        callback = MagicMock()
        client.remove_response_callback(callback)
        # Should not raise an error

    def test_callback_invoked_on_handle_response(self):
        """Test that callbacks are invoked when _handle_response is called."""
        client = GSProClient()
        callback = MagicMock()
        client.add_response_callback(callback)

        client._handle_response({"Code": 200, "Message": "OK"})

        callback.assert_called_once()
        response = callback.call_args[0][0]
        assert isinstance(response, GSProResponse)
        assert response.Code == 200

    def test_callback_exception_does_not_break_others(self):
        """Test that callback exceptions don't prevent other callbacks."""
        client = GSProClient()
        failing_callback = MagicMock(side_effect=Exception("Callback error"))
        working_callback = MagicMock()

        client.add_response_callback(failing_callback)
        client.add_response_callback(working_callback)

        client._handle_response({"Code": 200, "Message": "OK"})

        failing_callback.assert_called_once()
        working_callback.assert_called_once()


class TestGSProResponse:
    """Tests for GSProResponse model."""

    def test_from_dict_success(self, gspro_success_response_dict: dict[str, Any]):
        """Test parsing success response."""
        response = GSProResponse.from_dict(gspro_success_response_dict)
        assert response.Code == 200
        assert response.Message == "OK"
        assert response.is_success is True

    def test_from_dict_with_player(self, gspro_player_response_dict: dict[str, Any]):
        """Test parsing response with player info."""
        response = GSProResponse.from_dict(gspro_player_response_dict)
        assert response.Code == 201
        assert response.Player is not None
        assert response.Player["Handed"] == "RH"
        assert response.is_success is True

    def test_from_dict_error(self, gspro_error_response_dict: dict[str, Any]):
        """Test parsing error response."""
        response = GSProResponse.from_dict(gspro_error_response_dict)
        assert response.Code == 500
        assert response.Message == "Internal error"
        assert response.is_success is False

    def test_is_success_boundary_values(self):
        """Test is_success property for boundary values."""
        assert GSProResponse(Code=199).is_success is False
        assert GSProResponse(Code=200).is_success is True
        assert GSProResponse(Code=299).is_success is True
        assert GSProResponse(Code=300).is_success is False

    def test_from_dict_missing_fields(self):
        """Test parsing response with missing fields uses defaults."""
        response = GSProResponse.from_dict({})
        assert response.Code == 0
        assert response.Message == ""
        assert response.Player is None
