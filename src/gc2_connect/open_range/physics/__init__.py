# ABOUTME: Physics subpackage for Open Range trajectory simulation.
# ABOUTME: Contains aerodynamics, trajectory, ground physics, and constants.
"""Physics modules for golf ball trajectory simulation."""

from gc2_connect.open_range.physics.aerodynamics import (
    calculate_air_density,
    calculate_reynolds,
    get_drag_coefficient,
    get_lift_coefficient,
)
from gc2_connect.open_range.physics.trajectory import (
    FlightSimulator,
    SimulationState,
    calculate_initial_velocity,
    deg_to_rad,
    feet_to_meters,
    meters_to_feet,
    meters_to_yards,
    mph_to_ms,
    ms_to_mph,
    rad_to_deg,
    rpm_to_rad_s,
    yards_to_meters,
)

__all__ = [
    # Aerodynamics
    "calculate_air_density",
    "calculate_reynolds",
    "get_drag_coefficient",
    "get_lift_coefficient",
    # Trajectory
    "FlightSimulator",
    "SimulationState",
    "calculate_initial_velocity",
    # Unit conversions
    "deg_to_rad",
    "feet_to_meters",
    "meters_to_feet",
    "meters_to_yards",
    "mph_to_ms",
    "ms_to_mph",
    "rad_to_deg",
    "rpm_to_rad_s",
    "yards_to_meters",
]
