# ABOUTME: 3D driving range environment using NiceGUI Three.js integration.
# ABOUTME: Creates the visual scene with ground plane, distance markers, and lighting.
"""3D driving range environment for Open Range visualization.

This module provides:
- RangeScene: Complete 3D driving range setup
- Distance markers at standard intervals
- Target greens at common distances
- Dark theme friendly lighting
- Coordinate conversion utilities

Coordinate system:
- X: Forward toward targets (yards)
- Y: Vertical height (feet)
- Z: Lateral movement (+ = right)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gc2_connect.open_range.models import TrajectoryPoint, Vec3

if TYPE_CHECKING:
    pass


# Range dimensions (yards)
RANGE_LENGTH_YARDS: int = 400
RANGE_WIDTH_YARDS: int = 100

# Distance markers (yards)
DISTANCE_MARKERS: list[int] = [50, 100, 150, 200, 250, 300, 350]

# Target greens configuration: distance and radius in yards
TARGET_GREENS: list[dict[str, float]] = [
    {"distance": 75.0, "radius": 8.0},
    {"distance": 125.0, "radius": 10.0},
    {"distance": 175.0, "radius": 12.0},
    {"distance": 225.0, "radius": 12.0},
    {"distance": 275.0, "radius": 15.0},
]

# Lighting configuration
AMBIENT_LIGHT_INTENSITY: float = 0.5
DIRECTIONAL_LIGHT_INTENSITY: float = 0.8

# Colors (dark theme friendly)
GROUND_COLOR: str = "#2d5a27"  # Dark green fairway
MARKER_COLOR: str = "#ffffff"  # White markers
GREEN_COLOR: str = "#1a4d1a"  # Darker green for targets
BALL_COLOR: str = "#f0f0f0"  # Off-white ball
SKY_COLOR: str = "#1a2632"  # Dark blue-gray sky

# Scene scale: 1 yard = 1 scene unit
SCENE_SCALE: float = 1.0
# Feet to yards conversion
FEET_PER_YARD: float = 3.0


def yards_to_scene(yards: float) -> float:
    """Convert yards to scene units.

    Args:
        yards: Distance in yards.

    Returns:
        Distance in scene units.
    """
    return yards * SCENE_SCALE


def feet_to_scene(feet: float) -> float:
    """Convert feet to scene units.

    Args:
        feet: Distance in feet.

    Returns:
        Distance in scene units.
    """
    return (feet / FEET_PER_YARD) * SCENE_SCALE


def trajectory_to_scene_coords(trajectory: list[TrajectoryPoint]) -> list[Vec3]:
    """Convert trajectory points to scene coordinates.

    Trajectory points use:
    - x: forward distance (yards)
    - y: height (feet)
    - z: lateral distance (yards)

    Args:
        trajectory: List of trajectory points.

    Returns:
        List of Vec3 positions in scene coordinates.
    """
    return [
        Vec3(
            x=yards_to_scene(point.x),
            y=feet_to_scene(point.y),
            z=yards_to_scene(point.z),
        )
        for point in trajectory
    ]


class RangeScene:
    """3D driving range environment.

    Creates a complete driving range scene with:
    - Green fairway ground plane
    - Distance markers every 50 yards
    - Target greens at common distances
    - Appropriate lighting for dark theme

    The scene is built using NiceGUI's ui.scene() Three.js integration.
    When build() is called without NiceGUI context, it prepares the
    scene configuration but doesn't create the actual 3D elements.

    Example:
        scene = RangeScene(width=800, height=600)
        # In NiceGUI context:
        ui_scene = scene.build()
    """

    def __init__(self, width: int = 800, height: int = 600) -> None:
        """Initialize the range scene.

        Args:
            width: Scene viewport width in pixels.
            height: Scene viewport height in pixels.
        """
        self.width = width
        self.height = height
        self.scene: Any = None
        self.ball: Any = None
        self.trajectory_line: Any = None
        self._camera_position: Vec3 = Vec3(x=-10.0, y=10.0, z=0.0)

    def build(self) -> Any:
        """Create and return the 3D scene.

        Must be called within a NiceGUI context. Creates the Three.js
        scene with ground, markers, greens, and lighting.

        Returns:
            The NiceGUI scene element, or None if not in NiceGUI context.
        """
        try:
            from nicegui import ui

            self.scene = ui.scene(width=self.width, height=self.height)
            with self.scene:
                self._create_ground()
                self._create_distance_markers()
                self._create_target_greens()
                self._setup_lighting()
                self._create_ball()
            self._setup_camera()
            return self.scene
        except ImportError:
            # Not in NiceGUI context - return None for testing
            return None

    def _create_ground(self) -> None:
        """Create the driving range ground plane.

        Creates a large flat green surface extending the full length
        and width of the range.
        """
        if self.scene is None:
            return

        # Ground plane dimensions
        length = yards_to_scene(RANGE_LENGTH_YARDS)
        width = yards_to_scene(RANGE_WIDTH_YARDS)

        with self.scene:
            from nicegui import ui

            # Create ground as a flat box (thin plane)
            ui.scene.box(
                width=width,
                height=0.1,  # Very thin
                depth=length,
            ).material(GROUND_COLOR).move(
                length / 2,  # Center at half length (forward)
                -0.05,  # Slightly below y=0
                0,  # Centered laterally
            )

    def _create_distance_markers(self) -> None:
        """Add distance markers at standard intervals.

        Places white markers at each distance to help players
        gauge shot distances.
        """
        if self.scene is None:
            return

        with self.scene:
            from nicegui import ui

            for distance in DISTANCE_MARKERS:
                # Create marker as a thin white cylinder
                x = yards_to_scene(distance)
                ui.scene.cylinder(
                    top_radius=0.5,
                    bottom_radius=0.5,
                    height=0.1,
                ).material(MARKER_COLOR).move(x, 0.05, 0)

                # Add text label (using a small box as placeholder)
                # Note: NiceGUI's scene.text is limited; use alternative
                ui.scene.box(
                    width=2,
                    height=0.5,
                    depth=0.1,
                ).material(MARKER_COLOR).move(x, 0.5, 5)

    def _create_target_greens(self) -> None:
        """Add target greens at common distances.

        Creates circular darker green areas representing
        target greens that players can aim for.
        """
        if self.scene is None:
            return

        with self.scene:
            from nicegui import ui

            for green in TARGET_GREENS:
                distance = green["distance"]
                radius = green["radius"]
                x = yards_to_scene(distance)
                r = yards_to_scene(radius)

                # Create green as a flat cylinder
                ui.scene.cylinder(
                    top_radius=r,
                    bottom_radius=r,
                    height=0.05,
                ).material(GREEN_COLOR).move(x, 0.01, 0)

    def _setup_lighting(self) -> None:
        """Configure scene lighting for dark theme.

        Sets up ambient light for general visibility and
        directional light to simulate natural lighting.
        """
        if self.scene is None:
            return

        with self.scene:
            # NiceGUI's scene uses spot_light (no point_light available)
            # Use a wide-angle spot light as ambient simulation
            self.scene.spot_light(
                intensity=AMBIENT_LIGHT_INTENSITY * 1000,
                distance=500,
                angle=180,  # Wide angle for ambient effect
            ).move(0, 50, 0)

            # Directional light from above/behind
            self.scene.spot_light(
                intensity=DIRECTIONAL_LIGHT_INTENSITY * 1000,
                distance=500,
            ).move(-50, 100, 0)

    def _create_ball(self) -> None:
        """Create the golf ball sphere.

        Creates a white sphere that will be animated along
        the trajectory path.
        """
        if self.scene is None:
            return

        with self.scene:
            from nicegui import ui

            # Golf ball radius ~0.85 inches = ~0.024 yards
            # Use larger size for visibility in scene
            self.ball = ui.scene.sphere(radius=0.5).material(BALL_COLOR).move(0, 0.5, 0)

    def _setup_camera(self) -> None:
        """Set initial camera position behind ball.

        Positions the camera behind and above the tee box
        for a good view of the range.
        """
        if self.scene is None:
            return

        # Initial camera position: behind and above tee
        self.scene.move_camera(
            x=self._camera_position.x,
            y=self._camera_position.y,
            z=self._camera_position.z,
            look_at_x=50,  # Look toward middle of range
            look_at_y=5,
            look_at_z=0,
        )

    def update_ball_position(self, position: Vec3) -> None:
        """Update the ball's position in the scene.

        Args:
            position: New ball position in scene coordinates.
        """
        if self.ball is not None:
            self.ball.move(position.x, position.y, position.z)

    def update_camera(self, position: Vec3, look_at: Vec3) -> None:
        """Update the camera position and target.

        Args:
            position: Camera position in scene coordinates.
            look_at: Point the camera should look at.
        """
        if self.scene is not None:
            self._camera_position = position
            self.scene.move_camera(
                x=position.x,
                y=position.y,
                z=position.z,
                look_at_x=look_at.x,
                look_at_y=look_at.y,
                look_at_z=look_at.z,
            )

    def draw_trajectory_line(self, points: list[Vec3]) -> None:
        """Draw the trajectory path line.

        Args:
            points: List of positions forming the trajectory.
        """
        if self.scene is None or len(points) < 2:
            return

        # Clear existing trajectory line
        if self.trajectory_line is not None:
            try:
                self.trajectory_line.delete()
            except Exception:
                pass

        # Draw new line using connected cylinders
        # Note: NiceGUI's scene doesn't have a direct line API
        # For now, we skip the trajectory line as it requires
        # more complex Three.js integration
        pass

    def reset_ball(self) -> None:
        """Reset ball to starting position."""
        self.update_ball_position(Vec3(x=0.0, y=0.5, z=0.0))

    @property
    def camera_position(self) -> Vec3:
        """Get current camera position."""
        return self._camera_position
