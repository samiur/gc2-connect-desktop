# ABOUTME: Integration tests for connection handling between GC2 and GSPro.
# ABOUTME: Tests connection success, failure, and disconnection scenarios.
"""Integration tests for GSPro connection handling."""

from __future__ import annotations

import asyncio
import socket

from gc2_connect.gc2.usb_reader import MockGC2Reader
from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2ShotData


class TestGSProConnectionSuccess:
    """Test successful GSPro connections."""

    async def test_connect_to_mock_server(self, mock_gspro_server):
        """Test connecting to a mock GSPro server."""
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)

        connected = await client.connect()

        assert connected is True
        assert client.is_connected is True
        assert client.shot_number == 0

        await client.disconnect()
        assert client.is_connected is False

    async def test_multiple_connections_same_server(self, mock_gspro_server):
        """Test connecting, disconnecting, and reconnecting."""
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)

        # First connection
        assert await client.connect() is True
        assert client.is_connected is True
        await client.disconnect()
        assert client.is_connected is False

        # Give server time to accept new connection
        await asyncio.sleep(0.1)

        # Second connection
        assert await client.connect() is True
        assert client.is_connected is True
        await client.disconnect()


class TestGSProConnectionFailure:
    """Test GSPro connection failure scenarios."""

    async def test_connect_to_wrong_host(self):
        """Test connecting to non-existent host."""
        client = GSProClient(host="192.168.255.255", port=921)

        # Should fail to connect (timeout)
        connected = await client.connect()

        assert connected is False
        assert client.is_connected is False

    async def test_connect_to_wrong_port(self):
        """Test connecting to wrong port."""
        client = GSProClient(host="127.0.0.1", port=65000)

        connected = await client.connect()

        assert connected is False
        assert client.is_connected is False

    async def test_connect_to_closed_server(self):
        """Test connecting to a server that is not running."""
        # Use a port that nothing is listening on
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            closed_port = s.getsockname()[1]

        # Socket is closed, port is no longer listening
        client = GSProClient(host="127.0.0.1", port=closed_port)

        connected = await client.connect()

        assert connected is False
        assert client.is_connected is False


class TestGSProDisconnection:
    """Test GSPro disconnection scenarios."""

    async def test_send_after_disconnect(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that sending after disconnect returns without error."""
        await gspro_client.disconnect()

        # send_shot returns None (fire-and-forget, no exception on disconnect)
        result = await gspro_client.send_shot(sample_gc2_shot)

        assert result is None
        assert gspro_client.is_connected is False

    async def test_disconnect_callback_invoked_on_server_close(self, mock_gspro_server):
        """Test that disconnect callback is invoked when server closes connection."""
        from tests.simulators.gspro.config import MockGSProServerConfig, ResponseType
        from tests.simulators.gspro.server import MockGSProServer

        # Use a server that disconnects after one shot
        config = MockGSProServerConfig(
            host="127.0.0.1",
            port=0,
            response_type=ResponseType.DISCONNECT,
        )
        async with MockGSProServer(config) as server:
            client = GSProClient(host=server.host, port=server.port)
            await client.connect()

            disconnect_called = asyncio.Event()

            def on_disconnect() -> None:
                disconnect_called.set()

            client.add_disconnect_callback(on_disconnect)

            # Send a shot - server will disconnect immediately
            shot = GC2ShotData(
                shot_id=1,
                ball_speed=145,
                launch_angle=12,
                total_spin=2500,
                back_spin=2400,
                side_spin=100,
            )
            await client.send_shot(shot)

            # Wait for disconnect callback
            await asyncio.wait_for(disconnect_called.wait(), timeout=2.0)
            assert disconnect_called.is_set()


class TestMockGC2Connection:
    """Test MockGC2Reader connection behavior."""

    def test_mock_gc2_connect(self, mock_gc2_reader: MockGC2Reader):
        """Test MockGC2Reader connection."""
        assert mock_gc2_reader.is_connected is False

        connected = mock_gc2_reader.connect()

        assert connected is True
        assert mock_gc2_reader.is_connected is True

    def test_mock_gc2_disconnect(self, mock_gc2_reader: MockGC2Reader):
        """Test MockGC2Reader disconnection."""
        mock_gc2_reader.connect()
        assert mock_gc2_reader.is_connected is True

        mock_gc2_reader.disconnect()

        assert mock_gc2_reader.is_connected is False
        assert mock_gc2_reader.is_running is False

    def test_mock_gc2_initial_status(self, mock_gc2_reader: MockGC2Reader):
        """Test MockGC2Reader sends initial status on connect."""
        status_updates = []

        def on_status(status):
            status_updates.append(status)

        mock_gc2_reader.add_status_callback(on_status)
        mock_gc2_reader.connect()

        # Should have received initial status
        assert len(status_updates) == 1
        assert status_updates[0].is_ready is True
        assert status_updates[0].ball_detected is True


class TestHeartbeat:
    """Test heartbeat functionality."""

    async def test_heartbeat_sent_on_connect(self, mock_gspro_server):
        """Test that heartbeat is sent on connect."""
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)

        await client.connect()

        # Give time for heartbeat to be processed
        await asyncio.sleep(0.1)

        # Heartbeat should have been received by server
        await client.disconnect()

    async def test_manual_heartbeat(self, mock_gspro_server, gspro_client: GSProClient):
        """Test sending manual heartbeat."""
        # Note: GSPro doesn't respond to heartbeats
        result = await gspro_client.send_heartbeat()

        # Heartbeat returns None
        assert result is None

        # Client should still be connected
        assert gspro_client.is_connected is True


class TestBallStatus:
    """Test ball status updates."""

    def test_status_callback_on_gc2_connect(self, mock_gc2_reader: MockGC2Reader):
        """Test that status callback is invoked when GC2 connects."""
        statuses = []

        def on_status(status):
            statuses.append(status)

        mock_gc2_reader.add_status_callback(on_status)
        mock_gc2_reader.connect()

        # Initial status should be sent
        assert len(statuses) == 1
        assert statuses[0].flags == 7  # Green light
        assert statuses[0].ball_count == 1

    async def test_send_status_to_gspro(
        self, mock_gspro_server, gspro_client: GSProClient, mock_gc2_reader: MockGC2Reader
    ):
        """Test that ball status can be sent to GSPro."""
        mock_gc2_reader.connect()
        status = mock_gc2_reader.last_status

        assert status is not None

        # Send status (fire-and-forget, returns None)
        result = await gspro_client.send_status(status)

        # Should return None (no response expected)
        assert result is None

        # Client should still be connected
        assert gspro_client.is_connected is True
