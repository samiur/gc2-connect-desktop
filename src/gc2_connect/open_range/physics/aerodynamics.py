# ABOUTME: Aerodynamic coefficient calculations for golf ball simulation.
# ABOUTME: Based on WSU research data and libgolf reference implementation.
"""Aerodynamic calculations for golf ball physics.

This module implements:
- Reynolds number calculation
- Drag coefficient (Cd) with piecewise linear model and spin term
- Lift coefficient (Cl) using quadratic formula
- Air density with temperature, elevation, and humidity corrections

Based on:
- Professor Alan Nathan's trajectory calculator (UIUC)
- libgolf C++ reference implementation
- WSU Golf Ball Aerodynamics research
"""

from __future__ import annotations

import math

from gc2_connect.open_range.physics.constants import (
    BALL_DIAMETER_M,
    CD_HIGH,
    CD_LOW,
    CD_SPIN,
    CL_LINEAR,
    CL_MAX,
    CL_QUADRATIC,
    CL_SPIN_THRESHOLD,
    KINEMATIC_VISCOSITY,
    RE_HIGH,
    RE_LOW,
)


def calculate_reynolds(velocity_ms: float, air_density: float) -> float:  # noqa: ARG001
    """Calculate Reynolds number for golf ball at given velocity.

    The Reynolds number characterizes the flow regime around the ball.
    Formula: Re = V × D / ν

    Args:
        velocity_ms: Ball velocity in meters per second.
        air_density: Air density in kg/m³ (not used directly, kept for API
            consistency - kinematic viscosity is temperature-dependent but
            we use a constant approximation).

    Returns:
        Reynolds number (dimensionless).
    """
    # Re = V × D / ν
    # Using kinematic viscosity ν ≈ 1.5 × 10^-5 m²/s at standard conditions
    if velocity_ms <= 0:
        return 0.0

    return (velocity_ms * BALL_DIAMETER_M) / KINEMATIC_VISCOSITY


def get_drag_coefficient(reynolds: float, spin_factor: float = 0.0) -> float:
    """Get drag coefficient using piecewise linear model with spin term.

    The drag coefficient varies with Reynolds number due to the "drag crisis"
    effect where the boundary layer transitions from laminar to turbulent.

    Model:
    - Re < 0.5×10^5: Cd = 0.500 (laminar boundary layer)
    - Re > 1.0×10^5: Cd = 0.212 (turbulent boundary layer)
    - In between: Linear interpolation

    Additionally, spin adds to the drag via: Cd_spin = 0.15 × spin_factor

    Args:
        reynolds: Reynolds number (not in units of 10^5).
        spin_factor: Spin factor S = (ω × r) / V (dimensionless).

    Returns:
        Total drag coefficient Cd.
    """
    # Convert Reynolds to units of 10^5 for comparison with thresholds
    re = reynolds / 1e5

    # Piecewise linear base drag (drag crisis model)
    if re <= RE_LOW:
        base_cd = CD_LOW
    elif re >= RE_HIGH:
        base_cd = CD_HIGH
    else:
        # Linear interpolation in transition region
        t = (re - RE_LOW) / (RE_HIGH - RE_LOW)
        base_cd = CD_LOW + t * (CD_HIGH - CD_LOW)

    # Add spin-dependent drag
    total_cd = base_cd + CD_SPIN * spin_factor

    return total_cd


def get_lift_coefficient(spin_factor: float) -> float:
    """Get lift coefficient using quadratic formula.

    The lift coefficient depends on the spin factor S = (ω × r) / V.

    Formula: Cl = 1.990×S - 3.250×S²

    The coefficient is capped at CL_MAX (0.305) for spin factors above
    the threshold (0.30).

    Args:
        spin_factor: Spin factor S = (ω × r) / V (dimensionless).

    Returns:
        Lift coefficient Cl (dimensionless).
    """
    if spin_factor <= 0:
        return 0.0

    # Above threshold, Cl is capped at max value
    if spin_factor >= CL_SPIN_THRESHOLD:
        return CL_MAX

    # Quadratic formula: Cl = 1.990×S - 3.250×S²
    cl = CL_LINEAR * spin_factor + CL_QUADRATIC * spin_factor * spin_factor

    # Clamp to valid range (should not be negative for positive spin)
    return max(0.0, min(cl, CL_MAX))


def calculate_air_density(
    temp_f: float,
    elevation_ft: float,
    humidity_pct: float,
    pressure_inhg: float = 29.92,
) -> float:
    """Calculate air density with atmospheric corrections.

    Uses the ideal gas law with corrections for:
    - Temperature (warmer air is less dense)
    - Elevation (barometric formula for pressure reduction)
    - Humidity (water vapor is lighter than dry air)

    Args:
        temp_f: Temperature in degrees Fahrenheit.
        elevation_ft: Elevation above sea level in feet.
        humidity_pct: Relative humidity as a percentage (0-100).
        pressure_inhg: Barometric pressure in inches of mercury
            (default 29.92 = standard atmosphere).

    Returns:
        Air density in kg/m³.
    """
    # Convert temperature to Kelvin
    temp_c = (temp_f - 32.0) * 5.0 / 9.0
    temp_k = temp_c + 273.15

    # Pressure adjustment for elevation (barometric formula)
    # P = P0 × exp(-Mgh/RT) simplified to exp(-0.0001185 × h)
    elevation_m = elevation_ft * 0.3048
    pressure_pa = pressure_inhg * 3386.39  # inHg to Pa
    pressure_at_alt = pressure_pa * math.exp(-0.0001185 * elevation_m)

    # Saturation vapor pressure (Magnus formula)
    # es in hPa
    es = 6.1078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    # Actual vapor pressure
    e = (humidity_pct / 100.0) * es  # hPa
    e_pa = e * 100.0  # Convert to Pa

    # Air density using ideal gas law with humidity correction
    # ρ = (Pd × Md + Pv × Mv) / (R × T)
    # Simplified: ρ = Pd/(Rd×T) + Pv/(Rv×T)
    rd = 287.05  # Dry air gas constant (J/(kg·K))
    rv = 461.495  # Water vapor gas constant (J/(kg·K))

    # Partial pressure of dry air
    pd = pressure_at_alt - e_pa

    # Density = dry air component + water vapor component
    density = (pd / (rd * temp_k)) + (e_pa / (rv * temp_k))

    return density
