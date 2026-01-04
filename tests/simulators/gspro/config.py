# ABOUTME: Configuration for mock GSPro server behavior.
# ABOUTME: Defines response types, delays, and error injection.
"""Configuration for mock GSPro server.

This module provides:
- ResponseType: Enumeration of response behaviors
- MockGSProServerConfig: Dataclass for server configuration

Example:
    # Basic success server
    config = MockGSProServerConfig()

    # Slow server with latency
    config = MockGSProServerConfig(response_delay_ms=500.0)

    # Error response server
    config = MockGSProServerConfig(
        response_type=ResponseType.ERROR,
        error_code=501,
        error_message="Server error",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any


class ResponseType(Enum):
    """Types of responses the mock server can produce."""

    SUCCESS = "success"  # Normal 200 response
    ERROR = "error"  # Error code response
    TIMEOUT = "timeout"  # No response (simulate timeout)
    DISCONNECT = "disconnect"  # Close connection
    INVALID_JSON = "invalid_json"  # Return malformed JSON


@dataclass
class MockGSProServerConfig:
    """Configuration for mock GSPro server behavior.

    Attributes:
        host: Host address to bind to.
        port: Port to listen on. Use 0 for system-assigned port.
        response_type: Type of response to send.
        response_delay_ms: Delay before sending response in milliseconds.
        error_code: Error code for ERROR response type.
        error_message: Error message for ERROR response type.
        disconnect_after_shots: Disconnect after receiving N shots (0 = never).
    """

    host: str = "127.0.0.1"
    port: int = 0  # System-assigned port for tests
    response_type: ResponseType = ResponseType.SUCCESS
    response_delay_ms: float = 0.0
    error_code: int = 500
    error_message: str = "Server error"
    disconnect_after_shots: int = 0

    def with_updated(self, **kwargs: Any) -> MockGSProServerConfig:
        """Create new config with updated fields.

        Args:
            **kwargs: Fields to update.

        Returns:
            New MockGSProServerConfig with updates applied.
        """
        return replace(self, **kwargs)
