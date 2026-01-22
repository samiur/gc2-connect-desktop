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
- Shot classification display (shot name, rank badge with colors)
- Camera view controls (5 presets: Behind Ball, Tee Box, Follow, Overhead, Green)
- Minimap with shot dispersion visualization

The view integrates with RangeScene and BallAnimator for visualization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gc2_connect.open_range.models import (
    Conditions,
    DerivedShotData,
    LaunchData,
    Phase,
    ShotResult,
    ShotSummary,
    Vec3,
)
from gc2_connect.open_range.visualization.camera import CameraMode, get_mode_display_name
from gc2_connect.open_range.visualization.minimap import MinimapRenderer

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

# Rank colors as Tailwind CSS classes
# S+=gold, S=silver, A=green, B=blue, C=purple, D=orange, E=red
RANK_COLORS: dict[str, str] = {
    "S+": "text-yellow-400",
    "S": "text-gray-300",
    "A": "text-green-400",
    "B": "text-blue-400",
    "C": "text-purple-400",
    "D": "text-orange-400",
    "E": "text-red-400",
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

        # Minimap renderer
        self.minimap: MinimapRenderer = MinimapRenderer()

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

        # Shot classification UI element references
        self._shot_name_label: Any = None
        self._shot_rank_label: Any = None
        self._smash_factor_label: Any = None
        self._classification_panel: Any = None

        # Camera controls UI element references
        self._camera_mode_label: Any = None
        self._camera_mode_select: Any = None

        # Minimap UI element references
        self._minimap_container: Any = None
        self._minimap_canvas: Any = None
        self._minimap_toggle: Any = None

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

        # Update shot classification (from OpenGolfCoach)
        self._update_shot_classification(result.derived)

    def _update_shot_classification(self, derived: DerivedShotData | None) -> None:
        """Update shot classification display with derived data.

        Args:
            derived: The derived shot data from OpenGolfCoach, or None.
        """
        if derived is None:
            # No derived data - show placeholders
            if self._shot_name_label is not None:
                self._shot_name_label.text = "--"
            if self._shot_rank_label is not None:
                self._shot_rank_label.text = "--"
                # Reset to default color
                for color in RANK_COLORS.values():
                    self._shot_rank_label.classes(remove=color)
                self._shot_rank_label.classes(add="text-gray-400")
            if self._smash_factor_label is not None:
                self._smash_factor_label.text = "--"
            return

        # Update shot name
        if self._shot_name_label is not None:
            self._shot_name_label.text = derived.shot_name

        # Update shot rank with color coding
        if self._shot_rank_label is not None:
            self._shot_rank_label.text = derived.shot_rank
            # Update rank color
            for color in RANK_COLORS.values():
                self._shot_rank_label.classes(remove=color)
            rank_color = self.get_rank_color(derived.shot_rank)
            self._shot_rank_label.classes(add=rank_color)

        # Update smash factor
        if self._smash_factor_label is not None:
            self._smash_factor_label.text = self.format_smash_factor(derived.smash_factor)

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

    def format_shot_classification(self, derived: DerivedShotData | None) -> dict[str, str] | None:
        """Format shot classification data for display.

        Args:
            derived: The derived shot data from OpenGolfCoach, or None.

        Returns:
            Dictionary of formatted values, or None if no derived data.
        """
        if derived is None:
            return None

        return {
            "shot_name": derived.shot_name,
            "shot_rank": derived.shot_rank,
        }

    def format_smash_factor(self, smash_factor: float | None) -> str:
        """Format smash factor for display.

        Args:
            smash_factor: The smash factor value, or None.

        Returns:
            Formatted string with smash factor or placeholder.
        """
        if smash_factor is None:
            return "--"
        return f"{smash_factor:.2f}"

    def format_derived_summary(self, derived: DerivedShotData | None) -> dict[str, str] | None:
        """Format full derived data summary for display.

        Args:
            derived: The derived shot data from OpenGolfCoach, or None.

        Returns:
            Dictionary of formatted values, or None if no derived data.
        """
        if derived is None:
            return None

        return {
            "shot_name": derived.shot_name,
            "shot_rank": derived.shot_rank,
            "smash_factor": self.format_smash_factor(derived.smash_factor),
        }

    def get_rank_color(self, rank: str) -> str:
        """Get the Tailwind color class for a rank.

        Args:
            rank: The rank string (S+, S, A, B, C, D, E).

        Returns:
            Tailwind CSS color class for the rank.
        """
        return RANK_COLORS.get(rank, "text-gray-400")

    def set_camera_mode(self, mode: CameraMode) -> None:
        """Set the camera mode and update UI.

        Args:
            mode: The camera mode to switch to.
        """
        if self.animator is not None:
            self.animator.set_camera_mode(mode)
            self._apply_camera_to_scene()
            self._update_camera_mode_display()

    def cycle_camera_mode(self) -> None:
        """Cycle to the next camera mode."""
        if self.animator is not None:
            self.animator.cycle_camera_mode()
            self._apply_camera_to_scene()
            self._update_camera_mode_display()

    def _apply_camera_to_scene(self) -> None:
        """Apply current camera position to scene."""
        if self.animator is not None and self.range_scene is not None:
            camera_pos, look_at = self.animator.get_camera_position()
            self.range_scene.update_camera(camera_pos, look_at)

    def _update_camera_mode_display(self) -> None:
        """Update the camera mode label in UI."""
        if self._camera_mode_label is not None and self.animator is not None:
            mode_name = self.animator.get_camera_mode_name()
            self._camera_mode_label.text = mode_name

    def toggle_minimap(self) -> None:
        """Toggle minimap visibility."""
        self.minimap.set_visible(not self.minimap.visible)
        self._update_minimap_visibility()

    def _update_minimap_visibility(self) -> None:
        """Update minimap container visibility in UI."""
        if self._minimap_container is not None:
            if self.minimap.visible:
                self._minimap_container.classes(remove="hidden")
            else:
                self._minimap_container.classes(add="hidden")

    def update_minimap_positions(
        self,
        ball_position: Vec3 | None = None,
        target_position: Vec3 | None = None,
    ) -> None:
        """Update minimap with current ball and target positions.

        Args:
            ball_position: Current ball position, or None to keep current.
            target_position: Target position, or None to keep current.
        """
        if ball_position is not None:
            self.minimap.update_ball_position(ball_position)
        if target_position is not None:
            self.minimap.update_target_position(target_position)

    def add_landing_marker(self, position: Vec3) -> None:
        """Add a shot landing marker to the minimap.

        Args:
            position: Landing position in world coordinates.
        """
        self.minimap.add_landing_marker(position)

    def clear_landing_markers(self) -> None:
        """Clear all landing markers from the minimap."""
        self.minimap.clear_landing_markers()

    async def show_shot(self, result: ShotResult) -> None:
        """Display and animate a shot.

        Plays the ball animation and updates all data displays.
        Also adds landing marker to minimap for dispersion view.

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

        # Add landing position to minimap for dispersion visualization
        if result.trajectory:
            final_pos = result.trajectory[-1]
            # Convert to scene coordinates for minimap
            from gc2_connect.open_range.visualization.range_scene import (
                feet_to_scene,
                yards_to_scene,
            )

            landing_pos = Vec3(
                x=-yards_to_scene(final_pos.z),  # Physics lateral -> Scene X
                y=feet_to_scene(final_pos.y),
                z=yards_to_scene(final_pos.x),  # Physics forward -> Scene Z
            )
            self.add_landing_marker(landing_pos)

    def _on_phase_change(self, phase: Phase) -> None:
        """Handle phase change callback from animator.

        Args:
            phase: The new phase.
        """
        self.update_phase(phase)

    def build(self) -> Any:
        """Create the Open Range view UI.

        Must be called within a NiceGUI context. Creates the complete
        Open Range panel with 3D scene, data displays, camera controls,
        and minimap.

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

                # Left: 3D scene with camera controls
                with ui.column().classes("flex-grow"):
                    # Camera controls row above scene
                    self._build_camera_controls()

                    # 3D scene
                    self.range_scene = RangeScene(width=800, height=500)
                    self.range_scene.build()
                    self.animator = BallAnimator()

                    # Minimap overlay (positioned at bottom-right of scene)
                    self._build_minimap()

                # Right: Data panels
                with ui.column().classes("w-72 gap-2"):
                    self._build_phase_indicator()
                    self._build_shot_classification_panel()
                    self._build_shot_data_panel()
                    self._build_launch_data_panel()
                    self._build_conditions_panel()

            return container

        except ImportError:
            # Not in NiceGUI context - return None for testing
            return None

    def _build_camera_controls(self) -> None:
        """Build the camera mode controls row."""
        from nicegui import ui

        with ui.row().classes("w-full items-center gap-4 mb-2"):
            ui.label("Camera:").classes("text-sm text-gray-400")

            # Camera mode display
            self._camera_mode_label = ui.label("Tee Box").classes(
                "text-sm font-semibold text-white bg-gray-700 px-2 py-1 rounded"
            )

            # Camera mode selector dropdown
            camera_options = {mode.value: get_mode_display_name(mode) for mode in CameraMode}
            self._camera_mode_select = ui.select(
                options=camera_options,
                value=CameraMode.TEE_BOX.value,
                on_change=lambda e: self.set_camera_mode(CameraMode(e.value)),
            ).classes("w-32")

            # Cycle button
            ui.button(
                "Next View",
                on_click=self.cycle_camera_mode,
            ).classes("text-xs")

            # Spacer
            ui.space()

            # Minimap toggle
            self._minimap_toggle = ui.switch(
                "Minimap",
                value=True,
                on_change=lambda _: self.toggle_minimap(),
            ).classes("text-xs")

    def _build_minimap(self) -> None:
        """Build the minimap overlay container."""
        from nicegui import ui

        # Minimap container with styling from MinimapRenderer
        styles = self.minimap.get_css_styles()
        style_str = "; ".join(f"{k}: {v}" for k, v in styles.items())

        with ui.element("div").style(style_str) as minimap_container:
            self._minimap_container = minimap_container

            # Canvas for minimap rendering
            # The actual rendering happens in JavaScript via Three.js
            # This provides the container and placeholder
            with ui.element("div").classes("w-full h-full relative"):
                # Placeholder showing minimap info
                ui.label("Minimap").classes("absolute top-1 left-1 text-xs text-white/50")

                # Ball position indicator (simplified 2D)
                # Full 3D minimap rendering would require additional Three.js setup
                with (
                    ui.element("div")
                    .classes("absolute w-2 h-2 bg-white rounded-full")
                    .style("top: 50%; left: 50%; transform: translate(-50%, -50%)")
                ):
                    pass  # Ball marker

                # Target indicator
                with (
                    ui.element("div")
                    .classes("absolute w-3 h-3 border-2 border-red-500 rounded-full")
                    .style("top: 20%; left: 50%; transform: translate(-50%, -50%)")
                ):
                    pass  # Target marker

    def _build_phase_indicator(self) -> None:
        """Build the phase indicator panel."""
        from nicegui import ui

        with ui.card().classes("w-full"):
            ui.label("Phase").classes("text-sm text-gray-400")
            self._phase_label = ui.label("Ready").classes("text-2xl font-bold text-gray-400")

    def _build_shot_classification_panel(self) -> None:
        """Build the shot classification panel with rank badge."""
        from nicegui import ui

        with ui.card().classes("w-full") as panel:
            self._classification_panel = panel
            ui.label("Shot Classification").classes("text-sm text-gray-400 mb-2")

            with ui.row().classes("items-center gap-3 w-full"):
                # Shot name (main classification)
                with ui.column().classes("gap-0 flex-grow"):
                    ui.label("Shot Type").classes("text-xs text-gray-500")
                    self._shot_name_label = ui.label("--").classes("text-lg font-semibold")

                # Rank badge with color coding
                with ui.column().classes("gap-0 items-center"):
                    ui.label("Rank").classes("text-xs text-gray-500")
                    self._shot_rank_label = ui.label("--").classes(
                        "text-xl font-bold text-gray-400"
                    )

            # Smash factor row
            with ui.row().classes("mt-2 w-full"), ui.column().classes("gap-0"):
                ui.label("Smash Factor").classes("text-xs text-gray-500")
                self._smash_factor_label = ui.label("--").classes("text-md font-semibold")

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
            # Reset camera to default mode
            self.animator.set_camera_mode(CameraMode.TEE_BOX)

        if self.range_scene is not None:
            self.range_scene.reset_ball()
            # Reset camera position
            self._apply_camera_to_scene()

        # Reset minimap
        self.minimap.clear_landing_markers()
        self.minimap.update_ball_position(Vec3(x=0.0, y=0.0, z=0.0))

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

        # Reset classification labels
        if self._shot_name_label is not None:
            self._shot_name_label.text = "--"
        if self._shot_rank_label is not None:
            self._shot_rank_label.text = "--"
            for color in RANK_COLORS.values():
                self._shot_rank_label.classes(remove=color)
            self._shot_rank_label.classes(add="text-gray-400")
        if self._smash_factor_label is not None:
            self._smash_factor_label.text = "--"

        # Reset camera mode display
        self._update_camera_mode_display()

    def hide(self) -> None:
        """Hide the Open Range view."""
        if self._container is not None:
            self._container.classes(add="hidden")

    def show(self) -> None:
        """Show the Open Range view."""
        if self._container is not None:
            self._container.classes(remove="hidden")
