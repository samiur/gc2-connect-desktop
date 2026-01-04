# GC2 Connect Desktop - Implementation Plan

> **Related Documentation:**
> - `docs/PRD.md` - Product requirements (v1.0)
> - `docs/TRD.md` - Technical requirements (v1.0)
> - `docs/PRD_OPEN_RANGE.md` - Open Range feature requirements
> - `docs/TRD_OPEN_RANGE.md` - Open Range technical requirements
> - `docs/PHYSICS.md` - Golf ball physics specification
> - `docs/GC2_PROTOCOL.md` - USB protocol specification
> - `todo.md` - Implementation tracking

## Project Summary

GC2 Connect Desktop is a Python application that reads shot data from a Foresight GC2 golf launch monitor via USB and sends it to GSPro golf simulation software over the network. Version 1.1 adds Open Range - a built-in driving range simulator with physics-accurate ball flight visualization.

## Current State Analysis

The project has an initial implementation with the following components:

### Already Implemented
- **models.py**: Data models (GC2ShotData, GSProShotMessage, GSProResponse, etc.)
- **gc2/usb_reader.py**: USB reader with GC2USBReader and MockGC2Reader classes
- **gspro/client.py**: GSPro TCP client for Open Connect API v1
- **ui/app.py**: NiceGUI interface with connection panels, shot display, shot history
- **config/settings.py**: Settings persistence with platform-specific paths
- **tools/mock_gspro_server.py**: Mock GSPro server for testing
- **Testing infrastructure**: pytest, mypy, ruff configured
- **Unit tests**: Models, GC2 protocol, GSPro client

### Missing/Incomplete
- **Auto-reconnection**: Not fully implemented
- **Integration tests**: Not complete
- **Shot history improvements**: Basic implementation only
- **CSV export**: Not implemented
- **Open Range**: New feature - not started

## Implementation Phases

### Phase 1: Foundation & Testing Infrastructure ✅
Set up proper testing, linting, and type checking. Add tests for existing code.

### Phase 2: Configuration & Settings ✅
Implement settings persistence so users don't need to reconfigure each session.

### Phase 3: Reliability & Error Handling
Add auto-reconnection logic and improve error handling.

### Phase 4: GSPro Features
Integration tests, shot history improvements, CSV export.

### Phase 5: Open Range Feature (NEW)
Implement built-in driving range with physics simulation and 3D visualization.

### Phase 6: Polish & Packaging
Final testing, documentation, and packaging for distribution.

---

# Prompts

## Prompt 1: Project Setup & Testing Infrastructure ✅

```text
We are building a Python desktop app called GC2 Connect that reads data from a GC2 golf launch monitor via USB and sends it to GSPro. The project already has initial implementation files. Your task is to set up proper testing infrastructure.

CONTEXT:
- We use uv for package management (not pip/poetry)
- pyproject.toml exists with basic dependencies
- Tests should use pytest and pytest-asyncio
- We practice TDD - tests are critical

TASK:
1. Update pyproject.toml to add missing dev dependencies:
   - mypy
   - pytest-cov (for coverage)
   - types-* stubs as needed

2. Create pytest configuration in pyproject.toml:
   - Configure pytest-asyncio
   - Set up test paths
   - Configure coverage

3. Create a basic test structure:
   - tests/__init__.py
   - tests/conftest.py with common fixtures
   - tests/unit/__init__.py
   - tests/integration/__init__.py

4. Add mypy configuration to pyproject.toml:
   - Enable strict mode
   - Configure pydantic plugin

5. Add ruff configuration for linting

6. Create a simple test that verifies the test infrastructure works:
   - tests/unit/test_smoke.py with a basic passing test

7. Verify everything works:
   - Run: uv run pytest
   - Run: uv run mypy src/
   - Run: uv run ruff check .

REQUIREMENTS:
- All code files must start with a 2-line ABOUTME comment
- Do not modify existing implementation files yet
- Focus only on infrastructure setup
```

---

## Prompt 2: Add ABOUTME Comments to Existing Files ✅

```text
The codebase requires all Python files to start with a 2-line ABOUTME comment explaining what the file does. Each line should start with "ABOUTME: ".

TASK:
Add ABOUTME comments to the beginning of all existing Python files:

1. src/gc2_connect/__init__.py
2. src/gc2_connect/main.py
3. src/gc2_connect/models.py
4. src/gc2_connect/gc2/__init__.py
5. src/gc2_connect/gc2/usb_reader.py
6. src/gc2_connect/gspro/__init__.py
7. src/gc2_connect/gspro/client.py
8. src/gc2_connect/ui/__init__.py
9. src/gc2_connect/ui/app.py
10. src/gc2_connect/config/__init__.py
11. tools/mock_gspro_server.py

EXAMPLE FORMAT:
```python
# ABOUTME: This module handles USB communication with the GC2 launch monitor.
# ABOUTME: It provides classes for reading shot data and detecting the device.
```

REQUIREMENTS:
- Comments should be concise and descriptive
- Do not modify any other code in the files
- Run linting after to ensure no issues introduced
```

---

## Prompt 3: Unit Tests for Data Models ✅

```text
Write comprehensive unit tests for the data models in src/gc2_connect/models.py.

CONTEXT:
The models.py file contains:
- GC2ShotData: Shot data from the GC2 (ball speed, spin, angles, etc.)
- GSProBallData, GSProClubData, GSProShotOptions: GSPro API data structures
- GSProShotMessage: Complete message for GSPro API
- GSProResponse: Response from GSPro

TASK:
Create tests/unit/test_models.py with tests for:

1. GC2ShotData:
   - Test creation with default values
   - Test from_gc2_dict() parsing with ball data only
   - Test from_gc2_dict() parsing with HMT (club) data
   - Test spin_axis property calculation
   - Test is_valid() rejects zero spin
   - Test is_valid() rejects unrealistic speeds
   - Test is_valid() accepts valid shots
   - Test has_club_data property

2. GSProShotMessage:
   - Test from_gc2_shot() conversion without club data
   - Test from_gc2_shot() conversion with club data
   - Test to_dict() produces correct JSON structure

3. GSProResponse:
   - Test from_dict() parsing
   - Test is_success property for various codes

REQUIREMENTS:
- Use pytest fixtures for common test data
- Test edge cases (zero values, negative values, missing fields)
- Add fixtures to conftest.py if needed
- Run tests and verify they pass: uv run pytest tests/unit/test_models.py -v
```

---

## Prompt 4: Unit Tests for GC2 Protocol Parsing ✅

```text
Write unit tests for the GC2 USB reader's protocol parsing functionality.

CONTEXT:
The gc2/usb_reader.py contains parse_data() method that converts raw GC2 text data into GC2ShotData objects. The protocol format is:
- ASCII text, key=value pairs, newline-separated
- Fields: SHOT_ID, SPEED_MPH, ELEVATION_DEG, AZIMUTH_DEG, SPIN_RPM, BACK_RPM, SIDE_RPM
- HMT fields: CLUBSPEED_MPH, HPATH_DEG, VPATH_DEG, FACE_T_DEG, LIE_DEG, LOFT_DEG, HMT

TASK:
Create tests/unit/test_gc2_protocol.py with tests for:

1. Basic parsing:
   - Parse valid ball-only data
   - Parse valid data with HMT
   - Handle empty input
   - Handle malformed lines (no = sign)

2. Validation:
   - Reject zero spin (misread)
   - Reject unrealistic ball speed
   - Accept valid shots

3. Edge cases:
   - Handle extra whitespace
   - Handle unknown fields (should be ignored)
   - Handle partial data

4. Duplicate detection:
   - Same SHOT_ID should be detected as duplicate

SAMPLE TEST DATA (add as fixtures):
```python
VALID_BALL_ONLY = """
SHOT_ID=1
SPEED_MPH=145.2
ELEVATION_DEG=11.8
AZIMUTH_DEG=1.5
SPIN_RPM=2650
BACK_RPM=2480
SIDE_RPM=-320
"""

VALID_WITH_HMT = """
SHOT_ID=2
SPEED_MPH=150.5
ELEVATION_DEG=12.3
AZIMUTH_DEG=2.1
SPIN_RPM=2800
BACK_RPM=2650
SIDE_RPM=-400
CLUBSPEED_MPH=105.2
HPATH_DEG=3.1
VPATH_DEG=-4.2
FACE_T_DEG=1.5
LIE_DEG=0.5
LOFT_DEG=15.2
HMT=1
"""

INVALID_ZERO_SPIN = """
SHOT_ID=3
SPEED_MPH=145.0
ELEVATION_DEG=12.0
AZIMUTH_DEG=0.0
SPIN_RPM=0
BACK_RPM=0
SIDE_RPM=0
"""
```

REQUIREMENTS:
- Tests should be independent and isolated
- Use descriptive test names
- Run tests: uv run pytest tests/unit/test_gc2_protocol.py -v
```

---

## Prompt 5: Unit Tests for GSPro Client ✅

```text
Write unit tests for the GSPro client in src/gc2_connect/gspro/client.py.

CONTEXT:
GSProClient handles TCP socket communication with GSPro using the Open Connect API v1:
- Connects to GSPro on a configurable host:port (default 921)
- Sends shot data as JSON, newline-delimited
- Receives JSON responses with status codes

TASK:
Create tests/unit/test_gspro_client.py with tests for:

1. Client initialization:
   - Test default host and port
   - Test custom host and port

2. Connection state:
   - Test is_connected property when not connected
   - Test shot_number starts at 0

3. Message formatting:
   - Test that send_shot increments shot_number
   - Test heartbeat message structure

4. Response parsing:
   - Test GSProResponse parsing for success (200)
   - Test GSProResponse parsing for error codes
   - Test Player info extraction from response

NOTE: These are UNIT tests, not integration tests. Mock the socket.
You can use unittest.mock to mock socket operations.

Create a mock socket fixture in conftest.py that can be used to test
without actual network connections.

REQUIREMENTS:
- Use mocking for socket operations
- Test error handling paths
- Run tests: uv run pytest tests/unit/test_gspro_client.py -v
```

---

## Prompt 6: Settings Module Implementation ✅

```text
Implement the settings persistence module for GC2 Connect.

CONTEXT:
- Settings should be saved to a JSON file in platform-appropriate locations
- macOS: ~/Library/Application Support/GC2 Connect/settings.json
- Linux: ~/.config/gc2-connect/settings.json
- We use pydantic-settings for settings management

TASK:

1. First, write tests in tests/unit/test_settings.py:
   - Test Settings model default values
   - Test Settings.load() creates defaults if file doesn't exist
   - Test Settings.save() writes to file
   - Test Settings roundtrip (save then load)
   - Test settings file location per platform

2. Then implement src/gc2_connect/config/settings.py:
   - Create Settings class using pydantic-settings BaseSettings
   - Include GSPro settings: host, port, auto_connect
   - Include GC2 settings: auto_connect, reject_zero_spin, use_mock
   - Include UI settings: theme, show_history, history_limit
   - Implement get_settings_path() for platform detection
   - Implement load() class method
   - Implement save() instance method

3. Update src/gc2_connect/config/__init__.py to export Settings

SCHEMA:
```python
{
    "version": 1,
    "gspro": {
        "host": "192.168.1.100",
        "port": 921,
        "auto_connect": false
    },
    "gc2": {
        "auto_connect": true,
        "reject_zero_spin": true,
        "use_mock": false
    },
    "ui": {
        "theme": "dark",
        "show_history": true,
        "history_limit": 50
    }
}
```

REQUIREMENTS:
- Write tests FIRST (TDD)
- Use Annotated[Type, Field(...)] for Pydantic fields
- Handle file not found gracefully (return defaults)
- Handle JSON parse errors gracefully
- Create parent directories if they don't exist
- Run tests: uv run pytest tests/unit/test_settings.py -v
```

---

## Prompt 7: Integrate Settings into UI ✅

```text
Integrate the Settings module into the NiceGUI application.

CONTEXT:
- Settings module is now implemented in gc2_connect/config/settings.py
- UI is in gc2_connect/ui/app.py
- Settings should be loaded on app start and saved when changed

TASK:

1. First, write integration tests in tests/integration/test_settings_ui.py:
   - Test that settings are loaded on app init
   - Test that GSPro host/port inputs use saved values
   - Test that changing settings saves them

2. Modify GC2ConnectApp in ui/app.py:
   - Load settings in __init__
   - Initialize gspro_host_input and gspro_port_input with saved values
   - Add on_change handlers to save settings when inputs change
   - Save settings when auto_send toggle changes
   - Add a "Save Settings" button that explicitly saves

3. Add a Settings panel to the UI:
   - Add a collapsible settings section
   - Include auto-connect toggles for GC2 and GSPro
   - Include history limit setting
   - Show settings file location

REQUIREMENTS:
- Settings should persist across app restarts
- Changes should be saved automatically or with explicit save button
- Handle settings load/save errors gracefully with user notification
- Run tests: uv run pytest tests/integration/test_settings_ui.py -v
```

---

## Prompt 8: Auto-Reconnection Logic

```text
Implement automatic reconnection for both GC2 USB and GSPro network connections.

CONTEXT:
- GC2 can disconnect if USB is unplugged or device powers off
- GSPro connection can be lost due to network issues or GSPro restart
- Both should attempt to reconnect automatically

TASK:

1. First, write tests in tests/unit/test_reconnection.py:
   - Test reconnection attempt after disconnect
   - Test exponential backoff timing
   - Test max retry limit
   - Test reconnection callback notification

2. Create src/gc2_connect/utils/reconnect.py:
   - Implement ReconnectionManager class
   - Configurable max_retries (default 5)
   - Exponential backoff: 1, 2, 4, 8, 16 seconds
   - Callback for status updates
   - Method to attempt reconnection

3. Integrate into GC2USBReader:
   - Detect disconnection in read_loop
   - Trigger reconnection attempts
   - Update UI status during reconnection

4. Integrate into GSProClient:
   - Detect socket errors that indicate disconnection
   - Trigger reconnection attempts
   - Queue shots during reconnection (optional)

5. Update UI to show reconnection status:
   - Show "Reconnecting..." with attempt count
   - Show countdown to next attempt

REQUIREMENTS:
- Don't block the event loop during reconnection
- Use asyncio for async reconnection
- Respect max_retries limit
- Allow manual cancel of reconnection
- Run tests: uv run pytest tests/unit/test_reconnection.py -v
```

---

## Prompt 9: Integration Tests with Mock GSPro Server

```text
Create integration tests that test the full flow from GC2 mock to GSPro mock server.

CONTEXT:
- tools/mock_gspro_server.py provides a mock GSPro server
- gc2/usb_reader.py has MockGC2Reader for testing without hardware
- We need to test the complete flow

TASK:

1. Create tests/integration/test_shot_flow.py:
   - Test complete shot flow: MockGC2 -> App -> MockGSPro
   - Test shot data is correctly transformed
   - Test multiple shots in sequence
   - Test shot rejection (invalid shots not sent)

2. Create a test fixture that:
   - Starts mock GSPro server in background
   - Creates app instance with mock GC2
   - Connects both
   - Provides helpers to send test shots and verify receipt

3. Test scenarios:
   - Single valid shot sent and received correctly
   - Shot with HMT data includes club data
   - Invalid shot (zero spin) is rejected
   - Multiple shots increment shot number correctly

4. Create tests/integration/test_connection_handling.py:
   - Test GSPro connection success
   - Test GSPro connection failure (wrong host)
   - Test GSPro disconnection handling

REQUIREMENTS:
- Use pytest-asyncio for async tests
- Clean up server after tests
- Tests should be reliable (no flaky timing issues)
- Run tests: uv run pytest tests/integration/ -v
```

---

## Prompt 10: Shot History Improvements

```text
Improve the shot history feature as specified in PRD P1 requirements.

CONTEXT:
- Current history shows last 20 shots in a simple list
- PRD requests: scrollable list, shot count display, performance with 100+ shots

TASK:

1. Write tests in tests/unit/test_shot_history.py:
   - Test history maintains order (newest first)
   - Test history respects limit from settings
   - Test history can handle 100+ shots
   - Test clear history functionality

2. Create a ShotHistoryManager class in src/gc2_connect/services/history.py:
   - Store shots with configurable limit
   - Calculate session statistics (average speed, spin, etc.)
   - Support filtering by criteria
   - Export to list of dicts for UI

3. Update UI shot history panel:
   - Show shot count "Shots: 25/50"
   - Improve scrolling performance with virtual list
   - Add session statistics at top (avg ball speed, avg spin)
   - Add export button (for future CSV export)

4. Wire history manager into app:
   - Replace self.shot_history list with ShotHistoryManager
   - Update _on_shot_received to use manager
   - Load history limit from settings

REQUIREMENTS:
- Maintain backwards compatibility with existing UI
- Statistics should update in real-time
- Run tests: uv run pytest tests/unit/test_shot_history.py -v
```

---

## Prompt 11: CSV Export Feature

```text
Implement CSV export for shot data (PRD P2 feature).

CONTEXT:
- Users want to export their session data for analysis
- Export should include all shot metrics
- File should be compatible with Excel/Google Sheets

TASK:

1. Write tests in tests/unit/test_export.py:
   - Test export with no shots (empty file with headers)
   - Test export with ball-only shots
   - Test export with HMT shots
   - Test file path handling
   - Test CSV is valid and readable

2. Create src/gc2_connect/services/export.py:
   - Implement export_to_csv(shots, filepath) function
   - Include headers for all fields
   - Format numbers appropriately (2 decimal places for most)
   - Handle missing HMT data (empty cells)
   - Include timestamp for each shot

3. Add export button to UI:
   - Add "Export CSV" button to history panel
   - Open file save dialog
   - Default filename: gc2_session_YYYYMMDD_HHMMSS.csv
   - Show success/error notification

4. CSV columns should include:
   - Shot #, Timestamp
   - Ball Speed, Launch Angle, H. Launch Angle
   - Total Spin, Back Spin, Side Spin, Spin Axis
   - Club Speed, Path, Face, Attack Angle (if HMT)

REQUIREMENTS:
- Use Python csv module
- Handle special characters in filenames
- Show user-friendly error if write fails
- Run tests: uv run pytest tests/unit/test_export.py -v
```

---

# PHASE 5: OPEN RANGE FEATURE

The Open Range feature adds a built-in driving range simulator with physics-accurate ball flight visualization. This eliminates the need for GSPro for basic practice sessions.

## Prompt 12: Open Range Data Models and Physics Constants

```text
Create the foundation for the Open Range physics engine by implementing data models and physical constants.

CONTEXT:
- Open Range simulates golf ball trajectory based on launch monitor data
- Uses Nathan model + WSU aerodynamics research (see docs/PHYSICS.md)
- All physics calculations in Python, visualization via NiceGUI Three.js

TASK:

1. First, write tests in tests/unit/test_open_range/test_models.py:
   - Test Vec3 operations (add, subtract, scale, magnitude, normalize)
   - Test TrajectoryPoint creation with phase
   - Test ShotSummary validation
   - Test LaunchData from GC2ShotData conversion
   - Test Conditions default values

2. Create src/gc2_connect/open_range/__init__.py

3. Create src/gc2_connect/open_range/models.py with:
```python
from pydantic import BaseModel
from enum import Enum

class Phase(str, Enum):
    FLIGHT = "flight"
    BOUNCE = "bounce"
    ROLLING = "rolling"
    STOPPED = "stopped"

class Vec3(BaseModel):
    """3D vector for physics calculations"""
    x: float
    y: float
    z: float
    # Add helper methods for vector math

class TrajectoryPoint(BaseModel):
    """Single point in ball trajectory"""
    t: float           # Time (seconds)
    x: float           # Forward distance (yards)
    y: float           # Height (feet)
    z: float           # Lateral distance (yards)
    phase: Phase

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

class ShotResult(BaseModel):
    """Complete simulation result"""
    trajectory: list[TrajectoryPoint]
    summary: ShotSummary
    launch_data: LaunchData
    conditions: Conditions
```

4. Create src/gc2_connect/open_range/physics/__init__.py

5. Create src/gc2_connect/open_range/physics/constants.py with:
   - Ball properties (mass, diameter, radius, area) per USGA specs
   - Standard atmosphere constants
   - Physics constants (gravity, spin decay rate)
   - Simulation parameters (dt, max_time, max_iterations)
   - Ground surface properties (Fairway, Rough, Green, Bunker)

Reference docs/PHYSICS.md for exact values.

REQUIREMENTS:
- All code files must have ABOUTME comments
- Use Annotated[Type, Field(...)] for Pydantic fields
- Vec3 should have helper methods: add, sub, scale, mag, normalize, cross, dot
- Constants should match docs/PHYSICS.md exactly
- Run tests: uv run pytest tests/unit/test_open_range/test_models.py -v
```

---

## Prompt 13: Aerodynamics Module

```text
Implement the aerodynamic coefficient calculations for the golf ball physics engine.

CONTEXT:
- Drag coefficient (Cd) varies with Reynolds number (drag crisis effect)
- Lift coefficient (Cl) depends on spin factor S = (ω × r) / V
- Air density varies with temperature, elevation, and humidity
- See docs/PHYSICS.md for formulas and libgolf reference

TASK:

1. First, write tests in tests/unit/test_open_range/test_aerodynamics.py:
   - Test Reynolds number calculation at various speeds
   - Test Cd lookup: low Re -> ~0.5, high Re -> ~0.21
   - Test Cd transition in drag crisis region
   - Test Cd with spin-dependent term
   - Test Cl at spin factor 0 -> 0.0
   - Test Cl quadratic formula matches expected values
   - Test Cl caps at ClMax (0.305) above threshold
   - Test air density at standard conditions -> ~1.194 kg/m³
   - Test air density at Denver (5280 ft elevation) -> lower
   - Test air density at high temperature -> lower

2. Create src/gc2_connect/open_range/physics/aerodynamics.py:

```python
"""
ABOUTME: Aerodynamic coefficient calculations for golf ball simulation.
ABOUTME: Based on WSU research data and libgolf reference implementation.
"""

def calculate_reynolds(velocity_ms: float, air_density: float) -> float:
    """Calculate Reynolds number for golf ball at given velocity."""
    # Re = ρ × V × D / μ
    pass

def get_drag_coefficient(reynolds: float, spin_factor: float = 0.0) -> float:
    """
    Get drag coefficient using piecewise linear model with spin term.

    Args:
        reynolds: Reynolds number (not in units of 10^5)
        spin_factor: S = (ω × r) / V

    Returns:
        Total drag coefficient Cd
    """
    # Use constants from docs/PHYSICS.md:
    # CdLow = 0.500 (Re < 0.5×10^5)
    # CdHigh = 0.212 (Re > 1.0×10^5)
    # CdSpin = 0.15 (spin-dependent term)
    pass

def get_lift_coefficient(spin_factor: float) -> float:
    """
    Get lift coefficient using quadratic formula.

    Cl = 1.990×S - 3.250×S²
    Capped at ClMax = 0.305
    """
    pass

def calculate_air_density(
    temp_f: float,
    elevation_ft: float,
    humidity_pct: float,
    pressure_inhg: float = 29.92
) -> float:
    """Calculate air density with atmospheric corrections."""
    pass
```

3. Validation test data (from docs/PHYSICS.md):
   - At 80 mph (35.8 m/s), Re ≈ 1.0×10^5 -> Cd ≈ 0.21-0.50 (transition)
   - At 160 mph (71.5 m/s), Re ≈ 2.0×10^5 -> Cd ≈ 0.21 (turbulent)
   - Spin factor 0.30 -> Cl ≈ 0.305 (max)
   - Standard conditions -> ρ ≈ 1.194 kg/m³

REQUIREMENTS:
- Match docs/PHYSICS.md formulas exactly
- Use kinematic viscosity ν = 1.5×10^-5 m²/s for Reynolds calculation
- Cl formula: Cl = 1.990×S - 3.250×S² (quadratic, not table lookup)
- Run tests: uv run pytest tests/unit/test_open_range/test_aerodynamics.py -v
```

---

## Prompt 14: Trajectory Simulation with RK4 Integration

```text
Implement the core trajectory simulation using 4th-order Runge-Kutta integration.

CONTEXT:
- Ball trajectory is governed by gravity, drag, and Magnus force
- RK4 provides accurate integration without fixed small time steps
- Wind affects relative velocity
- See docs/PHYSICS.md section 6-7 for force calculations and RK4 algorithm

TASK:

1. First, write tests in tests/unit/test_open_range/test_trajectory.py:
   - Test initial velocity calculation from launch conditions
   - Test gravity-only trajectory (no air, should be parabola)
   - Test drag reduces distance vs gravity-only
   - Test backspin creates lift (higher apex, more carry)
   - Test sidespin creates curve (positive = fade/slice right)
   - Test wind affects trajectory
   - Test spin decay over time
   - Test trajectory terminates when ball lands (y <= 0)

2. Create src/gc2_connect/open_range/physics/trajectory.py:

```python
"""
ABOUTME: Golf ball trajectory simulation using RK4 integration.
ABOUTME: Implements Nathan model with drag, lift, and wind effects.
"""

from dataclasses import dataclass
from ..models import Vec3, TrajectoryPoint, Phase, Conditions
from .constants import *
from .aerodynamics import *

@dataclass
class SimulationState:
    """Current state of ball during simulation"""
    pos: Vec3
    vel: Vec3
    spin_back: float
    spin_side: float
    t: float
    phase: Phase

class FlightSimulator:
    """Simulates ball flight phase (before first ground contact)"""

    def __init__(self, conditions: Conditions, dt: float = 0.01):
        self.conditions = conditions
        self.dt = dt
        self.air_density = calculate_air_density(
            conditions.temp_f,
            conditions.elevation_ft,
            conditions.humidity_pct
        )

    def get_wind_at_height(self, height_m: float) -> Vec3:
        """Get wind velocity at height (logarithmic profile)"""
        pass

    def calculate_acceleration(
        self,
        pos: Vec3,
        vel: Vec3,
        spin_back: float,
        spin_side: float
    ) -> Vec3:
        """Calculate total acceleration from gravity, drag, and Magnus force"""
        # 1. Get wind and relative velocity
        # 2. Calculate drag force (opposes motion)
        # 3. Calculate Magnus force (perpendicular to spin × velocity)
        # 4. Sum all forces, divide by mass
        pass

    def rk4_step(self, state: SimulationState) -> SimulationState:
        """Perform one RK4 integration step"""
        # k1 = f(t, y)
        # k2 = f(t + dt/2, y + dt/2 * k1)
        # k3 = f(t + dt/2, y + dt/2 * k2)
        # k4 = f(t + dt, y + dt * k3)
        # y_new = y + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
        pass

    def simulate_flight(
        self,
        ball_speed_mph: float,
        vla_deg: float,
        hla_deg: float,
        backspin_rpm: float,
        sidespin_rpm: float
    ) -> tuple[list[TrajectoryPoint], SimulationState]:
        """
        Simulate flight until ball hits ground.

        Returns:
            (trajectory_points, final_state_at_landing)
        """
        pass
```

3. Unit conversion helpers needed:
   - mph_to_ms, ms_to_mph
   - meters_to_yards, meters_to_feet
   - rpm_to_rad_s
   - deg_to_rad

4. Validation test data (from docs/PHYSICS.md):
   - Driver (167 mph, 10.9°, 2686 rpm): expect ~275 yds carry
   - 7-iron (120 mph, 16.3°, 7097 rpm): expect ~172 yds carry
   - Allow ±5% tolerance for physics accuracy

REQUIREMENTS:
- Time step dt = 0.01s (10ms) for accuracy
- Max simulation time 30s (safety limit)
- Spin decays at 1% per second
- Use RK4, not Euler integration
- Run tests: uv run pytest tests/unit/test_open_range/test_trajectory.py -v
```

---

## Prompt 15: Ground Physics (Bounce and Roll)

```text
Implement ground interaction physics for bounce and roll behavior.

CONTEXT:
- When ball lands, it bounces based on coefficient of restitution (COR)
- Friction affects tangential velocity on bounce
- Rolling ball decelerates due to rolling resistance
- See docs/PHYSICS.md section 8 for ground physics

TASK:

1. First, write tests in tests/unit/test_open_range/test_ground.py:
   - Test bounce on fairway reduces vertical velocity by COR (0.6)
   - Test bounce reduces tangential velocity by friction
   - Test steep impact angle = less forward momentum retained
   - Test shallow impact angle = more forward momentum retained
   - Test roll deceleration on fairway
   - Test roll deceleration on green (lower resistance)
   - Test roll deceleration on rough (higher resistance)
   - Test ball stops when speed < 0.1 m/s
   - Test spin reduces on bounce
   - Test spin affects roll (backspin = longer roll? shorter?)

2. Create src/gc2_connect/open_range/physics/ground.py:

```python
"""
ABOUTME: Ground interaction physics for golf ball bounce and roll.
ABOUTME: Inspired by libgolf reference implementation.
"""

from dataclasses import dataclass
from ..models import Vec3, Phase
from .constants import SURFACES, GRAVITY_MS2, BALL_RADIUS_M

@dataclass
class GroundSurface:
    """Properties of a ground surface"""
    name: str
    cor: float              # Coefficient of restitution (0-1)
    rolling_resistance: float   # Deceleration factor
    friction: float         # Tangential friction on bounce

class GroundPhysics:
    """Handles bounce and roll physics"""

    def __init__(self, surface_name: str = "Fairway"):
        self.surface = SURFACES[surface_name]

    def bounce(self, state: "SimulationState") -> "SimulationState":
        """
        Apply bounce physics at ground contact.

        Physics:
        - Normal velocity: v_n_new = -v_n * COR
        - Tangential velocity: v_t_new = v_t * (1 - friction * factor)
        - Spin: reduced by friction interaction
        """
        pass

    def roll_step(self, state: "SimulationState", dt: float) -> "SimulationState":
        """
        Simulate one step of rolling.

        Physics:
        - Deceleration = rolling_resistance * g
        - Speed decreases by decel * dt
        - Position updates by velocity * dt
        - Stops when speed < 0.1 m/s
        """
        pass

    def should_continue_bouncing(self, state: "SimulationState") -> bool:
        """Check if ball has enough energy for another bounce"""
        # If vertical velocity < threshold, transition to rolling
        pass
```

3. Surface property reference (from constants):
   - Fairway: COR=0.6, resistance=0.10, friction=0.50
   - Green: COR=0.4, resistance=0.05, friction=0.30
   - Rough: COR=0.3, resistance=0.30, friction=0.70

4. Test realistic behaviors:
   - Driver landing at ~45° should bounce and roll significantly
   - Wedge landing at ~60° should have less roll
   - Ball on green should roll farther than rough

REQUIREMENTS:
- Bounce should feel realistic (multiple bounces for high-speed impacts)
- Maximum 5 bounces before forcing roll phase
- Ball must eventually stop (no infinite rolling)
- Run tests: uv run pytest tests/unit/test_open_range/test_ground.py -v
```

---

## Prompt 16: Complete Physics Engine Integration

```text
Wire together trajectory and ground physics into a complete simulation engine.

CONTEXT:
- FlightSimulator handles air phase
- GroundPhysics handles bounces and rolling
- Need to combine into seamless simulation from launch to rest
- Must validate against known data from docs/PHYSICS.md

TASK:

1. First, write validation tests in tests/unit/test_open_range/test_physics_validation.py:
   - Test driver shot (167 mph, 10.9°, 2686 rpm) -> 275 yds ± 5%
   - Test driver shot (160 mph, 11.0°, 3000 rpm) -> 259 yds ± 3%
   - Test 7-iron (120 mph, 16.3°, 7097 rpm) -> 172 yds ± 5%
   - Test wedge (102 mph, 24.2°, 9304 rpm) -> 136 yds ± 5%
   - Test sidespin creates expected curve direction
   - Test high elevation (Denver) increases carry
   - Test headwind decreases carry
   - Test tailwind increases carry

2. Create src/gc2_connect/open_range/physics/engine.py:

```python
"""
ABOUTME: Complete golf ball physics engine integrating flight and ground phases.
ABOUTME: Provides single simulate() method for full shot trajectory.
"""

from ..models import ShotResult, ShotSummary, LaunchData, Conditions, TrajectoryPoint, Phase
from .trajectory import FlightSimulator, SimulationState
from .ground import GroundPhysics
from .constants import MAX_BOUNCES

class PhysicsEngine:
    """Complete physics simulation from launch to rest"""

    def __init__(
        self,
        conditions: Conditions | None = None,
        surface: str = "Fairway",
        dt: float = 0.01
    ):
        self.conditions = conditions or Conditions()
        self.surface = surface
        self.dt = dt
        self.flight_sim = FlightSimulator(self.conditions, dt)
        self.ground = GroundPhysics(surface)

    def simulate(
        self,
        ball_speed_mph: float,
        vla_deg: float,
        hla_deg: float,
        backspin_rpm: float,
        sidespin_rpm: float
    ) -> ShotResult:
        """
        Run complete simulation from launch to rest.

        Phases:
        1. FLIGHT: RK4 integration until y <= 0
        2. BOUNCE: Apply bounce physics, return to flight if speed > threshold
        3. ROLLING: Decelerate until stopped
        4. STOPPED: Record final position

        Returns:
            ShotResult with full trajectory and summary metrics
        """
        pass

    def _calculate_summary(
        self,
        trajectory: list[TrajectoryPoint],
        landing_time: float,
        total_time: float,
        bounce_count: int
    ) -> ShotSummary:
        """Calculate shot summary from trajectory data"""
        # Find carry distance (position at first landing)
        # Find total distance (final position)
        # Find max height and time to max height
        pass
```

3. Performance requirements:
   - Full simulation < 100ms
   - Trajectory points sampled at reasonable intervals (not every 0.01s)
   - Memory-safe (limit max trajectory points)

4. Create src/gc2_connect/open_range/engine.py (high-level wrapper):

```python
"""
ABOUTME: High-level Open Range engine that processes GC2 shot data.
ABOUTME: Converts launch monitor input to simulated trajectory output.
"""

from .models import ShotResult, LaunchData, Conditions
from .physics.engine import PhysicsEngine
from ..models import GC2ShotData

class OpenRangeEngine:
    """Processes shots for Open Range visualization"""

    def __init__(self, conditions: Conditions | None = None, surface: str = "Fairway"):
        self.conditions = conditions or Conditions()
        self.surface = surface
        self.physics = PhysicsEngine(self.conditions, surface)

    def simulate_shot(self, shot: GC2ShotData) -> ShotResult:
        """Simulate a shot from GC2 data"""
        return self.physics.simulate(
            ball_speed_mph=shot.ball_speed,
            vla_deg=shot.launch_angle,
            hla_deg=shot.launch_direction,
            backspin_rpm=shot.back_spin,
            sidespin_rpm=shot.side_spin
        )

    def simulate_test_shot(self, club: str = "Driver") -> ShotResult:
        """Generate a realistic test shot for given club"""
        # Use typical values for club with some random variance
        pass
```

REQUIREMENTS:
- Validate against all test cases in docs/PHYSICS.md
- Performance < 100ms per shot
- Trajectory should be reasonably sampled (not thousands of points)
- Run tests: uv run pytest tests/unit/test_open_range/test_physics_validation.py -v
```

---

## Prompt 17: Mode Selection and Shot Router

```text
Implement mode selection and shot routing to direct shots to GSPro or Open Range.

CONTEXT:
- App needs to support two modes: GSPro (existing) and Open Range (new)
- Shots from GC2 should be routed to the active mode
- Mode can be switched without restarting app
- See docs/TRD_OPEN_RANGE.md for ShotRouter specification

TASK:

1. First, write tests in tests/unit/test_shot_router.py:
   - Test default mode is GSPRO
   - Test can set mode to OPEN_RANGE
   - Test mode change callback is invoked
   - Test route_shot in GSPRO mode calls gspro_client
   - Test route_shot in OPEN_RANGE mode calls open_range_engine
   - Test switching modes is graceful (no errors)

2. Create src/gc2_connect/services/__init__.py

3. Create src/gc2_connect/services/shot_router.py:

```python
"""
ABOUTME: Routes shot data to GSPro or Open Range based on current mode.
ABOUTME: Handles mode switching and destination management.
"""

from enum import Enum
from typing import Callable, Awaitable
from ..models import GC2ShotData
from ..gspro.client import GSProClient
from ..open_range.engine import OpenRangeEngine
from ..open_range.models import ShotResult

class AppMode(str, Enum):
    GSPRO = "gspro"
    OPEN_RANGE = "open_range"

class ShotRouter:
    """Routes shots between GSPro and Open Range modes"""

    def __init__(self):
        self._mode = AppMode.GSPRO
        self._gspro_client: GSProClient | None = None
        self._open_range_engine: OpenRangeEngine | None = None
        self._mode_change_callback: Callable[[AppMode], Awaitable[None]] | None = None
        self._shot_result_callback: Callable[[ShotResult], Awaitable[None]] | None = None

    @property
    def mode(self) -> AppMode:
        return self._mode

    async def set_mode(self, mode: AppMode) -> None:
        """Switch between modes"""
        if mode == self._mode:
            return

        # Cleanup previous mode if needed
        if self._mode == AppMode.GSPRO and self._gspro_client:
            # Don't disconnect GSPro, just stop sending to it
            pass

        self._mode = mode

        if self._mode_change_callback:
            await self._mode_change_callback(mode)

    def set_gspro_client(self, client: GSProClient) -> None:
        self._gspro_client = client

    def set_open_range_engine(self, engine: OpenRangeEngine) -> None:
        self._open_range_engine = engine

    def on_mode_change(self, callback: Callable[[AppMode], Awaitable[None]]) -> None:
        self._mode_change_callback = callback

    def on_shot_result(self, callback: Callable[[ShotResult], Awaitable[None]]) -> None:
        """Callback for Open Range shot results"""
        self._shot_result_callback = callback

    async def route_shot(self, shot: GC2ShotData) -> None:
        """Route shot to appropriate destination"""
        if self._mode == AppMode.GSPRO:
            await self._route_to_gspro(shot)
        else:
            await self._route_to_open_range(shot)

    async def _route_to_gspro(self, shot: GC2ShotData) -> None:
        """Send shot to GSPro"""
        if not self._gspro_client:
            raise RuntimeError("GSPro client not configured")
        # Existing GSPro send logic
        pass

    async def _route_to_open_range(self, shot: GC2ShotData) -> None:
        """Process shot in Open Range"""
        if not self._open_range_engine:
            raise RuntimeError("Open Range engine not configured")

        result = self._open_range_engine.simulate_shot(shot)

        if self._shot_result_callback:
            await self._shot_result_callback(result)
```

4. Add AppMode to models or services for import elsewhere

REQUIREMENTS:
- Mode switching should be fast (no delays)
- GSPro connection stays open when switching to Open Range
- Open Range doesn't require GSPro connection
- Run tests: uv run pytest tests/unit/test_shot_router.py -v
```

---

## Prompt 18: Open Range Settings Extension

```text
Extend the Settings module to include Open Range configuration.

CONTEXT:
- Settings class exists in gc2_connect/config/settings.py
- Need to add Open Range-specific settings
- Settings should persist between sessions
- See docs/TRD_OPEN_RANGE.md for settings schema

TASK:

1. First, write tests in tests/unit/test_open_range_settings.py:
   - Test OpenRangeSettings default values
   - Test conditions defaults (70°F, sea level, 50% humidity)
   - Test surface default is "Fairway"
   - Test settings save and load roundtrip
   - Test settings migration from v1 to v2 schema

2. Update src/gc2_connect/config/settings.py:

```python
# Add to existing file

class ConditionsSettings(BaseModel):
    """Environmental conditions for Open Range"""
    temp_f: float = 70.0
    elevation_ft: float = 0.0
    humidity_pct: float = 50.0
    wind_speed_mph: float = 0.0
    wind_dir_deg: float = 0.0

class OpenRangeSettings(BaseModel):
    """Open Range specific settings"""
    conditions: ConditionsSettings = Field(default_factory=ConditionsSettings)
    surface: str = "Fairway"
    show_trajectory: bool = True
    camera_follow: bool = True

# Update main Settings class
class Settings(BaseSettings):
    version: int = 2  # Bump version
    mode: str = "gspro"  # Default mode
    gspro: GSProSettings = Field(default_factory=GSProSettings)
    gc2: GC2Settings = Field(default_factory=GC2Settings)
    ui: UISettings = Field(default_factory=UISettings)
    open_range: OpenRangeSettings = Field(default_factory=OpenRangeSettings)  # NEW
```

3. Add settings migration for version 1 -> 2:
   - If loaded settings have version 1, add open_range with defaults
   - Save migrated settings

4. Update Settings schema version handling:
   - Read version field first
   - Apply migrations as needed
   - Save with current version

REQUIREMENTS:
- Backwards compatible with existing settings files
- Automatic migration from v1 to v2
- Default mode remains "gspro" for existing users
- Run tests: uv run pytest tests/unit/test_open_range_settings.py -v
```

---

## Prompt 19: 3D Driving Range Visualization

```text
Create the 3D driving range visualization using NiceGUI's Three.js integration.

CONTEXT:
- NiceGUI provides ui.scene() for Three.js integration
- Need to render a driving range environment
- Ball flight animation along trajectory
- Camera following the ball
- See docs/PRD_OPEN_RANGE.md F2, F3, F4 for requirements

TASK:

1. First, write tests in tests/unit/test_open_range/test_visualization.py:
   - Test RangeScene can be created
   - Test distance markers are placed correctly
   - Test ball can be added to scene
   - Test trajectory animation frames are calculated correctly
   - Test camera position updates with ball

2. Create src/gc2_connect/open_range/visualization/__init__.py

3. Create src/gc2_connect/open_range/visualization/range_scene.py:

```python
"""
ABOUTME: 3D driving range environment using NiceGUI Three.js.
ABOUTME: Creates the visual scene with ground, markers, and lighting.
"""

from nicegui import ui

class RangeScene:
    """3D driving range environment"""

    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.scene = None
        self.ball = None
        self.trajectory_line = None

    def build(self) -> ui.scene:
        """Create and return the 3D scene"""
        self.scene = ui.scene(width=self.width, height=self.height)
        with self.scene:
            self._create_ground()
            self._create_distance_markers()
            self._create_target_greens()
            self._setup_lighting()
            self._setup_camera()
        return self.scene

    def _create_ground(self):
        """Create the driving range ground plane"""
        # Green fairway extending to 350 yards
        pass

    def _create_distance_markers(self):
        """Add distance markers every 25-50 yards"""
        # Markers at 50, 100, 150, 200, 250, 300 yards
        pass

    def _create_target_greens(self):
        """Add target greens at common distances"""
        # Greens at 75, 125, 175, 225, 275 yards
        pass

    def _setup_lighting(self):
        """Configure scene lighting (dark theme friendly)"""
        pass

    def _setup_camera(self):
        """Set initial camera position behind ball"""
        pass
```

4. Create src/gc2_connect/open_range/visualization/ball_animation.py:

```python
"""
ABOUTME: Ball flight animation along trajectory path.
ABOUTME: Handles smooth animation with phase transitions.
"""

from ..models import TrajectoryPoint, Phase, ShotResult

class BallAnimator:
    """Animates ball along trajectory"""

    def __init__(self, scene: "RangeScene"):
        self.scene = scene
        self.current_frame = 0
        self.trajectory: list[TrajectoryPoint] = []
        self.is_animating = False

    async def animate_shot(self, result: ShotResult, speed: float = 1.0):
        """Animate ball along trajectory"""
        self.trajectory = result.trajectory
        self.is_animating = True

        for point in self.trajectory:
            if not self.is_animating:
                break

            # Update ball position
            # Update camera to follow
            # Update phase indicator
            # Wait for frame timing
            pass

        self.is_animating = False

    def stop(self):
        """Stop current animation"""
        self.is_animating = False

    def reset(self):
        """Reset ball to starting position"""
        pass
```

5. Coordinate system for visualization:
   - X = forward (toward targets), in yards
   - Y = height, in feet (scale to scene units)
   - Z = lateral (left/right), in yards
   - Scale factor: 1 yard = 1 scene unit (or appropriate scale)

REQUIREMENTS:
- Scene loads within 2 seconds
- Target 60 FPS animation
- Dark theme friendly colors
- Camera smoothly follows ball
- Run tests: uv run pytest tests/unit/test_open_range/test_visualization.py -v
```

---

## Prompt 20: Open Range UI Panel and Data Display

```text
Create the Open Range UI panel with shot data display and phase indicators.

CONTEXT:
- Need mode selector to switch between GSPro and Open Range
- Open Range view includes 3D scene + data panels
- Real-time shot data display during/after animation
- Phase indicators: Flight, Bounce, Rolling, Stopped
- See docs/PRD_OPEN_RANGE.md F5, F6 for data display requirements

TASK:

1. First, write tests in tests/integration/test_open_range_ui.py:
   - Test mode selector toggles between modes
   - Test Open Range panel shows when in Open Range mode
   - Test shot data displays correctly after simulation
   - Test phase indicator updates during animation

2. Create src/gc2_connect/ui/components/__init__.py

3. Create src/gc2_connect/ui/components/mode_selector.py:

```python
"""
ABOUTME: Mode selector component for switching between GSPro and Open Range.
ABOUTME: Provides toggle UI and handles mode change callbacks.
"""

from nicegui import ui
from ...services.shot_router import AppMode

class ModeSelector:
    """Toggle between GSPro and Open Range modes"""

    def __init__(self, on_change: Callable[[AppMode], Awaitable[None]]):
        self.on_change = on_change
        self.current_mode = AppMode.GSPRO
        self.toggle = None

    def build(self):
        """Create the mode selector UI"""
        with ui.row().classes('gap-4 items-center'):
            ui.label('Mode:').classes('text-lg')
            self.toggle = ui.toggle(
                {AppMode.GSPRO.value: 'GSPro', AppMode.OPEN_RANGE.value: 'Open Range'},
                value=AppMode.GSPRO.value,
                on_change=self._handle_change
            ).classes('bg-gray-800')

    async def _handle_change(self, e):
        self.current_mode = AppMode(e.value)
        await self.on_change(self.current_mode)
```

4. Create src/gc2_connect/ui/components/open_range_view.py:

```python
"""
ABOUTME: Open Range view component with 3D scene and data display.
ABOUTME: Main UI for the built-in driving range simulator.
"""

from nicegui import ui
from ...open_range.models import ShotResult, Phase
from ...open_range.visualization.range_scene import RangeScene
from ...open_range.visualization.ball_animation import BallAnimator

class OpenRangeView:
    """Complete Open Range UI panel"""

    def __init__(self):
        self.range_scene: RangeScene | None = None
        self.animator: BallAnimator | None = None
        self.current_phase = Phase.STOPPED

        # UI elements
        self.phase_label = None
        self.carry_label = None
        self.total_label = None
        self.height_label = None
        self.offline_label = None

    def build(self):
        """Create the Open Range view"""
        with ui.row().classes('w-full gap-4'):
            # Left: 3D scene
            with ui.column().classes('flex-grow'):
                self.range_scene = RangeScene(width=800, height=500)
                self.range_scene.build()
                self.animator = BallAnimator(self.range_scene)

            # Right: Data panel
            with ui.column().classes('w-64 gap-2'):
                self._build_phase_indicator()
                self._build_shot_data_panel()
                self._build_launch_data_panel()
                self._build_conditions_panel()

    def _build_phase_indicator(self):
        """Phase indicator with color coding"""
        with ui.card().classes('w-full'):
            ui.label('Phase').classes('text-sm text-gray-400')
            self.phase_label = ui.label('Ready').classes('text-xl font-bold')

    def _build_shot_data_panel(self):
        """Shot result metrics"""
        with ui.card().classes('w-full'):
            ui.label('Shot Data').classes('text-sm text-gray-400')
            with ui.column().classes('gap-1'):
                self.carry_label = ui.label('Carry: --')
                self.total_label = ui.label('Total: --')
                self.offline_label = ui.label('Offline: --')
                self.height_label = ui.label('Max Height: --')

    def _build_launch_data_panel(self):
        """Launch conditions from GC2"""
        pass

    def _build_conditions_panel(self):
        """Environmental conditions"""
        pass

    async def show_shot(self, result: ShotResult):
        """Display and animate a shot"""
        await self.animator.animate_shot(result)
        self._update_data_display(result)

    def _update_data_display(self, result: ShotResult):
        """Update data labels with shot result"""
        s = result.summary
        self.carry_label.text = f'Carry: {s.carry_distance:.1f} yds'
        self.total_label.text = f'Total: {s.total_distance:.1f} yds'
        self.offline_label.text = f'Offline: {s.offline_distance:+.1f} yds'
        self.height_label.text = f'Max Height: {s.max_height:.1f} ft'

    def update_phase(self, phase: Phase):
        """Update phase indicator"""
        self.current_phase = phase
        colors = {
            Phase.FLIGHT: 'text-green-400',
            Phase.BOUNCE: 'text-orange-400',
            Phase.ROLLING: 'text-blue-400',
            Phase.STOPPED: 'text-gray-400'
        }
        self.phase_label.classes(replace=colors.get(phase, ''))
        self.phase_label.text = phase.value.capitalize()
```

5. Update src/gc2_connect/ui/app.py:
   - Add mode selector to header
   - Add OpenRangeView component
   - Show/hide GSPro panel vs Open Range panel based on mode
   - Wire shot router to appropriate view

REQUIREMENTS:
- Clear visual distinction between modes
- Data updates in real-time during animation
- Phase colors: Flight=green, Bounce=orange, Rolling=blue, Stopped=gray
- Run tests: uv run pytest tests/integration/test_open_range_ui.py -v
```

---

## Prompt 21: Open Range Full Integration and Testing

```text
Wire together all Open Range components and create comprehensive integration tests.

CONTEXT:
- All Open Range components are implemented
- Need to integrate into main app
- Test complete flow: GC2 shot -> Physics -> Animation -> Display
- Ensure mode switching works correctly

TASK:

1. Create tests/integration/test_open_range_flow.py:
   - Test: Shot from MockGC2 -> Open Range engine -> Visualization
   - Test: Mode switch from GSPro to Open Range
   - Test: Mode switch back to GSPro
   - Test: Multiple shots in Open Range mode
   - Test: Settings changes update engine (conditions, surface)

2. Update src/gc2_connect/ui/app.py:
   - Add ModeSelector to header area
   - Create OpenRangeView instance
   - Create ShotRouter instance
   - Wire GC2 reader to shot router
   - Wire shot router to appropriate destination
   - Handle mode-specific UI visibility

3. Integration wiring:
```python
# In GC2ConnectApp.__init__
self.shot_router = ShotRouter()
self.open_range_engine = OpenRangeEngine()
self.open_range_view = OpenRangeView()

# Wire components
self.shot_router.set_gspro_client(self.gspro_client)
self.shot_router.set_open_range_engine(self.open_range_engine)
self.shot_router.on_shot_result(self._on_open_range_shot)
self.shot_router.on_mode_change(self._on_mode_change)

# In _on_shot_received (modify existing)
async def _on_shot_received(self, shot: GC2ShotData):
    await self.shot_router.route_shot(shot)
    # History still updates regardless of mode
    self.shot_history.append(shot)
```

4. Mode-specific UI:
   - When GSPRO: Show GSPro connection panel, hide Open Range view
   - When OPEN_RANGE: Show Open Range view, hide GSPro panel (but keep connection status)

5. Test shot button updates:
   - In GSPRO mode: Sends test shot to GSPro
   - In OPEN_RANGE mode: Simulates test shot in Open Range

6. Performance validation:
   - Measure physics calculation time
   - Measure animation frame rate
   - Log warnings if thresholds exceeded

REQUIREMENTS:
- Seamless mode switching
- Shot history works in both modes
- Settings apply correctly to Open Range
- No errors during mode transitions
- Run tests: uv run pytest tests/integration/test_open_range_flow.py -v
```

---

## Prompt 21b: Ball Trajectory Tracing

```text
Implement ball trajectory tracing to show the flight path during and after animation.

CONTEXT:
- Ball animation already follows the trajectory points
- Camera follows the ball with cinematic behavior (delay, follow, hold, reset)
- Need to draw a visible trace line showing the ball's path
- The trace should remain visible after the ball lands to show complete flight path
- NiceGUI's ui.scene doesn't have a direct line API, need to use alternative approach

TASK:

1. First, write tests in tests/unit/test_open_range/test_trajectory_trace.py:
   - Test trace line is created with correct number of segments
   - Test trace updates as ball animates
   - Test trace is cleared when new shot starts
   - Test trace color matches current phase
   - Test trace remains visible after animation completes

2. Implement trajectory line drawing in range_scene.py:
   - Option A: Use connected small spheres as "breadcrumbs" along the path
   - Option B: Use Three.js Line geometry via run_javascript
   - Option C: Use cylinders connecting consecutive points
   - Choose the approach that provides best visual result with NiceGUI

3. Update draw_trajectory_line() method in RangeScene:
```python
def draw_trajectory_line(self, points: list[Vec3], color: str = "#00ff88") -> None:
    """Draw the trajectory path line.

    Args:
        points: List of positions forming the trajectory.
        color: Hex color for the line (default green for flight).
    """
    # Clear existing trajectory
    self.clear_trajectory_line()

    # Draw new trajectory using chosen approach
    # Store references for later cleanup
    pass

def clear_trajectory_line(self) -> None:
    """Remove the current trajectory line from scene."""
    pass
```

4. Update BallAnimator to draw trajectory progressively:
   - As ball moves, add points to the trace
   - Consider drawing every Nth point (e.g., every 5th) for performance
   - Use phase-appropriate colors:
     - Flight: green (#00ff88)
     - Bounce: orange (#ff8844)
     - Rolling: blue (#00d4ff)
   - Keep full trace visible after animation ends

5. Performance considerations:
   - Limit number of trace segments (e.g., max 500)
   - Use efficient Three.js primitives
   - Don't redraw entire trace each frame - append incrementally

6. Visual appearance:
   - Trace should be thin but visible
   - Slight transparency or glow effect if possible
   - Should contrast well against the dark green fairway
   - Consider fading older segments (optional)

REQUIREMENTS:
- Trace visible during animation
- Trace remains visible after ball stops
- Trace cleared when new shot begins
- Performance: No frame drops during animation
- Run tests: uv run pytest tests/unit/test_open_range/test_trajectory_trace.py -v
```

---

# PHASE 6: POLISH & PACKAGING

## Prompt 22: End-to-End Tests

```text
Create end-to-end tests that verify the complete application works correctly.

CONTEXT:
- E2E tests should test the actual NiceGUI application
- Use browser automation or NiceGUI's test utilities
- Focus on critical user flows for both GSPro and Open Range modes

TASK:

1. Set up e2e test infrastructure:
   - Create tests/e2e/__init__.py
   - Add any needed dependencies (playwright or nicegui test utils)
   - Create fixtures for app lifecycle

2. Create tests/e2e/test_user_flows.py:
   - Test: App loads and displays correctly
   - Test: Can connect to mock GC2
   - Test: Can configure GSPro connection settings
   - Test: Mock shot appears in UI (GSPro mode)
   - Test: Can switch to Open Range mode
   - Test: Mock shot animates in Open Range
   - Test: Shot history updates in both modes
   - Test: Settings persist after restart

3. Create tests/e2e/test_error_handling.py:
   - Test: Clear error when GC2 not found
   - Test: Clear error when GSPro connection fails
   - Test: App recovers from errors gracefully
   - Test: Mode switch works even with GSPro disconnected

4. Focus on:
   - User-facing behavior, not implementation details
   - Critical paths that must work
   - Error states users might encounter

REQUIREMENTS:
- Tests should be reliable and not flaky
- Clean up resources after tests
- Use appropriate waits for async operations
- Run tests: uv run pytest tests/e2e/ -v
```

---

## Prompt 23: Type Checking & Linting Cleanup

```text
Fix all type checking and linting issues in the codebase.

CONTEXT:
- mypy is configured but may have errors
- ruff is configured for linting
- All code should pass both checks
- New Open Range code needs verification

TASK:

1. Run mypy and fix all errors:
   - uv run mypy src/
   - Add type hints where missing
   - Fix type incompatibilities
   - Add type: ignore comments only where truly necessary (with explanation)

2. Run ruff and fix all issues:
   - uv run ruff check . --fix
   - Review any remaining issues
   - Fix import ordering
   - Fix unused imports

3. Common issues to look for:
   - Optional types not handled (None checks)
   - Callback type annotations
   - Async function return types
   - Pydantic model typing
   - NiceGUI element typing

4. Update pyproject.toml if needed:
   - Add any missing type stubs
   - Adjust mypy/ruff config for edge cases

5. Add pre-commit hook config:
   - Create .pre-commit-config.yaml
   - Include ruff and mypy checks
   - Include pytest (optional)

REQUIREMENTS:
- Zero mypy errors (or documented exceptions)
- Zero ruff errors
- All tests still pass after changes
- Run: uv run mypy src/ && uv run ruff check . && uv run pytest
```

---

## Prompt 24: Documentation & Release

```text
Create comprehensive documentation and prepare for v1.1.0 release.

CONTEXT:
- README.md exists but needs updates for Open Range
- Users need setup instructions for both modes
- v1.1.0 adds the Open Range feature

TASK:

1. Update README.md:
   - Clear project description (now includes Open Range)
   - Feature overview (GSPro connector + built-in range)
   - Screenshots (add placeholders for Open Range UI)
   - Installation instructions (macOS and Linux)
   - Quick start guide (both modes)
   - Configuration options (including Open Range settings)
   - Troubleshooting section

2. Create CONTRIBUTING.md:
   - Development setup
   - Running tests
   - Code style guide
   - Pull request process

3. Update docs/:
   - Verify PRD_OPEN_RANGE.md is current
   - Verify TRD_OPEN_RANGE.md is current
   - Verify PHYSICS.md matches implementation
   - Add CHANGELOG.md with v1.1.0 notes

4. Add inline documentation:
   - Ensure all public functions have docstrings
   - Add module-level docstrings
   - Document physics calculations

5. Create USB permission guides:
   - docs/LINUX_USB_SETUP.md with udev rules
   - docs/MACOS_USB_SETUP.md if needed

6. Final testing & packaging:
   - Run full test suite with coverage
   - uv run pytest --cov=gc2_connect --cov-report=html
   - Target: >80% coverage
   - Verify package builds: uv build
   - Test entry point: gc2-connect command

7. Version bump:
   - Update version in pyproject.toml to 1.1.0
   - Update any version references in docs

REQUIREMENTS:
- Documentation should be clear for non-technical users
- Include actual commands that can be copy/pasted
- Test that all documented commands work
- Package builds and installs successfully
```

---

# Implementation Order Summary

## Phase 1-3: Foundation (Completed)
1. **Prompt 1**: Testing infrastructure setup ✅
2. **Prompt 2**: Add ABOUTME comments ✅
3. **Prompt 3**: Unit tests for models ✅
4. **Prompt 4**: Unit tests for GC2 protocol ✅
5. **Prompt 5**: Unit tests for GSPro client ✅
6. **Prompt 6**: Settings module (TDD) ✅
7. **Prompt 7**: Integrate settings into UI ✅

## Phase 3-4: Reliability & Features
8. **Prompt 8**: Auto-reconnection logic
9. **Prompt 9**: Integration tests
10. **Prompt 10**: Shot history improvements
11. **Prompt 11**: CSV export

## Phase 5: Open Range Feature
12. **Prompt 12**: Open Range data models & constants
13. **Prompt 13**: Aerodynamics module
14. **Prompt 14**: Trajectory simulation (RK4)
15. **Prompt 15**: Ground physics (bounce/roll)
16. **Prompt 16**: Physics engine integration
17. **Prompt 17**: Mode selection & shot router
18. **Prompt 18**: Open Range settings
19. **Prompt 19**: 3D driving range visualization
20. **Prompt 20**: Open Range UI panel
21. **Prompt 21**: Open Range integration
21b. **Prompt 21b**: Ball trajectory tracing

## Phase 6: Polish & Release
22. **Prompt 22**: End-to-end tests
23. **Prompt 23**: Type checking cleanup
24. **Prompt 24**: Documentation & release

Each prompt builds on previous work. No orphaned code - everything is integrated.
