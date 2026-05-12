# ABOUTME: Unit tests for GSPro client background reader loop.
# ABOUTME: Tests response handling for codes 201, 202, 203 and JSON buffering.
"""Unit tests for GSPro client background reader loop."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gc2_connect.gspro.client import GSProClient


@pytest.fixture
def connected_client() -> Generator[GSProClient, None, None]:
    """Create a GSProClient that appears connected with a mocked writer."""
    client = GSProClient()
    client._connected = True
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    client._writer = writer
    yield client


class TestGSProReaderCallbacks:
    """Test callback registration and management."""

    def test_add_player_info_callback(self) -> None:
        """Test adding player info callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_player_info_callback(callback)
        assert callback in client._player_info_callbacks

    def test_remove_player_info_callback(self) -> None:
        """Test removing player info callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_player_info_callback(callback)
        client.remove_player_info_callback(callback)
        assert callback not in client._player_info_callbacks

    def test_add_match_started_callback(self) -> None:
        """Test adding match started callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_started_callback(callback)
        assert callback in client._match_started_callbacks

    def test_remove_match_started_callback(self) -> None:
        """Test removing match started callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_started_callback(callback)
        client.remove_match_started_callback(callback)
        assert callback not in client._match_started_callbacks

    def test_add_match_ended_callback(self) -> None:
        """Test adding match ended callback."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_ended_callback(callback)
        assert callback in client._match_ended_callbacks

    def test_remove_match_ended_callback(self) -> None:
        """Test removing match ended callback."""
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


class TestDrainBuffer:
    """Test the _drain_buffer method."""

    def test_drain_buffer_processes_single_object(self) -> None:
        """Test that _drain_buffer processes a single JSON object."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        data = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8")
        remainder = client._drain_buffer(data)

        assert len(responses) == 1
        assert responses[0].Code == 200
        assert remainder == b""

    def test_drain_buffer_processes_multiple_objects(self) -> None:
        """Test that _drain_buffer processes multiple JSON objects."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        data = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8") + json.dumps(
            {"Code": 201, "Message": "Player", "Player": {}}
        ).encode("utf-8")
        remainder = client._drain_buffer(data)

        assert len(responses) == 2
        assert remainder == b""

    def test_drain_buffer_returns_incomplete_json(self) -> None:
        """Test that _drain_buffer returns incomplete JSON."""
        client = GSProClient()
        incomplete = b'{"Code": 200, "Mes'
        remainder = client._drain_buffer(incomplete)
        assert remainder == incomplete

    def test_drain_buffer_handles_gspro_ready_string(self) -> None:
        """Test that _drain_buffer handles bare 'GSPro ready' string."""
        client = GSProClient()

        with (
            patch.object(client, "_start_heartbeat_timer"),
            patch.object(client, "_schedule_heartbeat"),
        ):
            remainder = client._drain_buffer(b"GSPro ready\n")

        assert client.match_started is True
        assert remainder == b""

    def test_drain_buffer_handles_gspro_ready_as_code_202(self) -> None:
        """Test that 'GSPro ready' triggers match started callbacks."""
        client = GSProClient()
        callback = MagicMock()
        client.add_match_started_callback(callback)

        with (
            patch.object(client, "_start_heartbeat_timer"),
            patch.object(client, "_schedule_heartbeat"),
        ):
            client._drain_buffer(b"GSPro ready\n")

        callback.assert_called()

    def test_drain_buffer_handles_newline_terminated_json(self) -> None:
        """Test that _drain_buffer handles newline-terminated JSON."""
        client = GSProClient()
        responses = []
        client.add_response_callback(lambda r: responses.append(r))

        data = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8") + b"\n"
        remainder = client._drain_buffer(data)

        assert len(responses) == 1
        assert remainder == b""


class TestReaderLoop:
    """Test the async reader loop behavior."""

    @pytest.mark.asyncio
    async def test_reader_loop_stops_on_eof(self, connected_client: GSProClient) -> None:
        """Test reader loop stops when reader returns empty bytes (EOF)."""
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"")
        connected_client._reader = mock_reader

        await connected_client._reader_loop()

        # EOF detected, connection marked as lost
        assert connected_client.is_connected is False

    @pytest.mark.asyncio
    async def test_reader_loop_processes_response(self, connected_client: GSProClient) -> None:
        """Test reader loop processes a JSON response."""
        responses = []
        connected_client.add_response_callback(lambda r: responses.append(r))

        data = json.dumps({"Code": 200, "Message": "OK"}).encode("utf-8")
        call_count = 0

        async def mock_read(_n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return data
            else:
                connected_client._connected = False
                return b""

        mock_reader = MagicMock()
        mock_reader.read = mock_read
        connected_client._reader = mock_reader

        await connected_client._reader_loop()

        assert len(responses) == 1
        assert responses[0].Code == 200

    @pytest.mark.asyncio
    async def test_reader_loop_stops_on_connection_error(
        self, connected_client: GSProClient
    ) -> None:
        """Test reader loop stops on connection error."""
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(side_effect=OSError("Connection reset"))
        connected_client._reader = mock_reader

        await connected_client._reader_loop()

        # Should have exited cleanly and marked disconnected
        assert connected_client.is_connected is False

    @pytest.mark.asyncio
    async def test_reader_loop_stops_when_disconnected(self, connected_client: GSProClient) -> None:
        """Test reader loop stops when _connected becomes False."""
        connected_client._connected = False
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"")
        connected_client._reader = mock_reader

        # Should return immediately since _connected is False
        await connected_client._reader_loop()

    @pytest.mark.asyncio
    async def test_reader_loop_triggers_disconnect_callback_on_eof(
        self, connected_client: GSProClient
    ) -> None:
        """Test reader loop calls disconnect callbacks on EOF."""
        disconnect_callback = MagicMock()
        connected_client.add_disconnect_callback(disconnect_callback)

        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"")
        connected_client._reader = mock_reader

        await connected_client._reader_loop()

        disconnect_callback.assert_called_once()


class TestConnectWithReaderLoop:
    """Test that async connect starts the reader loop."""

    @pytest.mark.asyncio
    async def test_connect_creates_reader_task(self) -> None:
        """Test that successful connect creates a reader task."""
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
        assert client._reader_task is not None

    @pytest.mark.asyncio
    async def test_connect_failure_doesnt_create_reader_task(self) -> None:
        """Test that failed connect doesn't create a reader task."""
        client = GSProClient()

        with patch("asyncio.open_connection", side_effect=OSError("Connection refused")):
            result = await client.connect()

        assert result is False
        assert client._reader_task is None
