# ABOUTME: Unit tests for Open Range data models.
# ABOUTME: Tests Vec3 operations, trajectory points, shot summaries, and conditions.
"""Tests for Open Range physics data models."""

from __future__ import annotations

import pytest


class TestVec3:
    """Tests for Vec3 3D vector operations."""

    def test_creation_default(self) -> None:
        """Test Vec3 creation with default values."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_creation_with_values(self) -> None:
        """Test Vec3 creation with specified values."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_add(self) -> None:
        """Test Vec3 addition."""
        from gc2_connect.open_range.models import Vec3

        v1 = Vec3(x=1.0, y=2.0, z=3.0)
        v2 = Vec3(x=4.0, y=5.0, z=6.0)
        result = v1.add(v2)
        assert result.x == 5.0
        assert result.y == 7.0
        assert result.z == 9.0

    def test_sub(self) -> None:
        """Test Vec3 subtraction."""
        from gc2_connect.open_range.models import Vec3

        v1 = Vec3(x=4.0, y=5.0, z=6.0)
        v2 = Vec3(x=1.0, y=2.0, z=3.0)
        result = v1.sub(v2)
        assert result.x == 3.0
        assert result.y == 3.0
        assert result.z == 3.0

    def test_scale(self) -> None:
        """Test Vec3 scalar multiplication."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=1.0, y=2.0, z=3.0)
        result = v.scale(2.0)
        assert result.x == 2.0
        assert result.y == 4.0
        assert result.z == 6.0

    def test_magnitude(self) -> None:
        """Test Vec3 magnitude calculation."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=3.0, y=4.0, z=0.0)
        assert v.mag() == pytest.approx(5.0)

    def test_magnitude_3d(self) -> None:
        """Test Vec3 magnitude calculation in 3D."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=1.0, y=2.0, z=2.0)
        assert v.mag() == pytest.approx(3.0)

    def test_normalize(self) -> None:
        """Test Vec3 normalization."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=3.0, y=4.0, z=0.0)
        result = v.normalize()
        assert result.x == pytest.approx(0.6)
        assert result.y == pytest.approx(0.8)
        assert result.z == pytest.approx(0.0)
        assert result.mag() == pytest.approx(1.0)

    def test_normalize_zero_vector(self) -> None:
        """Test normalizing a zero vector returns zero vector."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=0.0, y=0.0, z=0.0)
        result = v.normalize()
        assert result.x == 0.0
        assert result.y == 0.0
        assert result.z == 0.0

    def test_dot(self) -> None:
        """Test Vec3 dot product."""
        from gc2_connect.open_range.models import Vec3

        v1 = Vec3(x=1.0, y=2.0, z=3.0)
        v2 = Vec3(x=4.0, y=5.0, z=6.0)
        result = v1.dot(v2)
        assert result == pytest.approx(32.0)  # 1*4 + 2*5 + 3*6

    def test_cross(self) -> None:
        """Test Vec3 cross product."""
        from gc2_connect.open_range.models import Vec3

        v1 = Vec3(x=1.0, y=0.0, z=0.0)
        v2 = Vec3(x=0.0, y=1.0, z=0.0)
        result = v1.cross(v2)
        assert result.x == pytest.approx(0.0)
        assert result.y == pytest.approx(0.0)
        assert result.z == pytest.approx(1.0)

    def test_cross_reversed(self) -> None:
        """Test Vec3 cross product order matters."""
        from gc2_connect.open_range.models import Vec3

        v1 = Vec3(x=1.0, y=0.0, z=0.0)
        v2 = Vec3(x=0.0, y=1.0, z=0.0)
        result = v2.cross(v1)
        assert result.x == pytest.approx(0.0)
        assert result.y == pytest.approx(0.0)
        assert result.z == pytest.approx(-1.0)

    def test_neg(self) -> None:
        """Test Vec3 negation."""
        from gc2_connect.open_range.models import Vec3

        v = Vec3(x=1.0, y=-2.0, z=3.0)
        result = v.neg()
        assert result.x == -1.0
        assert result.y == 2.0
        assert result.z == -3.0


class TestPhase:
    """Tests for Phase enum."""

    def test_phase_values(self) -> None:
        """Test Phase enum has expected values."""
        from gc2_connect.open_range.models import Phase

        assert Phase.FLIGHT.value == "flight"
        assert Phase.BOUNCE.value == "bounce"
        assert Phase.ROLLING.value == "rolling"
        assert Phase.STOPPED.value == "stopped"


class TestTrajectoryPoint:
    """Tests for TrajectoryPoint model."""

    def test_creation(self) -> None:
        """Test TrajectoryPoint creation."""
        from gc2_connect.open_range.models import Phase, TrajectoryPoint

        point = TrajectoryPoint(t=1.5, x=100.0, y=50.0, z=-5.0, phase=Phase.FLIGHT)
        assert point.t == 1.5
        assert point.x == 100.0
        assert point.y == 50.0
        assert point.z == -5.0
        assert point.phase == Phase.FLIGHT

    def test_different_phases(self) -> None:
        """Test TrajectoryPoint with different phases."""
        from gc2_connect.open_range.models import Phase, TrajectoryPoint

        flight = TrajectoryPoint(t=1.0, x=50.0, y=30.0, z=0.0, phase=Phase.FLIGHT)
        bounce = TrajectoryPoint(t=5.0, x=250.0, y=0.0, z=5.0, phase=Phase.BOUNCE)
        rolling = TrajectoryPoint(t=6.0, x=260.0, y=0.0, z=6.0, phase=Phase.ROLLING)
        stopped = TrajectoryPoint(t=8.0, x=280.0, y=0.0, z=8.0, phase=Phase.STOPPED)

        assert flight.phase == Phase.FLIGHT
        assert bounce.phase == Phase.BOUNCE
        assert rolling.phase == Phase.ROLLING
        assert stopped.phase == Phase.STOPPED


class TestShotSummary:
    """Tests for ShotSummary model."""

    def test_creation(self) -> None:
        """Test ShotSummary creation with all fields."""
        from gc2_connect.open_range.models import ShotSummary

        summary = ShotSummary(
            carry_distance=250.0,
            total_distance=280.0,
            roll_distance=30.0,
            offline_distance=10.0,
            max_height=95.0,
            max_height_time=2.5,
            flight_time=5.0,
            total_time=8.0,
            bounce_count=3,
        )
        assert summary.carry_distance == 250.0
        assert summary.total_distance == 280.0
        assert summary.roll_distance == 30.0
        assert summary.offline_distance == 10.0
        assert summary.max_height == 95.0
        assert summary.max_height_time == 2.5
        assert summary.flight_time == 5.0
        assert summary.total_time == 8.0
        assert summary.bounce_count == 3

    def test_negative_offline_distance(self) -> None:
        """Test ShotSummary allows negative offline (left of target)."""
        from gc2_connect.open_range.models import ShotSummary

        summary = ShotSummary(
            carry_distance=200.0,
            total_distance=220.0,
            roll_distance=20.0,
            offline_distance=-15.0,  # Left of target
            max_height=70.0,
            max_height_time=2.0,
            flight_time=4.5,
            total_time=7.0,
            bounce_count=2,
        )
        assert summary.offline_distance == -15.0


class TestLaunchData:
    """Tests for LaunchData model."""

    def test_creation(self) -> None:
        """Test LaunchData creation."""
        from gc2_connect.open_range.models import LaunchData

        launch = LaunchData(
            ball_speed=150.0,
            vla=12.5,
            hla=2.0,
            backspin=2800.0,
            sidespin=-400.0,
        )
        assert launch.ball_speed == 150.0
        assert launch.vla == 12.5
        assert launch.hla == 2.0
        assert launch.backspin == 2800.0
        assert launch.sidespin == -400.0

    def test_from_gc2_shot_data(self) -> None:
        """Test LaunchData creation from GC2ShotData."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.models import LaunchData

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=1.5,
            back_spin=2686.0,
            side_spin=-250.0,
        )
        launch = LaunchData.from_gc2_shot(gc2_shot)
        assert launch.ball_speed == 167.0
        assert launch.vla == 10.9
        assert launch.hla == 1.5
        assert launch.backspin == 2686.0
        assert launch.sidespin == -250.0


class TestConditions:
    """Tests for Conditions model."""

    def test_default_values(self) -> None:
        """Test Conditions default values match standard atmosphere."""
        from gc2_connect.open_range.models import Conditions

        conditions = Conditions()
        assert conditions.temp_f == 70.0
        assert conditions.elevation_ft == 0.0
        assert conditions.humidity_pct == 50.0
        assert conditions.wind_speed_mph == 0.0
        assert conditions.wind_dir_deg == 0.0

    def test_custom_conditions(self) -> None:
        """Test Conditions with custom values."""
        from gc2_connect.open_range.models import Conditions

        conditions = Conditions(
            temp_f=85.0,
            elevation_ft=5280.0,  # Denver
            humidity_pct=30.0,
            wind_speed_mph=10.0,
            wind_dir_deg=45.0,
        )
        assert conditions.temp_f == 85.0
        assert conditions.elevation_ft == 5280.0
        assert conditions.humidity_pct == 30.0
        assert conditions.wind_speed_mph == 10.0
        assert conditions.wind_dir_deg == 45.0


class TestShotResult:
    """Tests for ShotResult model."""

    def test_creation(self) -> None:
        """Test ShotResult creation with all components."""
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
            TrajectoryPoint(t=1.0, x=100.0, y=50.0, z=0.0, phase=Phase.FLIGHT),
            TrajectoryPoint(t=5.0, x=250.0, y=0.0, z=5.0, phase=Phase.STOPPED),
        ]
        summary = ShotSummary(
            carry_distance=250.0,
            total_distance=270.0,
            roll_distance=20.0,
            offline_distance=5.0,
            max_height=90.0,
            max_height_time=2.5,
            flight_time=5.0,
            total_time=7.0,
            bounce_count=2,
        )
        launch_data = LaunchData(
            ball_speed=160.0, vla=11.0, hla=1.0, backspin=3000.0, sidespin=200.0
        )
        conditions = Conditions()

        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )

        assert len(result.trajectory) == 3
        assert result.summary.carry_distance == 250.0
        assert result.launch_data.ball_speed == 160.0
        assert result.conditions.temp_f == 70.0
