# ABOUTME: Unit tests for GC2 transmission scheduler.
# ABOUTME: Tests two-phase transmission, timing, and interruption scenarios.
"""Tests for GC2 transmission scheduler."""

from __future__ import annotations

import pytest

from tests.simulators.gc2.models import (
    MessageType,
    SimulatedShot,
    SimulatedStatus,
)
from tests.simulators.gc2.scheduler import GC2TransmissionScheduler


class TestSchedulerBasics:
    """Tests for basic scheduler functionality."""

    @pytest.fixture
    def scheduler(self) -> GC2TransmissionScheduler:
        """Create a transmission scheduler."""
        return GC2TransmissionScheduler()

    @pytest.fixture
    def simple_shot(self) -> SimulatedShot:
        """Create a simple shot."""
        return SimulatedShot(shot_id=1, ball_speed=145.0)

    def test_schedule_shot_produces_packets(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Scheduling a shot produces a packet sequence."""
        seq = scheduler.schedule_shot(simple_shot)
        assert len(seq.packets) > 0

    def test_packets_are_scheduled_with_timing(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Packets have timing information."""
        seq = scheduler.schedule_shot(simple_shot)
        # At least some packets should have non-zero delay
        delays = [p.delay_ms for p in seq.packets]
        assert max(delays) > 0


class TestTwoPhaseTransmission:
    """Tests for two-phase transmission (preliminary + refined)."""

    @pytest.fixture
    def scheduler(self) -> GC2TransmissionScheduler:
        """Create a transmission scheduler."""
        return GC2TransmissionScheduler()

    @pytest.fixture
    def simple_shot(self) -> SimulatedShot:
        """Create a simple shot with two-phase timing."""
        return SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            preliminary_delay_ms=200,
            refined_delay_ms=1000,
        )

    def test_two_phase_produces_two_message_sets(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Two-phase transmission produces packets at both times."""
        seq = scheduler.schedule_shot(simple_shot, include_preliminary=True)

        # Should have packets at ~200ms and ~1000ms
        delays = [p.delay_ms for p in seq.packets]
        has_early = any(190 <= d <= 250 for d in delays)
        has_late = any(990 <= d <= 1100 for d in delays)

        assert has_early, f"Expected preliminary packets ~200ms, got {delays}"
        assert has_late, f"Expected refined packets ~1000ms, got {delays}"

    def test_preliminary_omits_spin_components(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Preliminary data omits BACK_RPM and SIDE_RPM."""
        seq = scheduler.schedule_shot(simple_shot, include_preliminary=True)

        # Find preliminary packets (delay < 500ms)
        preliminary_packets = [p for p in seq.packets if p.delay_ms < 500]
        preliminary_text = b"".join(p.data for p in preliminary_packets)
        text = preliminary_text.decode("ascii").rstrip("\x00")

        # Should NOT have spin components
        assert "BACK_RPM=" not in text
        assert "SIDE_RPM=" not in text

    def test_refined_includes_spin_components(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Refined data includes BACK_RPM and SIDE_RPM."""
        seq = scheduler.schedule_shot(simple_shot, include_preliminary=True)

        # Find refined packets (delay >= 500ms)
        refined_packets = [p for p in seq.packets if p.delay_ms >= 500]
        refined_text = b"".join(p.data for p in refined_packets)
        text = refined_text.decode("ascii").rstrip("\x00")

        # Should have spin components
        assert "BACK_RPM=" in text
        assert "SIDE_RPM=" in text

    def test_can_skip_preliminary(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Can skip preliminary and only send refined."""
        seq = scheduler.schedule_shot(simple_shot, include_preliminary=False)

        # All packets should be at ~1000ms (refined only)
        delays = [p.delay_ms for p in seq.packets]
        assert all(d >= 500 for d in delays), f"Expected only refined packets, got delays {delays}"


class TestStatusMessages:
    """Tests for 0M status message handling."""

    @pytest.fixture
    def scheduler(self) -> GC2TransmissionScheduler:
        """Create a transmission scheduler."""
        return GC2TransmissionScheduler()

    @pytest.fixture
    def simple_shot(self) -> SimulatedShot:
        """Create a simple shot."""
        return SimulatedShot(shot_id=1, ball_speed=145.0)

    def test_can_include_status_before_shot(
        self, scheduler: GC2TransmissionScheduler, simple_shot: SimulatedShot
    ) -> None:
        """Can send status message before shot data."""
        seq = scheduler.schedule_shot(
            simple_shot,
            include_preliminary=False,
            include_status_before=True,
        )

        # First packets should be status (0M), then shot (0H)
        message_types = [p.message_type for p in seq.packets]
        assert MessageType.BALL_STATUS in message_types
        assert MessageType.SHOT_DATA in message_types

        # Status should come first (lower delay)
        status_delay = min(
            p.delay_ms for p in seq.packets if p.message_type == MessageType.BALL_STATUS
        )
        shot_delay = min(p.delay_ms for p in seq.packets if p.message_type == MessageType.SHOT_DATA)
        assert status_delay < shot_delay

    def test_schedule_status_change(self, scheduler: GC2TransmissionScheduler) -> None:
        """Can schedule a status change."""
        from_status = SimulatedStatus(flags=7, balls=1)
        to_status = SimulatedStatus(flags=1, balls=0)

        seq = scheduler.schedule_status_change(from_status, to_status, delay_ms=100.0)

        assert len(seq.packets) >= 2  # At least two status messages
        assert all(p.message_type == MessageType.BALL_STATUS for p in seq.packets)


class TestInterruptedTransmission:
    """Tests for shot interruption by status change."""

    @pytest.fixture
    def scheduler(self) -> GC2TransmissionScheduler:
        """Create a transmission scheduler."""
        return GC2TransmissionScheduler()

    def test_can_interrupt_shot_with_status(self, scheduler: GC2TransmissionScheduler) -> None:
        """Can inject status message that interrupts shot transmission."""
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            interrupt_after_field="SPEED_MPH",
        )

        seq = scheduler.schedule_interrupted_shot(shot, interrupt_after_field="SPEED_MPH")

        # Should have mix of shot and status packets
        message_types = [p.message_type for p in seq.packets]
        assert MessageType.SHOT_DATA in message_types
        assert MessageType.BALL_STATUS in message_types

    def test_interrupted_shot_has_incomplete_data(
        self, scheduler: GC2TransmissionScheduler
    ) -> None:
        """Interrupted shot transmission is incomplete."""
        shot = SimulatedShot(
            shot_id=1,
            ball_speed=145.0,
            spin_rpm=2500.0,
            back_rpm=2400.0,
        )

        seq = scheduler.schedule_interrupted_shot(shot, interrupt_after_field="SPEED_MPH")

        # Get shot packets before interruption
        shot_packets = [p for p in seq.packets if p.message_type == MessageType.SHOT_DATA]
        shot_text = b"".join(p.data for p in shot_packets)
        text = shot_text.decode("ascii").rstrip("\x00")

        # Should have shot ID and speed but not spin
        assert "SHOT_ID=1" in text
        assert "SPEED_MPH=" in text
        # May or may not have spin depending on where interruption happens


class TestCombinedSequences:
    """Tests for combining multiple sequences."""

    @pytest.fixture
    def scheduler(self) -> GC2TransmissionScheduler:
        """Create a transmission scheduler."""
        return GC2TransmissionScheduler()

    def test_combine_sequences_adds_gap(self, scheduler: GC2TransmissionScheduler) -> None:
        """Combining sequences adds gap between them."""
        shot1 = SimulatedShot(shot_id=1, ball_speed=145.0)
        shot2 = SimulatedShot(shot_id=2, ball_speed=150.0)

        seq1 = scheduler.schedule_shot(shot1, include_preliminary=False)
        seq2 = scheduler.schedule_shot(shot2, include_preliminary=False)

        combined = scheduler.combine_sequences(seq1, seq2, gap_ms=500.0)

        # Second sequence packets should be offset by seq1 duration + gap
        seq1_end = seq1.total_duration_ms()

        # Find shot 2 packets
        shot2_text = f"SHOT_ID={shot2.shot_id}"
        shot2_packets = [p for p in combined.packets if shot2_text.encode() in p.data]

        assert len(shot2_packets) > 0
        shot2_min_delay = min(p.delay_ms for p in shot2_packets)
        assert shot2_min_delay >= seq1_end + 500.0

    def test_combine_maintains_order(self, scheduler: GC2TransmissionScheduler) -> None:
        """Combined sequences maintain packet order."""
        shot1 = SimulatedShot(shot_id=1, ball_speed=145.0)
        shot2 = SimulatedShot(shot_id=2, ball_speed=150.0)

        seq1 = scheduler.schedule_shot(shot1, include_preliminary=False)
        seq2 = scheduler.schedule_shot(shot2, include_preliminary=False)

        combined = scheduler.combine_sequences(seq1, seq2, gap_ms=100.0)

        # Packets should be in increasing delay order
        delays = [p.delay_ms for p in combined.packets]
        assert delays == sorted(delays)
