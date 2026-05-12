# ABOUTME: Unit tests for GSPro clean disconnect handling.
# ABOUTME: Tests the shutdown sequence: send LaunchMonitorIsReady=false, drain, close.
"""Unit tests for GSPro clean disconnect functionality."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gc2_connect.gspro.client import GSProClient


def make_connected_client() -> tuple[GSProClient, MagicMock]:
    """Return a GSProClient in connected state with a mocked writer."""
    client = GSProClient()
    client._connected = True
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    client._writer = writer
    return client, writer


class TestGSProCleanDisconnect:
    """Tests for GSProClient clean disconnect sequence."""

    @pytest.mark.asyncio
    async def test_disconnect_sends_shutdown_heartbeat(self):
        """Test that disconnect sends a heartbeat with LaunchMonitorIsReady=false."""
        client, writer = make_connected_client()

        # Clear any setup writes
        writer.write.reset_mock()

        await client.disconnect()

        # Should have sent a shutdown heartbeat
        assert writer.write.called
        sent_bytes = writer.write.call_args[0][0]
        assert sent_bytes.endswith(b"\n")
        message = json.loads(sent_bytes[:-1].decode("utf-8"))

        assert message["ShotDataOptions"]["IsHeartBeat"] is True
        assert message["ShotDataOptions"]["LaunchMonitorIsReady"] is False
        assert message["ShotDataOptions"]["ContainsBallData"] is False
        assert message["ShotDataOptions"]["ContainsClubData"] is False

    @pytest.mark.asyncio
    async def test_disconnect_waits_before_close(self):
        """Test that disconnect waits after sending heartbeat before closing."""
        client, writer = make_connected_client()

        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await client.disconnect()

        # Should have slept for the grace period
        mock_sleep.assert_called()
        sleep_durations = [call[0][0] for call in mock_sleep.call_args_list]
        assert any(0.24 <= d <= 0.26 for d in sleep_durations)

    @pytest.mark.asyncio
    async def test_disconnect_closes_writer_after_delay(self):
        """Test that disconnect closes the writer after the delay."""
        client, writer = make_connected_client()

        with patch("asyncio.sleep", new=AsyncMock()):
            await client.disconnect()

        writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_handles_writer_already_none(self):
        """Test that disconnect handles writer being None."""
        client = GSProClient()
        client._connected = False
        client._writer = None

        # Should not raise any exceptions
        await client.disconnect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_handles_send_failure_gracefully(self):
        """Test that disconnect handles failures when sending shutdown heartbeat."""
        client, writer = make_connected_client()

        # Make drain fail (write/drain are the shutdown heartbeat path)
        writer.drain.side_effect = OSError("Connection reset")

        with patch("asyncio.sleep", new=AsyncMock()):
            # Should not raise, should continue with disconnect
            await client.disconnect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_continues_after_heartbeat_failure(self):
        """Test that disconnect continues with close even if heartbeat fails."""
        client, writer = make_connected_client()

        # Make write fail on shutdown heartbeat
        writer.write.side_effect = OSError("Connection reset")

        with patch("asyncio.sleep", new=AsyncMock()):
            # Should not raise, should continue with close
            await client.disconnect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_handles_close_failure_gracefully(self):
        """Test that disconnect handles failures when closing writer."""
        client, writer = make_connected_client()

        # Make wait_closed fail
        writer.wait_closed.side_effect = OSError("Bad file descriptor")

        with patch("asyncio.sleep", new=AsyncMock()):
            # Should not raise
            await client.disconnect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_clears_internal_state(self):
        """Test that disconnect clears all internal state properly."""
        client, writer = make_connected_client()

        # Simulate some state
        client._shot_number = 5
        client._current_player = {"Handed": "RH"}

        with patch("asyncio.sleep", new=AsyncMock()):
            await client.disconnect()

        assert client._writer is None
        assert client._connected is False
        assert client._shot_number == 0
        assert client._current_player is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected_does_nothing(self):
        """Test that disconnect when not connected doesn't raise errors."""
        client = GSProClient()
        assert client.is_connected is False

        # Should not raise
        await client.disconnect()

        assert client.is_connected is False


class TestGSProDisconnectCallbacks:
    """Tests for disconnect callbacks during clean disconnect."""

    @pytest.mark.asyncio
    async def test_disconnect_does_not_trigger_disconnect_callback(self):
        """Test that intentional disconnect doesn't trigger disconnect callback.

        The disconnect callback should only be triggered on unexpected disconnections
        (e.g., network errors), not on intentional user-initiated disconnects.
        """
        client, writer = make_connected_client()
        callback = MagicMock()
        client.add_disconnect_callback(callback)

        with patch("asyncio.sleep", new=AsyncMock()):
            await client.disconnect()

        # Callback should NOT be called for intentional disconnect
        callback.assert_not_called()
