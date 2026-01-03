# ABOUTME: Physics subpackage for Open Range trajectory simulation.
# ABOUTME: Contains aerodynamics, trajectory, ground physics, and constants.
"""Physics modules for golf ball trajectory simulation."""

from gc2_connect.open_range.physics.aerodynamics import (
    calculate_air_density,
    calculate_reynolds,
    get_drag_coefficient,
    get_lift_coefficient,
)

__all__ = [
    "calculate_air_density",
    "calculate_reynolds",
    "get_drag_coefficient",
    "get_lift_coefficient",
]
