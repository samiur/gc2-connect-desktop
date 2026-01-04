# ABOUTME: Integration tests for producer-consumer queue pattern.
# ABOUTME: Tests queue behavior and shot callback patterns.
"""Integration tests for producer-consumer queue pattern.

These tests verify the queue behavior of the GC2USBReader,
ensuring shots are properly buffered and delivered to callbacks.
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


class TestShotCallbackPatterns:
    """Tests for shot callback patterns."""

    @pytest.mark.asyncio
    async def test_async_callback_receives_shot(self) -> None:
        """Async callback receives shot from reader."""
        sequence = create_two_phase_transmission_sequence(
            shot_id=1,
            ball_speed=145.0,
            spin_rpm=2500.0,
        )

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        # Track received shots
        received_shots: list[GC2ShotData] = []
        shot_event = asyncio.Event()

        def on_shot(shot: GC2ShotData) -> None:
            received_shots.append(shot)
            shot_event.set()

        reader.add_shot_callback(on_shot)

        # Run reader
        read_task = asyncio.create_task(reader.read_loop())

        # Wait for shot to be received
        try:
            await asyncio.wait_for(shot_event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

        reader._running = False
        source.stop()
        await asyncio.wait_for(read_task, timeout=1.0)

        assert len(received_shots) == 1
        assert received_shots[0].shot_id == 1

    @pytest.mark.asyncio
    async def test_multiple_callbacks_receive_same_shot(self) -> None:
        """Multiple callbacks all receive the same shot."""
        sequence = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        # Add multiple callbacks
        callback1_shots: list[GC2ShotData] = []
        callback2_shots: list[GC2ShotData] = []
        callback3_shots: list[GC2ShotData] = []

        reader.add_shot_callback(lambda s: callback1_shots.append(s))
        reader.add_shot_callback(lambda s: callback2_shots.append(s))
        reader.add_shot_callback(lambda s: callback3_shots.append(s))

        read_task = asyncio.create_task(reader.read_loop())
        await asyncio.sleep(0.2)
        reader._running = False
        source.stop()
        await asyncio.wait_for(read_task, timeout=1.0)

        # All callbacks should have received the shot
        assert len(callback1_shots) == 1
        assert len(callback2_shots) == 1
        assert len(callback3_shots) == 1

    @pytest.mark.asyncio
    async def test_remove_callback_stops_notifications(self) -> None:
        """Removed callback stops receiving shots."""
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
        ]
        sequence = create_rapid_fire_sequence(shots, gap_ms=100.0)

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        received_shots: list[GC2ShotData] = []

        def on_shot(shot: GC2ShotData) -> None:
            received_shots.append(shot)
            # Remove callback after first shot
            reader.remove_shot_callback(on_shot)

        reader.add_shot_callback(on_shot)

        read_task = asyncio.create_task(reader.read_loop())
        await asyncio.sleep(0.5)
        reader._running = False
        source.stop()
        await asyncio.wait_for(read_task, timeout=1.0)

        # Should only have received first shot (callback was removed)
        assert len(received_shots) == 1
        assert received_shots[0].shot_id == 1


class TestQueueBehavior:
    """Tests for queue behavior under load."""

    @pytest.mark.asyncio
    async def test_queue_handles_burst_of_packets(self) -> None:
        """Queue buffers burst of packets correctly."""
        # Create a sequence with many packets
        shots = [SimulatedShot(shot_id=i, ball_speed=145.0 + i) for i in range(1, 6)]
        sequence = create_rapid_fire_sequence(shots, gap_ms=50.0)

        time_controller = TimeController(mode=TimeMode.INSTANT)
        source = SimulatedPacketSource(sequence, time_controller)

        reader = GC2USBReader(packet_source=source)

        received_shots: list[GC2ShotData] = []
        reader.add_shot_callback(lambda s: received_shots.append(s))

        read_task = asyncio.create_task(reader.read_loop())
        await asyncio.sleep(1.0)
        reader._running = False
        source.stop()
        await asyncio.wait_for(read_task, timeout=2.0)

        # Should have received all 5 shots
        assert len(received_shots) == 5
        shot_ids = [s.shot_id for s in received_shots]
        assert shot_ids == [1, 2, 3, 4, 5]
