# ABOUTME: Generates realistic 64-byte USB packets for GC2 protocol simulation.
# ABOUTME: Handles field splitting, message framing, and terminators.
"""GC2 USB packet generator for test simulation.

This module generates realistic 64-byte USB packets that match the format
observed from real GC2 devices:

- Fixed 64-byte packet size
- ASCII text with newline separators
- Message terminator: \\n\\t
- Fields can be split across packet boundaries
"""

from __future__ import annotations

from tests.simulators.gc2.models import SimulatedShot, SimulatedStatus

# USB packet size for GC2
PACKET_SIZE = 64


class GC2PacketGenerator:
    """Generates realistic 64-byte USB packets for GC2 simulation.

    Replicates the exact packet format observed from real GC2 devices:
    - 64-byte fixed-size packets (padded with null bytes)
    - ASCII text with newline separators
    - Message terminator: \\n\\t
    - Fields can be split across packet boundaries

    Example:
        generator = GC2PacketGenerator()
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        packets = generator.generate_shot_packets(shot, msec_since_contact=1000)
    """

    def generate_status_packets(self, status: SimulatedStatus) -> list[bytes]:
        """Generate 64-byte packets for a 0M status message.

        Args:
            status: Ball status to encode.

        Returns:
            List of 64-byte packets that when concatenated form the message.
        """
        message = self._build_status_message(status)
        return self._split_into_packets(message)

    def generate_shot_packets(
        self,
        shot: SimulatedShot,
        msec_since_contact: int,
        include_spin: bool = True,
        split_at_field: str | None = None,
        split_at_position: int | None = None,
    ) -> list[bytes]:
        """Generate 64-byte packets for a shot message.

        Args:
            shot: Shot data to encode.
            msec_since_contact: MSEC_SINCE_CONTACT value
                (200 for preliminary, 1000 for refined).
            include_spin: Whether to include BACK_RPM and SIDE_RPM.
            split_at_field: Field name to split mid-value (e.g., "SPEED_MPH").
            split_at_position: Position within field value to split.

        Returns:
            List of 64-byte packets that when concatenated form the message.
        """
        message = self._build_shot_message(shot, msec_since_contact, include_spin)
        return self._split_into_packets(message, split_at_field, split_at_position)

    def _build_status_message(self, status: SimulatedStatus) -> str:
        """Build the complete status message text."""
        x, y, z = status.ball_position
        lines = [
            "0M",
            f"FLAGS={status.flags}",
            f"BALLS={status.balls}",
            f"BALL1={x},{y},{z}",
        ]
        return "\n".join(lines) + "\n\t"

    def _build_shot_message(
        self,
        shot: SimulatedShot,
        msec_since_contact: int,
        include_spin: bool,
    ) -> str:
        """Build the complete shot message text."""
        lines = [
            "0H",
            f"SHOT_ID={shot.shot_id}",
            "TIME_SEC=0",
            f"MSEC_SINCE_CONTACT={msec_since_contact}",
            f"SPEED_MPH={shot.ball_speed:.2f}",
            f"AZIMUTH_DEG={shot.azimuth_deg:.2f}",
            f"ELEVATION_DEG={shot.elevation_deg:.2f}",
            f"SPIN_RPM={shot.spin_rpm:.0f}",
        ]

        if include_spin:
            lines.append(f"BACK_RPM={shot.back_rpm:.0f}")
            lines.append(f"SIDE_RPM={shot.side_rpm:.0f}")

        # Add HMT data if present
        if shot.club_speed is not None:
            lines.append(f"CLUBSPEED_MPH={shot.club_speed:.2f}")
        if shot.hpath_deg is not None:
            lines.append(f"HPATH_DEG={shot.hpath_deg:.2f}")
        if shot.vpath_deg is not None:
            lines.append(f"VPATH_DEG={shot.vpath_deg:.2f}")
        if shot.face_t_deg is not None:
            lines.append(f"FACE_T_DEG={shot.face_t_deg:.2f}")
        if shot.lie_deg is not None:
            lines.append(f"LIE_DEG={shot.lie_deg:.2f}")
        if shot.loft_deg is not None:
            lines.append(f"LOFT_DEG={shot.loft_deg:.2f}")

        # Add message terminator
        return "\n".join(lines) + "\n\t"

    def _split_into_packets(
        self,
        message: str,
        split_at_field: str | None = None,
        split_at_position: int | None = None,
    ) -> list[bytes]:
        """Split message into 64-byte packets.

        Optionally inserts a forced split in the middle of a field value
        to test packet boundary handling in the parser.

        Args:
            message: Complete message text.
            split_at_field: Field name to split mid-value.
            split_at_position: Position within field value to split.

        Returns:
            List of 64-byte packets (null-padded).
        """
        message_bytes = message.encode("ascii")

        # If requested, force a split at a specific field
        if split_at_field and split_at_position is not None:
            message_bytes = self._force_split_at_field(
                message_bytes, split_at_field, split_at_position
            )

        # Split into 64-byte chunks
        packets: list[bytes] = []
        for i in range(0, len(message_bytes), PACKET_SIZE):
            chunk = message_bytes[i : i + PACKET_SIZE]
            # Pad to 64 bytes with null bytes
            if len(chunk) < PACKET_SIZE:
                chunk = chunk + b"\x00" * (PACKET_SIZE - len(chunk))
            packets.append(chunk)

        return packets

    def _force_split_at_field(
        self,
        message_bytes: bytes,
        field_name: str,
        split_position: int,
    ) -> bytes:
        """Force a packet boundary at a specific position in a field value.

        This creates a message that when split into 64-byte chunks will
        have the split occur at the specified position within the field value.

        Args:
            message_bytes: Original message bytes.
            field_name: Field to split (e.g., "SPEED_MPH").
            split_position: Position within value to split.

        Returns:
            Modified message bytes with padding to force split.
        """
        message = message_bytes.decode("ascii")

        # Find the field
        field_pattern = f"{field_name}="
        field_start = message.find(field_pattern)
        if field_start == -1:
            return message_bytes

        value_start = field_start + len(field_pattern)
        split_point = value_start + split_position

        # Calculate padding needed to put split_point at a packet boundary
        # We want split_point to be at position 0 of the second packet
        current_packet_offset = split_point % PACKET_SIZE
        if current_packet_offset == 0:
            # Already at boundary
            return message_bytes

        # Need to pad before the message to shift split point to boundary
        padding_needed = PACKET_SIZE - current_packet_offset
        padded_message = " " * padding_needed + message

        return padded_message.encode("ascii")
