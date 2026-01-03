# ABOUTME: Shot history manager for tracking and analyzing session shots.
# ABOUTME: Provides storage, statistics, and export capabilities for shot data.
"""Shot history management for GC2 Connect."""

from __future__ import annotations

from typing import Any

from gc2_connect.models import GC2ShotData


class ShotHistoryManager:
    """Manages shot history with configurable limit and statistics.

    The manager stores shots in newest-first order and provides
    session statistics like averages and max values.

    Attributes:
        limit: Maximum number of shots to store.
        shots: List of shots in newest-first order.
    """

    def __init__(self, limit: int = 50) -> None:
        """Initialize the shot history manager.

        Args:
            limit: Maximum number of shots to keep in history.
        """
        self._limit = limit
        self._shots: list[GC2ShotData] = []

    @property
    def limit(self) -> int:
        """Get the current history limit."""
        return self._limit

    @limit.setter
    def limit(self, value: int) -> None:
        """Set the history limit and trim if necessary.

        Args:
            value: New limit value.
        """
        self._limit = value
        self._trim_to_limit()

    @property
    def count(self) -> int:
        """Get the current number of shots in history."""
        return len(self._shots)

    @property
    def shots(self) -> list[GC2ShotData]:
        """Get the list of shots (newest first)."""
        return self._shots

    def add_shot(self, shot: GC2ShotData) -> None:
        """Add a shot to the history.

        Shots are added at the beginning (newest first).
        If the limit is exceeded, the oldest shot is removed.

        Args:
            shot: The shot data to add.
        """
        self._shots.insert(0, shot)
        self._trim_to_limit()

    def clear(self) -> None:
        """Clear all shots from history."""
        self._shots.clear()

    def _trim_to_limit(self) -> None:
        """Trim the history to the current limit."""
        if len(self._shots) > self._limit:
            self._shots = self._shots[: self._limit]

    def get_statistics(self) -> dict[str, float | int]:
        """Calculate session statistics from the shot history.

        Returns:
            Dictionary with count, averages, and max values.
        """
        if not self._shots:
            return {
                "count": 0,
                "avg_ball_speed": 0.0,
                "avg_launch_angle": 0.0,
                "avg_total_spin": 0.0,
                "max_ball_speed": 0.0,
                "max_total_spin": 0.0,
            }

        count = len(self._shots)
        total_ball_speed = sum(s.ball_speed for s in self._shots)
        total_launch_angle = sum(s.launch_angle for s in self._shots)
        total_spin = sum(s.total_spin for s in self._shots)

        max_ball_speed = max(s.ball_speed for s in self._shots)
        max_total_spin = max(s.total_spin for s in self._shots)

        return {
            "count": count,
            "avg_ball_speed": total_ball_speed / count,
            "avg_launch_angle": total_launch_angle / count,
            "avg_total_spin": total_spin / count,
            "max_ball_speed": max_ball_speed,
            "max_total_spin": max_total_spin,
        }

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Export shots as a list of dictionaries.

        Returns:
            List of dictionaries representing each shot.
        """
        result = []
        for shot in self._shots:
            shot_dict: dict[str, Any] = {
                "shot_id": shot.shot_id,
                "timestamp": shot.timestamp.isoformat(),
                "ball_speed": shot.ball_speed,
                "launch_angle": shot.launch_angle,
                "horizontal_launch_angle": shot.horizontal_launch_angle,
                "total_spin": shot.total_spin,
                "back_spin": shot.back_spin,
                "side_spin": shot.side_spin,
                "spin_axis": shot.spin_axis,
            }

            # Include club data if present
            if shot.club_speed is not None:
                shot_dict["club_speed"] = shot.club_speed
            if shot.swing_path is not None:
                shot_dict["swing_path"] = shot.swing_path
            if shot.face_to_target is not None:
                shot_dict["face_to_target"] = shot.face_to_target
            if shot.angle_of_attack is not None:
                shot_dict["angle_of_attack"] = shot.angle_of_attack
            if shot.lie is not None:
                shot_dict["lie"] = shot.lie
            if shot.dynamic_loft is not None:
                shot_dict["dynamic_loft"] = shot.dynamic_loft

            result.append(shot_dict)

        return result

    def format_count_display(self) -> str:
        """Format the count display string.

        Returns:
            String in format "Shots: X/Y" where X is count and Y is limit.
        """
        return f"Shots: {self.count}/{self.limit}"
