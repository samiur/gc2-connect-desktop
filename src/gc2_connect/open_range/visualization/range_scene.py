# ABOUTME: 3D driving range environment using NiceGUI Three.js integration.
# ABOUTME: Creates the visual scene with ground plane, distance markers, and lighting.
"""3D driving range environment for Open Range visualization.

This module provides:
- RangeScene: Complete 3D driving range setup
- Distance markers at standard intervals
- Target greens at common distances
- Dark theme friendly lighting
- Coordinate conversion utilities

Coordinate system (Three.js/NiceGUI):
- X: Lateral movement (+ = right)
- Y: Vertical height
- Z: Forward toward targets (+ = away from camera)

Physics coordinate mapping:
- Physics X (forward) -> Scene Z
- Physics Y (height) -> Scene Y
- Physics Z (lateral) -> Scene X
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gc2_connect.open_range.models import Phase, TrajectoryPoint, Vec3
from gc2_connect.open_range.visualization.trajectory_trace import TrajectoryTrace

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

# Tee box configuration (yards)
TEE_BOX_WIDTH: float = 12.0  # Width of tee box area
TEE_BOX_DEPTH: float = 8.0  # Depth of tee box area
TEE_MAT_WIDTH: float = 5.0  # Width of hitting mat
TEE_MAT_DEPTH: float = 3.0  # Depth of hitting mat
TEE_BOX_HEIGHT: float = 0.3  # Slight elevation

# Backdrop configuration (yards)
TREELINE_START_DISTANCE: float = 320.0  # Where trees start
TREELINE_DEPTH: float = 80.0  # How deep the tree forest is
TREE_MIN_HEIGHT: float = 15.0  # Minimum tree height
TREE_MAX_HEIGHT: float = 35.0  # Maximum tree height
TREE_BASE_RADIUS: float = 6.0  # Tree cone base radius
TREES_PER_ROW: int = 25  # Number of trees per row
TREE_ROWS: int = 5  # Number of tree rows

# Cloud configuration
CLOUD_COUNT: int = 12  # Number of cloud clusters
CLOUD_MIN_HEIGHT: float = 80.0  # Minimum cloud height (yards)
CLOUD_MAX_HEIGHT: float = 120.0  # Maximum cloud height (yards)
CLOUD_SPREAD: float = 300.0  # Horizontal spread of clouds (yards)

# Sky dome configuration
SKY_DOME_RADIUS: float = 500.0  # Radius of sky dome (yards)

# Colors
GROUND_COLOR: str = "#3d8c40"  # Bright green fairway (like reference)
MARKER_COLOR: str = "#ffffff"  # White markers
GREEN_COLOR: str = "#2d7030"  # Slightly darker green for targets
BALL_COLOR: str = "#f0f0f0"  # Off-white ball
SKY_COLOR: str = "#87ceeb"  # Sky blue (brighter)
TEE_BOX_COLOR: str = "#2d6830"  # Darker green for tee box
TEE_MAT_COLOR: str = "#4a9050"  # Lighter green hitting mat
TREE_COLOR: str = "#1a5a20"  # Dark green for pine trees
TREE_TRUNK_COLOR: str = "#4a3520"  # Brown for tree trunks
CLOUD_COLOR: str = "#ffffff"  # White clouds
FAIRWAY_STRIPE_LIGHT: str = "#45a048"  # Lighter stripe for mowing pattern
FAIRWAY_STRIPE_DARK: str = "#3d8c40"  # Darker stripe for mowing pattern

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

    Trajectory points use physics coordinates:
    - x: forward distance (yards) -> Scene Z
    - y: height (feet) -> Scene Y
    - z: lateral distance (yards) -> Scene X (negated)

    Args:
        trajectory: List of trajectory points.

    Returns:
        List of Vec3 positions in scene coordinates (X=lateral, Y=height, Z=forward).
    """
    return [
        Vec3(
            x=-yards_to_scene(point.z),  # Physics lateral -> Scene X (negated)
            y=feet_to_scene(point.y),  # Height stays Y
            z=yards_to_scene(point.x),  # Physics forward -> Scene Z
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
        self.trajectory_trace: TrajectoryTrace = TrajectoryTrace()
        # Camera behind tee (negative Z), above ground (positive Y), centered (X=0)
        self._camera_position: Vec3 = Vec3(x=0.0, y=15.0, z=-20.0)

    def build(self) -> Any:
        """Create and return the 3D scene.

        Must be called within a NiceGUI context. Creates the Three.js
        scene with ground, markers, greens, and lighting.

        Returns:
            The NiceGUI scene element, or None if not in NiceGUI context.
        """
        try:
            from nicegui import ui

            self.scene = ui.scene(
                width=self.width,
                height=self.height,
                background_color=SKY_COLOR,
                grid=False,  # Disable grid for cleaner look
            )
            with self.scene:
                self._create_clouds()
                self._create_backdrop()
                self._create_ground()
                self._create_tee_box()
                self._create_distance_markers()
                self._create_target_greens()
                self._setup_lighting()
                self._create_ball()
            self._setup_camera()
            return self.scene
        except ImportError:
            # Not in NiceGUI context - return None for testing
            return None

    def _create_clouds(self) -> None:
        """Create cloud clusters in the sky.

        Creates fluffy cloud formations using grouped spheres,
        similar to the reference implementation.
        """
        if self.scene is None:
            return

        import random

        random.seed(123)  # Consistent cloud placement

        with self.scene:
            from nicegui import ui

            for _ in range(CLOUD_COUNT):
                # Random cloud position
                cloud_x = random.uniform(
                    -yards_to_scene(CLOUD_SPREAD), yards_to_scene(CLOUD_SPREAD)
                )
                cloud_y = yards_to_scene(random.uniform(CLOUD_MIN_HEIGHT, CLOUD_MAX_HEIGHT))
                cloud_z = random.uniform(50, yards_to_scene(TREELINE_START_DISTANCE))

                # Create cloud as cluster of spheres (3-5 puffs per cloud)
                num_puffs = random.randint(3, 5)
                for _j in range(num_puffs):
                    # Offset each puff from cloud center
                    puff_x = cloud_x + random.uniform(-8, 8)
                    puff_y = cloud_y + random.uniform(-2, 2)
                    puff_z = cloud_z + random.uniform(-5, 5)
                    puff_radius = random.uniform(4, 8)

                    ui.scene.sphere(radius=puff_radius).material(CLOUD_COLOR).move(
                        puff_x, puff_y, puff_z
                    )

    def _create_ground(self) -> None:
        """Create the driving range ground plane with mowing stripes.

        Creates a large flat green surface with alternating stripes
        to simulate a mowed fairway pattern.
        """
        if self.scene is None:
            return

        # Ground plane dimensions (in scene units)
        length = yards_to_scene(RANGE_LENGTH_YARDS)
        width = yards_to_scene(RANGE_WIDTH_YARDS)

        with self.scene:
            from nicegui import ui

            # Create striped fairway pattern
            stripe_width = 10.0  # Width of each mowing stripe in yards
            num_stripes = int(RANGE_WIDTH_YARDS / stripe_width)

            for i in range(num_stripes):
                stripe_x = -width / 2 + (i + 0.5) * yards_to_scene(stripe_width)
                # Alternate between light and dark stripes
                color = FAIRWAY_STRIPE_LIGHT if i % 2 == 0 else FAIRWAY_STRIPE_DARK

                ui.scene.box(
                    width=yards_to_scene(stripe_width),
                    height=0.1,
                    depth=length,
                ).material(color).move(
                    stripe_x,
                    -0.05,
                    length / 2,
                )

    def _create_tee_box(self) -> None:
        """Create the tee box area where the ball sits.

        Creates an elevated platform with a hitting mat on top,
        positioned at the origin where shots are taken from.
        """
        if self.scene is None:
            return

        with self.scene:
            from nicegui import ui

            # Tee box platform (slightly elevated, darker green)
            tee_width = yards_to_scene(TEE_BOX_WIDTH)
            tee_depth = yards_to_scene(TEE_BOX_DEPTH)
            tee_height = yards_to_scene(TEE_BOX_HEIGHT)

            ui.scene.box(
                width=tee_width,
                height=tee_height,
                depth=tee_depth,
            ).material(TEE_BOX_COLOR).move(
                0,  # Centered laterally
                tee_height / 2,  # Raised above ground
                -tee_depth / 2,  # Positioned behind origin (ball at front edge)
            )

            # Hitting mat (lighter green, on top of tee box)
            mat_width = yards_to_scene(TEE_MAT_WIDTH)
            mat_depth = yards_to_scene(TEE_MAT_DEPTH)

            ui.scene.box(
                width=mat_width,
                height=0.05,
                depth=mat_depth,
            ).material(TEE_MAT_COLOR).move(
                0,  # Centered on tee box
                tee_height + 0.025,  # On top of tee box
                0,  # Centered at origin (where ball sits)
            )

    def _create_backdrop(self) -> None:
        """Create the backdrop with a forest of pine trees.

        Creates rows of cone-shaped trees at the far end of the range,
        similar to the reference implementations.
        """
        if self.scene is None:
            return

        import random

        # Use fixed seed for consistent tree placement
        random.seed(42)

        with self.scene:
            from nicegui import ui

            range_width = yards_to_scene(RANGE_WIDTH_YARDS)
            start_z = yards_to_scene(TREELINE_START_DISTANCE)
            row_spacing = yards_to_scene(TREELINE_DEPTH) / TREE_ROWS

            # Create multiple rows of trees
            for row in range(TREE_ROWS):
                row_z = start_z + row * row_spacing

                # Trees further back are taller (perspective effect)
                height_scale = 1.0 + (row * 0.15)

                for i in range(TREES_PER_ROW):
                    # Distribute trees across the width with some randomness
                    base_x = -range_width + (i * 2 * range_width / TREES_PER_ROW)
                    x_offset = random.uniform(-8, 8)
                    x = base_x + x_offset

                    # Random height variation
                    height = yards_to_scene(
                        random.uniform(TREE_MIN_HEIGHT, TREE_MAX_HEIGHT) * height_scale
                    )
                    radius = yards_to_scene(TREE_BASE_RADIUS) * (height / 30)

                    # Random z offset within row
                    z_offset = random.uniform(-5, 5)
                    z = row_z + z_offset

                    # Create pine tree as a cone
                    ui.scene.cylinder(
                        top_radius=0,  # Point at top = cone
                        bottom_radius=radius,
                        height=height,
                    ).material(TREE_COLOR).move(x, height / 2, z)

    def _create_distance_markers(self) -> None:
        """Add distance markers at standard intervals.

        Places white markers at each distance to help players
        gauge shot distances. Markers are placed along the Z axis (forward).
        """
        if self.scene is None:
            return

        with self.scene:
            from nicegui import ui

            for distance in DISTANCE_MARKERS:
                # Create marker as a thin white cylinder
                # Distance is along Z axis (forward)
                z = yards_to_scene(distance)
                ui.scene.cylinder(
                    top_radius=0.5,
                    bottom_radius=0.5,
                    height=0.1,
                ).material(MARKER_COLOR).move(0, 0.05, z)

                # Add text label (using a small box as placeholder)
                # Offset slightly to the side (X axis)
                ui.scene.box(
                    width=2,
                    height=0.5,
                    depth=0.1,
                ).material(MARKER_COLOR).move(5, 0.5, z)

    def _create_target_greens(self) -> None:
        """Add target greens at common distances.

        Creates circular darker green areas representing
        target greens that players can aim for. Greens are placed along Z axis.
        """
        if self.scene is None:
            return

        with self.scene:
            from nicegui import ui

            for green in TARGET_GREENS:
                distance = green["distance"]
                radius = green["radius"]
                z = yards_to_scene(distance)  # Distance along Z axis
                r = yards_to_scene(radius)

                # Create green as a flat cylinder
                ui.scene.cylinder(
                    top_radius=r,
                    bottom_radius=r,
                    height=0.05,
                ).material(GREEN_COLOR).move(0, 0.01, z)

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
            # Position above the middle of the range
            self.scene.spot_light(
                intensity=AMBIENT_LIGHT_INTENSITY * 1000,
                distance=500,
                angle=180,  # Wide angle for ambient effect
            ).move(0, 100, 150)  # Above and forward

            # Directional light from above/behind (simulating sun)
            self.scene.spot_light(
                intensity=DIRECTIONAL_LIGHT_INTENSITY * 1000,
                distance=500,
            ).move(0, 150, -50)  # Behind and high up

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
            # Ball sits on top of tee box + mat
            ball_y = yards_to_scene(TEE_BOX_HEIGHT) + 0.05 + 0.5  # tee height + mat + ball radius
            self.ball = ui.scene.sphere(radius=0.5).material(BALL_COLOR).move(0, ball_y, 0)

    def _setup_camera(self) -> None:
        """Set initial camera position behind ball.

        Positions the camera behind and above the tee box
        for a good view of the range. Camera looks forward along Z axis.
        """
        if self.scene is None:
            return

        # Initial camera position: behind (negative Z) and above tee
        # Looking forward along Z axis toward the range
        # up_y=1 keeps Y as "up" to prevent scene rotation
        self.scene.move_camera(
            x=self._camera_position.x,
            y=self._camera_position.y,
            z=self._camera_position.z,
            look_at_x=0,  # Centered laterally
            look_at_y=5,  # Slightly above ground
            look_at_z=100,  # Look forward toward range
            up_x=0,
            up_y=1,
            up_z=0,
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
            # up_y=1 keeps Y as "up" to prevent scene rotation during animation
            self.scene.move_camera(
                x=position.x,
                y=position.y,
                z=position.z,
                look_at_x=look_at.x,
                look_at_y=look_at.y,
                look_at_z=look_at.z,
                up_x=0,
                up_y=1,
                up_z=0,
            )

    def draw_trajectory_line(
        self, trajectory: list[TrajectoryPoint], sample_interval: int = 5
    ) -> None:
        """Draw the trajectory path line.

        Uses small spheres as "breadcrumbs" along the path, colored by phase.
        This creates a visible trace showing the complete ball flight.

        Args:
            trajectory: List of trajectory points with phase information.
            sample_interval: Draw every Nth point (default 5 for performance).
        """
        if self.scene is None or len(trajectory) < 2:
            return

        # Build trace from trajectory
        self.trajectory_trace.build_from_trajectory(trajectory, sample_interval)

        # Draw all segments in the scene
        self.trajectory_trace.draw_in_scene(self.scene)

    def add_trajectory_point(self, position: Vec3, phase: Phase) -> None:
        """Add a point to the trajectory trace progressively.

        Call this during animation to build the trace as the ball moves.
        Each point creates a new segment from the previous point.

        Args:
            position: Ball position in scene coordinates.
            phase: Current phase of ball motion.
        """
        if self.scene is None:
            return

        # Add point to trace
        self.trajectory_trace.add_point(position, phase)

        # Draw the new segment if one was created
        if self.trajectory_trace.segments:
            latest_segment = self.trajectory_trace.segments[-1]
            self.trajectory_trace.draw_segment_in_scene(self.scene, latest_segment)

    def clear_trajectory_line(self) -> None:
        """Remove the current trajectory line from scene."""
        self.trajectory_trace.clear()

    def reset_ball(self) -> None:
        """Reset ball to starting position on tee box."""
        ball_y = yards_to_scene(TEE_BOX_HEIGHT) + 0.05 + 0.5  # tee height + mat + ball radius
        self.update_ball_position(Vec3(x=0.0, y=ball_y, z=0.0))

    @property
    def camera_position(self) -> Vec3:
        """Get current camera position."""
        return self._camera_position
