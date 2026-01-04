# ABOUTME: Provides async packet source interface for injecting simulated packets.
# ABOUTME: Integrates with TimeController for deterministic timing in tests.
"""Simulated packet source for GC2 USB reader testing.

This module provides a SimulatedPacketSource that delivers USB packets
according to a scheduled sequence, with timing controlled by TimeController.

The packet source can be injected into GC2USBReader to test packet
processing without actual USB hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tests.simulators.gc2.models import PacketSequence
from tests.simulators.timing import TimeController, TimeMode


@dataclass
class USBPacket:
    """A simulated USB packet.

    Matches the structure expected by GC2USBReader.
    """

    endpoint_name: str
    data: bytes
    timestamp: float


class PacketSource(Protocol):
    """Protocol for USB packet sources.

    Both real USB and simulated sources can implement this interface,
    allowing GC2USBReader to work with either.
    """

    async def get_packet(self, timeout: float) -> USBPacket | None:
        """Get next packet, or None on timeout/end of stream."""
        ...

    def stop(self) -> None:
        """Signal the packet source to stop."""
        ...

    @property
    def is_active(self) -> bool:
        """Whether the source is still active."""
        ...


class SimulatedPacketSource:
    """Simulated packet source for testing.

    Delivers packets according to a scheduled sequence, with timing
    controlled by TimeController for determinism.

    Example (INSTANT mode - fast unit tests):
        controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, controller)
        while source.is_active:
            packet = await source.get_packet(timeout=1.0)

    Example (REAL mode - integration tests):
        controller = TimeController(mode=TimeMode.REAL)
        source = SimulatedPacketSource(sequence, controller)
        # Packets will be delivered with actual timing delays
    """

    def __init__(
        self,
        sequence: PacketSequence,
        time_controller: TimeController | None = None,
    ) -> None:
        """Initialize the packet source.

        Args:
            sequence: Packet sequence to deliver.
            time_controller: Time controller for timing. Creates INSTANT mode
                controller if not provided.
        """
        self._sequence = sequence
        self._time = time_controller or TimeController(mode=TimeMode.INSTANT)
        self._index = 0
        self._stopped = False
        self._start_time: float | None = None

    async def get_packet(self, timeout: float) -> USBPacket | None:
        """Get the next scheduled packet.

        Waits according to the packet's scheduled delay, using TimeController
        for deterministic timing in tests.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            Next packet, or None if no more packets or stopped.
        """
        if self._stopped or self._index >= len(self._sequence.packets):
            return None

        # Initialize start time on first call
        if self._start_time is None:
            self._start_time = self._time.now()

        scheduled = self._sequence.packets[self._index]
        target_time = self._start_time + (scheduled.delay_ms / 1000.0)

        # Wait until packet's scheduled time
        current = self._time.now()
        wait_duration = target_time - current
        if wait_duration > 0:
            # Cap wait to timeout
            actual_wait = min(wait_duration, timeout)
            await self._time.sleep(actual_wait)

            # Check if we actually reached target time
            if self._time.now() < target_time:
                # Timeout occurred before packet was ready
                return None

        # Deliver the packet
        self._index += 1

        return USBPacket(
            endpoint_name=scheduled.endpoint,
            data=scheduled.data,
            timestamp=self._time.now(),
        )

    def stop(self) -> None:
        """Stop packet delivery."""
        self._stopped = True

    @property
    def is_active(self) -> bool:
        """Whether there are more packets to deliver."""
        return not self._stopped and self._index < len(self._sequence.packets)

    def reset(self) -> None:
        """Reset to beginning of sequence."""
        self._index = 0
        self._start_time = None
        self._stopped = False

    @property
    def packets_delivered(self) -> int:
        """Number of packets delivered so far."""
        return self._index

    @property
    def packets_remaining(self) -> int:
        """Number of packets remaining to deliver."""
        return len(self._sequence.packets) - self._index
