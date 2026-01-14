# ABOUTME: Unit tests for GSPro clean disconnect handling.
# ABOUTME: Tests the shutdown sequence: send LaunchMonitorIsReady=false, flush, wait, close.
"""Unit tests for GSPro clean disconnect functionality."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from gc2_connect.gspro.client import GSProClient


class TestGSProCleanDisconnect:
    """Tests for GSProClient clean disconnect sequence."""

    def test_disconnect_sends_shutdown_heartbeat(self, mock_socket: MagicMock):
        """Test that disconnect sends a heartbeat with LaunchMonitorIsReady=false."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        # Clear the call history from connect's initial heartbeat
        mock_socket.sendall.reset_mock()

        # Now disconnect
        client.disconnect()

        # Should have sent a shutdown heartbeat
        assert mock_socket.sendall.called
        sent_data = mock_socket.sendall.call_args[0][0].decode("utf-8")
        message = json.loads(sent_data)

        assert message["ShotDataOptions"]["IsHeartBeat"] is True
        assert message["ShotDataOptions"]["LaunchMonitorIsReady"] is False
        assert message["ShotDataOptions"]["ContainsBallData"] is False
        assert message["ShotDataOptions"]["ContainsClubData"] is False

    def test_disconnect_waits_before_close(self, mock_socket: MagicMock):
        """Test that disconnect waits after sending heartbeat before closing."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        with patch("time.sleep") as mock_sleep:
            client.disconnect()

        # Should wait 250ms for GSPro to process the heartbeat
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 0.24 <= sleep_duration <= 0.26

    def test_disconnect_closes_socket_after_delay(self, mock_socket: MagicMock):
        """Test that disconnect closes the socket after the delay."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        with patch("time.sleep"):
            client.disconnect()

        mock_socket.close.assert_called_once()

    def test_disconnect_handles_socket_already_closed(self):
        """Test that disconnect handles socket already being closed."""
        client = GSProClient()
        # Set up client as if it was connected
        client._connected = True
        client._socket = None  # Socket is None, simulating already closed

        # Should not raise any exceptions
        client.disconnect()

        assert client.is_connected is False

    def test_disconnect_handles_send_failure_gracefully(self, mock_socket: MagicMock):
        """Test that disconnect handles failures when sending shutdown heartbeat."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        # Make sendall fail
        mock_socket.sendall.side_effect = OSError("Connection reset")

        with patch("time.sleep"):
            # Should not raise, should continue with disconnect
            client.disconnect()

        assert client.is_connected is False
        mock_socket.close.assert_called()

    def test_disconnect_continues_after_heartbeat_failure(self, mock_socket: MagicMock):
        """Test that disconnect continues with close even if heartbeat fails."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        # Make sendall fail (heartbeat send fails)
        mock_socket.sendall.side_effect = OSError("Connection reset")

        with patch("time.sleep"):
            # Should not raise, should continue with close
            client.disconnect()

        assert client.is_connected is False
        mock_socket.close.assert_called()

    def test_disconnect_handles_close_failure_gracefully(self, mock_socket: MagicMock):
        """Test that disconnect handles failures when closing socket."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        # Make close fail
        mock_socket.close.side_effect = OSError("Bad file descriptor")

        with patch("time.sleep"):
            # Should not raise
            client.disconnect()

        assert client.is_connected is False

    def test_disconnect_clears_internal_state(self, mock_socket: MagicMock):
        """Test that disconnect clears all internal state properly."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        # Simulate some state
        client._shot_number = 5
        client._current_player = {"Handed": "RH"}

        with patch("time.sleep"):
            client.disconnect()

        assert client._socket is None
        assert client._connected is False
        assert client._shot_number == 0
        assert client._current_player is None

    def test_disconnect_when_not_connected_does_nothing(self):
        """Test that disconnect when not connected doesn't raise errors."""
        client = GSProClient()
        assert client.is_connected is False

        # Should not raise
        client.disconnect()

        assert client.is_connected is False

    def test_disconnect_sequence_order(self, mock_socket: MagicMock):
        """Test that disconnect performs steps in correct order."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        mock_socket.reset_mock()
        call_order: list[str] = []

        def track_sendall(_data: bytes) -> None:
            call_order.append("sendall")

        def track_sleep(_duration: float) -> None:
            call_order.append("sleep")

        def track_close() -> None:
            call_order.append("close")

        mock_socket.sendall.side_effect = track_sendall
        mock_socket.close.side_effect = track_close

        with patch("time.sleep", side_effect=track_sleep):
            client.disconnect()

        # Verify order: sendall (heartbeat), sleep (wait for GSPro), close
        assert call_order == ["sendall", "sleep", "close"]


class TestGSProDisconnectAsync:
    """Tests for async disconnect functionality."""

    @pytest.mark.asyncio
    async def test_disconnect_async_completes_all_steps(self, mock_socket: MagicMock):
        """Test that async disconnect completes all steps."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        mock_socket.reset_mock()

        with patch("time.sleep"):
            await client.disconnect_async()

        assert client.is_connected is False
        assert client._socket is None
        mock_socket.sendall.assert_called()
        mock_socket.close.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_async_handles_errors(self, mock_socket: MagicMock):
        """Test that async disconnect handles errors gracefully."""
        client = GSProClient()
        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        # Make everything fail
        mock_socket.sendall.side_effect = OSError("Error")
        mock_socket.close.side_effect = OSError("Error")

        with patch("time.sleep"):
            # Should not raise
            await client.disconnect_async()

        assert client.is_connected is False


class TestGSProDisconnectCallbacks:
    """Tests for disconnect callbacks during clean disconnect."""

    def test_disconnect_does_not_trigger_disconnect_callback(self, mock_socket: MagicMock):
        """Test that intentional disconnect doesn't trigger disconnect callback.

        The disconnect callback should only be triggered on unexpected disconnections
        (e.g., network errors), not on intentional user-initiated disconnects.
        """
        client = GSProClient()
        callback = MagicMock()
        client.add_disconnect_callback(callback)

        with patch("socket.create_connection", return_value=mock_socket):
            client.connect()

        with patch("time.sleep"):
            client.disconnect()

        # Callback should NOT be called for intentional disconnect
        callback.assert_not_called()
