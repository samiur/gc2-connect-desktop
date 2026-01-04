# ABOUTME: Unit tests for GC2 packet generator.
# ABOUTME: Tests 64-byte packet generation, field splitting, and message framing.
"""Tests for GC2 packet generator."""

from __future__ import annotations

import pytest

from tests.simulators.gc2.models import SimulatedShot, SimulatedStatus
from tests.simulators.gc2.packet_generator import (
    PACKET_SIZE,
    GC2PacketGenerator,
)


class TestPacketGeneratorConstants:
    """Tests for packet generator constants."""

    def test_packet_size_is_64(self) -> None:
        """USB packet size is 64 bytes."""
        assert PACKET_SIZE == 64


class TestStatusMessageGeneration:
    """Tests for 0M status message generation."""

    @pytest.fixture
    def generator(self) -> GC2PacketGenerator:
        """Create a packet generator."""
        return GC2PacketGenerator()

    def test_generate_default_status(self, generator: GC2PacketGenerator) -> None:
        """Can generate default status message."""
        status = SimulatedStatus()
        packets = generator.generate_status_packets(status)

        # Should produce at least one packet
        assert len(packets) >= 1

        # First packet should start with "0M\n"
        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert text.startswith("0M\n")

    def test_status_contains_flags(self, generator: GC2PacketGenerator) -> None:
        """Status message contains FLAGS field."""
        status = SimulatedStatus(flags=7)
        packets = generator.generate_status_packets(status)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "FLAGS=7" in text

    def test_status_contains_balls(self, generator: GC2PacketGenerator) -> None:
        """Status message contains BALLS field."""
        status = SimulatedStatus(balls=1)
        packets = generator.generate_status_packets(status)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "BALLS=1" in text

    def test_status_contains_ball_position(self, generator: GC2PacketGenerator) -> None:
        """Status message contains BALL1 position field."""
        status = SimulatedStatus(ball_position=(100, 200, 15))
        packets = generator.generate_status_packets(status)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "BALL1=100,200,15" in text

    def test_status_ends_with_terminator(self, generator: GC2PacketGenerator) -> None:
        """Status message ends with \\n\\t terminator."""
        status = SimulatedStatus()
        packets = generator.generate_status_packets(status)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert text.endswith("\n\t")

    def test_status_packets_are_64_bytes(self, generator: GC2PacketGenerator) -> None:
        """Each status packet is exactly 64 bytes."""
        status = SimulatedStatus()
        packets = generator.generate_status_packets(status)

        for packet in packets:
            assert len(packet) == PACKET_SIZE


class TestShotMessageGeneration:
    """Tests for 0H shot message generation."""

    @pytest.fixture
    def generator(self) -> GC2PacketGenerator:
        """Create a packet generator."""
        return GC2PacketGenerator()

    @pytest.fixture
    def simple_shot(self) -> SimulatedShot:
        """Create a simple shot."""
        return SimulatedShot(shot_id=1, ball_speed=145.0)

    def test_generate_basic_shot(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Can generate basic shot message."""
        packets = generator.generate_shot_packets(simple_shot, msec_since_contact=1000)

        assert len(packets) >= 1

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert text.startswith("0H\n")

    def test_shot_contains_shot_id(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Shot message contains SHOT_ID field."""
        packets = generator.generate_shot_packets(simple_shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "SHOT_ID=1" in text

    def test_shot_contains_speed(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Shot message contains SPEED_MPH field."""
        packets = generator.generate_shot_packets(simple_shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "SPEED_MPH=145.00" in text

    def test_shot_contains_msec(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Shot message contains MSEC_SINCE_CONTACT field."""
        packets = generator.generate_shot_packets(simple_shot, msec_since_contact=200)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "MSEC_SINCE_CONTACT=200" in text

    def test_shot_contains_spin_when_included(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Shot message contains spin fields when include_spin=True."""
        packets = generator.generate_shot_packets(
            simple_shot, msec_since_contact=1000, include_spin=True
        )

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "BACK_RPM=" in text
        assert "SIDE_RPM=" in text

    def test_shot_omits_spin_when_excluded(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Shot message omits spin components when include_spin=False."""
        packets = generator.generate_shot_packets(
            simple_shot, msec_since_contact=200, include_spin=False
        )

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "BACK_RPM=" not in text
        assert "SIDE_RPM=" not in text

    def test_shot_contains_elevation(self, generator: GC2PacketGenerator) -> None:
        """Shot message contains ELEVATION_DEG field."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0, elevation_deg=11.8)
        packets = generator.generate_shot_packets(shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "ELEVATION_DEG=11.80" in text

    def test_shot_contains_azimuth(self, generator: GC2PacketGenerator) -> None:
        """Shot message contains AZIMUTH_DEG field."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0, azimuth_deg=2.5)
        packets = generator.generate_shot_packets(shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "AZIMUTH_DEG=2.50" in text

    def test_shot_ends_with_terminator(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Shot message ends with \\n\\t terminator."""
        packets = generator.generate_shot_packets(simple_shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert text.endswith("\n\t")

    def test_shot_packets_are_64_bytes(
        self, generator: GC2PacketGenerator, simple_shot: SimulatedShot
    ) -> None:
        """Each shot packet is exactly 64 bytes."""
        packets = generator.generate_shot_packets(simple_shot, msec_since_contact=1000)

        for packet in packets:
            assert len(packet) == PACKET_SIZE


class TestPacketSplitting:
    """Tests for splitting messages across packet boundaries."""

    @pytest.fixture
    def generator(self) -> GC2PacketGenerator:
        """Create a packet generator."""
        return GC2PacketGenerator()

    def test_long_message_splits_into_multiple_packets(self, generator: GC2PacketGenerator) -> None:
        """Long message is split into multiple 64-byte packets."""
        # Shot with HMT data will be longer than 64 bytes
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            club_speed=105.2,
            hpath_deg=3.1,
            vpath_deg=-4.2,
            face_t_deg=1.5,
        )
        packets = generator.generate_shot_packets(shot, msec_since_contact=1000)

        # Should produce multiple packets
        assert len(packets) >= 2

    def test_split_field_value_across_packets(self, generator: GC2PacketGenerator) -> None:
        """Can split a field value at a specific position."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.20)

        # Request split in middle of SPEED_MPH value
        packets = generator.generate_shot_packets(
            shot,
            msec_since_contact=1000,
            split_at_field="SPEED_MPH",
            split_at_position=3,  # Split after "145"
        )

        # First packet should end with partial value
        first_text = packets[0].decode("ascii").rstrip("\x00")
        assert "SPEED_MPH=145" in first_text

        # Second packet should start with rest of value
        second_text = packets[1].decode("ascii").rstrip("\x00")
        assert second_text.startswith(".20") or ".20" in second_text[:10]

    def test_reconstructed_message_is_valid(self, generator: GC2PacketGenerator) -> None:
        """Reassembled message from split packets is valid."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.20)

        packets = generator.generate_shot_packets(
            shot,
            msec_since_contact=1000,
            split_at_field="SPEED_MPH",
            split_at_position=3,
        )

        # Combine and verify
        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")

        assert "SHOT_ID=1" in text
        assert "SPEED_MPH=145.20" in text
        assert text.endswith("\n\t")


class TestHMTData:
    """Tests for HMT (club) data generation."""

    @pytest.fixture
    def generator(self) -> GC2PacketGenerator:
        """Create a packet generator."""
        return GC2PacketGenerator()

    def test_hmt_data_included_when_present(self, generator: GC2PacketGenerator) -> None:
        """HMT fields are included when set on shot."""
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            club_speed=105.2,
            hpath_deg=3.1,
            vpath_deg=-4.2,
            face_t_deg=1.5,
        )
        packets = generator.generate_shot_packets(shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")

        assert "CLUBSPEED_MPH=105.20" in text
        assert "HPATH_DEG=3.10" in text
        assert "VPATH_DEG=-4.20" in text
        assert "FACE_T_DEG=1.50" in text

    def test_hmt_data_omitted_when_not_set(self, generator: GC2PacketGenerator) -> None:
        """HMT fields are omitted when not set on shot."""
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        packets = generator.generate_shot_packets(shot, msec_since_contact=1000)

        combined = b"".join(packets)
        text = combined.decode("ascii").rstrip("\x00")

        assert "CLUBSPEED_MPH" not in text
        assert "HPATH_DEG" not in text
