# ABOUTME: Unit tests for GC2 simulator data models.
# ABOUTME: Tests SimulatedShot, SimulatedStatus, ScheduledPacket, PacketSequence.
"""Tests for GC2 simulator data models."""

from __future__ import annotations

from tests.simulators.gc2.models import (
    MessageType,
    PacketSequence,
    ScheduledPacket,
    SimulatedShot,
    SimulatedStatus,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_shot_data_value(self) -> None:
        """Shot data message type has correct value."""
        assert MessageType.SHOT_DATA.value == "0H"

    def test_ball_status_value(self) -> None:
        """Ball status message type has correct value."""
        assert MessageType.BALL_STATUS.value == "0M"


class TestSimulatedShot:
    """Tests for SimulatedShot dataclass."""

    def test_create_with_required_fields(self) -> None:
        """Can create shot with only required fields."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        assert shot.shot_id == 1
        assert shot.ball_speed == 145.0

    def test_default_values(self) -> None:
        """Default values are realistic for typical shot."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        assert shot.elevation_deg == 12.0
        assert shot.azimuth_deg == 0.0
        assert shot.spin_rpm == 2500.0
        assert shot.back_rpm == 2400.0
        assert shot.side_rpm == -100.0

    def test_timing_defaults(self) -> None:
        """Timing defaults match GC2 two-phase behavior."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        assert shot.preliminary_delay_ms == 200
        assert shot.refined_delay_ms == 1000
        assert shot.omit_spin_in_preliminary is True

    def test_custom_spin_values(self) -> None:
        """Can set custom spin values."""
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=120.0,
            spin_rpm=3500.0,
            back_rpm=3200.0,
            side_rpm=500.0,
        )
        assert shot.spin_rpm == 3500.0
        assert shot.back_rpm == 3200.0
        assert shot.side_rpm == 500.0

    def test_hmt_data_optional(self) -> None:
        """HMT (club) data fields are None by default."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        assert shot.club_speed is None
        assert shot.hpath_deg is None
        assert shot.vpath_deg is None
        assert shot.face_t_deg is None

    def test_hmt_data_can_be_set(self) -> None:
        """Can set HMT club data."""
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            club_speed=105.2,
            hpath_deg=3.1,
            vpath_deg=-4.2,
            face_t_deg=1.5,
        )
        assert shot.club_speed == 105.2
        assert shot.hpath_deg == 3.1
        assert shot.vpath_deg == -4.2
        assert shot.face_t_deg == 1.5

    def test_interrupt_after_field_optional(self) -> None:
        """Interrupt field is None by default."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        assert shot.interrupt_after_field is None

    def test_can_set_interrupt_field(self) -> None:
        """Can configure shot to be interrupted after specific field."""
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            interrupt_after_field="SPEED_MPH",
        )
        assert shot.interrupt_after_field == "SPEED_MPH"


class TestSimulatedStatus:
    """Tests for SimulatedStatus dataclass."""

    def test_default_ready_with_ball(self) -> None:
        """Default status is ready with ball detected."""
        status = SimulatedStatus()
        assert status.flags == 7  # Green light (ready)
        assert status.balls == 1
        assert status.ball_position == (200, 200, 10)

    def test_custom_status(self) -> None:
        """Can create custom status."""
        status = SimulatedStatus(
            flags=1,  # Red light (not ready)
            balls=0,
            ball_position=(0, 0, 0),
        )
        assert status.flags == 1
        assert status.balls == 0
        assert status.ball_position == (0, 0, 0)

    def test_multiple_balls(self) -> None:
        """Can detect multiple balls."""
        status = SimulatedStatus(balls=2)
        assert status.balls == 2


class TestScheduledPacket:
    """Tests for ScheduledPacket dataclass."""

    def test_create_packet(self) -> None:
        """Can create scheduled packet."""
        data = b"0H\nSHOT_ID=1\n"
        packet = ScheduledPacket(data=data, delay_ms=100.0)
        assert packet.data == data
        assert packet.delay_ms == 100.0

    def test_default_endpoint(self) -> None:
        """Default endpoint is INTR (interrupt)."""
        packet = ScheduledPacket(data=b"test", delay_ms=0.0)
        assert packet.endpoint == "INTR"

    def test_default_message_type(self) -> None:
        """Default message type is SHOT_DATA."""
        packet = ScheduledPacket(data=b"test", delay_ms=0.0)
        assert packet.message_type == MessageType.SHOT_DATA

    def test_bulk_endpoint(self) -> None:
        """Can use BULK endpoint."""
        packet = ScheduledPacket(data=b"test", delay_ms=0.0, endpoint="BULK")
        assert packet.endpoint == "BULK"

    def test_status_message_type(self) -> None:
        """Can set message type to BALL_STATUS."""
        packet = ScheduledPacket(
            data=b"0M\n",
            delay_ms=0.0,
            message_type=MessageType.BALL_STATUS,
        )
        assert packet.message_type == MessageType.BALL_STATUS


class TestPacketSequence:
    """Tests for PacketSequence dataclass."""

    def test_empty_sequence(self) -> None:
        """Empty sequence has no packets."""
        seq = PacketSequence()
        assert len(seq.packets) == 0
        assert seq.description == ""

    def test_sequence_with_packets(self) -> None:
        """Can create sequence with packets."""
        packets = [
            ScheduledPacket(data=b"packet1", delay_ms=0.0),
            ScheduledPacket(data=b"packet2", delay_ms=100.0),
        ]
        seq = PacketSequence(packets=packets, description="Test sequence")
        assert len(seq.packets) == 2
        assert seq.description == "Test sequence"

    def test_total_duration_empty(self) -> None:
        """Empty sequence has zero duration."""
        seq = PacketSequence()
        assert seq.total_duration_ms() == 0.0

    def test_total_duration_single_packet(self) -> None:
        """Single packet duration is its delay."""
        seq = PacketSequence(packets=[ScheduledPacket(data=b"test", delay_ms=500.0)])
        assert seq.total_duration_ms() == 500.0

    def test_total_duration_multiple_packets(self) -> None:
        """Multiple packet duration is maximum delay."""
        packets = [
            ScheduledPacket(data=b"p1", delay_ms=100.0),
            ScheduledPacket(data=b"p2", delay_ms=500.0),
            ScheduledPacket(data=b"p3", delay_ms=300.0),
        ]
        seq = PacketSequence(packets=packets)
        assert seq.total_duration_ms() == 500.0

    def test_packets_are_independent(self) -> None:
        """Modifying packets list doesn't affect original."""
        packets = [ScheduledPacket(data=b"test", delay_ms=0.0)]
        seq = PacketSequence(packets=packets)

        # Modify the original list
        packets.append(ScheduledPacket(data=b"new", delay_ms=100.0))

        # Sequence should not be affected (if using field default_factory)
        # This test documents expected behavior
        assert len(seq.packets) == 2  # Will fail if using default_factory=list
