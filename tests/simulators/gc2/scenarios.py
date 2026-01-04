# ABOUTME: Pre-built test scenarios for common GC2 USB packet patterns.
# ABOUTME: Provides convenience functions for creating realistic test sequences.
"""Pre-built test scenarios for GC2 USB simulation.

This module provides convenience functions for creating common test scenarios:

- Two-phase transmission: preliminary then refined data
- Status interruption: 0M message interrupts 0H transmission
- Split field: field value split across packet boundaries
- Rapid fire: multiple shots in quick succession

Example:
    # Create a realistic two-phase shot sequence
    seq = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

    # Use with SimulatedPacketSource
    source = SimulatedPacketSource(seq, time_controller)
"""

from __future__ import annotations

from tests.simulators.gc2.models import PacketSequence, SimulatedShot
from tests.simulators.gc2.scheduler import GC2TransmissionScheduler


def create_two_phase_transmission_sequence(
    shot_id: int,
    ball_speed: float,
    spin_rpm: float = 2500.0,
    back_rpm: float = 2400.0,
    side_rpm: float = -100.0,
    preliminary_delay_ms: float = 200.0,
    refined_delay_ms: float = 1000.0,
) -> PacketSequence:
    """Create a two-phase transmission sequence.

    Simulates realistic GC2 behavior where:
    - Preliminary data arrives at ~200ms (basic ball data, no spin)
    - Refined data arrives at ~1000ms (complete data with spin)

    Args:
        shot_id: Shot identifier.
        ball_speed: Ball speed in mph.
        spin_rpm: Total spin in rpm.
        back_rpm: Backspin in rpm.
        side_rpm: Sidespin in rpm.
        preliminary_delay_ms: Delay for preliminary data.
        refined_delay_ms: Delay for refined data.

    Returns:
        PacketSequence with two-phase shot transmission.
    """
    shot = SimulatedShot(
        shot_id=shot_id,
        ball_speed=ball_speed,
        spin_rpm=spin_rpm,
        back_rpm=back_rpm,
        side_rpm=side_rpm,
        preliminary_delay_ms=preliminary_delay_ms,
        refined_delay_ms=refined_delay_ms,
        omit_spin_in_preliminary=True,
    )

    scheduler = GC2TransmissionScheduler()
    return scheduler.schedule_shot(shot, include_preliminary=True)


def create_status_interrupted_sequence(
    shot_id: int,
    ball_speed: float,
    spin_rpm: float = 2500.0,
    interrupt_after_field: str = "SPEED_MPH",
) -> PacketSequence:
    """Create a status-interrupted transmission sequence.

    Simulates the scenario where 0M status message interrupts
    0H shot data transmission (e.g., ball moved during measurement).

    Args:
        shot_id: Shot identifier.
        ball_speed: Ball speed in mph.
        spin_rpm: Total spin in rpm.
        interrupt_after_field: Field after which status interrupts.

    Returns:
        PacketSequence with interrupted shot transmission.
    """
    shot = SimulatedShot(
        shot_id=shot_id,
        ball_speed=ball_speed,
        spin_rpm=spin_rpm,
        interrupt_after_field=interrupt_after_field,
    )

    scheduler = GC2TransmissionScheduler()
    return scheduler.schedule_interrupted_shot(shot, interrupt_after_field)


def create_split_field_sequence(
    shot_id: int,
    ball_speed: float = 145.0,
    split_field: str = "SPEED_MPH",
    split_position: int = 5,
) -> PacketSequence:
    """Create a sequence where a field is split across packet boundaries.

    Forces a field value to be split at a specific position, testing
    the parser's ability to handle partial data across 64-byte packets.

    Args:
        shot_id: Shot identifier.
        ball_speed: Ball speed in mph.
        split_field: Field to split across boundary.
        split_position: Position within field value to split.

    Returns:
        PacketSequence with split field.
    """
    shot = SimulatedShot(
        shot_id=shot_id,
        ball_speed=ball_speed,
    )

    from tests.simulators.gc2.models import MessageType, ScheduledPacket
    from tests.simulators.gc2.packet_generator import GC2PacketGenerator

    generator = GC2PacketGenerator()
    packets = generator.generate_shot_packets(
        shot,
        msec_since_contact=1000,
        include_spin=True,
        split_at_field=split_field,
        split_at_position=split_position,
    )

    scheduled = [
        ScheduledPacket(
            data=data,
            delay_ms=1000.0 + i * 3.0,
            message_type=MessageType.SHOT_DATA,
        )
        for i, data in enumerate(packets)
    ]

    return PacketSequence(
        packets=scheduled,
        description=f"Split field {split_field} at position {split_position}",
    )


def create_rapid_fire_sequence(
    shots: list[SimulatedShot],
    gap_ms: float = 100.0,
    include_preliminary: bool = False,
) -> PacketSequence:
    """Create a rapid-fire sequence of multiple shots.

    Simulates multiple shots in quick succession, useful for testing
    the producer-consumer queue behavior under load.

    Args:
        shots: List of shots to include.
        gap_ms: Gap between shots in milliseconds.
        include_preliminary: Whether to include preliminary data.

    Returns:
        PacketSequence with all shots combined.
    """
    scheduler = GC2TransmissionScheduler()

    sequences = [
        scheduler.schedule_shot(shot, include_preliminary=include_preliminary) for shot in shots
    ]

    return scheduler.combine_sequences(*sequences, gap_ms=gap_ms)
