# ABOUTME: Validation tests comparing OpenGolfCoach distances with physics engine.
# ABOUTME: Ensures both engines produce distances within 15% tolerance for various clubs.
"""Tests comparing OpenGolfCoach distances with our physics engine.

These tests validate that the OpenGolfCoach library and our custom physics engine
produce consistent distance results within an acceptable tolerance (15%). This
ensures reliable shot simulation regardless of which engine calculates the distance.

Tests cover:
- Driver shots (high speed, low spin, low launch)
- 7-Iron shots (medium speed, medium spin, medium launch)
- Wedge shots (low speed, high spin, high launch)
"""

from __future__ import annotations

import pytest

# Skip marker for when OpenGolfCoach is not installed
requires_opengolfcoach = pytest.mark.skipif(
    "not config.getoption('--run-ogc', default=False)",
)


def ogc_available() -> bool:
    """Check if OpenGolfCoach is available for tests."""
    try:
        from gc2_connect.open_range.physics.opengolfcoach_wrapper import is_available

        return is_available()
    except ImportError:
        return False


class TestDriverShotComparison:
    """Tests comparing driver shot distances between engines."""

    def test_driver_carry_distance_within_tolerance(self) -> None:
        """Test that driver carry distances are within 15% tolerance."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Typical driver shot: 167 mph ball speed, 10.9° launch, 2686 rpm backspin
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=167.0,
            launch_angle=10.9,
            horizontal_launch_angle=0.0,
            back_spin=2686.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        # Physics engine carry distance
        physics_carry = result.summary.carry_distance

        # OpenGolfCoach carry distance
        assert result.derived is not None, "OpenGolfCoach derived data missing"
        assert result.derived.ogc_carry_distance is not None, "OGC carry distance missing"
        ogc_carry = result.derived.ogc_carry_distance

        # Calculate percentage difference
        diff_pct = abs(physics_carry - ogc_carry) / ogc_carry * 100

        # Log comparison for debugging
        _log_distance_comparison("Driver (carry)", physics_carry, ogc_carry, diff_pct)

        # Assert within 15% tolerance
        assert diff_pct <= 15.0, (
            f"Driver carry distance difference too large: {diff_pct:.1f}% "
            f"(physics={physics_carry:.1f}yd, ogc={ogc_carry:.1f}yd)"
        )

    def test_driver_total_distance_logged(self) -> None:
        """Test that driver total distances are logged for comparison.

        Note: Total distance includes roll, which varies significantly between
        engines due to different ground physics models. We use a 35% tolerance
        here (vs 15% for carry) since roll calculation is less standardized.
        The physics engine simulates detailed bounce/roll while OGC uses estimates.
        """
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

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

        physics_total = result.summary.total_distance

        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None
        ogc_total = result.derived.ogc_total_distance

        diff_pct = abs(physics_total - ogc_total) / ogc_total * 100

        _log_distance_comparison("Driver (total)", physics_total, ogc_total, diff_pct)

        # Relaxed tolerance for total distance due to ground physics variations
        assert diff_pct <= 35.0, (
            f"Driver total distance difference too large: {diff_pct:.1f}% "
            f"(physics={physics_total:.1f}yd, ogc={ogc_total:.1f}yd)"
        )

    def test_driver_reasonable_carry_range(self) -> None:
        """Test that driver carry is in a reasonable range (230-290 yards)."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

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

        # Both engines should produce reasonable driver distance
        assert (
            230 <= result.summary.carry_distance <= 290
        ), f"Physics engine carry out of range: {result.summary.carry_distance:.1f}yd"

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        assert (
            230 <= result.derived.ogc_carry_distance <= 290
        ), f"OGC carry out of range: {result.derived.ogc_carry_distance:.1f}yd"


class TestSevenIronShotComparison:
    """Tests comparing 7-iron shot distances between engines."""

    def test_7iron_carry_distance_within_tolerance(self) -> None:
        """Test that 7-iron carry distances are within 15% tolerance."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Typical 7-iron shot: 120 mph ball speed, 16.3° launch, 7097 rpm backspin
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=120.0,
            launch_angle=16.3,
            horizontal_launch_angle=0.0,
            back_spin=7097.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        physics_carry = result.summary.carry_distance

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        ogc_carry = result.derived.ogc_carry_distance

        diff_pct = abs(physics_carry - ogc_carry) / ogc_carry * 100

        _log_distance_comparison("7-Iron (carry)", physics_carry, ogc_carry, diff_pct)

        assert diff_pct <= 15.0, (
            f"7-Iron carry distance difference too large: {diff_pct:.1f}% "
            f"(physics={physics_carry:.1f}yd, ogc={ogc_carry:.1f}yd)"
        )

    def test_7iron_total_distance_logged(self) -> None:
        """Test that 7-iron total distances are logged for comparison.

        Note: Total distance includes roll, which varies significantly between
        engines. 7-irons have higher spin which affects roll differently in each
        model. We use a 35% tolerance for total distance comparisons.
        """
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=120.0,
            launch_angle=16.3,
            horizontal_launch_angle=0.0,
            back_spin=7097.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        physics_total = result.summary.total_distance

        assert result.derived is not None
        assert result.derived.ogc_total_distance is not None
        ogc_total = result.derived.ogc_total_distance

        diff_pct = abs(physics_total - ogc_total) / ogc_total * 100

        _log_distance_comparison("7-Iron (total)", physics_total, ogc_total, diff_pct)

        # Relaxed tolerance for total distance due to ground physics variations
        assert diff_pct <= 35.0, (
            f"7-Iron total distance difference too large: {diff_pct:.1f}% "
            f"(physics={physics_total:.1f}yd, ogc={ogc_total:.1f}yd)"
        )

    def test_7iron_reasonable_carry_range(self) -> None:
        """Test that 7-iron carry is in a reasonable range (140-180 yards)."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=120.0,
            launch_angle=16.3,
            horizontal_launch_angle=0.0,
            back_spin=7097.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert (
            140 <= result.summary.carry_distance <= 180
        ), f"Physics engine carry out of range: {result.summary.carry_distance:.1f}yd"

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        assert (
            140 <= result.derived.ogc_carry_distance <= 180
        ), f"OGC carry out of range: {result.derived.ogc_carry_distance:.1f}yd"


class TestWedgeShotComparison:
    """Tests comparing wedge shot distances between engines."""

    def test_pw_carry_distance_within_tolerance(self) -> None:
        """Test that PW carry distances are within 15% tolerance."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Typical PW shot: 102 mph ball speed, 24.2° launch, 9304 rpm backspin
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=102.0,
            launch_angle=24.2,
            horizontal_launch_angle=0.0,
            back_spin=9304.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        physics_carry = result.summary.carry_distance

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        ogc_carry = result.derived.ogc_carry_distance

        diff_pct = abs(physics_carry - ogc_carry) / ogc_carry * 100

        _log_distance_comparison("PW (carry)", physics_carry, ogc_carry, diff_pct)

        assert diff_pct <= 15.0, (
            f"PW carry distance difference too large: {diff_pct:.1f}% "
            f"(physics={physics_carry:.1f}yd, ogc={ogc_carry:.1f}yd)"
        )

    def test_sw_carry_distance_within_tolerance(self) -> None:
        """Test that SW carry distances are within 15% tolerance."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Typical SW shot: 85 mph ball speed, 30° launch, 10000 rpm backspin
        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=85.0,
            launch_angle=30.0,
            horizontal_launch_angle=0.0,
            back_spin=10000.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        physics_carry = result.summary.carry_distance

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        ogc_carry = result.derived.ogc_carry_distance

        diff_pct = abs(physics_carry - ogc_carry) / ogc_carry * 100

        _log_distance_comparison("SW (carry)", physics_carry, ogc_carry, diff_pct)

        assert diff_pct <= 15.0, (
            f"SW carry distance difference too large: {diff_pct:.1f}% "
            f"(physics={physics_carry:.1f}yd, ogc={ogc_carry:.1f}yd)"
        )

    def test_wedge_reasonable_carry_range(self) -> None:
        """Test that PW carry is in a reasonable range (100-140 yards)."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        gc2_shot = GC2ShotData(
            shot_id=1,
            ball_speed=102.0,
            launch_angle=24.2,
            horizontal_launch_angle=0.0,
            back_spin=9304.0,
            side_spin=0.0,
        )

        result = engine.simulate_shot(gc2_shot)

        assert (
            100 <= result.summary.carry_distance <= 140
        ), f"Physics engine carry out of range: {result.summary.carry_distance:.1f}yd"

        assert result.derived is not None
        assert result.derived.ogc_carry_distance is not None
        assert (
            100 <= result.derived.ogc_carry_distance <= 140
        ), f"OGC carry out of range: {result.derived.ogc_carry_distance:.1f}yd"


class TestMultipleClubsComparison:
    """Tests comparing multiple clubs in batch for consistency."""

    def test_all_clubs_within_tolerance(self) -> None:
        """Test that all club profiles produce distances within tolerance."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.open_range.engine import CLUB_PROFILES, OpenRangeEngine

        engine = OpenRangeEngine()

        # Track failures for comprehensive reporting
        failures: list[str] = []
        comparisons: list[dict[str, float | str]] = []

        for club_name, (ball_speed, vla, backspin, _variance) in CLUB_PROFILES.items():
            result = engine.simulate_manual(
                ball_speed_mph=ball_speed,
                vla_deg=vla,
                hla_deg=0.0,
                backspin_rpm=backspin,
                sidespin_rpm=0.0,
            )

            if result.derived is None or result.derived.ogc_carry_distance is None:
                failures.append(f"{club_name}: OGC data missing")
                continue

            physics_carry = result.summary.carry_distance
            ogc_carry = result.derived.ogc_carry_distance

            # Avoid division by zero
            if ogc_carry == 0:
                failures.append(f"{club_name}: OGC carry is zero")
                continue

            diff_pct = abs(physics_carry - ogc_carry) / ogc_carry * 100

            comparisons.append(
                {
                    "club": club_name,
                    "physics": physics_carry,
                    "ogc": ogc_carry,
                    "diff_pct": diff_pct,
                }
            )

            if diff_pct > 15.0:
                failures.append(
                    f"{club_name}: {diff_pct:.1f}% diff "
                    f"(physics={physics_carry:.1f}yd, ogc={ogc_carry:.1f}yd)"
                )

        # Log all comparisons
        _log_comparison_table(comparisons)

        # Assert no failures
        assert not failures, "Clubs with >15% difference:\n" + "\n".join(failures)

    def test_distance_ordering_matches(self) -> None:
        """Test that club distance ordering is consistent between engines."""
        if not ogc_available():
            pytest.skip("OpenGolfCoach not available")

        from gc2_connect.open_range.engine import OpenRangeEngine

        engine = OpenRangeEngine()

        # Test three clubs that should have clearly different distances
        clubs = ["Driver", "7-Iron", "SW"]
        physics_distances: list[float] = []
        ogc_distances: list[float] = []

        for club in clubs:
            result = engine.simulate_test_shot(club=club)

            physics_distances.append(result.summary.carry_distance)

            if result.derived is not None and result.derived.ogc_carry_distance is not None:
                ogc_distances.append(result.derived.ogc_carry_distance)

        # Skip if OGC not available for all clubs
        if len(ogc_distances) != len(clubs):
            pytest.skip("OGC distances not available for all clubs")

        # Both engines should have Driver > 7-Iron > SW
        assert (
            physics_distances[0] > physics_distances[1] > physics_distances[2]
        ), f"Physics distance ordering wrong: {physics_distances}"
        assert (
            ogc_distances[0] > ogc_distances[1] > ogc_distances[2]
        ), f"OGC distance ordering wrong: {ogc_distances}"


class TestGracefulSkipping:
    """Tests verifying graceful behavior when OpenGolfCoach is not available."""

    def test_comparison_skips_when_ogc_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that comparison tests skip gracefully when OGC unavailable."""
        from gc2_connect.open_range.physics import opengolfcoach_wrapper

        # Mock is_available to return False
        monkeypatch.setattr(opengolfcoach_wrapper, "_OPENGOLFCOACH_AVAILABLE", False)

        # Our ogc_available() function should now return False
        assert not ogc_available()

    def test_physics_engine_works_without_ogc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test physics engine still works when OGC is unavailable."""
        from gc2_connect.models import GC2ShotData
        from gc2_connect.open_range import engine as engine_module
        from gc2_connect.open_range.engine import OpenRangeEngine

        # Disable OGC
        monkeypatch.setattr(engine_module, "OPENGOLFCOACH_AVAILABLE", False)

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

        # Physics engine should still produce valid results
        assert result.summary.carry_distance > 200
        assert len(result.trajectory) > 10
        # Derived should be None
        assert result.derived is None


def _log_distance_comparison(shot_type: str, physics: float, ogc: float, diff_pct: float) -> None:
    """Log distance comparison for debugging.

    Args:
        shot_type: Description of the shot type.
        physics: Distance from physics engine (yards).
        ogc: Distance from OpenGolfCoach (yards).
        diff_pct: Percentage difference.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"{shot_type}: physics={physics:.1f}yd, ogc={ogc:.1f}yd, diff={diff_pct:.1f}%")


def _log_comparison_table(comparisons: list[dict[str, float | str]]) -> None:
    """Log a table of all club comparisons.

    Args:
        comparisons: List of comparison dictionaries.
    """
    import logging

    logger = logging.getLogger(__name__)

    if not comparisons:
        return

    logger.info("\n=== Physics vs OpenGolfCoach Comparison ===")
    logger.info(f"{'Club':<12} {'Physics':>10} {'OGC':>10} {'Diff %':>8}")
    logger.info("-" * 44)

    for comp in comparisons:
        logger.info(
            f"{comp['club']:<12} {comp['physics']:>10.1f} {comp['ogc']:>10.1f} {comp['diff_pct']:>7.1f}%"
        )
