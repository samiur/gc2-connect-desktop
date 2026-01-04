# ABOUTME: Test simulator package for GC2 Connect Desktop.
# ABOUTME: Provides realistic USB and network simulation for testing.
"""Test simulators for GC2 Connect Desktop.

This package provides:
- GC2 USB packet simulation (realistic 64-byte packets, timing, interruptions)
- Configurable GSPro server mock (latency, errors, shot tracking)
- Time controller for deterministic testing

Usage:
    from tests.simulators import (
        SimulatedShot,
        GC2PacketGenerator,
        GC2TransmissionScheduler,
        SimulatedPacketSource,
        MockGSProServer,
        TimeController,
    )
"""

from tests.simulators.gc2.models import (
    MessageType,
    PacketSequence,
    ScheduledPacket,
    SimulatedShot,
    SimulatedStatus,
)
from tests.simulators.gc2.packet_generator import (
    PACKET_SIZE,
    GC2PacketGenerator,
)
from tests.simulators.timing import (
    TimeController,
    TimeMode,
)

__all__ = [
    # GC2 models
    "MessageType",
    "PacketSequence",
    "ScheduledPacket",
    "SimulatedShot",
    "SimulatedStatus",
    # Packet generator
    "GC2PacketGenerator",
    "PACKET_SIZE",
    # Timing
    "TimeController",
    "TimeMode",
]
