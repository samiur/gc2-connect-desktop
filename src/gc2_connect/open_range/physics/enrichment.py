# ABOUTME: Enrichment module for adding OpenGolfCoach derived values to shot results.
# ABOUTME: Provides factory function to enrich ShotResult with classification and metrics.
"""Enrichment module for OpenGolfCoach integration.

This module provides the enrich_shot_result() function that adds OpenGolfCoach
derived values (shot classification, ranking, distances) to a ShotResult.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gc2_connect.open_range.models import DerivedShotData, ShotResult
from gc2_connect.open_range.physics.opengolfcoach_wrapper import (
    calculate_shot_from_gc2,
    is_available,
)

if TYPE_CHECKING:
    from gc2_connect.models import GC2ShotData

logger = logging.getLogger(__name__)


def enrich_shot_result(result: ShotResult, gc2_shot: GC2ShotData) -> ShotResult:
    """Add OpenGolfCoach derived values to a ShotResult.

    This function takes an existing ShotResult (with trajectory from the physics
    engine) and enriches it with classification and metrics from OpenGolfCoach.

    Args:
        result: The ShotResult to enrich.
        gc2_shot: The original GC2 shot data for OpenGolfCoach calculation.

    Returns:
        A new ShotResult with the derived field populated, or the original
        result if OpenGolfCoach is unavailable or calculation fails.
    """
    if not is_available():
        logger.debug("OpenGolfCoach not available, returning original result")
        return result

    try:
        ogc_result = calculate_shot_from_gc2(gc2_shot)

        derived = DerivedShotData(
            shot_name=ogc_result.shot_name,
            shot_rank=ogc_result.shot_rank,
            shot_color_rgb=ogc_result.shot_color_rgb,
            smash_factor=ogc_result.smash_factor,
            estimated_club_speed_mph=ogc_result.club_speed_mph,
            estimated_club_path_deg=ogc_result.club_path_degrees,
            estimated_face_angle_deg=ogc_result.club_face_to_target_degrees,
            ogc_carry_distance=ogc_result.carry_distance_yards,
            ogc_total_distance=ogc_result.total_distance_yards,
        )

        return result.model_copy(update={"derived": derived})

    except Exception:
        logger.exception("Failed to enrich shot result with OpenGolfCoach data")
        return result
