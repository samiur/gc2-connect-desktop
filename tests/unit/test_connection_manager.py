# ABOUTME: Unit tests for the singleton connection managers.
# ABOUTME: Tests UICallbackRegistry, GC2ConnectionManager, and GSProConnectionManager.
"""Unit tests for connection manager module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gc2_connect.models import GC2BallStatus, GC2ShotData
from gc2_connect.services.connection_manager import (
    GC2ConnectionManager,
    GSProConnectionManager,
    UICallbackRegistry,
    get_callback_registry,
    get_gc2_manager,
    get_gspro_manager,
    reset_all,
    shutdown_all,
)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before and after each test."""
    reset_all()
    yield
    reset_all()


class TestUICallbackRegistry:
    """Tests for UICallbackRegistry."""

    def test_register_and_notify_shot_callback(self) -> None:
        """Test registering and notifying shot callbacks."""
        registry = UICallbackRegistry()
        received_shots: list[GC2ShotData] = []

        def callback(shot: GC2ShotData) -> None:
            received_shots.append(shot)

        registry.register_shot_callback(callback, "token1")

        shot = GC2ShotData(shot_id=1, ball_speed=150.0)
        registry.notify_shot(shot)

        assert len(received_shots) == 1
        assert received_shots[0].shot_id == 1

    def test_register_and_notify_status_callback(self) -> None:
        """Test registering and notifying status callbacks."""
        registry = UICallbackRegistry()
        received_statuses: list[GC2BallStatus] = []

        def callback(status: GC2BallStatus) -> None:
            received_statuses.append(status)

        registry.register_status_callback(callback, "token1")

        status = GC2BallStatus(flags=7, ball_count=1)
        registry.notify_status(status)

        assert len(received_statuses) == 1
        assert received_statuses[0].flags == 7

    def test_multiple_callbacks_same_event(self) -> None:
        """Test multiple callbacks for the same event type."""
        registry = UICallbackRegistry()
        results: list[str] = []

        registry.register_shot_callback(lambda _s: results.append("cb1"), "token1")
        registry.register_shot_callback(lambda _s: results.append("cb2"), "token2")

        shot = GC2ShotData(shot_id=1, ball_speed=150.0)
        registry.notify_shot(shot)

        assert len(results) == 2
        assert "cb1" in results
        assert "cb2" in results

    def test_unregister_all_removes_callbacks(self) -> None:
        """Test that unregister_all removes all callbacks for a token."""
        registry = UICallbackRegistry()
        results: list[str] = []

        registry.register_shot_callback(lambda _s: results.append("shot"), "token1")
        registry.register_status_callback(lambda _s: results.append("status"), "token1")
        registry.register_gc2_connect_callback(lambda _s: results.append("connect"), "token1")

        # Unregister all for token1
        registry.unregister_all("token1")

        # None of these should trigger callbacks
        registry.notify_shot(GC2ShotData(shot_id=1, ball_speed=150.0))
        registry.notify_status(GC2BallStatus(flags=7, ball_count=1))
        registry.notify_gc2_connect(True)

        assert len(results) == 0

    def test_unregister_only_affects_specified_token(self) -> None:
        """Test that unregister_all only affects the specified token."""
        registry = UICallbackRegistry()
        results: list[str] = []

        registry.register_shot_callback(lambda _s: results.append("token1"), "token1")
        registry.register_shot_callback(lambda _s: results.append("token2"), "token2")

        # Unregister only token1
        registry.unregister_all("token1")

        registry.notify_shot(GC2ShotData(shot_id=1, ball_speed=150.0))

        assert results == ["token2"]

    def test_dead_callback_auto_removed(self) -> None:
        """Test that callbacks throwing 'client deleted' errors are auto-removed."""
        registry = UICallbackRegistry()
        call_count = 0

        def dead_callback(_shot: GC2ShotData) -> None:
            raise RuntimeError("The client this element belongs to has been deleted.")

        def alive_callback(_shot: GC2ShotData) -> None:
            nonlocal call_count
            call_count += 1

        registry.register_shot_callback(dead_callback, "dead_token")
        registry.register_shot_callback(alive_callback, "alive_token")

        shot = GC2ShotData(shot_id=1, ball_speed=150.0)

        # First call - dead callback will be removed
        registry.notify_shot(shot)
        assert call_count == 1

        # Second call - only alive callback should be called
        registry.notify_shot(shot)
        assert call_count == 2

    def test_gc2_connect_disconnect_callbacks(self) -> None:
        """Test GC2 connect/disconnect callbacks."""
        registry = UICallbackRegistry()
        connect_results: list[bool] = []
        disconnect_count = 0

        def on_connect(success: bool) -> None:
            connect_results.append(success)

        def on_disconnect() -> None:
            nonlocal disconnect_count
            disconnect_count += 1

        registry.register_gc2_connect_callback(on_connect, "token1")
        registry.register_gc2_disconnect_callback(on_disconnect, "token1")

        registry.notify_gc2_connect(True)
        registry.notify_gc2_connect(False)
        registry.notify_gc2_disconnect()

        assert connect_results == [True, False]
        assert disconnect_count == 1

    def test_gspro_connect_disconnect_callbacks(self) -> None:
        """Test GSPro connect/disconnect callbacks."""
        registry = UICallbackRegistry()
        connect_results: list[bool] = []
        disconnect_count = 0

        def on_connect(success: bool) -> None:
            connect_results.append(success)

        def on_disconnect() -> None:
            nonlocal disconnect_count
            disconnect_count += 1

        registry.register_gspro_connect_callback(on_connect, "token1")
        registry.register_gspro_disconnect_callback(on_disconnect, "token1")

        registry.notify_gspro_connect(True)
        registry.notify_gspro_disconnect()

        assert connect_results == [True]
        assert disconnect_count == 1


class TestGC2ConnectionManager:
    """Tests for GC2ConnectionManager."""

    def test_connect_mock_mode(self) -> None:
        """Test connecting in mock mode."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)

        assert not manager.is_connected

        success = manager.connect(use_mock=True)

        assert success
        assert manager.is_connected
        assert manager.use_mock

    def test_disconnect(self) -> None:
        """Test disconnecting."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)

        manager.connect(use_mock=True)
        assert manager.is_connected

        manager.disconnect()
        assert not manager.is_connected

    def test_connect_notifies_callbacks(self) -> None:
        """Test that connect notifies callbacks."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)
        connect_results: list[bool] = []

        registry.register_gc2_connect_callback(lambda s: connect_results.append(s), "token1")

        manager.connect(use_mock=True)

        assert connect_results == [True]

    def test_shot_routed_to_registry(self) -> None:
        """Test that shots from reader are routed to registry."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)
        received_shots: list[GC2ShotData] = []

        registry.register_shot_callback(lambda s: received_shots.append(s), "token1")

        manager.connect(use_mock=True)

        # Simulate a shot from the reader
        shot = GC2ShotData(shot_id=1, ball_speed=150.0)
        manager._on_shot(shot)

        assert len(received_shots) == 1
        assert manager.last_shot_id == 1

    def test_status_routed_to_registry(self) -> None:
        """Test that status from reader is routed to registry."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)
        received_statuses: list[GC2BallStatus] = []

        registry.register_status_callback(lambda s: received_statuses.append(s), "token1")

        manager.connect(use_mock=True)

        # MockGC2Reader sends an initial status on connect, so clear it
        received_statuses.clear()

        # Simulate a status from the reader
        status = GC2BallStatus(flags=7, ball_count=1)
        manager._on_status(status)

        assert len(received_statuses) == 1

    def test_send_test_shot_mock_only(self) -> None:
        """Test that send_test_shot only works in mock mode."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)

        # Not connected - should log warning
        manager.send_test_shot()

        # Connect in mock mode
        manager.connect(use_mock=True)
        # This should work (no exception)
        manager.send_test_shot()

    def test_last_shot_id_persists(self) -> None:
        """Test that last_shot_id persists across reconnects."""
        registry = UICallbackRegistry()
        manager = GC2ConnectionManager(registry)

        manager.connect(use_mock=True)
        manager._on_shot(GC2ShotData(shot_id=5, ball_speed=150.0))
        assert manager.last_shot_id == 5

        manager.disconnect()
        assert manager.last_shot_id == 5  # Still remembered

        manager.connect(use_mock=True)
        assert manager.last_shot_id == 5  # Still remembered after reconnect


class TestGSProConnectionManager:
    """Tests for GSProConnectionManager."""

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful GSPro connection."""
        registry = UICallbackRegistry()
        manager = GSProConnectionManager(registry)

        with patch.object(manager, "_client", create=True):
            # Create a mock client
            mock_client = MagicMock()
            mock_client.connect_async = AsyncMock(return_value=True)
            mock_client.is_connected = True
            mock_client._shot_number = 0
            mock_client.add_disconnect_callback = MagicMock()

            with patch(
                "gc2_connect.services.connection_manager.GSProClient",
                return_value=mock_client,
            ):
                success = await manager.connect(host="127.0.0.1", port=921)

        assert success
        assert manager.host == "127.0.0.1"
        assert manager.port == 921

    @pytest.mark.asyncio
    async def test_connect_notifies_callbacks(self) -> None:
        """Test that connect notifies callbacks."""
        registry = UICallbackRegistry()
        manager = GSProConnectionManager(registry)
        connect_results: list[bool] = []

        registry.register_gspro_connect_callback(lambda s: connect_results.append(s), "token1")

        mock_client = MagicMock()
        mock_client.connect_async = AsyncMock(return_value=True)
        mock_client.is_connected = True
        mock_client._shot_number = 0
        mock_client.add_disconnect_callback = MagicMock()

        with patch(
            "gc2_connect.services.connection_manager.GSProClient",
            return_value=mock_client,
        ):
            await manager.connect(host="127.0.0.1", port=921)

        assert connect_results == [True]

    def test_shot_number_persists_across_disconnect(self) -> None:
        """Test that shot number persists across disconnects."""
        registry = UICallbackRegistry()
        manager = GSProConnectionManager(registry)

        # Simulate having sent some shots
        manager._shot_number = 10

        # Create mock client
        mock_client = MagicMock()
        mock_client.shot_number = 10
        mock_client.disconnect = MagicMock()
        manager._client = mock_client

        manager.disconnect()

        # Shot number should be preserved
        assert manager.shot_number == 10
        assert manager._client is None

    @pytest.mark.asyncio
    async def test_shot_number_restored_on_reconnect(self) -> None:
        """Test that shot number is restored when reconnecting."""
        registry = UICallbackRegistry()
        manager = GSProConnectionManager(registry)
        manager._shot_number = 15  # Previously had 15 shots

        mock_client = MagicMock()
        mock_client.connect_async = AsyncMock(return_value=True)
        mock_client.is_connected = True
        mock_client._shot_number = 0  # Client starts at 0
        mock_client.add_disconnect_callback = MagicMock()

        with patch(
            "gc2_connect.services.connection_manager.GSProClient",
            return_value=mock_client,
        ):
            await manager.connect(host="127.0.0.1", port=921)

        # Client's shot number should be restored from manager
        assert mock_client._shot_number == 15

    @pytest.mark.asyncio
    async def test_send_shot(self) -> None:
        """Test sending a shot."""
        registry = UICallbackRegistry()
        manager = GSProConnectionManager(registry)

        mock_client = MagicMock()
        mock_client.connect_async = AsyncMock(return_value=True)
        mock_client.is_connected = True
        mock_client._shot_number = 0
        mock_client.shot_number = 1  # After sending
        mock_client.send_shot_async = AsyncMock(return_value={"Code": 200})
        mock_client.add_disconnect_callback = MagicMock()

        with patch(
            "gc2_connect.services.connection_manager.GSProClient",
            return_value=mock_client,
        ):
            await manager.connect(host="127.0.0.1", port=921)

        shot = GC2ShotData(shot_id=1, ball_speed=150.0)
        response = await manager.send_shot(shot)

        assert response == {"Code": 200}
        mock_client.send_shot_async.assert_called_once_with(shot)


class TestSingletons:
    """Tests for singleton functions."""

    def test_get_callback_registry_returns_same_instance(self) -> None:
        """Test that get_callback_registry returns the same instance."""
        registry1 = get_callback_registry()
        registry2 = get_callback_registry()
        assert registry1 is registry2

    def test_get_gc2_manager_returns_same_instance(self) -> None:
        """Test that get_gc2_manager returns the same instance."""
        manager1 = get_gc2_manager()
        manager2 = get_gc2_manager()
        assert manager1 is manager2

    def test_get_gspro_manager_returns_same_instance(self) -> None:
        """Test that get_gspro_manager returns the same instance."""
        manager1 = get_gspro_manager()
        manager2 = get_gspro_manager()
        assert manager1 is manager2

    def test_reset_all_clears_singletons(self) -> None:
        """Test that reset_all clears all singletons."""
        # Get initial instances
        registry1 = get_callback_registry()
        gc2_1 = get_gc2_manager()
        gspro_1 = get_gspro_manager()

        reset_all()

        # Get new instances
        registry2 = get_callback_registry()
        gc2_2 = get_gc2_manager()
        gspro_2 = get_gspro_manager()

        # Should be different instances
        assert registry1 is not registry2
        assert gc2_1 is not gc2_2
        assert gspro_1 is not gspro_2

    def test_shutdown_all_disconnects(self) -> None:
        """Test that shutdown_all disconnects all connections."""
        gc2 = get_gc2_manager()
        gc2.connect(use_mock=True)
        assert gc2.is_connected

        shutdown_all()

        assert not gc2.is_connected

    def test_managers_share_registry(self) -> None:
        """Test that managers share the same callback registry."""
        gc2 = get_gc2_manager()
        gspro = get_gspro_manager()

        assert gc2._callback_registry is gspro._callback_registry
        assert gc2._callback_registry is get_callback_registry()
