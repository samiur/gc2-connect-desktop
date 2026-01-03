# ABOUTME: CSV export functionality for shot session data.
# ABOUTME: Exports GC2 shot data to CSV format for external analysis.
"""CSV export module for GC2 Connect."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from gc2_connect.models import GC2ShotData

# CSV column headers
CSV_HEADERS = [
    "Shot #",
    "Timestamp",
    "Ball Speed (mph)",
    "Launch Angle (°)",
    "H. Launch Angle (°)",
    "Total Spin (RPM)",
    "Back Spin (RPM)",
    "Side Spin (RPM)",
    "Spin Axis (°)",
    "Club Speed (mph)",
    "Path (°)",
    "Attack Angle (°)",
    "Face to Target (°)",
    "Lie (°)",
    "Dynamic Loft (°)",
]


def generate_export_filename() -> str:
    """Generate a default export filename with timestamp.

    Returns:
        Filename in format: gc2_session_YYYYMMDD_HHMMSS.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"gc2_session_{timestamp}.csv"


def _format_float(value: float | None, decimals: int = 2) -> str:
    """Format a float value with specified decimal places.

    Args:
        value: The value to format, or None.
        decimals: Number of decimal places.

    Returns:
        Formatted string or empty string if value is None.
    """
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _format_int(value: float | None) -> str:
    """Format a float value as an integer.

    Args:
        value: The value to format, or None.

    Returns:
        Formatted string or empty string if value is None.
    """
    if value is None:
        return ""
    return str(round(value))


def _shot_to_row(shot: GC2ShotData) -> list[str]:
    """Convert a shot to a CSV row.

    Args:
        shot: The shot data to convert.

    Returns:
        List of string values for the CSV row.
    """
    return [
        str(shot.shot_id),
        shot.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        _format_float(shot.ball_speed),
        _format_float(shot.launch_angle),
        _format_float(shot.horizontal_launch_angle),
        _format_int(shot.total_spin),
        _format_int(shot.back_spin),
        _format_int(shot.side_spin),
        _format_float(shot.spin_axis),
        _format_float(shot.club_speed),
        _format_float(shot.swing_path),
        _format_float(shot.angle_of_attack),
        _format_float(shot.face_to_target),
        _format_float(shot.lie),
        _format_float(shot.dynamic_loft),
    ]


def export_to_csv(shots: Sequence[GC2ShotData], filepath: str | Path) -> None:
    """Export shot data to a CSV file.

    Creates a CSV file with all shot metrics. The file includes headers
    for all possible fields, with empty values for missing HMT data.

    Args:
        shots: List of shots to export.
        filepath: Path to the output CSV file (string or Path object).

    Raises:
        OSError: If the file cannot be written.
    """
    filepath = Path(filepath)

    # Create parent directories if they don't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)

        # Write headers
        writer.writerow(CSV_HEADERS)

        # Write shot data
        for shot in shots:
            writer.writerow(_shot_to_row(shot))
