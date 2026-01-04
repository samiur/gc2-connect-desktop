# ABOUTME: Integration tests for USB packet simulation.
# ABOUTME: Tests GC2USBReader with SimulatedPacketSource to verify packet processing.
"""Integration tests for USB packet simulation.

These tests use the SimulatedPacketSource to inject packets into
GC2USBReader and verify the packet processing logic works correctly.
"""

from __future__ import annotations

import asyncio

import pytest

from gc2_connect.gc2 import GC2USBReader
from gc2_connect.models import GC2ShotData
from tests.simulators.gc2 import (
    SimulatedPacketSource,
    SimulatedShot,
    create_rapid_fire_sequence,
    create_two_phase_transmission_sequence,
)
from tests.simulators.timing import TimeController, TimeMode


class TestSimulatedPacketProcessing:
    """Tests for processing simulated USB packets."""

    @pytest.mark.asyncio
    async def test_processes_two_phase_shot(self) -> None:
        """GC2USBReader processes a two-phase shot correctly."""
        # Create a two-phase transmission sequence
        sequence = create_two_phase_transmission_sequence(
            shot_id=1,
            ball_speed=145.0,
            spin_rpm=2500.0,
            back_rpm=2400.0,
            side_rpm=-100.0,
        )

        # Create time controller in INSTANT mode for fast tests
        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        # Create reader with injected packet source
        reader = GC2USBReader(packet_source=source)

        # Track received shots
        received_shots: list[GC2ShotData] = []

        def on_shot(shot: GC2ShotData) -> None:
            received_shots.append(shot)

        reader.add_shot_callback(on_shot)

        # Run read loop (will complete when source is exhausted)
        read_task = asyncio.create_task(reader.read_loop())

        # Wait a bit for processing (INSTANT mode is fast)
        await asyncio.sleep(0.1)
        reader._running = False
        source.stop()

        # Wait for task to complete
        await asyncio.wait_for(read_task, timeout=1.0)

        # Should have received the shot
        assert len(received_shots) == 1
        shot = received_shots[0]
        assert shot.shot_id == 1
        assert 140 < shot.ball_speed < 150  # Approximate match

    @pytest.mark.asyncio
    async def test_processes_rapid_fire_shots(self) -> None:
        """GC2USBReader processes multiple rapid shots correctly."""
        # Create sequence with multiple shots
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
            SimulatedShot(shot_id=3, ball_speed=155.0),
        ]
        sequence = create_rapid_fire_sequence(shots, gap_ms=100.0)

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        received_shots: list[GC2ShotData] = []
        reader.add_shot_callback(lambda s: received_shots.append(s))

        # Run read loop
        read_task = asyncio.create_task(reader.read_loop())

        # Wait for processing
        await asyncio.sleep(0.2)
        reader._running = False
        source.stop()

        await asyncio.wait_for(read_task, timeout=1.0)

        # Should have received all three shots
        assert len(received_shots) == 3
        assert received_shots[0].shot_id == 1
        assert received_shots[1].shot_id == 2
        assert received_shots[2].shot_id == 3

    @pytest.mark.asyncio
    async def test_shot_callback_receives_correct_data(self) -> None:
        """Shot callback receives correct ball data."""
        sequence = create_two_phase_transmission_sequence(
            shot_id=42,
            ball_speed=165.0,
            spin_rpm=3000.0,
            back_rpm=2900.0,
            side_rpm=-200.0,
        )

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        received_shots: list[GC2ShotData] = []
        reader.add_shot_callback(lambda s: received_shots.append(s))

        read_task = asyncio.create_task(reader.read_loop())
        await asyncio.sleep(0.1)
        reader._running = False
        source.stop()
        await asyncio.wait_for(read_task, timeout=1.0)

        assert len(received_shots) == 1
        shot = received_shots[0]
        assert shot.shot_id == 42
        # Verify ball data is approximately correct (generator may have some variance)
        assert 160 < shot.ball_speed < 170
        assert shot.total_spin > 0


class TestSimulatedTimingModes:
    """Tests for different timing modes."""

    @pytest.mark.asyncio
    async def test_instant_mode_completes_fast(self) -> None:
        """INSTANT mode processes packets immediately."""
        import time

        sequence = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

        # INSTANT mode
        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)
        received_shots: list[GC2ShotData] = []
        reader.add_shot_callback(lambda s: received_shots.append(s))

        start = time.monotonic()
        read_task = asyncio.create_task(reader.read_loop())
        await asyncio.sleep(0.2)
        reader._running = False
        source.stop()
        await asyncio.wait_for(read_task, timeout=1.0)
        elapsed = time.monotonic() - start

        # Should complete in under 1 second (INSTANT mode)
        assert elapsed < 1.0
        assert len(received_shots) == 1


class TestPacketSourceIntegration:
    """Tests for packet source integration."""

    @pytest.mark.asyncio
    async def test_source_stop_ends_reader(self) -> None:
        """Stopping packet source ends read loop."""
        sequence = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        read_task = asyncio.create_task(reader.read_loop())

        # Let it start processing
        await asyncio.sleep(0.05)

        # Stop the source
        source.stop()

        # Read loop should end
        await asyncio.wait_for(read_task, timeout=2.0)
        assert not reader._running

    @pytest.mark.asyncio
    async def test_empty_sequence_completes(self) -> None:
        """Empty packet sequence completes without error."""
        from tests.simulators.gc2.models import PacketSequence

        empty_sequence = PacketSequence(packets=[])

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(empty_sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        read_task = asyncio.create_task(reader.read_loop())

        # Should complete quickly
        await asyncio.wait_for(read_task, timeout=1.0)
