# ABOUTME: Open Range view component with 3D scene and data display.
# ABOUTME: Main UI for the built-in driving range simulator.
"""Open Range view component for GC2 Connect.

This module provides the complete Open Range UI panel with:
- 3D driving range visualization
- Ball flight animation
- Phase indicators (Flight, Bounce, Rolling, Stopped)
- Shot data display (carry, total, offline, height)
- Launch data display (ball speed, spin, angles)
- Environmental conditions display

The view integrates with RangeScene and BallAnimator for visualization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gc2_connect.open_range.models import (
    Conditions,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
)

if TYPE_CHECKING:
    from gc2_connect.open_range.visualization.ball_animation import BallAnimator
    from gc2_connect.open_range.visualization.range_scene import RangeScene


# Phase colors as Tailwind CSS classes
PHASE_COLORS: dict[Phase, str] = {
    Phase.FLIGHT: "text-green-400",
    Phase.BOUNCE: "text-orange-400",
    Phase.ROLLING: "text-blue-400",
    Phase.STOPPED: "text-gray-400",
}


def format_distance(yards: float) -> str:
    """Format distance in yards with units.

    Args:
        yards: Distance in yards.

    Returns:
        Formatted string with units (e.g., "275.5 yds").
    """
    return f"{yards:.1f} yds"


def format_height(feet: float) -> str:
    """Format height in feet with units.

    Args:
        feet: Height in feet.

    Returns:
        Formatted string with units (e.g., "50.5 ft").
    """
    return f"{feet:.1f} ft"


def format_offline(yards: float) -> str:
    """Format offline distance with direction.

    Args:
        yards: Offline distance in yards (positive = right, negative = left).

    Returns:
        Formatted string with direction indicator.
    """
    if yards > 0:
        return f"{yards:.1f} yds R"
    elif yards < 0:
        return f"{abs(yards):.1f} yds L"
    else:
        return "0.0 yds"


class OpenRangeView:
    """Complete Open Range UI panel.

    Provides the main visualization and data display for the Open Range
    driving range mode. Includes:
    - 3D scene with ball animation
    - Phase indicator with color coding
    - Shot summary data (carry, total, offline, height)
    - Launch data from GC2
    - Environmental conditions

    Example:
        view = OpenRangeView()
        view.build()  # Call within NiceGUI context
        await view.show_shot(shot_result)
    """

    def __init__(self) -> None:
        """Initialize the Open Range view."""
        self.range_scene: RangeScene | None = None
        self.animator: BallAnimator | None = None
        self.current_phase: Phase = Phase.STOPPED
        self.last_shot_result: ShotResult | None = None

        # UI element references
        self._container: Any = None
        self._phase_label: Any = None
        self._carry_label: Any = None
        self._total_label: Any = None
        self._offline_label: Any = None
        self._height_label: Any = None
        self._ball_speed_label: Any = None
        self._spin_label: Any = None
        self._launch_angle_label: Any = None
        self._temp_label: Any = None
        self._elevation_label: Any = None
        self._wind_label: Any = None

    def update_phase(self, phase: Phase) -> None:
        """Update the current phase and UI indicator.

        Args:
            phase: The new phase.
        """
        self.current_phase = phase
        if self._phase_label is not None:
            # Update text
            self._phase_label.text = phase.value.capitalize()
            # Update color class
            color_class = PHASE_COLORS.get(phase, "text-gray-400")
            # Remove all phase color classes and add the new one
            for color in PHASE_COLORS.values():
                self._phase_label.classes(remove=color)
            self._phase_label.classes(add=color_class)

    def update_shot_data(self, result: ShotResult) -> None:
        """Update shot data display with new result.

        Args:
            result: The shot result to display.
        """
        self.last_shot_result = result
        summary = result.summary

        if self._carry_label is not None:
            self._carry_label.text = format_distance(summary.carry_distance)
        if self._total_label is not None:
            self._total_label.text = format_distance(summary.total_distance)
        if self._offline_label is not None:
            self._offline_label.text = format_offline(summary.offline_distance)
        if self._height_label is not None:
            self._height_label.text = format_height(summary.max_height)

        # Update launch data
        launch = result.launch_data
        if self._ball_speed_label is not None:
            self._ball_speed_label.text = f"{launch.ball_speed:.1f} mph"
        if self._spin_label is not None:
            self._spin_label.text = f"{launch.backspin:.0f} rpm"
        if self._launch_angle_label is not None:
            self._launch_angle_label.text = f"{launch.vla:.1f}°"

        # Update conditions
        conditions = result.conditions
        if self._temp_label is not None:
            self._temp_label.text = f"{conditions.temp_f:.0f}°F"
        if self._elevation_label is not None:
            self._elevation_label.text = f"{conditions.elevation_ft:.0f} ft"
        if self._wind_label is not None:
            self._wind_label.text = f"{conditions.wind_speed_mph:.0f} mph"

    def format_shot_summary(self, summary: ShotSummary) -> dict[str, str]:
        """Format shot summary data for display.

        Args:
            summary: The shot summary to format.

        Returns:
            Dictionary of formatted values keyed by metric name.
        """
        return {
            "carry_distance": format_distance(summary.carry_distance),
            "total_distance": format_distance(summary.total_distance),
            "roll_distance": format_distance(summary.roll_distance),
            "offline_distance": format_offline(summary.offline_distance),
            "max_height": format_height(summary.max_height),
            "flight_time": f"{summary.flight_time:.1f}s",
            "total_time": f"{summary.total_time:.1f}s",
            "bounce_count": str(summary.bounce_count),
        }

    def format_launch_data(self, launch: LaunchData) -> dict[str, str]:
        """Format launch data for display.

        Args:
            launch: The launch data to format.

        Returns:
            Dictionary of formatted values keyed by metric name.
        """
        return {
            "ball_speed": f"{launch.ball_speed:.1f} mph",
            "vla": f"{launch.vla:.1f}°",
            "hla": f"{launch.hla:.1f}°",
            "backspin": f"{launch.backspin:.0f} rpm",
            "sidespin": f"{launch.sidespin:.0f} rpm",
        }

    def format_conditions(self, conditions: Conditions) -> dict[str, str]:
        """Format environmental conditions for display.

        Args:
            conditions: The conditions to format.

        Returns:
            Dictionary of formatted values keyed by condition name.
        """
        return {
            "temp_f": f"{conditions.temp_f:.0f}°F",
            "elevation_ft": f"{conditions.elevation_ft:.0f} ft",
            "humidity_pct": f"{conditions.humidity_pct:.0f}%",
            "wind_speed_mph": f"{conditions.wind_speed_mph:.0f} mph",
            "wind_dir_deg": f"{conditions.wind_dir_deg:.0f}°",
        }

    async def show_shot(self, result: ShotResult) -> None:
        """Display and animate a shot.

        Plays the ball animation and updates all data displays.

        Args:
            result: The shot result to display.
        """
        self.update_shot_data(result)
        self.update_phase(Phase.FLIGHT)

        if self.animator is not None and self.range_scene is not None:
            await self.animator.animate_shot(
                result,
                scene=self.range_scene,
                on_phase_change=self._on_phase_change,
            )

        self.update_phase(Phase.STOPPED)

    def _on_phase_change(self, phase: Phase) -> None:
        """Handle phase change callback from animator.

        Args:
            phase: The new phase.
        """
        self.update_phase(phase)

    def build(self) -> Any:
        """Create the Open Range view UI.

        Must be called within a NiceGUI context. Creates the complete
        Open Range panel with 3D scene and data displays.

        Returns:
            The container element, or None if not in NiceGUI context.
        """
        try:
            from nicegui import ui

            from gc2_connect.open_range.visualization.ball_animation import (
                BallAnimator,
            )
            from gc2_connect.open_range.visualization.range_scene import RangeScene

            with ui.row().classes("w-full gap-4") as container:
                self._container = container

                # Left: 3D scene
                with ui.column().classes("flex-grow"):
                    self.range_scene = RangeScene(width=800, height=500)
                    self.range_scene.build()
                    self.animator = BallAnimator()

                # Right: Data panels
                with ui.column().classes("w-72 gap-2"):
                    self._build_phase_indicator()
                    self._build_shot_data_panel()
                    self._build_launch_data_panel()
                    self._build_conditions_panel()

            return container

        except ImportError:
            # Not in NiceGUI context - return None for testing
            return None

    def _build_phase_indicator(self) -> None:
        """Build the phase indicator panel."""
        from nicegui import ui

        with ui.card().classes("w-full"):
            ui.label("Phase").classes("text-sm text-gray-400")
            self._phase_label = ui.label("Ready").classes("text-2xl font-bold text-gray-400")

    def _build_shot_data_panel(self) -> None:
        """Build the shot result data panel."""
        from nicegui import ui

        with ui.card().classes("w-full"):
            ui.label("Shot Data").classes("text-sm text-gray-400 mb-2")

            with ui.grid(columns=2).classes("gap-2 w-full"):
                # Carry distance
                with ui.column().classes("gap-0"):
                    ui.label("Carry").classes("text-xs text-gray-500")
                    self._carry_label = ui.label("-- yds").classes("text-lg font-semibold")

                # Total distance
                with ui.column().classes("gap-0"):
                    ui.label("Total").classes("text-xs text-gray-500")
                    self._total_label = ui.label("-- yds").classes("text-lg font-semibold")

                # Offline distance
                with ui.column().classes("gap-0"):
                    ui.label("Offline").classes("text-xs text-gray-500")
                    self._offline_label = ui.label("-- yds").classes("text-lg font-semibold")

                # Max height
                with ui.column().classes("gap-0"):
                    ui.label("Max Height").classes("text-xs text-gray-500")
                    self._height_label = ui.label("-- ft").classes("text-lg font-semibold")

    def _build_launch_data_panel(self) -> None:
        """Build the launch data panel."""
        from nicegui import ui

        with ui.card().classes("w-full"):
            ui.label("Launch Data").classes("text-sm text-gray-400 mb-2")

            with ui.grid(columns=3).classes("gap-2 w-full"):
                # Ball speed
                with ui.column().classes("gap-0"):
                    ui.label("Ball Speed").classes("text-xs text-gray-500")
                    self._ball_speed_label = ui.label("-- mph").classes("text-md font-semibold")

                # Back spin
                with ui.column().classes("gap-0"):
                    ui.label("Spin").classes("text-xs text-gray-500")
                    self._spin_label = ui.label("-- rpm").classes("text-md font-semibold")

                # Launch angle
                with ui.column().classes("gap-0"):
                    ui.label("Launch").classes("text-xs text-gray-500")
                    self._launch_angle_label = ui.label("--°").classes("text-md font-semibold")

    def _build_conditions_panel(self) -> None:
        """Build the environmental conditions panel."""
        from nicegui import ui

        with ui.card().classes("w-full"):
            ui.label("Conditions").classes("text-sm text-gray-400 mb-2")

            with ui.grid(columns=3).classes("gap-2 w-full"):
                # Temperature
                with ui.column().classes("gap-0"):
                    ui.label("Temp").classes("text-xs text-gray-500")
                    self._temp_label = ui.label("70°F").classes("text-md font-semibold")

                # Elevation
                with ui.column().classes("gap-0"):
                    ui.label("Elev").classes("text-xs text-gray-500")
                    self._elevation_label = ui.label("0 ft").classes("text-md font-semibold")

                # Wind
                with ui.column().classes("gap-0"):
                    ui.label("Wind").classes("text-xs text-gray-500")
                    self._wind_label = ui.label("0 mph").classes("text-md font-semibold")

    def reset(self) -> None:
        """Reset the view to initial state."""
        self.current_phase = Phase.STOPPED
        self.last_shot_result = None

        if self.animator is not None:
            self.animator.reset()

        if self.range_scene is not None:
            self.range_scene.reset_ball()

        # Reset UI labels
        if self._phase_label is not None:
            self._phase_label.text = "Ready"
            self._phase_label.classes(remove="text-green-400 text-orange-400 text-blue-400")
            self._phase_label.classes(add="text-gray-400")

        if self._carry_label is not None:
            self._carry_label.text = "-- yds"
        if self._total_label is not None:
            self._total_label.text = "-- yds"
        if self._offline_label is not None:
            self._offline_label.text = "-- yds"
        if self._height_label is not None:
            self._height_label.text = "-- ft"

    def hide(self) -> None:
        """Hide the Open Range view."""
        if self._container is not None:
            self._container.classes(add="hidden")

    def show(self) -> None:
        """Show the Open Range view."""
        if self._container is not None:
            self._container.classes(remove="hidden")
