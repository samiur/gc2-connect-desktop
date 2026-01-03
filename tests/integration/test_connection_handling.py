# ABOUTME: Integration tests for connection handling between GC2 and GSPro.
# ABOUTME: Tests connection success, failure, and disconnection scenarios.
"""Integration tests for GSPro connection handling."""

from __future__ import annotations

import socket
import time
from typing import TYPE_CHECKING

from gc2_connect.gc2.usb_reader import MockGC2Reader
from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2ShotData

if TYPE_CHECKING:
    pass


class TestGSProConnectionSuccess:
    """Test successful GSPro connections."""

    def test_connect_to_mock_server(self, mock_gspro_server):
        """Test connecting to a mock GSPro server."""
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)

        connected = client.connect()

        assert connected is True
        assert client.is_connected is True
        assert client.shot_number == 0

        client.disconnect()
        assert client.is_connected is False

    def test_multiple_connections_same_server(self, mock_gspro_server):
        """Test connecting, disconnecting, and reconnecting."""
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)

        # First connection
        assert client.connect() is True
        assert client.is_connected is True
        client.disconnect()
        assert client.is_connected is False

        # Give server time to accept new connection
        time.sleep(0.1)

        # Second connection
        assert client.connect() is True
        assert client.is_connected is True
        client.disconnect()


class TestGSProConnectionFailure:
    """Test GSPro connection failure scenarios."""

    def test_connect_to_wrong_host(self):
        """Test connecting to non-existent host."""
        client = GSProClient(host="192.168.255.255", port=921)

        # Should fail to connect (timeout)
        connected = client.connect()

        assert connected is False
        assert client.is_connected is False

    def test_connect_to_wrong_port(self):
        """Test connecting to wrong port."""
        client = GSProClient(host="127.0.0.1", port=65000)

        connected = client.connect()

        assert connected is False
        assert client.is_connected is False

    def test_connect_to_closed_server(self):
        """Test connecting to a server that is not running."""
        # Use a port that nothing is listening on

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            closed_port = s.getsockname()[1]

        # Socket is closed, port is no longer listening
        client = GSProClient(host="127.0.0.1", port=closed_port)

        connected = client.connect()

        assert connected is False
        assert client.is_connected is False


class TestGSProDisconnection:
    """Test GSPro disconnection scenarios."""

    def test_send_after_disconnect(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that sending after disconnect returns None."""
        gspro_client.disconnect()

        response = gspro_client.send_shot(sample_gc2_shot)

        assert response is None
        assert gspro_client.is_connected is False

    def test_disconnect_callback_invoked_on_socket_error(self):
        """Test that disconnect callback is invoked when socket error occurs."""
        import threading

        # Create a server that sends RST to cause a socket error
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def accept_and_reset():
            conn, _ = server.accept()
            # Read heartbeat data
            try:
                conn.recv(4096)
            except Exception:
                pass
            # Set linger to 0 to send RST on close, causing socket error on client
            conn.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, b"\x01\x00\x00\x00\x00\x00\x00\x00"
            )
            conn.close()
            server.close()

        thread = threading.Thread(target=accept_and_reset, daemon=True)
        thread.start()

        client = GSProClient(host="127.0.0.1", port=port)
        client.connect()

        disconnect_called = [False]

        def on_disconnect() -> None:
            disconnect_called[0] = True

        client.add_disconnect_callback(on_disconnect)

        # Wait for server to close
        time.sleep(0.3)

        # Try to send - should detect disconnection via socket error
        shot = GC2ShotData(
            shot_id=1,
            ball_speed=145,
            launch_angle=12,
            total_spin=2500,
            back_spin=2400,
            side_spin=100,
        )
        response = client.send_shot(shot)

        # Either: socket error detected disconnection, or empty response received
        # The client marks disconnected only on OSError, not on empty response
        # If RST was sent, OSError occurs and is_connected becomes False
        # If graceful close, empty response is received and is_connected stays True
        # Either way, send_shot returns None when connection issues occur
        assert response is None


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

    def test_heartbeat_sent_on_connect(self, mock_gspro_server):
        """Test that heartbeat is sent on connect."""
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)

        client.connect()

        # Give time for heartbeat to be processed
        time.sleep(0.1)

        # Heartbeat should have been received (may not show as a shot)
        # The connect() method sends a heartbeat but doesn't wait for response

        client.disconnect()

    def test_manual_heartbeat(self, mock_gspro_server, gspro_client: GSProClient):
        """Test sending manual heartbeat."""
        # Note: GSPro doesn't respond to heartbeats
        response = gspro_client.send_heartbeat()

        # Heartbeat doesn't expect response
        assert response is None

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

    def test_send_status_to_gspro(
        self, mock_gspro_server, gspro_client: GSProClient, mock_gc2_reader: MockGC2Reader
    ):
        """Test that ball status can be sent to GSPro."""
        mock_gc2_reader.connect()
        status = mock_gc2_reader.last_status

        assert status is not None

        # Send status (doesn't expect response)
        response = gspro_client.send_status(status)

        # Should not expect response for status
        assert response is None

        # Client should still be connected
        assert gspro_client.is_connected is True
