# ABOUTME: Unit tests for OpenRangeEngine integration with OpenGolfCoach.
# ABOUTME: Tests that simulate_shot() returns results enriched with derived data.
"""Tests for OpenRangeEngine integration with OpenGolfCoach.

These tests verify that OpenRangeEngine correctly enriches shot results with
OpenGolfCoach derived values (shot classification, ranking, etc.) while
gracefully falling back when OpenGolfCoach is unavailable.
"""

from __future__ import annotations

import pytest


class TestSimulateShotWithDerivedData:
    """Tests for simulate_shot() returning results with derived data."""

    def test_simulate_shot_returns_result_with_derived_data(self) -> None:
        """Test simulate_shot() returns ShotResult with derived field populated."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=1.5,
            back_spin=2686.0,
            side_spin=-250.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        assert result.derived.shot_name != ""
        assert result.derived.shot_rank in ["S+", "S", "A", "B", "C", "D", "E"]
        assert result.derived.shot_color_rgb != ""

    def test_simulate_shot_derived_shot_name_populated(self) -> None:
        """Test that derived.shot_name is populated with a descriptive name."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=2.0,
            back_spin=2500.0,
            side_spin=200.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        assert result.derived.shot_name != "Unknown"

    def test_simulate_shot_derived_shot_rank_populated(self) -> None:
        """Test that derived.shot_rank is populated with a valid rank."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=120.0,
            launch_angle=16.0,
            horizontal_launch_angle=0.0,
            back_spin=7000.0,
            side_spin=-100.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        valid_ranks = ["S+", "S", "A", "B", "C", "D", "E"]
        assert result.derived.shot_rank in valid_ranks

    def test_simulate_shot_preserves_trajectory_from_physics_engine(self) -> None:
        """Test that trajectory still comes from physics engine, not OpenGolfCoach."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=0.0,
            back_spin=2686.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        # Trajectory should have multiple points from physics simulation
        assert len(result.trajectory) > 10
        # Should have valid phases
        from gc2_connect.open_range.models import Phase

        assert result.trajectory[0].phase == Phase.FLIGHT
        # Last point should be stopped
        assert result.trajectory[-1].phase == Phase.STOPPED

    def test_simulate_shot_populates_ogc_distances(self) -> None:
        """Test that derived data includes OGC carry and total distances."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=0.0,
            back_spin=2686.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        assert result.derived.ogc_carry_distance > 200  # Driver should carry 200+ yards
        assert result.derived.ogc_total_distance is not None
        assert result.derived.ogc_total_distance >= result.derived.ogc_carry_distance


class TestSimulateManualWithDerivedData:
    """Tests for simulate_manual() returning results with derived data."""

    def test_simulate_manual_returns_result_with_derived_data(self) -> None:
        """Test simulate_manual() returns ShotResult with derived field populated."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        result = engine.simulate_manual(
            ball_speed_mph=161.0,
            vla_deg=12.0,
            hla_deg=2.0,
            backspin_rpm=2500.0,
            sidespin_rpm=200.0,
        )

        assert result.derived is not None
        assert result.derived.shot_name != ""
        assert result.derived.shot_rank in ["S+", "S", "A", "B", "C", "D", "E"]

    def test_simulate_manual_derived_matches_shot_parameters(self) -> None:
        """Test simulate_manual() derived data reflects the input parameters."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        # 7-iron like shot
        result = engine.simulate_manual(
            ball_speed_mph=120.0,
            vla_deg=18.0,
            hla_deg=0.0,
            backspin_rpm=7000.0,
            sidespin_rpm=0.0,
        )

        assert result.derived is not None
        # OGC distance should be reasonable for a 7-iron (140-180 yards)
        assert result.derived.ogc_carry_distance is not None
        assert 100 < result.derived.ogc_carry_distance < 200


class TestGracefulFallback:
    """Tests for graceful fallback when OpenGolfCoach is unavailable."""

    def test_simulate_shot_works_when_opengolfcoach_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test simulate_shot() works when OpenGolfCoach is not installed."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range import engine as engine_module
        from gc2_connect.open_range.engine import OpenRangeEngine

        # Mock is_available to return False
        monkeypatch.setattr(engine_module, "OPENGOLFCOACH_AVAILABLE", False)

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=1.5,
            back_spin=2686.0,
            side_spin=-250.0,
        )

        result = engine.simulate_shot(gc2_shot)

        # Should still have valid trajectory and summary from physics engine
        assert len(result.trajectory) > 0
        assert result.summary.carry_distance > 0
        # Derived should be None when OGC unavailable
        assert result.derived is None

    def test_simulate_shot_fallback_on_opengolfcoach_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test simulate_shot() gracefully handles OpenGolfCoach errors."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range import engine as engine_module
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics import enrichment

        # Make sure OGC is "available" but calculation fails
        monkeypatch.setattr(engine_module, "OPENGOLFCOACH_AVAILABLE", True)

        def mock_enrich_error(
            _result: engine_module.ShotResult, _gc2_shot: GC2ShotData
        ) -> engine_module.ShotResult:
            raise RuntimeError("Mock OpenGolfCoach error")

        monkeypatch.setattr(enrichment, "enrich_shot_result", mock_enrich_error)

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=1.5,
            back_spin=2686.0,
            side_spin=-250.0,
        )

        # Should not raise, should return result without derived
        result = engine.simulate_shot(gc2_shot)

        assert len(result.trajectory) > 0
        assert result.summary.carry_distance > 0
        assert result.derived is None

    def test_simulate_manual_works_when_opengolfcoach_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test simulate_manual() works when OpenGolfCoach is not installed."""
        from gc2_connect.open_range import engine as engine_module
        from gc2_connect.open_range.engine import OpenRangeEngine

        monkeypatch.setattr(engine_module, "OPENGOLFCOACH_AVAILABLE", False)

        engine = OpenRangeEngine()
        result = engine.simulate_manual(
            ball_speed_mph=161.0,
            vla_deg=12.0,
            hla_deg=2.0,
            backspin_rpm=2500.0,
            sidespin_rpm=200.0,
        )

        # Should still work with physics engine
        assert len(result.trajectory) > 0
        assert result.summary.carry_distance > 0
        assert result.derived is None


class TestSimulateTestShot:
    """Tests for simulate_test_shot() with derived data."""

    def test_simulate_test_shot_includes_derived_data(self) -> None:
        """Test simulate_test_shot() returns result with derived data."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        result = engine.simulate_test_shot(club="Driver")

        assert result.derived is not None
        assert result.derived.shot_name != ""
        assert result.derived.shot_rank in ["S+", "S", "A", "B", "C", "D", "E"]

    def test_simulate_test_shot_driver_has_reasonable_derived_distances(self) -> None:
        """Test simulate_test_shot() with Driver has reasonable OGC distances."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        result = engine.simulate_test_shot(club="Driver")

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        # Driver should carry 200+ yards
        assert result.derived.ogc_carry_distance > 200

    def test_simulate_test_shot_7iron_has_reasonable_derived_distances(self) -> None:
        """Test simulate_test_shot() with 7-Iron has reasonable OGC distances."""
        from gc2_connect.open_range.engine import OpenRangeEngine
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        if not is_available():
            pytest.skip("OpenGolfCoach not available")

        engine = OpenRangeEngine()
        result = engine.simulate_test_shot(club="7-Iron")

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        # 7-Iron should carry 140-180 yards
        assert 100 < result.derived.ogc_carry_distance < 200


class TestAPIBackwardsCompatibility:
    """Tests ensuring backwards compatibility of the engine API."""

    def test_simulate_shot_api_unchanged(self) -> None:
        """Test that simulate_shot() API signature is unchanged."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=2500.0,
            side_spin=0.0,
        )

        # Should accept single GC2ShotData argument
        result = engine.simulate_shot(gc2_shot)

        # Should return ShotResult with expected fields
        assert hasattr(result, "trajectory")
        assert hasattr(result, "summary")
        assert hasattr(result, "launch_data")
        assert hasattr(result, "conditions")
        assert hasattr(result, "derived")  # New field, but optional

    def test_simulate_manual_api_unchanged(self) -> None:
        """Test that simulate_manual() API signature is unchanged."""
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Should accept the same parameters as before
        result = engine.simulate_manual(
            ball_speed_mph=161.0,
            vla_deg=12.0,
            hla_deg=0.0,
            backspin_rpm=2500.0,
            sidespin_rpm=0.0,
        )

        assert hasattr(result, "trajectory")
        assert hasattr(result, "summary")

    def test_existing_code_pattern_works(self) -> None:
        """Test that existing code patterns continue to work."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=161.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=2500.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        # Existing code would access these fields
        assert result.summary.carry_distance > 0
        # With OGC targeting, total can equal carry when OGC predicts minimal roll
        assert result.summary.total_distance >= result.summary.carry_distance
        assert len(result.trajectory) > 0
        assert result.launch_data.ball_speed == 161.0
