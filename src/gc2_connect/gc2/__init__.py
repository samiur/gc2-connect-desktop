# ABOUTME: GC2 launch monitor communication package.
# ABOUTME: Contains USB reader for connecting to and reading data from the GC2 device.
"""GC2 launch monitor communication package.

This package provides:
- GC2USBReader: Reads shot data from GC2 via USB
- MockGC2Reader: Mock reader for testing
- PacketSource: Protocol for USB packet sources (for testing)
- USBPacket: Dataclass representing a USB packet
"""

from gc2_connect.gc2.usb_reader import (
    GC2USBReader,
    MockGC2Reader,
    PacketSource,
    USBPacket,
)

__all__ = [
    "GC2USBReader",
    "MockGC2Reader",
    "PacketSource",
    "USBPacket",
]
