# ABOUTME: Schedules packet delivery with realistic timing for GC2 simulation.
# ABOUTME: Handles two-phase transmission and interruption scenarios.
"""GC2 transmission scheduler for test simulation.

This module schedules USB packet delivery with realistic GC2 timing:

- Two-phase transmission: preliminary at ~200ms, refined at ~1000ms
- Status messages (0M) can be interspersed with shot data
- Interruption scenarios where status interrupts shot transmission
"""

from __future__ import annotations

from tests.simulators.gc2.models import (
    MessageType,
    PacketSequence,
    ScheduledPacket,
    SimulatedShot,
    SimulatedStatus,
)
from tests.simulators.gc2.packet_generator import GC2PacketGenerator


class GC2TransmissionScheduler:
    """Schedules packet delivery with realistic GC2 timing.

    GC2 behavior:
    - Preliminary data at ~200ms (basic ball data, no spin components)
    - Refined data at ~1000ms (complete data with spin)
    - 0M status messages can arrive at any time

    Example:
        scheduler = GC2TransmissionScheduler()
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        seq = scheduler.schedule_shot(shot, include_preliminary=True)
    """

    def __init__(self, packet_generator: GC2PacketGenerator | None = None) -> None:
        """Initialize the scheduler.

        Args:
            packet_generator: Packet generator to use. Creates one if not provided.
        """
        self._generator = packet_generator or GC2PacketGenerator()

    def schedule_shot(
        self,
        shot: SimulatedShot,
        include_preliminary: bool = True,
        include_status_before: bool = False,
        interrupt_with_status: bool = False,
    ) -> PacketSequence:
        """Schedule a complete shot transmission.

        Args:
            shot: Shot data to transmit.
            include_preliminary: Whether to send preliminary data at ~200ms.
            include_status_before: Whether to send 0M status before shot.
            interrupt_with_status: Whether to inject 0M mid-shot.

        Returns:
            PacketSequence with all scheduled packets and their timing.
        """
        packets: list[ScheduledPacket] = []
        current_delay = 0.0

        # Optional status before shot
        if include_status_before:
            status = SimulatedStatus()
            status_packets = self._generator.generate_status_packets(status)
            for data in status_packets:
                packets.append(
                    ScheduledPacket(
                        data=data,
                        delay_ms=current_delay,
                        message_type=MessageType.BALL_STATUS,
                    )
                )
                current_delay += 5.0  # Small gap between packets

            # Gap before shot data
            current_delay += 50.0

        # Preliminary data (if requested)
        if include_preliminary:
            preliminary_packets = self._generator.generate_shot_packets(
                shot,
                msec_since_contact=int(shot.preliminary_delay_ms),
                include_spin=not shot.omit_spin_in_preliminary,
            )
            delay = shot.preliminary_delay_ms
            for i, data in enumerate(preliminary_packets):
                packets.append(
                    ScheduledPacket(
                        data=data,
                        delay_ms=delay + i * 3.0,  # 3ms between packets (realistic burst)
                        message_type=MessageType.SHOT_DATA,
                    )
                )

        # Refined data
        refined_packets = self._generator.generate_shot_packets(
            shot,
            msec_since_contact=int(shot.refined_delay_ms),
            include_spin=True,
        )
        delay = shot.refined_delay_ms
        for i, data in enumerate(refined_packets):
            packets.append(
                ScheduledPacket(
                    data=data,
                    delay_ms=delay + i * 3.0,  # 3ms between packets
                    message_type=MessageType.SHOT_DATA,
                )
            )

        # Sort by delay to ensure correct order
        packets.sort(key=lambda p: p.delay_ms)

        return PacketSequence(
            packets=packets,
            description=f"Shot {shot.shot_id}: {shot.ball_speed:.1f} mph",
        )

    def schedule_status_change(
        self,
        from_status: SimulatedStatus,
        to_status: SimulatedStatus,
        delay_ms: float = 0.0,
    ) -> PacketSequence:
        """Schedule a status change (e.g., ball removed then replaced).

        Args:
            from_status: Initial status.
            to_status: New status.
            delay_ms: Delay before first status packet.

        Returns:
            PacketSequence with status change packets.
        """
        packets: list[ScheduledPacket] = []

        # First status
        from_packets = self._generator.generate_status_packets(from_status)
        for i, data in enumerate(from_packets):
            packets.append(
                ScheduledPacket(
                    data=data,
                    delay_ms=delay_ms + i * 3.0,
                    message_type=MessageType.BALL_STATUS,
                )
            )

        # Gap between status changes
        gap = 100.0

        # Second status
        to_packets = self._generator.generate_status_packets(to_status)
        for i, data in enumerate(to_packets):
            packets.append(
                ScheduledPacket(
                    data=data,
                    delay_ms=delay_ms + gap + i * 3.0,
                    message_type=MessageType.BALL_STATUS,
                )
            )

        return PacketSequence(
            packets=packets,
            description="Status change",
        )

    def schedule_interrupted_shot(
        self,
        shot: SimulatedShot,
        interrupt_after_field: str,
    ) -> PacketSequence:
        """Schedule a shot that gets interrupted by status change.

        Simulates the scenario where the GC2 abandons shot data
        transmission when ball status changes (e.g., ball moved).

        Args:
            shot: Shot data to transmit.
            interrupt_after_field: Field after which to inject 0M.

        Returns:
            PacketSequence with interrupted shot and status packets.
        """
        packets: list[ScheduledPacket] = []

        # Generate partial shot data (will be interrupted)
        # Force split at the specified field
        partial_packets = self._generator.generate_shot_packets(
            shot,
            msec_since_contact=int(shot.refined_delay_ms),
            include_spin=True,
            split_at_field=interrupt_after_field,
            split_at_position=5,  # Split partway through field
        )

        # Only take first packet(s) up to and including the interrupted one
        delay = shot.refined_delay_ms
        for i, data in enumerate(partial_packets[:2]):  # Take first 2 packets
            packets.append(
                ScheduledPacket(
                    data=data,
                    delay_ms=delay + i * 3.0,
                    message_type=MessageType.SHOT_DATA,
                )
            )

        # Inject status message that interrupts
        status = SimulatedStatus(flags=1, balls=0)  # Ball removed
        status_packets = self._generator.generate_status_packets(status)
        for i, data in enumerate(status_packets):
            packets.append(
                ScheduledPacket(
                    data=data,
                    delay_ms=delay + 10.0 + i * 3.0,  # 10ms after last shot packet
                    message_type=MessageType.BALL_STATUS,
                )
            )

        return PacketSequence(
            packets=packets,
            description=f"Interrupted shot {shot.shot_id}",
        )

    def combine_sequences(
        self,
        *sequences: PacketSequence,
        gap_ms: float = 100.0,
    ) -> PacketSequence:
        """Combine multiple sequences with gaps between them.

        Args:
            *sequences: Sequences to combine.
            gap_ms: Gap between sequences in milliseconds.

        Returns:
            Combined PacketSequence.
        """
        combined_packets: list[ScheduledPacket] = []
        current_offset = 0.0

        for seq in sequences:
            for packet in seq.packets:
                combined_packets.append(
                    ScheduledPacket(
                        data=packet.data,
                        delay_ms=current_offset + packet.delay_ms,
                        endpoint=packet.endpoint,
                        message_type=packet.message_type,
                    )
                )

            # Next sequence starts after this one ends + gap
            current_offset += seq.total_duration_ms() + gap_ms

        # Sort by delay
        combined_packets.sort(key=lambda p: p.delay_ms)

        descriptions = [s.description for s in sequences if s.description]
        return PacketSequence(
            packets=combined_packets,
            description=" + ".join(descriptions),
        )
