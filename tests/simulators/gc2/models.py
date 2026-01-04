# ABOUTME: Data models for GC2 USB simulation test infrastructure.
# ABOUTME: Defines shot data, packets, and scheduling structures.
"""Data models for GC2 USB simulator.

This module provides the core data structures for simulating GC2 USB
communication in tests:

- SimulatedShot: Shot data to send (ball speed, spin, launch angles)
- SimulatedStatus: Ball status/tracking data (FLAGS, BALLS)
- ScheduledPacket: A USB packet scheduled for delivery at a specific time
- PacketSequence: A complete sequence of packets for a test scenario
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    """Type of GC2 USB message.

    The GC2 sends two types of messages:
    - 0H: Shot data with ball metrics
    - 0M: Ball tracking/status updates
    """

    SHOT_DATA = "0H"
    BALL_STATUS = "0M"


@dataclass
class SimulatedShot:
    """Shot data to simulate via USB packets.

    All values use GC2 native units (mph, degrees, RPM).

    Attributes:
        shot_id: Unique shot identifier (increments per shot)
        ball_speed: Ball speed in mph (typical: 80-180)
        elevation_deg: Vertical launch angle in degrees (typical: 8-20)
        azimuth_deg: Horizontal launch angle in degrees (+ = right)
        spin_rpm: Total spin rate in RPM
        back_rpm: Backspin component in RPM
        side_rpm: Sidespin component in RPM (+ = fade)
        club_speed: Optional club head speed in mph (HMT data)
        hpath_deg: Optional horizontal swing path (HMT data)
        vpath_deg: Optional vertical swing path / attack angle (HMT data)
        face_t_deg: Optional face angle to target (HMT data)
        lie_deg: Optional lie angle (HMT data)
        loft_deg: Optional dynamic loft (HMT data)
        preliminary_delay_ms: When to send preliminary data (default: 200ms)
        refined_delay_ms: When to send refined data (default: 1000ms)
        omit_spin_in_preliminary: Whether preliminary omits spin components
        interrupt_after_field: Field after which to inject 0M interruption
    """

    # Required fields
    shot_id: int
    ball_speed: float

    # Ball data with realistic defaults
    elevation_deg: float = 12.0
    azimuth_deg: float = 0.0
    spin_rpm: float = 2500.0
    back_rpm: float = 2400.0
    side_rpm: float = -100.0

    # Optional HMT (club) data
    club_speed: float | None = None
    hpath_deg: float | None = None
    vpath_deg: float | None = None
    face_t_deg: float | None = None
    lie_deg: float | None = None
    loft_deg: float | None = None

    # Timing control (milliseconds after impact)
    preliminary_delay_ms: float = 200
    refined_delay_ms: float = 1000

    # Simulation options
    omit_spin_in_preliminary: bool = True
    interrupt_after_field: str | None = None


@dataclass
class SimulatedStatus:
    """Ball status to simulate via USB packets.

    Represents a 0M message from the GC2 containing device readiness
    and ball detection information.

    Attributes:
        flags: Device status flags (7 = ready/green, 1 = not ready/red)
        balls: Number of balls detected (0 = no ball)
        ball_position: Ball position as (x, y, z) coordinates
    """

    flags: int = 7  # 7 = green light (ready)
    balls: int = 1  # Number of balls detected
    ball_position: tuple[int, int, int] = (200, 200, 10)


@dataclass
class ScheduledPacket:
    """A USB packet scheduled for delivery at a specific time.

    Represents a single 64-byte USB packet that will be delivered
    to the simulated USB reader at a specific delay.

    Attributes:
        data: Raw packet data (up to 64 bytes)
        delay_ms: Delay from sequence start in milliseconds
        endpoint: USB endpoint name ("INTR" or "BULK")
        message_type: Type of message this packet is part of
    """

    data: bytes
    delay_ms: float
    endpoint: str = "INTR"
    message_type: MessageType = MessageType.SHOT_DATA


@dataclass
class PacketSequence:
    """A complete sequence of packets representing a test scenario.

    Contains all the packets needed for a test case, with timing
    information for each packet.

    Attributes:
        packets: List of scheduled packets in delivery order
        description: Human-readable description of the scenario
    """

    packets: list[ScheduledPacket] = field(default_factory=list)
    description: str = ""

    def total_duration_ms(self) -> float:
        """Get total duration of the sequence in milliseconds.

        Returns:
            Maximum delay value among all packets, or 0 if empty.
        """
        if not self.packets:
            return 0.0
        return max(p.delay_ms for p in self.packets)
