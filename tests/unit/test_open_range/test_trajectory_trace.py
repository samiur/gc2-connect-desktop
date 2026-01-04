# ABOUTME: Unit tests for trajectory trace visualization in Open Range.
# ABOUTME: Tests trace line creation, phase-based coloring, and progressive drawing.
"""Tests for trajectory trace visualization."""

from __future__ import annotations

import pytest

from gc2_connect.open_range.models import Phase, TrajectoryPoint, Vec3


# Test trajectory data for trace tests
@pytest.fixture
def sample_trajectory() -> list[TrajectoryPoint]:
    """Create a sample trajectory for testing."""
    return [
        TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=0.5, x=50.0, y=30.0, z=1.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=1.0, x=100.0, y=50.0, z=2.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=1.5, x=150.0, y=60.0, z=2.5, phase=Phase.FLIGHT),
        TrajectoryPoint(t=2.0, x=200.0, y=55.0, z=3.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=2.5, x=240.0, y=30.0, z=3.5, phase=Phase.FLIGHT),
        TrajectoryPoint(t=3.0, x=270.0, y=5.0, z=4.0, phase=Phase.FLIGHT),
        TrajectoryPoint(t=3.2, x=275.0, y=0.0, z=4.0, phase=Phase.BOUNCE),
        TrajectoryPoint(t=3.4, x=278.0, y=2.0, z=4.0, phase=Phase.BOUNCE),
        TrajectoryPoint(t=3.6, x=282.0, y=0.0, z=4.1, phase=Phase.ROLLING),
        TrajectoryPoint(t=4.0, x=290.0, y=0.0, z=4.2, phase=Phase.ROLLING),
        TrajectoryPoint(t=4.5, x=295.0, y=0.0, z=4.2, phase=Phase.STOPPED),
    ]


@pytest.fixture
def scene_coordinates() -> list[Vec3]:
    """Create sample scene coordinates (converted from trajectory)."""
    return [
        Vec3(x=0.0, y=0.0, z=0.0),
        Vec3(x=-1.0, y=10.0, z=50.0),
        Vec3(x=-2.0, y=16.67, z=100.0),
        Vec3(x=-2.5, y=20.0, z=150.0),
        Vec3(x=-3.0, y=18.33, z=200.0),
        Vec3(x=-3.5, y=10.0, z=240.0),
        Vec3(x=-4.0, y=1.67, z=270.0),
        Vec3(x=-4.0, y=0.0, z=275.0),
        Vec3(x=-4.0, y=0.67, z=278.0),
        Vec3(x=-4.1, y=0.0, z=282.0),
        Vec3(x=-4.2, y=0.0, z=290.0),
        Vec3(x=-4.2, y=0.0, z=295.0),
    ]


class TestTrajectoryTraceCreation:
    """Tests for TrajectoryTrace class creation and initialization."""

    def test_trajectory_trace_can_be_instantiated(self) -> None:
        """Test that TrajectoryTrace can be created."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        assert trace is not None
        assert trace.segments == []

    def test_trajectory_trace_with_max_segments(self) -> None:
        """Test that TrajectoryTrace respects max_segments limit."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace(max_segments=100)
        assert trace.max_segments == 100


class TestTrajectorySegments:
    """Tests for trajectory segment management."""

    def test_add_segment_stores_segment(self) -> None:
        """Test that adding a segment stores it correctly."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        start = Vec3(x=0.0, y=0.0, z=0.0)
        end = Vec3(x=1.0, y=1.0, z=10.0)

        trace.add_segment(start, end, Phase.FLIGHT)

        assert len(trace.segments) == 1
        assert trace.segments[0].start == start
        assert trace.segments[0].end == end
        assert trace.segments[0].phase == Phase.FLIGHT

    def test_add_multiple_segments(self) -> None:
        """Test adding multiple segments."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()

        trace.add_segment(Vec3(x=0, y=0, z=0), Vec3(x=1, y=1, z=10), Phase.FLIGHT)
        trace.add_segment(Vec3(x=1, y=1, z=10), Vec3(x=2, y=0, z=20), Phase.BOUNCE)
        trace.add_segment(Vec3(x=2, y=0, z=20), Vec3(x=3, y=0, z=25), Phase.ROLLING)

        assert len(trace.segments) == 3
        assert trace.segments[0].phase == Phase.FLIGHT
        assert trace.segments[1].phase == Phase.BOUNCE
        assert trace.segments[2].phase == Phase.ROLLING

    def test_max_segments_limit_enforced(self) -> None:
        """Test that segments beyond max are not added."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace(max_segments=5)

        for i in range(10):
            trace.add_segment(
                Vec3(x=0, y=0, z=float(i)),
                Vec3(x=0, y=0, z=float(i + 1)),
                Phase.FLIGHT,
            )

        # Should be limited to max_segments
        assert len(trace.segments) == 5

    def test_clear_removes_all_segments(self) -> None:
        """Test that clear removes all segments."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        trace.add_segment(Vec3(x=0, y=0, z=0), Vec3(x=1, y=1, z=10), Phase.FLIGHT)
        trace.add_segment(Vec3(x=1, y=1, z=10), Vec3(x=2, y=0, z=20), Phase.BOUNCE)

        trace.clear()

        assert len(trace.segments) == 0


class TestPhaseColors:
    """Tests for phase-specific colors in trajectory trace."""

    def test_get_color_for_flight_phase(self) -> None:
        """Test that flight phase gets green color."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            get_phase_color,
        )

        color = get_phase_color(Phase.FLIGHT)
        assert color == "#00ff88"

    def test_get_color_for_bounce_phase(self) -> None:
        """Test that bounce phase gets orange color."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            get_phase_color,
        )

        color = get_phase_color(Phase.BOUNCE)
        assert color == "#ff8844"

    def test_get_color_for_rolling_phase(self) -> None:
        """Test that rolling phase gets blue color."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            get_phase_color,
        )

        color = get_phase_color(Phase.ROLLING)
        assert color == "#00d4ff"

    def test_get_color_for_stopped_phase(self) -> None:
        """Test that stopped phase gets gray color."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            get_phase_color,
        )

        color = get_phase_color(Phase.STOPPED)
        assert color == "#888888"


class TestTraceFromTrajectory:
    """Tests for creating trace from trajectory points."""

    def test_build_trace_from_trajectory(self, sample_trajectory: list[TrajectoryPoint]) -> None:
        """Test building trace from full trajectory."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        trace.build_from_trajectory(sample_trajectory)

        # Should have segments connecting each point
        assert len(trace.segments) == len(sample_trajectory) - 1

    def test_build_trace_preserves_phases(self, sample_trajectory: list[TrajectoryPoint]) -> None:
        """Test that building trace preserves phase information."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        trace.build_from_trajectory(sample_trajectory)

        # First segments should be flight
        assert trace.segments[0].phase == Phase.FLIGHT

        # Find a bounce segment (around index 7)
        bounce_segments = [s for s in trace.segments if s.phase == Phase.BOUNCE]
        assert len(bounce_segments) > 0

        # Find rolling segments
        rolling_segments = [s for s in trace.segments if s.phase == Phase.ROLLING]
        assert len(rolling_segments) > 0

    def test_build_trace_with_sample_interval(
        self, sample_trajectory: list[TrajectoryPoint]
    ) -> None:
        """Test building trace with sampling interval."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        # Sample every 2nd point
        trace.build_from_trajectory(sample_trajectory, sample_interval=2)

        # Should have fewer segments
        expected_segments = len(sample_trajectory) // 2
        assert len(trace.segments) <= expected_segments

    def test_build_trace_empty_trajectory(self) -> None:
        """Test building trace from empty trajectory."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        trace.build_from_trajectory([])

        assert len(trace.segments) == 0

    def test_build_trace_single_point_trajectory(self) -> None:
        """Test building trace from single-point trajectory."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        trace.build_from_trajectory(
            [TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT)]
        )

        # No segments can be created from single point
        assert len(trace.segments) == 0


class TestProgressiveTrace:
    """Tests for progressive trace drawing during animation."""

    def test_progressive_add_point(self) -> None:
        """Test adding points progressively during animation."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()

        # Initially no segments
        assert len(trace.segments) == 0

        # Add first point - no segment yet (need 2 points)
        trace.add_point(Vec3(x=0, y=0, z=0), Phase.FLIGHT)
        assert len(trace.segments) == 0

        # Add second point - creates first segment
        trace.add_point(Vec3(x=0, y=10, z=50), Phase.FLIGHT)
        assert len(trace.segments) == 1

        # Add third point - creates second segment
        trace.add_point(Vec3(x=0, y=15, z=100), Phase.FLIGHT)
        assert len(trace.segments) == 2

    def test_progressive_add_tracks_phase_changes(self) -> None:
        """Test that progressive adding tracks phase changes."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()

        # Flight points
        trace.add_point(Vec3(x=0, y=0, z=0), Phase.FLIGHT)
        trace.add_point(Vec3(x=0, y=10, z=50), Phase.FLIGHT)

        # Bounce point
        trace.add_point(Vec3(x=0, y=0, z=100), Phase.BOUNCE)

        assert len(trace.segments) == 2
        assert trace.segments[0].phase == Phase.FLIGHT
        assert trace.segments[1].phase == Phase.BOUNCE


class TestTraceVisibility:
    """Tests for trace visibility management."""

    def test_trace_visible_by_default(self) -> None:
        """Test that trace is visible by default."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()
        assert trace.visible is True

    def test_trace_visibility_can_be_toggled(self) -> None:
        """Test that trace visibility can be toggled."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TrajectoryTrace,
        )

        trace = TrajectoryTrace()

        trace.set_visible(False)
        assert trace.visible is False

        trace.set_visible(True)
        assert trace.visible is True


class TestTraceSegmentModel:
    """Tests for TraceSegment data model."""

    def test_trace_segment_creation(self) -> None:
        """Test TraceSegment can be created with all fields."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TraceSegment,
        )

        segment = TraceSegment(
            start=Vec3(x=0, y=0, z=0),
            end=Vec3(x=1, y=1, z=10),
            phase=Phase.FLIGHT,
        )

        assert segment.start == Vec3(x=0, y=0, z=0)
        assert segment.end == Vec3(x=1, y=1, z=10)
        assert segment.phase == Phase.FLIGHT

    def test_trace_segment_color_property(self) -> None:
        """Test TraceSegment color property returns correct phase color."""
        from gc2_connect.open_range.visualization.trajectory_trace import (
            TraceSegment,
        )

        flight_segment = TraceSegment(
            start=Vec3(x=0, y=0, z=0),
            end=Vec3(x=1, y=1, z=10),
            phase=Phase.FLIGHT,
        )
        assert flight_segment.color == "#00ff88"

        bounce_segment = TraceSegment(
            start=Vec3(x=0, y=0, z=0),
            end=Vec3(x=1, y=0, z=10),
            phase=Phase.BOUNCE,
        )
        assert bounce_segment.color == "#ff8844"
