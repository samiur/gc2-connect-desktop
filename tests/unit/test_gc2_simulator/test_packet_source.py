# ABOUTME: Unit tests for SimulatedPacketSource.
# ABOUTME: Tests async packet delivery with TimeController integration.
"""Tests for SimulatedPacketSource."""

from __future__ import annotations

import pytest

from tests.simulators.gc2.models import (
    PacketSequence,
    ScheduledPacket,
    SimulatedShot,
)
from tests.simulators.gc2.packet_source import SimulatedPacketSource
from tests.simulators.gc2.scheduler import GC2TransmissionScheduler
from tests.simulators.timing import TimeController, TimeMode


class TestPacketSourceBasics:
    """Tests for basic packet source functionality."""

    @pytest.fixture
    def simple_sequence(self) -> PacketSequence:
        """Create a simple packet sequence."""
        return PacketSequence(
            packets=[
                ScheduledPacket(data=b"packet1", delay_ms=0.0),
                ScheduledPacket(data=b"packet2", delay_ms=100.0),
                ScheduledPacket(data=b"packet3", delay_ms=200.0),
            ]
        )

    @pytest.fixture
    def instant_controller(self) -> TimeController:
        """Create a time controller in INSTANT mode."""
        return TimeController(mode=TimeMode.INSTANT)

    @pytest.mark.asyncio
    async def test_delivers_all_packets(
        self, simple_sequence: PacketSequence, instant_controller: TimeController
    ) -> None:
        """Delivers all packets in sequence."""
        source = SimulatedPacketSource(simple_sequence, instant_controller)

        packets = []
        while source.is_active:
            packet = await source.get_packet(timeout=1.0)
            if packet is not None:
                packets.append(packet)

        assert len(packets) == 3

    @pytest.mark.asyncio
    async def test_packets_contain_correct_data(
        self, simple_sequence: PacketSequence, instant_controller: TimeController
    ) -> None:
        """Packets contain correct data from sequence."""
        source = SimulatedPacketSource(simple_sequence, instant_controller)

        packet1 = await source.get_packet(timeout=1.0)
        packet2 = await source.get_packet(timeout=1.0)
        packet3 = await source.get_packet(timeout=1.0)

        assert packet1 is not None and packet1.data == b"packet1"
        assert packet2 is not None and packet2.data == b"packet2"
        assert packet3 is not None and packet3.data == b"packet3"

    @pytest.mark.asyncio
    async def test_returns_none_when_complete(
        self, simple_sequence: PacketSequence, instant_controller: TimeController
    ) -> None:
        """Returns None when all packets delivered."""
        source = SimulatedPacketSource(simple_sequence, instant_controller)

        # Consume all packets
        for _ in range(3):
            await source.get_packet(timeout=1.0)

        # Should return None now
        assert not source.is_active
        result = await source.get_packet(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_stop_ends_delivery(
        self, simple_sequence: PacketSequence, instant_controller: TimeController
    ) -> None:
        """Calling stop() ends packet delivery."""
        source = SimulatedPacketSource(simple_sequence, instant_controller)

        # Get first packet
        await source.get_packet(timeout=1.0)

        # Stop
        source.stop()

        # Should no longer be active
        assert not source.is_active

    @pytest.mark.asyncio
    async def test_reset_restarts_sequence(
        self, simple_sequence: PacketSequence, instant_controller: TimeController
    ) -> None:
        """Reset restarts packet delivery from beginning."""
        source = SimulatedPacketSource(simple_sequence, instant_controller)

        # Consume all packets
        for _ in range(3):
            await source.get_packet(timeout=1.0)

        # Reset
        source.reset()

        # Should be active again
        assert source.is_active

        # Should get first packet again
        packet = await source.get_packet(timeout=1.0)
        assert packet is not None and packet.data == b"packet1"


class TestPacketSourceTiming:
    """Tests for packet delivery timing."""

    @pytest.fixture
    def timed_sequence(self) -> PacketSequence:
        """Create a sequence with specific timing."""
        return PacketSequence(
            packets=[
                ScheduledPacket(data=b"t0", delay_ms=0.0),
                ScheduledPacket(data=b"t50", delay_ms=50.0),
                ScheduledPacket(data=b"t100", delay_ms=100.0),
            ]
        )

    @pytest.mark.asyncio
    async def test_instant_mode_delivers_immediately(self, timed_sequence: PacketSequence) -> None:
        """In INSTANT mode, all packets deliver without real delay."""
        import time

        controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(timed_sequence, controller)

        start = time.monotonic()
        packets = []
        while source.is_active:
            packet = await source.get_packet(timeout=1.0)
            if packet is not None:
                packets.append(packet)
        elapsed = time.monotonic() - start

        # Should have all packets
        assert len(packets) == 3
        # Should be nearly instant (< 100ms real time)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_real_mode_respects_timing(self, timed_sequence: PacketSequence) -> None:
        """In REAL mode, packets respect actual timing."""
        import time

        controller = TimeController(mode=TimeMode.REAL)
        source = SimulatedPacketSource(timed_sequence, controller)

        start = time.monotonic()

        # Get first packet (delay=0)
        packet1 = await source.get_packet(timeout=1.0)
        time1 = time.monotonic() - start

        # Get second packet (delay=50ms)
        packet2 = await source.get_packet(timeout=1.0)
        time2 = time.monotonic() - start

        assert packet1 is not None
        assert packet2 is not None

        # First should be immediate-ish
        assert time1 < 0.02

        # Second should be ~50ms after start
        assert 0.04 < time2 < 0.1


class TestPacketSourceWithScheduler:
    """Tests for packet source with transmission scheduler."""

    @pytest.mark.asyncio
    async def test_delivers_shot_packets(self) -> None:
        """Delivers packets for a scheduled shot."""
        scheduler = GC2TransmissionScheduler()
        shot = SimulatedShot(shot_id=1, ball_speed=145.0)
        sequence = scheduler.schedule_shot(shot, include_preliminary=False)

        controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, controller)

        packets = []
        while source.is_active:
            packet = await source.get_packet(timeout=1.0)
            if packet is not None:
                packets.append(packet)

        # Should have received packets
        assert len(packets) > 0

        # Combine and verify contains shot data
        combined = b"".join(p.data for p in packets)
        text = combined.decode("ascii").rstrip("\x00")
        assert "SHOT_ID=1" in text
        assert "SPEED_MPH=" in text

    @pytest.mark.asyncio
    async def test_packet_endpoint_matches_sequence(self) -> None:
        """Packet endpoint_name matches scheduled endpoint."""
        sequence = PacketSequence(
            packets=[
                ScheduledPacket(data=b"intr", delay_ms=0.0, endpoint="INTR"),
                ScheduledPacket(data=b"bulk", delay_ms=10.0, endpoint="BULK"),
            ]
        )

        controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, controller)

        packet1 = await source.get_packet(timeout=1.0)
        packet2 = await source.get_packet(timeout=1.0)

        assert packet1 is not None and packet1.endpoint_name == "INTR"
        assert packet2 is not None and packet2.endpoint_name == "BULK"

    @pytest.mark.asyncio
    async def test_packet_has_timestamp(self) -> None:
        """Packets have timestamp from TimeController."""
        sequence = PacketSequence(packets=[ScheduledPacket(data=b"test", delay_ms=100.0)])

        controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, controller)

        packet = await source.get_packet(timeout=1.0)

        assert packet is not None
        # In INSTANT mode, time advances by delay
        assert packet.timestamp >= 0.1  # 100ms = 0.1s
