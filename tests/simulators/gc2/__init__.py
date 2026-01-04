# ABOUTME: GC2 USB simulator package for testing.
# ABOUTME: Generates realistic USB packets matching real GC2 device behavior.
"""GC2 USB simulator for testing.

This package provides:
- SimulatedShot: Shot data to simulate
- GC2PacketGenerator: Generates 64-byte USB packets
- GC2TransmissionScheduler: Schedules packets with realistic timing
- SimulatedPacketSource: Async packet source for injection into GC2USBReader
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
from tests.simulators.gc2.packet_source import (
    PacketSource,
    SimulatedPacketSource,
    USBPacket,
)
from tests.simulators.gc2.scenarios import (
    create_rapid_fire_sequence,
    create_split_field_sequence,
    create_status_interrupted_sequence,
    create_two_phase_transmission_sequence,
)
from tests.simulators.gc2.scheduler import GC2TransmissionScheduler

__all__ = [
    "MessageType",
    "PacketSequence",
    "ScheduledPacket",
    "SimulatedShot",
    "SimulatedStatus",
    "GC2PacketGenerator",
    "PACKET_SIZE",
    "GC2TransmissionScheduler",
    "PacketSource",
    "SimulatedPacketSource",
    "USBPacket",
    "create_rapid_fire_sequence",
    "create_split_field_sequence",
    "create_status_interrupted_sequence",
    "create_two_phase_transmission_sequence",
]
