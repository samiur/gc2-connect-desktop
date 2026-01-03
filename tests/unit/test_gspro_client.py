# ABOUTME: Unit tests for the GSPro client TCP communication.
# ABOUTME: Tests initialization, connection state, message formatting, and response parsing.
"""Unit tests for GSProClient."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

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

    def test_connect_success(self, mock_socket_with_success_response: MagicMock):
        """Test successful connection."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_success_response):
            result = client.connect()
        assert result is True
        assert client.is_connected is True

    def test_connect_failure(self, mock_socket: MagicMock):
        """Test failed connection."""
        mock_socket.connect.side_effect = OSError("Connection refused")
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket):
            result = client.connect()
        assert result is False
        assert client.is_connected is False

    def test_disconnect(self, mock_socket_with_success_response: MagicMock):
        """Test disconnect resets state."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
        assert client.is_connected is True
        client.disconnect()
        assert client.is_connected is False

    def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected does not error."""
        client = GSProClient()
        client.disconnect()
        assert client.is_connected is False


class TestGSProClientMessageFormatting:
    """Tests for GSProClient message formatting."""

    def test_send_shot_increments_shot_number(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket_with_success_response: MagicMock,
    ):
        """Test that send_shot increments the shot number."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
            assert client.shot_number == 0

            client.send_shot(sample_gc2_shot)
            assert client.shot_number == 1

            client.send_shot(sample_gc2_shot)
            assert client.shot_number == 2

    def test_send_shot_when_not_connected(self, sample_gc2_shot: GC2ShotData):
        """Test that send_shot returns None when not connected."""
        client = GSProClient()
        result = client.send_shot(sample_gc2_shot)
        assert result is None
        assert client.shot_number == 0

    def test_send_shot_message_structure(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket_with_success_response: MagicMock,
    ):
        """Test that send_shot sends correctly formatted JSON."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
            client.send_shot(sample_gc2_shot)

        # Verify sendall was called with valid JSON
        call_args = mock_socket_with_success_response.sendall.call_args
        sent_data = call_args[0][0].decode("utf-8")
        message = json.loads(sent_data)

        # Verify message structure
        assert "DeviceID" in message
        assert "ShotNumber" in message
        assert "BallData" in message
        assert "ShotDataOptions" in message
        assert message["ShotNumber"] == 1
        assert message["BallData"]["Speed"] == sample_gc2_shot.ball_speed

    def test_heartbeat_message_structure(
        self,
        mock_socket_with_success_response: MagicMock,
    ):
        """Test that heartbeat sends correctly formatted message."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
            client.send_heartbeat()

        # Verify sendall was called with valid JSON
        call_args = mock_socket_with_success_response.sendall.call_args
        sent_data = call_args[0][0].decode("utf-8")
        message = json.loads(sent_data)

        # Verify heartbeat message
        assert message["ShotDataOptions"]["IsHeartBeat"] is True
        assert message["ShotDataOptions"]["ContainsBallData"] is False
        assert message["ShotDataOptions"]["ContainsClubData"] is False

    def test_send_heartbeat_when_not_connected(self):
        """Test that send_heartbeat returns None when not connected."""
        client = GSProClient()
        result = client.send_heartbeat()
        assert result is None


class TestGSProClientResponseParsing:
    """Tests for GSProClient response parsing."""

    def test_response_parsing_success(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket_with_success_response: MagicMock,
    ):
        """Test parsing of success response."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
            response = client.send_shot(sample_gc2_shot)

        assert response is not None
        assert response.Code == 200
        assert response.is_success is True

    def test_response_parsing_player_info(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket_with_player_response: MagicMock,
    ):
        """Test parsing of response with player info."""
        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket_with_player_response):
            client.connect()
            response = client.send_shot(sample_gc2_shot)

        assert response is not None
        assert response.Code == 201
        assert response.Player is not None
        assert response.Player["Handed"] == "RH"
        assert response.Player["Club"] == "DR"

        # Verify client stores player info
        assert client.current_player is not None
        assert client.current_player["Handed"] == "RH"

    def test_response_parsing_error_code(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket: MagicMock,
    ):
        """Test parsing of error response."""
        error_response = {"Code": 500, "Message": "Internal error"}
        mock_socket.recv.return_value = json.dumps(error_response).encode("utf-8")

        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket):
            client.connect()
            response = client.send_shot(sample_gc2_shot)

        assert response is not None
        assert response.Code == 500
        assert response.is_success is False
        assert response.Message == "Internal error"

    def test_empty_response(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket: MagicMock,
    ):
        """Test handling of empty response."""
        mock_socket.recv.return_value = b""

        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket):
            client.connect()
            response = client.send_shot(sample_gc2_shot)

        assert response is None

    def test_invalid_json_response(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket: MagicMock,
    ):
        """Test handling of invalid JSON response."""
        mock_socket.recv.return_value = b"not valid json"

        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket):
            client.connect()
            response = client.send_shot(sample_gc2_shot)

        assert response is None

    def test_socket_timeout(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket: MagicMock,
    ):
        """Test handling of socket timeout."""
        mock_socket.recv.side_effect = TimeoutError("Timeout")

        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket):
            client.connect()
            response = client.send_shot(sample_gc2_shot)

        assert response is None

    def test_socket_error_disconnects(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket: MagicMock,
    ):
        """Test that socket error sets connected to False."""
        # First recv is for initial heartbeat (success), second is for shot (error)
        success_response = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8")
        mock_socket.recv.side_effect = [success_response, OSError("Connection reset")]

        client = GSProClient()
        with patch("socket.socket", return_value=mock_socket):
            client.connect()
            assert client.is_connected is True
            client.send_shot(sample_gc2_shot)
            assert client.is_connected is False


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

    def test_callback_invoked_on_response(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket_with_success_response: MagicMock,
    ):
        """Test that callbacks are invoked when response is received."""
        client = GSProClient()
        callback = MagicMock()

        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
            # Add callback after connect so we only see shot responses
            client.add_response_callback(callback)
            client.send_shot(sample_gc2_shot)

        callback.assert_called_once()
        response = callback.call_args[0][0]
        assert isinstance(response, GSProResponse)
        assert response.Code == 200

    def test_callback_exception_does_not_break_others(
        self,
        sample_gc2_shot: GC2ShotData,
        mock_socket_with_success_response: MagicMock,
    ):
        """Test that callback exceptions don't prevent other callbacks."""
        client = GSProClient()
        failing_callback = MagicMock(side_effect=Exception("Callback error"))
        working_callback = MagicMock()

        with patch("socket.socket", return_value=mock_socket_with_success_response):
            client.connect()
            # Add callbacks after connect so we only see shot responses
            client.add_response_callback(failing_callback)
            client.add_response_callback(working_callback)
            client.send_shot(sample_gc2_shot)

        # Both callbacks should have been called
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
