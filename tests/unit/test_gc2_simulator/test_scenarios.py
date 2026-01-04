# ABOUTME: Unit tests for pre-built GC2 test scenarios.
# ABOUTME: Tests scenario generators for common USB packet patterns.
"""Tests for pre-built GC2 test scenarios."""

from __future__ import annotations

from tests.simulators.gc2.models import MessageType, SimulatedShot
from tests.simulators.gc2.scenarios import (
    create_rapid_fire_sequence,
    create_split_field_sequence,
    create_status_interrupted_sequence,
    create_two_phase_transmission_sequence,
)


class TestTwoPhaseTransmission:
    """Tests for two-phase transmission scenario."""

    def test_creates_valid_sequence(self) -> None:
        """Creates a valid packet sequence."""
        seq = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)
        assert len(seq.packets) > 0

    def test_has_preliminary_and_refined_phases(self) -> None:
        """Sequence has packets at both preliminary and refined times."""
        seq = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

        delays = [p.delay_ms for p in seq.packets]
        has_preliminary = any(d < 500 for d in delays)
        has_refined = any(d >= 500 for d in delays)

        assert has_preliminary, "Expected preliminary phase packets"
        assert has_refined, "Expected refined phase packets"

    def test_preliminary_omits_spin(self) -> None:
        """Preliminary phase omits spin components."""
        seq = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

        preliminary_packets = [p for p in seq.packets if p.delay_ms < 500]
        preliminary_text = b"".join(p.data for p in preliminary_packets)
        text = preliminary_text.decode("ascii").rstrip("\x00")

        assert "BACK_RPM=" not in text
        assert "SIDE_RPM=" not in text

    def test_refined_includes_spin(self) -> None:
        """Refined phase includes spin components."""
        seq = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

        refined_packets = [p for p in seq.packets if p.delay_ms >= 500]
        refined_text = b"".join(p.data for p in refined_packets)
        text = refined_text.decode("ascii").rstrip("\x00")

        assert "BACK_RPM=" in text
        assert "SIDE_RPM=" in text

    def test_custom_timing(self) -> None:
        """Can customize preliminary and refined timing."""
        seq = create_two_phase_transmission_sequence(
            shot_id=1,
            ball_speed=145.0,
            preliminary_delay_ms=100.0,
            refined_delay_ms=500.0,
        )

        delays = [p.delay_ms for p in seq.packets]
        has_early = any(90 <= d <= 150 for d in delays)
        has_late = any(490 <= d <= 550 for d in delays)

        assert has_early, f"Expected packets ~100ms, got {delays}"
        assert has_late, f"Expected packets ~500ms, got {delays}"


class TestStatusInterrupted:
    """Tests for status-interrupted transmission scenario."""

    def test_creates_valid_sequence(self) -> None:
        """Creates a valid packet sequence."""
        seq = create_status_interrupted_sequence(shot_id=1, ball_speed=145.0)
        assert len(seq.packets) > 0

    def test_has_both_message_types(self) -> None:
        """Sequence has both shot and status packets."""
        seq = create_status_interrupted_sequence(shot_id=1, ball_speed=145.0)

        message_types = {p.message_type for p in seq.packets}
        assert MessageType.SHOT_DATA in message_types
        assert MessageType.BALL_STATUS in message_types

    def test_status_interrupts_shot(self) -> None:
        """Status message appears after some shot packets."""
        seq = create_status_interrupted_sequence(shot_id=1, ball_speed=145.0)

        # Find shot and status delays
        shot_delays = [p.delay_ms for p in seq.packets if p.message_type == MessageType.SHOT_DATA]
        status_delays = [
            p.delay_ms for p in seq.packets if p.message_type == MessageType.BALL_STATUS
        ]

        # Status should come after first shot packet
        assert min(shot_delays) < min(status_delays)

    def test_shot_data_is_incomplete(self) -> None:
        """Shot data is incomplete (missing later fields)."""
        seq = create_status_interrupted_sequence(shot_id=1, ball_speed=145.0, spin_rpm=2500.0)

        shot_packets = [p for p in seq.packets if p.message_type == MessageType.SHOT_DATA]
        shot_text = b"".join(p.data for p in shot_packets)
        text = shot_text.decode("ascii").rstrip("\x00")

        # Should have shot ID and speed
        assert "SHOT_ID=1" in text
        assert "SPEED_MPH=" in text


class TestSplitField:
    """Tests for field split across packet boundary scenario."""

    def test_creates_valid_sequence(self) -> None:
        """Creates a valid packet sequence."""
        seq = create_split_field_sequence(shot_id=1)
        assert len(seq.packets) > 0

    def test_produces_multiple_packets(self) -> None:
        """Field split forces multiple packets."""
        seq = create_split_field_sequence(shot_id=1)
        assert len(seq.packets) >= 2

    def test_combined_data_is_valid(self) -> None:
        """Combined packet data forms valid shot message."""
        seq = create_split_field_sequence(shot_id=1, ball_speed=145.0)

        combined = b"".join(p.data for p in seq.packets)
        text = combined.decode("ascii").rstrip("\x00")

        assert "SHOT_ID=1" in text
        assert "SPEED_MPH=" in text


class TestRapidFire:
    """Tests for rapid-fire sequence (multiple shots)."""

    def test_creates_sequence_with_multiple_shots(self) -> None:
        """Creates sequence with requested number of shots."""
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
            SimulatedShot(shot_id=3, ball_speed=155.0),
        ]
        seq = create_rapid_fire_sequence(shots)

        # Should have packets for all three shots
        combined = b"".join(p.data for p in seq.packets)
        text = combined.decode("ascii")

        assert "SHOT_ID=1" in text
        assert "SHOT_ID=2" in text
        assert "SHOT_ID=3" in text

    def test_shots_are_sequential(self) -> None:
        """Shot packets appear in sequence order."""
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
        ]
        seq = create_rapid_fire_sequence(shots)

        # Find first packet of each shot
        shot1_delay = None
        shot2_delay = None

        for p in seq.packets:
            text = p.data.decode("ascii")
            if "SHOT_ID=1" in text and shot1_delay is None:
                shot1_delay = p.delay_ms
            if "SHOT_ID=2" in text and shot2_delay is None:
                shot2_delay = p.delay_ms

        assert shot1_delay is not None
        assert shot2_delay is not None
        assert shot1_delay < shot2_delay

    def test_default_gap_between_shots(self) -> None:
        """Default gap between shots."""
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
        ]
        seq = create_rapid_fire_sequence(shots)

        # Check that total duration is reasonable
        total_duration = seq.total_duration_ms()
        # At least some gap between shots
        assert total_duration > 1000  # Both shots have refined at 1000ms

    def test_custom_gap(self) -> None:
        """Can customize gap between shots."""
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
        ]
        seq = create_rapid_fire_sequence(shots, gap_ms=2000.0)

        # With 2000ms gap, second shot should start much later
        combined = b"".join(p.data for p in seq.packets)
        text = combined.decode("ascii")

        # Both shots should be present
        assert "SHOT_ID=1" in text
        assert "SHOT_ID=2" in text

    def test_include_preliminary(self) -> None:
        """Can include preliminary data in rapid fire."""
        shots = [
            SimulatedShot(shot_id=1, ball_speed=145.0),
            SimulatedShot(shot_id=2, ball_speed=150.0),
        ]
        seq = create_rapid_fire_sequence(shots, include_preliminary=True)

        # Should have more packets with preliminary included
        delays = [p.delay_ms for p in seq.packets]
        # Should have some packets at ~200ms range (preliminary)
        has_preliminary_timing = any(150 <= d <= 300 for d in delays)
        assert has_preliminary_timing
