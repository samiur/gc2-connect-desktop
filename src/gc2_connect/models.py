# ABOUTME: Pydantic/dataclass models for GC2 shot data and GSPro API messages.
# ABOUTME: Handles data parsing, validation, and conversion between GC2 and GSPro formats.
"""Data models for GC2 shot data and GSPro messages."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GC2ShotData:
    """Shot data from the GC2 launch monitor."""

    shot_id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    # Ball data
    ball_speed: float = 0.0  # mph
    launch_angle: float = 0.0  # degrees (vertical)
    horizontal_launch_angle: float = 0.0  # degrees
    total_spin: float = 0.0  # RPM
    back_spin: float = 0.0  # RPM
    side_spin: float = 0.0  # RPM

    # Club data (HMT)
    club_speed: float | None = None  # mph
    swing_path: float | None = None  # degrees
    angle_of_attack: float | None = None  # degrees
    face_to_target: float | None = None  # degrees
    lie: float | None = None  # degrees
    dynamic_loft: float | None = None  # degrees
    horizontal_impact: float | None = None  # mm
    vertical_impact: float | None = None  # mm
    closure_rate: float | None = None  # deg/sec

    # Flags
    has_hmt: bool = False

    @property
    def spin_axis(self) -> float:
        """Calculate spin axis from back/side spin components."""
        if self.back_spin == 0:
            return 0.0
        return math.degrees(math.atan2(self.side_spin, self.back_spin))

    @property
    def has_club_data(self) -> bool:
        """Check if club data is available."""
        return self.club_speed is not None

    def is_valid(self) -> bool:
        """Check if shot data appears valid (not a misread)."""
        # Reject zero spin shots as misreads (per gc2_to_TGC logic)
        # Note: check back_spin AND side_spin, not total_spin
        if self.back_spin == 0.0 and self.side_spin == 0.0:
            return False
        # Reject 2222 backspin as known error code
        if self.back_spin == 2222.0:
            return False
        # Reject clearly invalid speeds (0 or negative, or impossibly high)
        if self.ball_speed <= 0 or self.ball_speed > 250:
            return False
        return True

    @classmethod
    def from_gc2_dict(cls, data: dict[str, str]) -> GC2ShotData:
        """Parse GC2 USB text data into a ShotData object."""
        shot = cls()

        # Field mapping from GC2 protocol
        field_map: dict[str, tuple[str, Callable[[str], Any]]] = {
            "SHOT_ID": ("shot_id", int),
            "SPEED_MPH": ("ball_speed", float),
            "ELEVATION_DEG": ("launch_angle", float),
            "AZIMUTH_DEG": ("horizontal_launch_angle", float),
            "SPIN_RPM": ("total_spin", float),
            "BACK_RPM": ("back_spin", float),
            "SIDE_RPM": ("side_spin", float),
            "CLUBSPEED_MPH": ("club_speed", float),
            "HPATH_DEG": ("swing_path", float),
            "VPATH_DEG": ("angle_of_attack", float),
            "FACE_T_DEG": ("face_to_target", float),
            "LIE_DEG": ("lie", float),
            "LOFT_DEG": ("dynamic_loft", float),
            "HIMPACT_MM": ("horizontal_impact", float),
            "VIMPACT_MM": ("vertical_impact", float),
            "CLOSING_RATE_DEGSEC": ("closure_rate", float),
            "HMT": ("has_hmt", lambda x: x.lower() in ("1", "true", "yes")),
        }

        for gc2_key, (attr, converter) in field_map.items():
            if gc2_key in data:
                try:
                    setattr(shot, attr, converter(data[gc2_key]))
                except (ValueError, TypeError):
                    pass

        return shot


@dataclass
class GC2BallStatus:
    """Ball detection status from the GC2 launch monitor.

    The GC2 sends 0M (ball movement/tracking) messages with:
    - FLAGS: Bitmask indicating device readiness
      - 1 (001): Red light - not ready
      - 7 (111): Green light - fully ready
    - BALLS: Number of balls detected (0 or 1+)
    - BALL1: Position of first ball as "x,y,z"
    """

    flags: int = 0
    ball_count: int = 0
    ball_position: tuple[int, int, int] | None = None  # (x, y, z)

    @property
    def is_ready(self) -> bool:
        """Check if GC2 is ready (green light, FLAGS=7)."""
        # FLAGS appears to be a 3-bit mask, 7 (111) = all ready
        return self.flags == 7

    @property
    def ball_detected(self) -> bool:
        """Check if a ball is detected."""
        return self.ball_count > 0

    @classmethod
    def from_gc2_dict(cls, data: dict[str, str]) -> GC2BallStatus:
        """Parse GC2 0M message data into a BallStatus object."""
        status = cls()

        # Parse FLAGS
        if "FLAGS" in data:
            try:
                status.flags = int(data["FLAGS"])
            except ValueError:
                pass

        # Parse BALLS count
        if "BALLS" in data:
            try:
                status.ball_count = int(data["BALLS"])
            except ValueError:
                pass

        # Parse BALL1 position (format: "x,y,z")
        if "BALL1" in data:
            try:
                parts = data["BALL1"].split(",")
                if len(parts) == 3:
                    status.ball_position = (
                        int(parts[0]),
                        int(parts[1]),
                        int(parts[2]),
                    )
            except (ValueError, IndexError):
                pass

        return status


@dataclass
class GSProBallData:
    """Ball data for GSPro API."""

    Speed: float = 0.0
    SpinAxis: float = 0.0
    TotalSpin: float = 0.0
    BackSpin: float = 0.0
    SideSpin: float = 0.0
    HLA: float = 0.0  # Horizontal Launch Angle
    VLA: float = 0.0  # Vertical Launch Angle
    CarryDistance: float = 0.0


@dataclass
class GSProClubData:
    """Club data for GSPro API."""

    Speed: float = 0.0
    AngleOfAttack: float = 0.0
    FaceToTarget: float = 0.0
    Lie: float = 0.0
    Loft: float = 0.0
    Path: float = 0.0
    SpeedAtImpact: float = 0.0
    VerticalFaceImpact: float = 0.0
    HorizontalFaceImpact: float = 0.0
    ClosureRate: float = 0.0


@dataclass
class GSProShotOptions:
    """Shot options for GSPro API."""

    ContainsBallData: bool = True
    ContainsClubData: bool = False
    LaunchMonitorIsReady: bool = True
    LaunchMonitorBallDetected: bool = True
    IsHeartBeat: bool = False


@dataclass
class GSProShotMessage:
    """Complete shot message for GSPro API."""

    DeviceID: str = "GC2 Connect"
    Units: str = "Yards"
    ShotNumber: int = 1
    APIversion: str = "1"
    BallData: GSProBallData = field(default_factory=GSProBallData)
    ClubData: GSProClubData = field(default_factory=GSProClubData)
    ShotDataOptions: GSProShotOptions = field(default_factory=GSProShotOptions)

    @classmethod
    def from_gc2_shot(cls, shot: GC2ShotData, shot_number: int) -> GSProShotMessage:
        """Convert GC2 shot data to GSPro message format.

        Note: GSPro Open Connect API expects ball speed in mph.
        """
        ball_data = GSProBallData(
            Speed=shot.ball_speed,
            SpinAxis=shot.spin_axis,
            TotalSpin=shot.total_spin,
            BackSpin=shot.back_spin,
            SideSpin=shot.side_spin,
            HLA=shot.horizontal_launch_angle,
            VLA=shot.launch_angle,
            CarryDistance=0,
        )

        club_data = GSProClubData()
        has_club = False

        if shot.has_club_data:
            has_club = True
            club_data = GSProClubData(
                Speed=shot.club_speed or 0,
                AngleOfAttack=shot.angle_of_attack or 0,
                FaceToTarget=shot.face_to_target or 0,
                Lie=shot.lie or 0,
                Loft=shot.dynamic_loft or 0,
                Path=shot.swing_path or 0,
                SpeedAtImpact=shot.club_speed or 0,
                VerticalFaceImpact=shot.vertical_impact or 0,
                HorizontalFaceImpact=shot.horizontal_impact or 0,
                ClosureRate=shot.closure_rate or 0,
            )

        options = GSProShotOptions(
            ContainsBallData=True,
            ContainsClubData=has_club,
        )

        return cls(
            ShotNumber=shot_number,
            BallData=ball_data,
            ClubData=club_data,
            ShotDataOptions=options,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "DeviceID": self.DeviceID,
            "Units": self.Units,
            "ShotNumber": self.ShotNumber,
            "APIversion": self.APIversion,
            "BallData": {
                "Speed": self.BallData.Speed,
                "SpinAxis": self.BallData.SpinAxis,
                "TotalSpin": self.BallData.TotalSpin,
                "BackSpin": self.BallData.BackSpin,
                "SideSpin": self.BallData.SideSpin,
                "HLA": self.BallData.HLA,
                "VLA": self.BallData.VLA,
                "CarryDistance": self.BallData.CarryDistance,
            },
            "ClubData": {
                "Speed": self.ClubData.Speed,
                "AngleOfAttack": self.ClubData.AngleOfAttack,
                "FaceToTarget": self.ClubData.FaceToTarget,
                "Lie": self.ClubData.Lie,
                "Loft": self.ClubData.Loft,
                "Path": self.ClubData.Path,
                "SpeedAtImpact": self.ClubData.SpeedAtImpact,
                "VerticalFaceImpact": self.ClubData.VerticalFaceImpact,
                "HorizontalFaceImpact": self.ClubData.HorizontalFaceImpact,
                "ClosureRate": self.ClubData.ClosureRate,
            },
            "ShotDataOptions": {
                "ContainsBallData": self.ShotDataOptions.ContainsBallData,
                "ContainsClubData": self.ShotDataOptions.ContainsClubData,
                "LaunchMonitorIsReady": self.ShotDataOptions.LaunchMonitorIsReady,
                "LaunchMonitorBallDetected": self.ShotDataOptions.LaunchMonitorBallDetected,
                "IsHeartBeat": self.ShotDataOptions.IsHeartBeat,
            },
        }


@dataclass
class GSProResponse:
    """Response from GSPro API."""

    Code: int = 0
    Message: str = ""
    Player: dict[str, Any] | None = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.Code < 300

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GSProResponse:
        return cls(
            Code=data.get("Code", 0),
            Message=data.get("Message", ""),
            Player=data.get("Player"),
        )
