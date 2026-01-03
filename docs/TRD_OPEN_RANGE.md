# Technical Requirements Document (TRD)
# GC2 Connect Desktop - Open Range Feature

## Overview

### Document Purpose
This document defines the technical architecture, implementation details, and integration requirements for adding the Open Range driving range simulator to GC2 Connect Desktop.

### Version
1.1.0

### Last Updated
December 2024

### Parent Document
GC2 Connect Desktop TRD v1.0.0

---

## System Architecture

### Extended High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           GC2 Connect Desktop v1.1                                │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────────────────────┐  │
│  │   UI Layer   │    │   Service    │    │       Communication Layer          │  │
│  │   (NiceGUI)  │◄──►│   Layer      │◄──►│                                    │  │
│  │              │    │              │    │  ┌────────┐ ┌──────────┐           │  │
│  │ • Mode       │    │ • AppState   │    │  │ GC2    │ │ GSPro    │           │  │
│  │   Selector   │    │ • ShotMgr    │    │  │ USB    │ │ TCP      │           │  │
│  │ • GSPro      │    │ • Config     │    │  │ Reader │ │ Client   │           │  │
│  │   Panel      │    │ • Router  ◄──┼────┼──┴────┬───┘ └────┬─────┘           │  │
│  │ • Open Range │    │              │    │       │          │                 │  │
│  │   View    ◄──┼────┼──────────────┼────┼───────┼──────────┘                 │  │
│  └──────────────┘    └──────────────┘    └───────┼────────────────────────────┘  │
│         │                   │                    │                                │
│         │            ┌──────┴──────┐             │                                │
│         │            │  Open Range │             │                                │
│         │            │   Engine    │             │                                │
│         │            │             │             │                                │
│         │            │ • Physics   │             │                                │
│         └────────────► • 3D Render │             │                                │
│                      │ • Animation │             │                                │
│                      └─────────────┘             │                                │
│                                                  │                                │
└──────────────────────────────────────────────────┼────────────────────────────────┘
                                             USB   │
                                                   ▼
                                         ┌─────────────┐
                                         │ Foresight   │
                                         │ GC2         │
                                         └─────────────┘
```

### Component Changes

#### New Components
1. **Mode Router**: Directs shot data to either GSPro client or Open Range engine
2. **Open Range Engine**: Physics simulation and visualization
3. **3D Renderer**: Three.js-based driving range visualization

#### Modified Components
1. **AppState**: Extended with mode selection and Open Range state
2. **ShotManager**: Routes shots based on active mode
3. **UI Layer**: Mode selector and Open Range view panel

---

## Extended Directory Structure

```
gc2-connect-desktop/
├── ... (existing files)
├── src/
│   └── gc2_connect/
│       ├── ... (existing modules)
│       │
│       ├── open_range/                    # NEW: Open Range feature
│       │   ├── __init__.py
│       │   ├── engine.py                  # Main Open Range engine
│       │   ├── physics/
│       │   │   ├── __init__.py
│       │   │   ├── constants.py           # Physical constants
│       │   │   ├── aerodynamics.py        # Cd/Cl calculations
│       │   │   ├── trajectory.py          # RK4 integration, ball flight
│       │   │   ├── ground.py              # Bounce and roll physics
│       │   │   └── atmospheric.py         # Air density, wind
│       │   ├── visualization/
│       │   │   ├── __init__.py
│       │   │   ├── range_scene.py         # 3D scene setup
│       │   │   ├── ball_animation.py      # Ball flight animation
│       │   │   └── ui_overlay.py          # Data display overlays
│       │   └── models.py                  # Open Range data models
│       │
│       ├── ui/
│       │   ├── ... (existing)
│       │   ├── components/
│       │   │   ├── ... (existing)
│       │   │   ├── mode_selector.py       # NEW: Mode toggle component
│       │   │   └── open_range_view.py     # NEW: Open Range 3D view
│       │   └── app.py                     # MODIFIED: Add mode routing
│       │
│       └── services/
│           ├── ... (existing)
│           └── shot_router.py             # NEW: Route shots by mode
│
└── tests/
    ├── ... (existing)
    └── test_open_range/
        ├── test_physics.py
        ├── test_trajectory.py
        └── test_ground.py
```

---

## Module Specifications

### open_range/models.py - Data Models

```python
from pydantic import BaseModel
from typing import Optional, Literal
from enum import Enum

class Phase(str, Enum):
    FLIGHT = "flight"
    BOUNCE = "bounce"
    ROLLING = "rolling"
    STOPPED = "stopped"

class Vec3(BaseModel):
    """3D vector"""
    x: float
    y: float
    z: float

class TrajectoryPoint(BaseModel):
    """Single point in ball trajectory"""
    t: float           # Time (seconds)
    x: float           # Forward distance (yards)
    y: float           # Height (feet)
    z: float           # Lateral distance (yards)
    phase: Phase

class ShotResult(BaseModel):
    """Complete simulation result"""
    trajectory: list[TrajectoryPoint]
    summary: "ShotSummary"
    launch_data: "LaunchData"
    conditions: "Conditions"

class ShotSummary(BaseModel):
    """Shot outcome metrics"""
    carry_distance: float      # yards
    total_distance: float      # yards
    roll_distance: float       # yards
    offline_distance: float    # yards (+ right, - left)
    max_height: float          # feet
    max_height_time: float     # seconds
    flight_time: float         # seconds
    total_time: float          # seconds
    bounce_count: int

class LaunchData(BaseModel):
    """Input launch conditions"""
    ball_speed: float          # mph
    vla: float                 # vertical launch angle (degrees)
    hla: float                 # horizontal launch angle (degrees)
    backspin: float            # rpm
    sidespin: float            # rpm

class Conditions(BaseModel):
    """Environmental conditions"""
    temp_f: float = 70.0
    elevation_ft: float = 0.0
    humidity_pct: float = 50.0
    wind_speed_mph: float = 0.0
    wind_dir_deg: float = 0.0
    air_density: float = 1.194
    surface: str = "Fairway"

class GroundSurface(BaseModel):
    """Ground surface properties"""
    name: str
    coefficient_of_restitution: float  # 0-1, bounce height
    rolling_resistance: float           # deceleration factor
    friction_coefficient: float         # tangential friction
```

### open_range/physics/constants.py - Physical Constants

```python
"""
Physical constants for golf ball simulation.
Based on USGA specifications and Prof. Nathan's research.
"""

# Ball properties (USGA specifications)
BALL_MASS_KG = 0.04593           # 1.62 oz
BALL_DIAMETER_M = 0.04267        # 42.67mm (minimum)
BALL_RADIUS_M = 0.021335
BALL_AREA_M2 = 3.14159 * BALL_RADIUS_M ** 2

# Standard atmosphere
STD_TEMP_F = 70.0
STD_ELEVATION_FT = 0.0
STD_HUMIDITY_PCT = 50.0
STD_PRESSURE_INHG = 29.92
STD_AIR_DENSITY_KGM3 = 1.194     # From Nathan spreadsheet

# Physics
GRAVITY_MS2 = 9.81

# Simulation parameters
DT = 0.02                        # Time step (seconds)
MAX_TIME = 30.0                  # Maximum simulation time
MAX_ITERATIONS = 1500            # Safety limit
MAX_TRAJECTORY_POINTS = 600      # Memory safety

# Spin decay
SPIN_DECAY_RATE = 0.01           # Per second

# Drag coefficient table (WSU data via Nathan)
# Reynolds number in units of 10^5
CD_TABLE = [
    (0.375, 1.945),   # 30 mph - subcritical
    (0.500, 1.945),   # 40 mph
    (0.625, 1.492),   # 50 mph - transition
    (0.750, 1.039),   # 60 mph
    (0.875, 0.586),   # 70 mph - drag crisis
    (1.000, 0.132),   # 80 mph - supercritical
]

CD_HIGH = 0.132  # Turbulent regime value

# Lift coefficient table (WSU data)
# S = spin factor = (ω × r) / v
CL_TABLE = [
    (0.00, 0.000),
    (0.05, 0.069),
    (0.10, 0.091),
    (0.15, 0.107),
    (0.20, 0.121),
    (0.25, 0.132),
    (0.30, 0.142),
    (0.35, 0.151),
    (0.40, 0.159),
    (0.45, 0.167),
    (0.50, 0.174),
    (0.55, 0.181),
]

# Ground surfaces (from libgolf)
SURFACES = {
    "Fairway": {
        "coefficient_of_restitution": 0.6,
        "rolling_resistance": 0.10,
        "friction_coefficient": 0.5,
    },
    "Rough": {
        "coefficient_of_restitution": 0.3,
        "rolling_resistance": 0.30,
        "friction_coefficient": 0.7,
    },
    "Green": {
        "coefficient_of_restitution": 0.4,
        "rolling_resistance": 0.05,
        "friction_coefficient": 0.3,
    },
    "Bunker": {
        "coefficient_of_restitution": 0.2,
        "rolling_resistance": 0.50,
        "friction_coefficient": 0.8,
    },
}
```

### open_range/physics/aerodynamics.py - Aerodynamic Calculations

```python
"""
Aerodynamic coefficient calculations based on WSU research.
"""
import math
from .constants import (
    CD_TABLE, CD_HIGH, CL_TABLE,
    BALL_DIAMETER_M, STD_AIR_DENSITY_KGM3
)

def calculate_reynolds(velocity: float, air_density: float) -> float:
    """
    Calculate Reynolds number.
    
    Args:
        velocity: Ball speed (m/s)
        air_density: Air density (kg/m³)
    
    Returns:
        Reynolds number in units of 10^5
    """
    dynamic_viscosity = 1.81e-5  # kg/(m·s) at ~20°C
    Re = (air_density * velocity * BALL_DIAMETER_M) / dynamic_viscosity
    return Re / 1e5

def get_drag_coefficient(Re: float) -> float:
    """
    Get drag coefficient from Reynolds number via interpolation.
    
    Uses WSU experimental data showing drag crisis transition.
    
    Args:
        Re: Reynolds number in units of 10^5
    
    Returns:
        Drag coefficient Cd
    """
    # Below table range
    if Re <= CD_TABLE[0][0]:
        return CD_TABLE[0][1]
    
    # Above table range (constant in turbulent regime)
    if Re >= CD_TABLE[-1][0]:
        return CD_HIGH
    
    # Linear interpolation
    for i in range(len(CD_TABLE) - 1):
        if CD_TABLE[i][0] <= Re < CD_TABLE[i + 1][0]:
            t = (Re - CD_TABLE[i][0]) / (CD_TABLE[i + 1][0] - CD_TABLE[i][0])
            return CD_TABLE[i][1] + t * (CD_TABLE[i + 1][1] - CD_TABLE[i][1])
    
    return CD_HIGH

def get_lift_coefficient(S: float) -> float:
    """
    Get lift coefficient from spin factor via interpolation.
    
    Args:
        S: Spin factor = (ω × r) / v
    
    Returns:
        Lift coefficient Cl
    """
    if S <= 0:
        return 0.0
    if S > 0.55:
        S = 0.55  # Cap at measured range
    
    # Linear interpolation
    for i in range(len(CL_TABLE) - 1):
        if CL_TABLE[i][0] <= S < CL_TABLE[i + 1][0]:
            t = (S - CL_TABLE[i][0]) / (CL_TABLE[i + 1][0] - CL_TABLE[i][0])
            return CL_TABLE[i][1] + t * (CL_TABLE[i + 1][1] - CL_TABLE[i][1])
    
    return CL_TABLE[-1][1]

def calculate_air_density(
    temp_f: float,
    elevation_ft: float,
    humidity_pct: float,
    pressure_inhg: float
) -> float:
    """
    Calculate air density with atmospheric corrections.
    
    Args:
        temp_f: Temperature in Fahrenheit
        elevation_ft: Elevation in feet
        humidity_pct: Relative humidity percentage
        pressure_inhg: Barometric pressure in inches Hg
    
    Returns:
        Air density in kg/m³
    """
    temp_c = (temp_f - 32) * 5 / 9
    temp_k = temp_c + 273.15
    
    # Saturation vapor pressure (Magnus formula) in mm Hg
    SVP = 4.5841 * math.exp((18.687 - temp_c / 234.5) * temp_c / (257.14 + temp_c))
    
    # Actual vapor pressure
    VP = (humidity_pct / 100) * SVP
    
    # Barometric pressure in mm Hg
    pressure_mmhg = pressure_inhg * 25.4
    
    # Pressure correction for elevation
    pressure_at_elev = pressure_mmhg * math.exp(-elevation_ft / 27000)
    
    # Air density calculation
    rho = 1.2929 * (273.15 / temp_k) * ((pressure_at_elev - 0.3783 * VP) / 760)
    
    return rho
```

### open_range/physics/trajectory.py - Trajectory Simulation

```python
"""
Golf ball trajectory simulation using RK4 integration.
"""
import math
from dataclasses import dataclass
from typing import Optional, Callable
from ..models import Vec3, TrajectoryPoint, Phase, ShotResult, ShotSummary, LaunchData, Conditions
from .constants import *
from .aerodynamics import calculate_reynolds, get_drag_coefficient, get_lift_coefficient, calculate_air_density
from .ground import GroundPhysics

@dataclass
class SimulationState:
    """Current state of ball simulation"""
    pos: Vec3
    vel: Vec3
    spin_back: float
    spin_side: float
    t: float
    phase: Phase

class TrajectorySimulator:
    """
    Simulates golf ball trajectory with full physics.
    """
    
    def __init__(
        self,
        temp_f: float = STD_TEMP_F,
        elevation_ft: float = STD_ELEVATION_FT,
        humidity_pct: float = STD_HUMIDITY_PCT,
        pressure_inhg: float = STD_PRESSURE_INHG,
        wind_speed_mph: float = 0.0,
        wind_dir_deg: float = 0.0,
        surface: str = "Fairway",
        dt: float = DT
    ):
        self.temp_f = temp_f
        self.elevation_ft = elevation_ft
        self.humidity_pct = humidity_pct
        self.pressure_inhg = pressure_inhg
        self.wind_speed_mph = wind_speed_mph
        self.wind_dir_deg = wind_dir_deg
        self.surface = SURFACES.get(surface, SURFACES["Fairway"])
        self.surface_name = surface
        self.dt = dt
        
        # Calculate air density
        self.air_density = calculate_air_density(
            temp_f, elevation_ft, humidity_pct, pressure_inhg
        )
        
        # Ground physics
        self.ground = GroundPhysics(self.surface)
    
    def _mph_to_ms(self, mph: float) -> float:
        return mph * 0.44704
    
    def _ms_to_mph(self, ms: float) -> float:
        return ms / 0.44704
    
    def _meters_to_yards(self, m: float) -> float:
        return m * 1.09361
    
    def _meters_to_feet(self, m: float) -> float:
        return m / 0.3048
    
    def _rpm_to_rad_s(self, rpm: float) -> float:
        return rpm * 2 * math.pi / 60
    
    def _deg_to_rad(self, deg: float) -> float:
        return deg * math.pi / 180
    
    def _vec_add(self, a: Vec3, b: Vec3) -> Vec3:
        return Vec3(x=a.x + b.x, y=a.y + b.y, z=a.z + b.z)
    
    def _vec_sub(self, a: Vec3, b: Vec3) -> Vec3:
        return Vec3(x=a.x - b.x, y=a.y - b.y, z=a.z - b.z)
    
    def _vec_scale(self, v: Vec3, s: float) -> Vec3:
        return Vec3(x=v.x * s, y=v.y * s, z=v.z * s)
    
    def _vec_mag(self, v: Vec3) -> float:
        return math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)
    
    def _vec_normalize(self, v: Vec3) -> Vec3:
        m = self._vec_mag(v)
        if m < 1e-10:
            return Vec3(x=0, y=0, z=0)
        return self._vec_scale(v, 1 / m)
    
    def _vec_cross(self, a: Vec3, b: Vec3) -> Vec3:
        return Vec3(
            x=a.y * b.z - a.z * b.y,
            y=a.z * b.x - a.x * b.z,
            z=a.x * b.y - a.y * b.x
        )
    
    def _vec_dot(self, a: Vec3, b: Vec3) -> float:
        return a.x * b.x + a.y * b.y + a.z * b.z
    
    def _get_wind_at_height(self, height_m: float) -> Vec3:
        """Get wind velocity at height (logarithmic profile)"""
        if self.wind_speed_mph == 0:
            return Vec3(x=0, y=0, z=0)
        
        height_ft = self._meters_to_feet(height_m)
        z0 = 0.01  # Surface roughness
        ref_height = 10  # Reference height (ft)
        
        factor = 1.0
        if height_ft > 0.1:
            factor = math.log(height_ft / z0) / math.log(ref_height / z0)
            factor = max(0, min(factor, 2))
        
        wind_speed = self._mph_to_ms(self.wind_speed_mph * factor)
        wind_dir = self._deg_to_rad(self.wind_dir_deg)
        
        return Vec3(
            x=-wind_speed * math.cos(wind_dir),
            y=0,
            z=wind_speed * math.sin(wind_dir)
        )
    
    def _calculate_acceleration(
        self,
        pos: Vec3,
        vel: Vec3,
        spin_back: float,
        spin_side: float
    ) -> Vec3:
        """Calculate total acceleration on the ball"""
        wind = self._get_wind_at_height(pos.y)
        rel_vel = self._vec_sub(vel, wind)
        speed = self._vec_mag(rel_vel)
        
        if speed < 0.1:
            return Vec3(x=0, y=-GRAVITY_MS2, z=0)
        
        # Aerodynamic coefficients
        Re = calculate_reynolds(speed, self.air_density)
        Cd = get_drag_coefficient(Re)
        
        omega = self._rpm_to_rad_s(math.sqrt(spin_back ** 2 + spin_side ** 2))
        S = (omega * BALL_RADIUS_M) / speed
        Cl = get_lift_coefficient(S)
        
        # Dynamic pressure
        q = 0.5 * self.air_density * speed * speed
        
        # Drag force
        drag_mag = q * Cd * BALL_AREA_M2
        drag_dir = self._vec_normalize(self._vec_scale(rel_vel, -1))
        drag_force = self._vec_scale(drag_dir, drag_mag)
        
        # Magnus force
        omega_back = self._rpm_to_rad_s(spin_back)
        omega_side = self._rpm_to_rad_s(spin_side)
        spin_vec = Vec3(x=0, y=omega_side, z=omega_back)
        
        magnus_dir = self._vec_cross(spin_vec, rel_vel)
        magnus_dir_norm = self._vec_normalize(magnus_dir)
        magnus_mag = q * Cl * BALL_AREA_M2
        magnus_force = self._vec_scale(magnus_dir_norm, magnus_mag)
        
        # Total force = Gravity + Drag + Magnus
        gravity_force = Vec3(x=0, y=-BALL_MASS_KG * GRAVITY_MS2, z=0)
        total_force = self._vec_add(
            self._vec_add(gravity_force, drag_force),
            magnus_force
        )
        
        # Acceleration = Force / Mass
        accel = self._vec_scale(total_force, 1 / BALL_MASS_KG)
        
        # Safety check
        if not all(math.isfinite(v) for v in [accel.x, accel.y, accel.z]):
            return Vec3(x=0, y=-GRAVITY_MS2, z=0)
        
        return accel
    
    def _rk4_step(self, state: SimulationState) -> SimulationState:
        """Perform one RK4 integration step"""
        pos, vel = state.pos, state.vel
        spin_back, spin_side = state.spin_back, state.spin_side
        dt = self.dt
        
        # k1
        a1 = self._calculate_acceleration(pos, vel, spin_back, spin_side)
        k1_pos = vel
        k1_vel = a1
        
        # k2
        pos2 = self._vec_add(pos, self._vec_scale(k1_pos, dt / 2))
        vel2 = self._vec_add(vel, self._vec_scale(k1_vel, dt / 2))
        a2 = self._calculate_acceleration(pos2, vel2, spin_back, spin_side)
        k2_pos = vel2
        k2_vel = a2
        
        # k3
        pos3 = self._vec_add(pos, self._vec_scale(k2_pos, dt / 2))
        vel3 = self._vec_add(vel, self._vec_scale(k2_vel, dt / 2))
        a3 = self._calculate_acceleration(pos3, vel3, spin_back, spin_side)
        k3_pos = vel3
        k3_vel = a3
        
        # k4
        pos4 = self._vec_add(pos, self._vec_scale(k3_pos, dt))
        vel4 = self._vec_add(vel, self._vec_scale(k3_vel, dt))
        a4 = self._calculate_acceleration(pos4, vel4, spin_back, spin_side)
        k4_pos = vel4
        k4_vel = a4
        
        # Combine
        new_pos = self._vec_add(pos, self._vec_scale(
            self._vec_add(
                self._vec_add(k1_pos, self._vec_scale(k2_pos, 2)),
                self._vec_add(self._vec_scale(k3_pos, 2), k4_pos)
            ),
            dt / 6
        ))
        new_vel = self._vec_add(vel, self._vec_scale(
            self._vec_add(
                self._vec_add(k1_vel, self._vec_scale(k2_vel, 2)),
                self._vec_add(self._vec_scale(k3_vel, 2), k4_vel)
            ),
            dt / 6
        ))
        
        # Spin decay
        spin_decay = 1 - SPIN_DECAY_RATE * dt
        
        return SimulationState(
            pos=new_pos,
            vel=new_vel,
            spin_back=spin_back * spin_decay,
            spin_side=spin_side * spin_decay,
            t=state.t + dt,
            phase=state.phase
        )
    
    def simulate(
        self,
        ball_speed_mph: float,
        vla_deg: float,
        hla_deg: float,
        backspin_rpm: float,
        sidespin_rpm: float
    ) -> ShotResult:
        """
        Run full trajectory simulation.
        
        Args:
            ball_speed_mph: Ball speed in mph
            vla_deg: Vertical launch angle in degrees
            hla_deg: Horizontal launch angle in degrees
            backspin_rpm: Backspin in rpm
            sidespin_rpm: Sidespin in rpm
        
        Returns:
            ShotResult with trajectory and summary
        """
        # Convert to SI
        speed_ms = self._mph_to_ms(ball_speed_mph)
        vla_rad = self._deg_to_rad(vla_deg)
        hla_rad = self._deg_to_rad(hla_deg)
        
        # Initial velocity (X forward, Y up, Z lateral)
        vx = speed_ms * math.cos(vla_rad) * math.cos(hla_rad)
        vy = speed_ms * math.sin(vla_rad)
        vz = speed_ms * math.cos(vla_rad) * math.sin(hla_rad)
        
        # Initial state
        state = SimulationState(
            pos=Vec3(x=0, y=0, z=0),
            vel=Vec3(x=vx, y=vy, z=vz),
            spin_back=backspin_rpm,
            spin_side=sidespin_rpm,
            t=0,
            phase=Phase.FLIGHT
        )
        
        # Trajectory recording
        trajectory: list[TrajectoryPoint] = []
        max_height = 0.0
        max_height_time = 0.0
        landing_time = 0.0
        bounce_count = 0
        
        trajectory.append(TrajectoryPoint(t=0, x=0, y=0, z=0, phase=Phase.FLIGHT))
        
        # Simulation loop
        iter_count = 0
        max_iter = min(MAX_ITERATIONS, int(MAX_TIME / self.dt))
        sample_rate = max(1, max_iter // 400)
        
        while state.t < MAX_TIME and state.phase != Phase.STOPPED and iter_count < max_iter:
            iter_count += 1
            
            if len(trajectory) > MAX_TRAJECTORY_POINTS:
                state.phase = Phase.STOPPED
                break
            
            if state.phase in (Phase.FLIGHT, Phase.BOUNCE):
                state = self._rk4_step(state)
                
                if state.pos.y > max_height:
                    max_height = state.pos.y
                    max_height_time = state.t
                
                if state.pos.y <= 0 and state.t > 0.1:
                    if landing_time == 0:
                        landing_time = state.t
                    
                    speed = self._vec_mag(state.vel)
                    if speed > 2 and bounce_count < 5:
                        state = self.ground.bounce(state)
                        bounce_count += 1
                    else:
                        state.pos = Vec3(x=state.pos.x, y=0, z=state.pos.z)
                        state.vel = Vec3(x=state.vel.x, y=0, z=state.vel.z)
                        state.phase = Phase.ROLLING
            
            elif state.phase == Phase.ROLLING:
                state = self.ground.roll_step(state, self.dt)
            
            # Sample trajectory points
            if iter_count % sample_rate == 0 or state.phase == Phase.STOPPED:
                trajectory.append(TrajectoryPoint(
                    t=state.t,
                    x=self._meters_to_yards(state.pos.x),
                    y=self._meters_to_feet(max(0, state.pos.y)),
                    z=self._meters_to_yards(state.pos.z),
                    phase=state.phase
                ))
        
        # Calculate results
        carry_point = next((p for p in trajectory if p.t >= landing_time), trajectory[-1])
        carry_distance = math.sqrt(carry_point.x ** 2 + carry_point.z ** 2) if landing_time > 0 else 0
        
        final_x = self._meters_to_yards(state.pos.x)
        final_z = self._meters_to_yards(state.pos.z)
        total_distance = math.sqrt(final_x ** 2 + final_z ** 2)
        
        return ShotResult(
            trajectory=trajectory,
            summary=ShotSummary(
                carry_distance=carry_distance,
                total_distance=total_distance,
                roll_distance=total_distance - carry_distance,
                offline_distance=final_z,
                max_height=self._meters_to_feet(max_height),
                max_height_time=max_height_time,
                flight_time=landing_time,
                total_time=state.t,
                bounce_count=bounce_count
            ),
            launch_data=LaunchData(
                ball_speed=ball_speed_mph,
                vla=vla_deg,
                hla=hla_deg,
                backspin=backspin_rpm,
                sidespin=sidespin_rpm
            ),
            conditions=Conditions(
                temp_f=self.temp_f,
                elevation_ft=self.elevation_ft,
                humidity_pct=self.humidity_pct,
                wind_speed_mph=self.wind_speed_mph,
                wind_dir_deg=self.wind_dir_deg,
                air_density=self.air_density,
                surface=self.surface_name
            )
        )
```

### open_range/physics/ground.py - Ground Physics

```python
"""
Ground interaction physics: bounce and roll.
Inspired by libgolf (github.com/gdifiore/libgolf).
"""
import math
from ..models import Vec3, Phase
from .constants import GRAVITY_MS2, BALL_RADIUS_M

class GroundPhysics:
    """Handles bounce and roll physics"""
    
    def __init__(self, surface: dict):
        self.cor = surface["coefficient_of_restitution"]
        self.rolling_resistance = surface["rolling_resistance"]
        self.friction = surface["friction_coefficient"]
    
    def bounce(self, state) -> "SimulationState":
        """Apply bounce physics at ground contact"""
        from .trajectory import SimulationState
        
        pos, vel = state.pos, state.vel
        
        # Surface normal (flat ground)
        normal = Vec3(x=0, y=1, z=0)
        
        # Decompose velocity
        v_dot_n = vel.y  # Simplified for flat ground
        v_normal = Vec3(x=0, y=v_dot_n, z=0)
        v_tangent = Vec3(x=vel.x, y=0, z=vel.z)
        
        # Apply COR to normal component
        new_v_normal = Vec3(x=0, y=-v_dot_n * self.cor, z=0)
        
        # Apply friction to tangential component
        tangent_speed = math.sqrt(v_tangent.x ** 2 + v_tangent.z ** 2)
        friction_loss = min(self.friction * abs(v_dot_n), tangent_speed)
        
        if tangent_speed > 0.01:
            scale = (tangent_speed - friction_loss) / tangent_speed
            new_v_tangent = Vec3(x=v_tangent.x * scale, y=0, z=v_tangent.z * scale)
        else:
            new_v_tangent = Vec3(x=0, y=0, z=0)
        
        new_vel = Vec3(
            x=new_v_tangent.x,
            y=new_v_normal.y,
            z=new_v_tangent.z
        )
        
        # Spin change from friction
        spin_change = friction_loss * 30 / (math.pi * BALL_RADIUS_M)
        
        return SimulationState(
            pos=Vec3(x=pos.x, y=0.001, z=pos.z),
            vel=new_vel,
            spin_back=state.spin_back - spin_change,
            spin_side=state.spin_side,
            t=state.t,
            phase=Phase.BOUNCE
        )
    
    def roll_step(self, state, dt: float) -> "SimulationState":
        """Simulate one step of rolling"""
        from .trajectory import SimulationState
        
        pos, vel = state.pos, state.vel
        speed = math.sqrt(vel.x ** 2 + vel.z ** 2)
        
        # Check if stopped
        if speed < 0.1:
            return SimulationState(
                pos=pos,
                vel=Vec3(x=0, y=0, z=0),
                spin_back=0,
                spin_side=0,
                t=state.t + dt,
                phase=Phase.STOPPED
            )
        
        # Rolling resistance deceleration
        decel = max(0.5, self.rolling_resistance * GRAVITY_MS2)
        
        # Spin effect (capped)
        spin_effect = min(0.3, abs(state.spin_back) * BALL_RADIUS_M * 0.0001)
        spin_effect *= 1 if state.spin_back > 0 else -1
        
        # New speed
        new_speed = max(0, speed - decel * dt + spin_effect * dt * 0.5)
        
        if new_speed > 0.01:
            scale = new_speed / speed
            new_vel = Vec3(x=vel.x * scale, y=0, z=vel.z * scale)
        else:
            new_vel = Vec3(x=0, y=0, z=0)
        
        # New position
        new_pos = Vec3(
            x=pos.x + vel.x * dt,
            y=0,
            z=pos.z + vel.z * dt
        )
        
        return SimulationState(
            pos=new_pos,
            vel=new_vel,
            spin_back=state.spin_back * (1 - 0.1 * dt),
            spin_side=state.spin_side * (1 - 0.1 * dt),
            t=state.t + dt,
            phase=Phase.STOPPED if new_speed < 0.1 else Phase.ROLLING
        )
```

### services/shot_router.py - Shot Routing

```python
"""
Routes shots to appropriate destination based on mode.
"""
from enum import Enum
from typing import Optional, Callable, Awaitable
from ..models import GC2ShotData
from ..gspro import GSProClient
from ..open_range.engine import OpenRangeEngine

class AppMode(str, Enum):
    GSPRO = "gspro"
    OPEN_RANGE = "open_range"

class ShotRouter:
    """Routes shots between GSPro and Open Range modes"""
    
    def __init__(self):
        self._mode = AppMode.GSPRO
        self._gspro_client: Optional[GSProClient] = None
        self._open_range_engine: Optional[OpenRangeEngine] = None
        self._shot_callback: Optional[Callable] = None
    
    @property
    def mode(self) -> AppMode:
        return self._mode
    
    async def set_mode(self, mode: AppMode):
        """Switch between modes"""
        if mode == self._mode:
            return
        
        # Cleanup previous mode
        if self._mode == AppMode.GSPRO and self._gspro_client:
            await self._gspro_client.disconnect()
        
        self._mode = mode
    
    def set_gspro_client(self, client: GSProClient):
        self._gspro_client = client
    
    def set_open_range_engine(self, engine: OpenRangeEngine):
        self._open_range_engine = engine
    
    def set_shot_callback(self, callback: Callable):
        """Set callback for shot results (used by UI)"""
        self._shot_callback = callback
    
    async def route_shot(self, shot: GC2ShotData):
        """Route shot to appropriate destination"""
        if self._mode == AppMode.GSPRO:
            await self._route_to_gspro(shot)
        else:
            await self._route_to_open_range(shot)
    
    async def _route_to_gspro(self, shot: GC2ShotData):
        """Send shot to GSPro"""
        if not self._gspro_client:
            raise RuntimeError("GSPro client not configured")
        
        message = self._convert_to_gspro_format(shot)
        await self._gspro_client.send_shot(message)
    
    async def _route_to_open_range(self, shot: GC2ShotData):
        """Process shot in Open Range"""
        if not self._open_range_engine:
            raise RuntimeError("Open Range engine not configured")
        
        result = self._open_range_engine.simulate_shot(shot)
        
        if self._shot_callback:
            await self._shot_callback(result)
    
    def _convert_to_gspro_format(self, shot: GC2ShotData) -> dict:
        """Convert GC2 shot data to GSPro API format"""
        # Existing conversion logic...
        pass
```

---

## UI Integration

### NiceGUI Components

#### ui/components/mode_selector.py

```python
"""Mode selector component"""
from nicegui import ui
from ...services.shot_router import AppMode

class ModeSelector:
    """Toggle between GSPro and Open Range modes"""
    
    def __init__(self, on_change: callable):
        self.on_change = on_change
        self.current_mode = AppMode.GSPRO
    
    def build(self):
        with ui.row().classes('gap-2'):
            ui.label('Mode:').classes('self-center')
            self.toggle = ui.toggle(
                {AppMode.GSPRO: 'GSPro', AppMode.OPEN_RANGE: 'Open Range'},
                value=AppMode.GSPRO,
                on_change=self._handle_change
            ).classes('bg-gray-800')
    
    async def _handle_change(self, e):
        self.current_mode = e.value
        await self.on_change(e.value)
```

#### ui/components/open_range_view.py

```python
"""Open Range 3D view component"""
from nicegui import ui
from nicegui.element import Element

class OpenRangeView:
    """3D driving range visualization"""
    
    def __init__(self):
        self.scene: Optional[Element] = None
    
    def build(self):
        # Use NiceGUI's Three.js scene
        with ui.scene(width=800, height=600).classes('rounded-lg') as self.scene:
            self._setup_range()
            self._setup_lighting()
    
    def _setup_range(self):
        """Create driving range environment"""
        # Ground plane
        with self.scene:
            ui.scene.plane(20, 40).material('#3d8c40').move(0, 0, 20)
            # Add distance markers, targets, etc.
    
    def _setup_lighting(self):
        """Configure scene lighting"""
        with self.scene:
            ui.scene.ambient_light(intensity=0.5)
            ui.scene.directional_light().move(10, 15, 5)
    
    def animate_shot(self, trajectory: list):
        """Animate ball along trajectory"""
        # Animation logic using NiceGUI's scene API
        pass
```

---

## Configuration Changes

### Extended Settings Schema

```json
{
  "version": 2,
  "mode": "gspro",
  "gspro": {
    "host": "192.168.1.100",
    "port": 921,
    "auto_connect": true
  },
  "gc2": {
    "auto_connect": true,
    "reject_zero_spin": true
  },
  "open_range": {
    "conditions": {
      "temp_f": 70,
      "elevation_ft": 0,
      "humidity_pct": 50,
      "wind_speed_mph": 0,
      "wind_dir_deg": 0
    },
    "surface": "Fairway",
    "show_trajectory": true,
    "camera_follow": true
  },
  "ui": {
    "theme": "dark",
    "show_history": true,
    "history_limit": 100
  }
}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_open_range/test_physics.py

import pytest
from gc2_connect.open_range.physics.trajectory import TrajectorySimulator

# Validation data from Nathan's spreadsheet
NATHAN_TEST_CASES = [
    {"speed": 167, "vla": 10.9, "spin": 2686, "expected_carry": 275, "tolerance": 0.05},
    {"speed": 160, "vla": 11.0, "spin": 3000, "expected_carry": 259.3, "tolerance": 0.03},
    {"speed": 120, "vla": 16.3, "spin": 7097, "expected_carry": 172, "tolerance": 0.05},
    {"speed": 102, "vla": 24.2, "spin": 9304, "expected_carry": 136, "tolerance": 0.05},
]

@pytest.mark.parametrize("test_case", NATHAN_TEST_CASES)
def test_carry_distance_accuracy(test_case):
    """Validate physics against Nathan's expected values"""
    sim = TrajectorySimulator()
    result = sim.simulate(
        ball_speed_mph=test_case["speed"],
        vla_deg=test_case["vla"],
        hla_deg=0,
        backspin_rpm=test_case["spin"],
        sidespin_rpm=0
    )
    
    carry = result.summary.carry_distance
    expected = test_case["expected_carry"]
    tolerance = test_case["tolerance"]
    
    error = abs(carry - expected) / expected
    assert error <= tolerance, f"Carry {carry:.1f} not within {tolerance*100}% of {expected}"

def test_sidespin_curves_ball():
    """Verify sidespin produces lateral movement"""
    sim = TrajectorySimulator()
    
    # Straight shot
    straight = sim.simulate(160, 11, 0, 3000, 0)
    
    # Slice
    slice_shot = sim.simulate(160, 11, 0, 3000, 1500)
    
    # Draw
    draw_shot = sim.simulate(160, 11, 0, 3000, -1500)
    
    assert abs(straight.summary.offline_distance) < 2
    assert slice_shot.summary.offline_distance > 10
    assert draw_shot.summary.offline_distance < -10
```

---

## Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Physics calculation | < 100ms per shot |
| Trajectory points | < 500 per shot |
| 3D render frame rate | 60 FPS |
| Memory (Open Range active) | < 150MB total app |
| Mode switch time | < 500ms |

---

## Migration Path

### v1.0 → v1.1 Upgrade

1. Settings file auto-migrates (version field)
2. Default mode remains GSPro for existing users
3. Open Range is opt-in feature
4. No breaking changes to existing functionality

---

## Future Considerations

### v1.2 Potential Features
- Multiple range environments
- Shot dispersion visualization
- Club gapping analysis
- Practice game modes
- Session export

### Technical Improvements
- WebGPU for better 3D performance
- Shared memory for physics workers
- Precomputed trajectory caching
