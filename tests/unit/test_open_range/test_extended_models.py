# ABOUTME: Unit tests for extended Open Range models with OpenGolfCoach integration.
# ABOUTME: Tests DerivedShotData model, ShotResult with derived data, and enrichment functions.
"""Tests for extended Open Range models with OpenGolfCoach derived values."""

from __future__ import annotations

import pytest


class TestDerivedShotData:
    """Tests for DerivedShotData model."""

    def test_creation_with_defaults(self) -> None:
        """Test DerivedShotData creation with default values."""
        from gc2_connect.open_range.models import DerivedShotData

        derived = DerivedShotData()
        assert derived.shot_name == "Unknown"
        assert derived.shot_rank == "D"
        assert derived.shot_color_rgb == "#808080"
        assert derived.smash_factor is None
        assert derived.estimated_club_speed_mph is None
        assert derived.estimated_club_path_deg is None
        assert derived.estimated_face_angle_deg is None
        assert derived.ogc_carry_distance is None
        assert derived.ogc_total_distance is None

    def test_creation_with_all_fields(self) -> None:
        """Test DerivedShotData creation with all fields specified."""
        from gc2_connect.open_range.models import DerivedShotData

        derived = DerivedShotData(
            shot_name="Straight Fade",
            shot_rank="A",
            shot_color_rgb="#00D977",
            smash_factor=1.488,
            estimated_club_speed_mph=108.3,
            estimated_club_path_deg=0.48,
            estimated_face_angle_deg=2.27,
            ogc_carry_distance=247.5,
            ogc_total_distance=258.3,
        )
        assert derived.shot_name == "Straight Fade"
        assert derived.shot_rank == "A"
        assert derived.shot_color_rgb == "#00D977"
        assert derived.smash_factor == 1.488
        assert derived.estimated_club_speed_mph == 108.3
        assert derived.estimated_club_path_deg == 0.48
        assert derived.estimated_face_angle_deg == 2.27
        assert derived.ogc_carry_distance == 247.5
        assert derived.ogc_total_distance == 258.3

    def test_shot_rank_valid_values(self) -> None:
        """Test DerivedShotData accepts all valid rank values."""
        from gc2_connect.open_range.models import DerivedShotData

        valid_ranks = ["S+", "S", "A", "B", "C", "D", "E"]
        for rank in valid_ranks:
            derived = DerivedShotData(shot_rank=rank)
            assert derived.shot_rank == rank

    def test_partial_fields(self) -> None:
        """Test DerivedShotData with only some fields populated."""
        from gc2_connect.open_range.models import DerivedShotData

        derived = DerivedShotData(
            shot_name="Push Slice",
            shot_rank="C",
            shot_color_rgb="#FFA500",
            # Other fields remain as defaults (None)
        )
        assert derived.shot_name == "Push Slice"
        assert derived.shot_rank == "C"
        assert derived.smash_factor is None
        assert derived.ogc_carry_distance is None


class TestShotResultWithDerived:
    """Tests for ShotResult with optional derived field."""

    def test_shot_result_without_derived(self) -> None:
        """Test ShotResult creation without derived data (backwards compatible)."""
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

        # Create without derived field
        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )

        assert result.derived is None
        assert len(result.trajectory) == 2
        assert result.summary.carry_distance == 250.0

    def test_shot_result_with_derived(self) -> None:
        """Test ShotResult creation with derived data."""
        from gc2_connect.open_range.models import (
            Conditions,
            DerivedShotData,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
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
        derived = DerivedShotData(
            shot_name="Straight",
            shot_rank="A",
            shot_color_rgb="#00FF00",
            smash_factor=1.48,
            ogc_carry_distance=248.0,
            ogc_total_distance=268.0,
        )

        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
            derived=derived,
        )

        assert result.derived is not None
        assert result.derived.shot_name == "Straight"
        assert result.derived.shot_rank == "A"
        assert result.derived.smash_factor == 1.48

    def test_shot_result_model_copy_with_derived(self) -> None:
        """Test ShotResult can be updated with derived using model_copy."""
        from gc2_connect.open_range.models import (
            Conditions,
            DerivedShotData,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        ]
        summary = ShotSummary()
        launch_data = LaunchData()
        conditions = Conditions()

        # Create without derived
        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )
        assert result.derived is None

        # Update with derived using model_copy
        derived = DerivedShotData(shot_name="Draw", shot_rank="S")
        updated_result = result.model_copy(update={"derived": derived})

        assert updated_result.derived is not None
        assert updated_result.derived.shot_name == "Draw"
        assert updated_result.derived.shot_rank == "S"
        # Original should be unchanged
        assert result.derived is None


class TestEnrichShotResult:
    """Tests for enrich_shot_result() factory function."""

    def test_enrich_adds_derived_data(self) -> None:
        """Test enrich_shot_result() adds OpenGolfCoach derived values."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.open_range.physics.enrichment import enrich_shot_result

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        ]
        summary = ShotSummary(carry_distance=250.0, total_distance=270.0)
        launch_data = LaunchData(
            ball_speed=161.0, vla=12.0, hla=2.0, backspin=2500.0, sidespin=200.0
        )
        conditions = Conditions()

        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=2.0,
            back_spin=2500.0,
            side_spin=200.0,
        )

        enriched = enrich_shot_result(result, gc2_shot)

        assert enriched.derived is not None
        assert enriched.derived.shot_name != ""
        assert enriched.derived.shot_rank in ["S+", "S", "A", "B", "C", "D", "E"]
        assert enriched.derived.shot_color_rgb != ""

    def test_enrich_preserves_trajectory(self) -> None:
        """Test enrich_shot_result() preserves original trajectory."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.open_range.physics.enrichment import enrich_shot_result

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
            TrajectoryPoint(t=1.0, x=100.0, y=50.0, z=2.0, phase=Phase.FLIGHT),
            TrajectoryPoint(t=5.0, x=250.0, y=0.0, z=5.0, phase=Phase.STOPPED),
        ]
        summary = ShotSummary(carry_distance=250.0, total_distance=270.0)
        launch_data = LaunchData(
            ball_speed=161.0, vla=12.0, hla=2.0, backspin=2500.0, sidespin=200.0
        )
        conditions = Conditions()

        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=2.0,
            back_spin=2500.0,
            side_spin=200.0,
        )

        enriched = enrich_shot_result(result, gc2_shot)

        # Trajectory should be unchanged
        assert len(enriched.trajectory) == 3
        assert enriched.trajectory[0].x == 0.0
        assert enriched.trajectory[1].x == 100.0
        assert enriched.trajectory[2].x == 250.0

    def test_enrich_graceful_fallback_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test enrich_shot_result() returns original result on error."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )
        from gc2_connect.open_range.physics import enrichment

        # Mock calculate_shot_from_gc2 to raise an exception
        def mock_calculate_error(_shot: GC2ShotData) -> None:
            raise RuntimeError("Mock error")

        monkeypatch.setattr(enrichment, "calculate_shot_from_gc2", mock_calculate_error)

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        ]
        summary = ShotSummary()
        launch_data = LaunchData()
        conditions = Conditions()

        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=2.0,
            back_spin=2500.0,
            side_spin=200.0,
        )

        # Should not raise, should return original result
        enriched = enrichment.enrich_shot_result(result, gc2_shot)
        assert enriched.derived is None

    def test_enrich_populates_ogc_distances(self) -> None:
        """Test enrich_shot_result() populates OGC carry and total distance."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.open_range.physics.enrichment import enrich_shot_result

        trajectory = [
            TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT),
        ]
        summary = ShotSummary()
        launch_data = LaunchData(ball_speed=161.0, vla=12.0, hla=0.0, backspin=2500.0, sidespin=0.0)
        conditions = Conditions()

        result = ShotResult(
            trajectory=trajectory,
            summary=summary,
            launch_data=launch_data,
            conditions=conditions,
        )

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=2500.0,
            side_spin=0.0,
        )

        enriched = enrich_shot_result(result, gc2_shot)

        assert enriched.derived is not None
        assert enriched.derived.ogc_carry_distance is not None
        assert enriched.derived.ogc_carry_distance > 200  # Driver should carry 200+
        assert enriched.derived.ogc_total_distance is not None
        assert enriched.derived.ogc_total_distance >= enriched.derived.ogc_carry_distance


class TestBackwardsCompatibility:
    """Tests ensuring backwards compatibility with existing code."""

    def test_shot_result_serialization_without_derived(self) -> None:
        """Test ShotResult JSON serialization without derived field."""
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )

        result = ShotResult(
            trajectory=[TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT)],
            summary=ShotSummary(),
            launch_data=LaunchData(),
            conditions=Conditions(),
        )

        # Serialize and deserialize
        json_data = result.model_dump_json()
        restored = ShotResult.model_validate_json(json_data)

        assert restored.derived is None

    def test_shot_result_serialization_with_derived(self) -> None:
        """Test ShotResult JSON serialization with derived field."""
        from gc2_connect.open_range.models import (
            Conditions,
            DerivedShotData,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )

        derived = DerivedShotData(
            shot_name="Fade",
            shot_rank="B",
            shot_color_rgb="#0000FF",
            smash_factor=1.45,
            ogc_carry_distance=220.0,
        )

        result = ShotResult(
            trajectory=[TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT)],
            summary=ShotSummary(),
            launch_data=LaunchData(),
            conditions=Conditions(),
            derived=derived,
        )

        # Serialize and deserialize
        json_data = result.model_dump_json()
        restored = ShotResult.model_validate_json(json_data)

        assert restored.derived is not None
        assert restored.derived.shot_name == "Fade"
        assert restored.derived.shot_rank == "B"
        assert restored.derived.smash_factor == 1.45

    def test_existing_code_without_derived_still_works(self) -> None:
        """Test that existing code patterns work without modification."""
        from gc2_connect.open_range.models import (
            Conditions,
            LaunchData,
            Phase,
            ShotResult,
            ShotSummary,
            TrajectoryPoint,
        )

        # Old pattern: create ShotResult without derived
        result = ShotResult(
            trajectory=[TrajectoryPoint(t=0.0, x=0.0, y=0.0, z=0.0, phase=Phase.FLIGHT)],
            summary=ShotSummary(carry_distance=250.0),
            launch_data=LaunchData(ball_speed=160.0),
            conditions=Conditions(),
        )

        # Old pattern: access summary and launch_data
        assert result.summary.carry_distance == 250.0
        assert result.launch_data.ball_speed == 160.0

        # Old pattern: iterate trajectory
        for point in result.trajectory:
            assert isinstance(point, TrajectoryPoint)
