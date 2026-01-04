# ABOUTME: Unit tests for MockGSProServerConfig.
# ABOUTME: Tests configuration options and response type enumeration.
"""Tests for MockGSProServerConfig."""

from __future__ import annotations

from tests.simulators.gspro.config import (
    MockGSProServerConfig,
    ResponseType,
)


class TestResponseType:
    """Tests for ResponseType enumeration."""

    def test_success_type_exists(self) -> None:
        """SUCCESS response type exists."""
        assert ResponseType.SUCCESS.value == "success"

    def test_error_type_exists(self) -> None:
        """ERROR response type exists."""
        assert ResponseType.ERROR.value == "error"

    def test_timeout_type_exists(self) -> None:
        """TIMEOUT response type exists."""
        assert ResponseType.TIMEOUT.value == "timeout"

    def test_disconnect_type_exists(self) -> None:
        """DISCONNECT response type exists."""
        assert ResponseType.DISCONNECT.value == "disconnect"

    def test_invalid_json_type_exists(self) -> None:
        """INVALID_JSON response type exists."""
        assert ResponseType.INVALID_JSON.value == "invalid_json"


class TestMockGSProServerConfig:
    """Tests for MockGSProServerConfig."""

    def test_default_config(self) -> None:
        """Default config has reasonable values."""
        config = MockGSProServerConfig()

        assert config.response_type == ResponseType.SUCCESS
        assert config.response_delay_ms == 0.0
        assert config.host == "127.0.0.1"
        assert config.port == 0  # System-assigned port

    def test_custom_host_port(self) -> None:
        """Can set custom host and port."""
        config = MockGSProServerConfig(host="0.0.0.0", port=9210)

        assert config.host == "0.0.0.0"
        assert config.port == 9210

    def test_custom_response_type(self) -> None:
        """Can set custom response type."""
        config = MockGSProServerConfig(response_type=ResponseType.ERROR)

        assert config.response_type == ResponseType.ERROR

    def test_custom_response_delay(self) -> None:
        """Can set custom response delay."""
        config = MockGSProServerConfig(response_delay_ms=500.0)

        assert config.response_delay_ms == 500.0

    def test_error_code_for_error_response(self) -> None:
        """Can set custom error code."""
        config = MockGSProServerConfig(
            response_type=ResponseType.ERROR,
            error_code=501,
        )

        assert config.error_code == 501

    def test_error_message_for_error_response(self) -> None:
        """Can set custom error message."""
        config = MockGSProServerConfig(
            response_type=ResponseType.ERROR,
            error_message="Test error",
        )

        assert config.error_message == "Test error"

    def test_disconnect_after_shots(self) -> None:
        """Can configure disconnect after N shots."""
        config = MockGSProServerConfig(disconnect_after_shots=5)

        assert config.disconnect_after_shots == 5

    def test_with_updated(self) -> None:
        """with_updated creates new config with overrides."""
        config = MockGSProServerConfig(
            response_type=ResponseType.SUCCESS,
            response_delay_ms=100.0,
        )

        updated = config.with_updated(
            response_type=ResponseType.ERROR,
            response_delay_ms=200.0,
        )

        # Original unchanged
        assert config.response_type == ResponseType.SUCCESS
        assert config.response_delay_ms == 100.0

        # New config has updates
        assert updated.response_type == ResponseType.ERROR
        assert updated.response_delay_ms == 200.0

    def test_with_updated_partial(self) -> None:
        """with_updated preserves unmodified fields."""
        config = MockGSProServerConfig(
            host="0.0.0.0",
            port=9210,
            response_type=ResponseType.SUCCESS,
        )

        updated = config.with_updated(response_type=ResponseType.ERROR)

        assert updated.host == "0.0.0.0"
        assert updated.port == 9210
        assert updated.response_type == ResponseType.ERROR
