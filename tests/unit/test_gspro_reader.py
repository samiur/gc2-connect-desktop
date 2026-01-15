# ABOUTME: Unit tests for GSPro client background reader loop.
# ABOUTME: Tests response handling for codes 201, 202, 203 and JSON buffering.
"""Unit tests for GSPro client background reader loop."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gc2_connect.gspro.client import GSProClient


class TestGSProReaderCallbacks:
    """Test callback registration and management."""

    def test_add_player_info_callback(self) -> None:
        """Test adding a player info callback."""
        client = GSProClient()
        callback = MagicMock()

        client.add_player_info_callback(callback)

        assert callback in client._player_info_callbacks

    def test_add_match_started_callback(self) -> None:
        """Test adding a match started callback."""
        client = GSProClient()
        callback = MagicMock()

        client.add_match_started_callback(callback)

        assert callback in client._match_started_callbacks

    def test_add_match_ended_callback(self) -> None:
        """Test adding a match ended callback."""
        client = GSProClient()
        callback = MagicMock()

        client.add_match_ended_callback(callback)

        assert callback in client._match_ended_callbacks

    def test_remove_player_info_callback(self) -> None:
        """Test removing a player info callback."""
        client = GSProClient()
        callback = MagicMock()

        client.add_player_info_callback(callback)
        client.remove_player_info_callback(callback)

        assert callback not in client._player_info_callbacks

    def test_remove_match_started_callback(self) -> None:
        """Test removing a match started callback."""
        client = GSProClient()
        callback = MagicMock()

        client.add_match_started_callback(callback)
        client.remove_match_started_callback(callback)

        assert callback not in client._match_started_callbacks

    def test_remove_match_ended_callback(self) -> None:
        """Test removing a match ended callback."""
        client = GSProClient()
        callback = MagicMock()

        client.add_match_ended_callback(callback)
        client.remove_match_ended_callback(callback)

        assert callback not in client._match_ended_callbacks

    def test_remove_nonexistent_callback_no_error(self) -> None:
        """Test removing a callback that was never added doesn't raise."""
        client = GSProClient()
        callback = MagicMock()

        # Should not raise
        client.remove_player_info_callback(callback)
        client.remove_match_started_callback(callback)
        client.remove_match_ended_callback(callback)


class TestHandleResponse:
    """Test the _handle_response method."""

    def test_handle_code_201_player_info(self) -> None:
        """Test handling code 201 triggers player info callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_player_info_callback(callback)

        player_data = {
            "Handed": "Right",
            "Club": "DR",
            "DistanceToTarget": 150.5,
        }
        response = {"Code": 201, "Player": player_data}

        client._handle_response(response)

        callback.assert_called_once_with(player_data)

    def test_handle_code_201_no_player_data(self) -> None:
        """Test handling code 201 without player data doesn't trigger callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_player_info_callback(callback)

        response = {"Code": 201}  # No Player field

        client._handle_response(response)

        callback.assert_not_called()

    def test_handle_code_201_empty_player_data(self) -> None:
        """Test handling code 201 with empty player data doesn't trigger callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_player_info_callback(callback)

        response = {"Code": 201, "Player": {}}

        client._handle_response(response)

        callback.assert_not_called()

    def test_handle_code_202_match_started(self) -> None:
        """Test handling code 202 triggers match started callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_started_callback(callback)

        response = {"Code": 202, "Message": "GSPro is Ready"}

        client._handle_response(response)

        callback.assert_called_once()

    def test_handle_code_203_match_ended(self) -> None:
        """Test handling code 203 with round ended message triggers callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_ended_callback(callback)

        response = {"Code": 203, "Message": "GSPro round ended"}

        client._handle_response(response)

        callback.assert_called_once()

    def test_handle_code_203_other_message(self) -> None:
        """Test handling code 203 with non-round-ended message doesn't trigger callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_ended_callback(callback)

        response = {"Code": 203, "Message": "Some other message"}

        client._handle_response(response)

        callback.assert_not_called()

    def test_handle_code_203_case_insensitive(self) -> None:
        """Test handling code 203 round ended check is case insensitive."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_ended_callback(callback)

        response = {"Code": 203, "Message": "GSPRO ROUND ENDED"}

        client._handle_response(response)

        callback.assert_called_once()

    def test_handle_response_callback_exception_doesnt_propagate(self) -> None:
        """Test that callback exceptions don't propagate to caller."""
        client = GSProClient()
        bad_callback = MagicMock(side_effect=RuntimeError("Test error"))
        good_callback = MagicMock()
        client.add_match_started_callback(bad_callback)
        client.add_match_started_callback(good_callback)

        response = {"Code": 202, "Message": "GSPro is Ready"}

        # Should not raise
        client._handle_response(response)

        # Both callbacks should be called, bad one first
        bad_callback.assert_called_once()
        good_callback.assert_called_once()

    def test_handle_unknown_code_no_error(self) -> None:
        """Test handling unknown response code doesn't raise."""
        client = GSProClient()

        response = {"Code": 999, "Message": "Unknown"}

        # Should not raise
        client._handle_response(response)

    def test_handle_missing_code_no_error(self) -> None:
        """Test handling response without code doesn't raise."""
        client = GSProClient()

        response = {"Message": "No code"}

        # Should not raise
        client._handle_response(response)


class TestReaderLoopControl:
    """Test starting and stopping the reader loop."""

    def test_start_reader_loop_sets_running_flag(self) -> None:
        """Test starting reader loop sets the running flag."""
        client = GSProClient()
        client._connected = True
        client._socket = MagicMock()

        # We need to mock the async task creation
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            client._start_reader_loop()

            assert client._reader_running is True
            assert client._reader_task is mock_task

    def test_stop_reader_loop_clears_running_flag(self) -> None:
        """Test stopping reader loop clears the running flag."""
        client = GSProClient()
        client._reader_running = True
        mock_task = MagicMock()
        client._reader_task = mock_task

        client._stop_reader_loop()

        assert client._reader_running is False
        mock_task.cancel.assert_called_once()
        assert client._reader_task is None

    def test_stop_reader_loop_when_not_running(self) -> None:
        """Test stopping reader loop when not running is safe."""
        client = GSProClient()
        client._reader_running = False
        client._reader_task = None

        # Should not raise
        client._stop_reader_loop()

        assert client._reader_running is False

    def test_start_reader_loop_already_running(self) -> None:
        """Test starting reader loop when already running doesn't create new task."""
        client = GSProClient()
        client._connected = True
        client._socket = MagicMock()

        existing_task = MagicMock()
        existing_task.done.return_value = False
        client._reader_task = existing_task
        client._reader_running = True

        with patch("asyncio.create_task") as mock_create_task:
            client._start_reader_loop()

            # Should not create new task since one is running
            mock_create_task.assert_not_called()


class TestReaderLoop:
    """Test the reader loop behavior."""

    @pytest.mark.asyncio
    async def test_reader_loop_processes_single_json_object(self) -> None:
        """Test reader loop processes a single JSON object."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        callback = MagicMock()
        client.add_match_started_callback(callback)

        # Mock socket
        mock_socket = MagicMock()
        response_json = json.dumps({"Code": 202, "Message": "GSPro is Ready"})

        # Socket returns data once, then raises BlockingIOError, then we stop
        call_count = 0

        def recv_side_effect(_size: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return response_json.encode("utf-8")
            # Stop the loop after processing
            client._reader_running = False
            raise BlockingIOError()

        mock_socket.recv.side_effect = recv_side_effect
        client._socket = mock_socket

        # Run reader loop
        await client._reader_loop()

        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_reader_loop_handles_multiple_json_objects(self) -> None:
        """Test reader loop processes multiple JSON objects in one read."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        callback_202 = MagicMock()
        callback_201 = MagicMock()
        client.add_match_started_callback(callback_202)
        client.add_player_info_callback(callback_201)

        mock_socket = MagicMock()
        # Two JSON objects concatenated
        response1 = {"Code": 202, "Message": "GSPro is Ready"}
        response2 = {"Code": 201, "Player": {"Club": "DR"}}
        combined = json.dumps(response1) + json.dumps(response2)

        call_count = 0

        def recv_side_effect(_size: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return combined.encode("utf-8")
            client._reader_running = False
            raise BlockingIOError()

        mock_socket.recv.side_effect = recv_side_effect
        client._socket = mock_socket

        await client._reader_loop()

        callback_202.assert_called_once()
        callback_201.assert_called_once_with({"Club": "DR"})

    @pytest.mark.asyncio
    async def test_reader_loop_handles_incomplete_json(self) -> None:
        """Test reader loop buffers incomplete JSON until complete."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        callback = MagicMock()
        client.add_match_started_callback(callback)

        mock_socket = MagicMock()

        # Split JSON across two reads
        full_json = json.dumps({"Code": 202, "Message": "GSPro is Ready"})
        part1 = full_json[:10]
        part2 = full_json[10:]

        call_count = 0

        def recv_side_effect(_size: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return part1.encode("utf-8")
            if call_count == 2:
                return part2.encode("utf-8")
            client._reader_running = False
            raise BlockingIOError()

        mock_socket.recv.side_effect = recv_side_effect
        client._socket = mock_socket

        await client._reader_loop()

        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_reader_loop_stops_on_connection_closed(self) -> None:
        """Test reader loop stops when connection is closed (empty recv)."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        mock_socket = MagicMock()
        mock_socket.recv.return_value = b""  # Empty = connection closed
        client._socket = mock_socket

        await client._reader_loop()

        # Loop should have exited
        assert True  # If we get here, loop exited properly

    @pytest.mark.asyncio
    async def test_reader_loop_stops_on_socket_error(self) -> None:
        """Test reader loop stops gracefully on socket error."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        mock_socket = MagicMock()
        mock_socket.recv.side_effect = OSError("Connection reset")
        client._socket = mock_socket

        # Should not raise
        await client._reader_loop()

        # Loop should have exited
        assert True

    @pytest.mark.asyncio
    async def test_reader_loop_stops_when_running_flag_cleared(self) -> None:
        """Test reader loop stops when running flag is cleared."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        mock_socket = MagicMock()
        call_count = 0

        def recv_side_effect(_size: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Clear the flag to stop the loop
                client._reader_running = False
            raise BlockingIOError()

        mock_socket.recv.side_effect = recv_side_effect
        client._socket = mock_socket

        await client._reader_loop()

        # Should have exited after flag was cleared
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_reader_loop_stops_when_disconnected(self) -> None:
        """Test reader loop stops when client is disconnected."""
        client = GSProClient()
        client._connected = True
        client._reader_running = True

        mock_socket = MagicMock()
        call_count = 0

        def recv_side_effect(_size: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Disconnect
                client._connected = False
            raise BlockingIOError()

        mock_socket.recv.side_effect = recv_side_effect
        client._socket = mock_socket

        await client._reader_loop()

        assert call_count >= 1


class TestConnectWithReaderLoop:
    """Test that connect starts the reader loop."""

    def test_connect_starts_reader_loop(self) -> None:
        """Test that successful connect starts the reader loop."""
        client = GSProClient()

        with (
            patch("socket.create_connection") as mock_create,
            patch.object(client, "_start_reader_loop") as mock_start_reader,
            patch.object(client, "send_heartbeat"),
        ):
            mock_socket = MagicMock()
            mock_create.return_value = mock_socket

            result = client.connect()

            assert result is True
            mock_start_reader.assert_called_once()

    def test_connect_failure_doesnt_start_reader(self) -> None:
        """Test that failed connect doesn't start the reader loop."""
        client = GSProClient()

        with (
            patch("socket.create_connection") as mock_create,
            patch.object(client, "_start_reader_loop") as mock_start_reader,
        ):
            mock_create.side_effect = OSError("Connection refused")

            result = client.connect()

            assert result is False
            mock_start_reader.assert_not_called()


class TestDisconnectWithReaderLoop:
    """Test that disconnect stops the reader loop."""

    def test_disconnect_stops_reader_loop(self) -> None:
        """Test that disconnect stops the reader loop."""
        client = GSProClient()
        client._connected = True
        client._socket = MagicMock()

        with patch.object(client, "_stop_reader_loop") as mock_stop_reader:
            client.disconnect()

            mock_stop_reader.assert_called_once()

    def test_disconnect_stops_reader_before_shutdown_heartbeat(self) -> None:
        """Test that reader is stopped before shutdown heartbeat is sent."""
        client = GSProClient()
        client._connected = True
        mock_socket = MagicMock()
        client._socket = mock_socket

        call_order: list[str] = []

        def record_stop() -> None:
            call_order.append("stop_reader")

        def record_send(*_args: Any, **_kwargs: Any) -> None:
            call_order.append("send_heartbeat")

        with (
            patch.object(client, "_stop_reader_loop", side_effect=record_stop),
            patch.object(client, "_send_shutdown_heartbeat", side_effect=record_send),
        ):
            client.disconnect()

            # Reader should be stopped before heartbeat is sent
            assert call_order == ["stop_reader", "send_heartbeat"]


class TestAsyncConnectWithReaderLoop:
    """Test async connect with reader loop."""

    @pytest.mark.asyncio
    async def test_connect_async_starts_reader_loop(self) -> None:
        """Test that async connect starts the reader loop."""
        client = GSProClient()

        with (
            patch("socket.create_connection") as mock_create,
            patch.object(client, "_start_reader_loop") as mock_start_reader,
            patch.object(client, "send_heartbeat"),
        ):
            mock_socket = MagicMock()
            mock_create.return_value = mock_socket

            result = await client.connect_async()

            assert result is True
            mock_start_reader.assert_called_once()
