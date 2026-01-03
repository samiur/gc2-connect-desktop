# ABOUTME: Data models for Open Range physics simulation.
# ABOUTME: Includes Vec3, trajectory points, shot summaries, and environmental conditions.
"""Data models for Open Range physics calculations."""

from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from gc2_connect.models import GC2ShotData


class Phase(str, Enum):
    """Phase of ball trajectory."""

    FLIGHT = "flight"
    BOUNCE = "bounce"
    ROLLING = "rolling"
    STOPPED = "stopped"


class Vec3(BaseModel):
    """3D vector for physics calculations.

    Coordinate system:
    - X: Forward toward target (yards in output, meters in simulation)
    - Y: Vertical height (feet in output, meters in simulation)
    - Z: Lateral (+ = right of target)
    """

    x: Annotated[float, Field(description="X component (forward)")] = 0.0
    y: Annotated[float, Field(description="Y component (vertical)")] = 0.0
    z: Annotated[float, Field(description="Z component (lateral)")] = 0.0

    def add(self, other: Vec3) -> Vec3:
        """Add two vectors."""
        return Vec3(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def sub(self, other: Vec3) -> Vec3:
        """Subtract another vector from this one."""
        return Vec3(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    def scale(self, scalar: float) -> Vec3:
        """Multiply vector by a scalar."""
        return Vec3(x=self.x * scalar, y=self.y * scalar, z=self.z * scalar)

    def neg(self) -> Vec3:
        """Return negated vector."""
        return Vec3(x=-self.x, y=-self.y, z=-self.z)

    def mag(self) -> float:
        """Calculate magnitude (length) of vector."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> Vec3:
        """Return unit vector in same direction.

        Returns zero vector if magnitude is zero.
        """
        magnitude = self.mag()
        if magnitude == 0:
            return Vec3(x=0.0, y=0.0, z=0.0)
        return self.scale(1.0 / magnitude)

    def dot(self, other: Vec3) -> float:
        """Calculate dot product with another vector."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        """Calculate cross product with another vector."""
        return Vec3(
            x=self.y * other.z - self.z * other.y,
            y=self.z * other.x - self.x * other.z,
            z=self.x * other.y - self.y * other.x,
        )


class TrajectoryPoint(BaseModel):
    """Single point in ball trajectory."""

    t: Annotated[float, Field(description="Time in seconds")] = 0.0
    x: Annotated[float, Field(description="Forward distance in yards")] = 0.0
    y: Annotated[float, Field(description="Height in feet")] = 0.0
    z: Annotated[float, Field(description="Lateral distance in yards (+ = right)")] = 0.0
    phase: Annotated[Phase, Field(description="Current phase of ball motion")] = Phase.FLIGHT


class ShotSummary(BaseModel):
    """Shot outcome metrics."""

    carry_distance: Annotated[float, Field(description="Carry distance in yards")] = 0.0
    total_distance: Annotated[float, Field(description="Total distance in yards")] = 0.0
    roll_distance: Annotated[float, Field(description="Roll distance in yards")] = 0.0
    offline_distance: Annotated[
        float, Field(description="Lateral distance (+ right, - left) in yards")
    ] = 0.0
    max_height: Annotated[float, Field(description="Maximum height in feet")] = 0.0
    max_height_time: Annotated[float, Field(description="Time to max height in seconds")] = 0.0
    flight_time: Annotated[float, Field(description="Time to first landing in seconds")] = 0.0
    total_time: Annotated[float, Field(description="Total time to stop in seconds")] = 0.0
    bounce_count: Annotated[int, Field(description="Number of bounces")] = 0


class LaunchData(BaseModel):
    """Input launch conditions from GC2."""

    ball_speed: Annotated[float, Field(description="Ball speed in mph")] = 0.0
    vla: Annotated[float, Field(description="Vertical launch angle in degrees")] = 0.0
    hla: Annotated[float, Field(description="Horizontal launch angle in degrees")] = 0.0
    backspin: Annotated[float, Field(description="Backspin in rpm")] = 0.0
    sidespin: Annotated[float, Field(description="Sidespin in rpm")] = 0.0

    @classmethod
    def from_gc2_shot(cls, shot: GC2ShotData) -> LaunchData:
        """Create LaunchData from GC2ShotData."""
        return cls(
            ball_speed=shot.ball_speed,
            vla=shot.launch_angle,
            hla=shot.horizontal_launch_angle,
            backspin=shot.back_spin,
            sidespin=shot.side_spin,
        )


class Conditions(BaseModel):
    """Environmental conditions for simulation."""

    temp_f: Annotated[float, Field(description="Temperature in Fahrenheit")] = 70.0
    elevation_ft: Annotated[float, Field(description="Elevation in feet")] = 0.0
    humidity_pct: Annotated[float, Field(description="Humidity percentage")] = 50.0
    wind_speed_mph: Annotated[float, Field(description="Wind speed in mph")] = 0.0
    wind_dir_deg: Annotated[
        float, Field(description="Wind direction in degrees (0=from north/headwind)")
    ] = 0.0


class ShotResult(BaseModel):
    """Complete simulation result."""

    trajectory: Annotated[list[TrajectoryPoint], Field(description="List of trajectory points")]
    summary: Annotated[ShotSummary, Field(description="Shot summary metrics")]
    launch_data: Annotated[LaunchData, Field(description="Input launch conditions")]
    conditions: Annotated[Conditions, Field(description="Environmental conditions")]
