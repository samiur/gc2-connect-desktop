# ABOUTME: Physical constants for Open Range golf ball simulation.
# ABOUTME: Based on Nathan model, libgolf reference, and docs/PHYSICS.md specifications.
"""Physical constants for golf ball trajectory simulation.

Based on:
- Professor Alan Nathan's trajectory calculator (UIUC)
- libgolf C++ reference implementation (https://github.com/gdifiore/libgolf)
- WSU Golf Ball Aerodynamics research
- USGA Ball Specifications
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# =============================================================================
# Ball Properties (USGA Specifications)
# =============================================================================

# Mass: 1.620 oz maximum = 0.04593 kg
BALL_MASS_KG: float = 0.04593

# Diameter: 1.680 inches minimum = 0.04267 m
BALL_DIAMETER_M: float = 0.04267
BALL_RADIUS_M: float = BALL_DIAMETER_M / 2.0  # 0.021335 m

# Cross-sectional area = π × r²
BALL_AREA_M2: float = math.pi * BALL_RADIUS_M * BALL_RADIUS_M  # ≈ 0.001430 m²


# =============================================================================
# Standard Atmosphere
# =============================================================================

STD_TEMP_F: float = 70.0  # 21.1°C
STD_ELEVATION_FT: float = 0.0  # Sea level
STD_HUMIDITY_PCT: float = 50.0
STD_PRESSURE_INHG: float = 29.92  # 1013.25 hPa
STD_AIR_DENSITY: float = 1.194  # kg/m³


# =============================================================================
# Physics Constants
# =============================================================================

GRAVITY_MS2: float = 9.81  # m/s²
SPIN_DECAY_RATE: float = 0.01  # Per second (1%)
KINEMATIC_VISCOSITY: float = 1.5e-5  # m²/s at standard conditions


# =============================================================================
# Drag Coefficient Constants (from libgolf)
# =============================================================================

# Piecewise linear drag model based on Reynolds number
CD_LOW: float = 0.500  # Low Reynolds (Re < 0.5×10^5)
CD_HIGH: float = 0.212  # High Reynolds (Re > 1.0×10^5)
CD_SPIN: float = 0.15  # Spin-dependent drag coefficient

# Reynolds number thresholds (in units of 10^5)
RE_LOW: float = 0.5  # Low Reynolds threshold
RE_HIGH: float = 1.0  # High Reynolds threshold


# =============================================================================
# Lift Coefficient Constants (from libgolf quadratic formula)
# =============================================================================

# Quadratic formula: Cl = 1.990×S - 3.250×S²
CL_LINEAR: float = 1.990  # Linear term coefficient
CL_QUADRATIC: float = -3.250  # Quadratic term coefficient
CL_MAX: float = 0.305  # Maximum lift coefficient
CL_SPIN_THRESHOLD: float = 0.30  # Spin factor where Cl maxes out


# =============================================================================
# Simulation Parameters
# =============================================================================

DT: float = 0.01  # Time step in seconds (10ms)
MAX_TIME: float = 30.0  # Maximum simulation time in seconds
MAX_ITERATIONS: int = 3000  # Safety limit on iterations
MAX_TRAJECTORY_POINTS: int = 600  # Memory limit on stored points
STOPPED_THRESHOLD: float = 0.1  # Velocity below which ball is "stopped" (m/s)
MAX_BOUNCES: int = 5  # Maximum number of bounces before forcing roll


# =============================================================================
# Ground Surface Properties
# =============================================================================


@dataclass(frozen=True)
class GroundSurface:
    """Properties of a ground surface type."""

    name: str
    cor: float  # Coefficient of Restitution (0-1)
    rolling_resistance: float  # Deceleration factor
    friction: float  # Tangential friction on bounce


# Surface definitions matching docs/PHYSICS.md
SURFACES: dict[str, GroundSurface] = {
    "Fairway": GroundSurface(
        name="Fairway",
        cor=0.60,
        rolling_resistance=0.10,
        friction=0.50,
    ),
    "Green": GroundSurface(
        name="Green",
        cor=0.40,
        rolling_resistance=0.05,
        friction=0.30,
    ),
    "Rough": GroundSurface(
        name="Rough",
        cor=0.30,
        rolling_resistance=0.30,
        friction=0.70,
    ),
}
