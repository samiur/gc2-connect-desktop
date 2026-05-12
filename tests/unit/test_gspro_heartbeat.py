# ABOUTME: Unit tests for GSPro client heartbeat timer and match state tracking.
# ABOUTME: Tests periodic heartbeats during active matches and is_ready_to_report state.
"""Unit tests for GSPro client heartbeat timer and match state tracking."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gc2_connect.gspro.client import HEARTBEAT_INTERVAL_SECONDS, GSProClient


@pytest.fixture
def client() -> GSProClient:
    """Create a fresh GSProClient for testing."""
    return GSProClient()


@pytest.fixture
def connected_client() -> Generator[GSProClient, None, None]:
    """Create a GSProClient that appears connected, with a mocked writer."""
    client = GSProClient()
    client._connected = True
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    client._writer = writer
    yield client


class TestMatchStateTracking:
    """Test match state tracking properties and methods."""

    def test_match_started_default_false(self, client: GSProClient) -> None:
        """Test match_started is False by default."""
        assert client.match_started is False

    def test_hardware_ready_default_false(self, client: GSProClient) -> None:
        """Test hardware_ready is False by default."""
        assert client.hardware_ready is False

    def test_is_ready_to_report_requires_both_states(self, client: GSProClient) -> None:
        """Test is_ready_to_report is True only when both match started AND hardware ready."""
        # Neither ready
        assert client.is_ready_to_report is False

        # Only hardware ready
        client._hardware_ready = True
        assert client.is_ready_to_report is False

        # Only match started
        client._hardware_ready = False
        client._match_started = True
        assert client.is_ready_to_report is False

        # Both ready
        client._hardware_ready = True
        client._match_started = True
        assert client.is_ready_to_report is True


class TestSetHardwareReady:
    """Test set_hardware_ready method."""

    def test_set_hardware_ready_updates_state(self, client: GSProClient) -> None:
        """Test set_hardware_ready updates the hardware_ready state."""
        assert client.hardware_ready is False

        client.set_hardware_ready(True)
        assert client.hardware_ready is True

        client.set_hardware_ready(False)
        assert client.hardware_ready is False

    def test_set_hardware_ready_sends_status_during_match(
        self, connected_client: GSProClient
    ) -> None:
        """Test set_hardware_ready schedules a heartbeat when match is active."""
        connected_client._match_started = True

        with patch.object(connected_client, "_schedule_heartbeat") as mock_schedule:
            connected_client.set_hardware_ready(True)

            mock_schedule.assert_called_once()

    def test_set_hardware_ready_no_status_when_no_match(
        self, connected_client: GSProClient
    ) -> None:
        """Test set_hardware_ready doesn't schedule heartbeat when no match is active."""
        connected_client._match_started = False

        with patch.object(connected_client, "_schedule_heartbeat") as mock_schedule:
            connected_client.set_hardware_ready(True)

            mock_schedule.assert_not_called()

    def test_set_hardware_ready_no_status_when_value_unchanged(
        self, connected_client: GSProClient
    ) -> None:
        """Test set_hardware_ready doesn't schedule heartbeat when value doesn't change."""
        connected_client._match_started = True
        connected_client._hardware_ready = True

        with patch.object(connected_client, "_schedule_heartbeat") as mock_schedule:
            connected_client.set_hardware_ready(True)  # Same value

            mock_schedule.assert_not_called()


class TestOnMatchStarted:
    """Test _on_match_started internal handler."""

    def test_on_match_started_sets_flag(self, connected_client: GSProClient) -> None:
        """Test _on_match_started sets match_started flag."""
        assert connected_client._match_started is False

        with (
            patch.object(connected_client, "_start_heartbeat_timer"),
            patch.object(connected_client, "_schedule_heartbeat"),
        ):
            connected_client._on_match_started()

        assert connected_client._match_started is True

    def test_on_match_started_starts_heartbeat_timer(self, connected_client: GSProClient) -> None:
        """Test _on_match_started starts the heartbeat timer."""
        with (
            patch.object(connected_client, "_start_heartbeat_timer") as mock_start_timer,
            patch.object(connected_client, "_schedule_heartbeat"),
        ):
            connected_client._on_match_started()

            mock_start_timer.assert_called_once()

    def test_on_match_started_sends_status(self, connected_client: GSProClient) -> None:
        """Test _on_match_started schedules a heartbeat."""
        with (
            patch.object(connected_client, "_start_heartbeat_timer"),
            patch.object(connected_client, "_schedule_heartbeat") as mock_schedule,
        ):
            connected_client._on_match_started()

            mock_schedule.assert_called_once()

    def test_on_match_started_idempotent(self, connected_client: GSProClient) -> None:
        """Test _on_match_started is idempotent (no double-start)."""
        connected_client._match_started = True  # Already started

        with (
            patch.object(connected_client, "_start_heartbeat_timer") as mock_start_timer,
            patch.object(connected_client, "_schedule_heartbeat") as mock_schedule,
        ):
            connected_client._on_match_started()

            mock_start_timer.assert_not_called()
            mock_schedule.assert_not_called()


class TestOnMatchEnded:
    """Test _on_match_ended internal handler."""

    def test_on_match_ended_clears_flag(self, connected_client: GSProClient) -> None:
        """Test _on_match_ended clears match_started flag."""
        connected_client._match_started = True

        with patch.object(connected_client, "_stop_heartbeat_timer"):
            connected_client._on_match_ended()

        assert connected_client._match_started is False

    def test_on_match_ended_stops_heartbeat_timer(self, connected_client: GSProClient) -> None:
        """Test _on_match_ended stops the heartbeat timer."""
        connected_client._match_started = True

        with patch.object(connected_client, "_stop_heartbeat_timer") as mock_stop_timer:
            connected_client._on_match_ended()

            mock_stop_timer.assert_called_once()

    def test_on_match_ended_idempotent(self, connected_client: GSProClient) -> None:
        """Test _on_match_ended is idempotent (no double-stop)."""
        connected_client._match_started = False  # Already ended

        with patch.object(connected_client, "_stop_heartbeat_timer") as mock_stop_timer:
            connected_client._on_match_ended()

            mock_stop_timer.assert_not_called()


class TestHeartbeatTimerControl:
    """Test heartbeat timer start/stop methods."""

    def test_start_heartbeat_timer_creates_task(self, connected_client: GSProClient) -> None:
        """Test _start_heartbeat_timer creates async task."""
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            connected_client._start_heartbeat_timer()

            assert connected_client._heartbeat_task is mock_task
            mock_create_task.assert_called_once()

    def test_start_heartbeat_timer_stops_existing(self, connected_client: GSProClient) -> None:
        """Test _start_heartbeat_timer stops any existing timer first."""
        existing_task = MagicMock()
        connected_client._heartbeat_task = existing_task

        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            connected_client._start_heartbeat_timer()

            existing_task.cancel.assert_called_once()

    def test_stop_heartbeat_timer_cancels_task(self, connected_client: GSProClient) -> None:
        """Test _stop_heartbeat_timer cancels the task."""
        mock_task = MagicMock()
        connected_client._heartbeat_task = mock_task

        connected_client._stop_heartbeat_timer()

        mock_task.cancel.assert_called_once()
        assert connected_client._heartbeat_task is None

    def test_stop_heartbeat_timer_when_none(self, connected_client: GSProClient) -> None:
        """Test _stop_heartbeat_timer is safe when no timer running."""
        connected_client._heartbeat_task = None

        # Should not raise
        connected_client._stop_heartbeat_timer()


class TestHeartbeatLoop:
    """Test the heartbeat loop behavior."""

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_heartbeats(self, connected_client: GSProClient) -> None:
        """Test heartbeat loop sends heartbeats at intervals."""
        connected_client._match_started = True
        heartbeat_count = 0

        async def mock_send_heartbeat() -> None:
            nonlocal heartbeat_count
            heartbeat_count += 1
            # Stop after 2 heartbeats
            if heartbeat_count >= 2:
                connected_client._match_started = False

        with (
            patch.object(
                connected_client, "send_heartbeat", new=AsyncMock(side_effect=mock_send_heartbeat)
            ),
            patch("asyncio.sleep", new=AsyncMock(return_value=None)) as mock_sleep,
        ):
            await connected_client._heartbeat_loop()

            assert heartbeat_count == 2
            # Should have slept between heartbeats
            assert mock_sleep.call_count >= 1
            mock_sleep.assert_called_with(HEARTBEAT_INTERVAL_SECONDS)

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_on_disconnect(self, connected_client: GSProClient) -> None:
        """Test heartbeat loop stops when client disconnects."""
        connected_client._match_started = True
        iteration = 0

        async def mock_sleep(_seconds: float) -> None:
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                connected_client._connected = False

        with (
            patch.object(connected_client, "send_heartbeat", new=AsyncMock()),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await connected_client._heartbeat_loop()

            # Loop should have exited
            assert iteration >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_on_match_ended(self, connected_client: GSProClient) -> None:
        """Test heartbeat loop stops when match ends."""
        connected_client._match_started = True
        iteration = 0

        async def mock_sleep(_seconds: float) -> None:
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                connected_client._match_started = False

        with (
            patch.object(connected_client, "send_heartbeat", new=AsyncMock()),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await connected_client._heartbeat_loop()

            # Loop should have exited
            assert iteration >= 1


class TestSendHeartbeatWithReadyState:
    """Test that send_heartbeat uses is_ready_to_report."""

    @pytest.mark.asyncio
    async def test_send_heartbeat_uses_is_ready_to_report_true(
        self, connected_client: GSProClient
    ) -> None:
        """Test send_heartbeat sends LaunchMonitorIsReady=true when is_ready_to_report is true."""
        connected_client._hardware_ready = True
        connected_client._match_started = True

        mock_writer = connected_client._writer
        assert mock_writer is not None

        await connected_client.send_heartbeat()

        # Check the sent data
        mock_writer.write.assert_called_once()
        sent_data = mock_writer.write.call_args[0][0].decode("utf-8")
        assert '"LaunchMonitorIsReady": true' in sent_data
        assert sent_data.endswith("\n")

    @pytest.mark.asyncio
    async def test_send_heartbeat_uses_is_ready_to_report_false(
        self, connected_client: GSProClient
    ) -> None:
        """Test send_heartbeat sends LaunchMonitorIsReady=false when is_ready_to_report is false."""
        connected_client._hardware_ready = True
        connected_client._match_started = False  # Match not started

        mock_writer = connected_client._writer
        assert mock_writer is not None

        await connected_client.send_heartbeat()

        # Check the sent data
        mock_writer.write.assert_called_once()
        sent_data = mock_writer.write.call_args[0][0].decode("utf-8")
        assert '"LaunchMonitorIsReady": false' in sent_data
        assert sent_data.endswith("\n")


class TestDisconnectStopsHeartbeat:
    """Test that disconnect stops the heartbeat timer."""

    @pytest.mark.asyncio
    async def test_disconnect_stops_heartbeat_timer(self, connected_client: GSProClient) -> None:
        """Test disconnect stops the heartbeat timer."""
        mock_task = MagicMock()
        connected_client._heartbeat_task = mock_task

        with patch.object(connected_client, "_send_shutdown_heartbeat", new=AsyncMock()):
            await connected_client.disconnect()

        mock_task.cancel.assert_called_once()
        assert connected_client._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_disconnect_clears_match_state(self, connected_client: GSProClient) -> None:
        """Test disconnect clears match state."""
        connected_client._match_started = True

        with patch.object(connected_client, "_send_shutdown_heartbeat", new=AsyncMock()):
            await connected_client.disconnect()

        assert connected_client._match_started is False


class TestMatchStateCallbackWiring:
    """Test that match started/ended callbacks trigger state changes."""

    def test_code_202_sets_match_started(self, client: GSProClient) -> None:
        """Test that code 202 response sets match_started flag via _on_match_started."""
        assert client._match_started is False

        # Prevent actual heartbeat timer from being created
        with patch.object(client, "_start_heartbeat_timer"):
            client._handle_response({"Code": 202, "Message": "GSPro is Ready"})

        assert client._match_started is True

    def test_code_203_clears_match_started(self, client: GSProClient) -> None:
        """Test that code 203 response clears match_started flag via _on_match_ended."""
        client._match_started = True

        client._handle_response({"Code": 203, "Message": "GSPro round ended"})

        assert client._match_started is False

    def test_code_203_non_round_ended_doesnt_change_state(self, client: GSProClient) -> None:
        """Test that code 203 without 'round ended' doesn't clear match_started."""
        client._match_started = True

        client._handle_response({"Code": 203, "Message": "Other message"})

        assert client._match_started is True


class TestHeartbeatIntervalConstant:
    """Test the heartbeat interval constant."""

    def test_heartbeat_interval_is_6_seconds(self) -> None:
        """Test HEARTBEAT_INTERVAL_SECONDS is 6.0 (matching OpenSkyPlus2)."""
        assert HEARTBEAT_INTERVAL_SECONDS == 6.0


class TestInitializationWithCallbacks:
    """Test that callbacks are properly wired during initialization."""

    def test_match_started_callback_wired(self) -> None:
        """Test that _on_match_started is registered as match started callback."""
        client = GSProClient()

        # The _on_match_started should be in the match_started_callbacks
        assert client._on_match_started in client._match_started_callbacks

    def test_match_ended_callback_wired(self) -> None:
        """Test that _on_match_ended is registered as match ended callback."""
        client = GSProClient()

        # The _on_match_ended should be in the match_ended_callbacks
        assert client._on_match_ended in client._match_ended_callbacks
