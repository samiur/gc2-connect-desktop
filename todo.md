# GC2 Connect Desktop - Implementation TODO

## Current Status: Open Range Feature Development

Started: 2025-12-30
Target Release: v1.1.0 (with Open Range)

---

## Phase 1: Foundation & Testing Infrastructure ✅

- [x] **Prompt 1**: Project Setup & Testing Infrastructure
  - [x] Update pyproject.toml with dev dependencies
  - [x] Create pytest configuration
  - [x] Create test directory structure
  - [x] Add mypy configuration
  - [x] Add ruff configuration
  - [x] Create smoke test
  - [x] Verify all tools work

- [x] **Prompt 2**: Add ABOUTME Comments
  - [x] Add comments to all Python files
  - [x] Verify linting passes

- [x] **Prompt 3**: Unit Tests for Data Models
  - [x] Test GC2ShotData
  - [x] Test GSProShotMessage
  - [x] Test GSProResponse

- [x] **Prompt 4**: Unit Tests for GC2 Protocol
  - [x] Test basic parsing
  - [x] Test validation
  - [x] Test edge cases

- [x] **Prompt 5**: Unit Tests for GSPro Client
  - [x] Test initialization
  - [x] Test connection state
  - [x] Test message formatting
  - [x] Mock socket operations

---

## Phase 2: Configuration & Settings ✅

- [x] **Prompt 6**: Settings Module Implementation
  - [x] Write tests first (TDD)
  - [x] Implement Settings class
  - [x] Platform-specific paths
  - [x] Load/save functionality

- [x] **Prompt 7**: Integrate Settings into UI
  - [x] Load settings on startup
  - [x] Save settings on change
  - [x] Add settings panel

---

## Phase 3: Reliability & Error Handling ✅

- [x] **Prompt 8**: Auto-Reconnection Logic
  - [x] Write tests for reconnection
  - [x] Create ReconnectionManager
  - [x] Integrate with GC2 reader
  - [x] Integrate with GSPro client
  - [x] Update UI for status

---

## Phase 4: GSPro Features

- [x] **Prompt 9**: Integration Tests
  - [x] Test full shot flow (MockGC2 -> App -> MockGSPro)
  - [x] Test connection handling
  - [x] Create test fixtures

- [x] **Prompt 10**: Shot History Improvements
  - [x] Create ShotHistoryManager
  - [x] Add session statistics
  - [x] Improve UI performance

- [x] **Prompt 11**: CSV Export
  - [x] Implement export function
  - [x] Add UI export button
  - [x] Test file output

---

## Phase 5: Open Range Feature (NEW)

### Physics Engine

- [x] **Prompt 12**: Open Range Data Models & Constants
  - [x] Write tests for Vec3, TrajectoryPoint, etc.
  - [x] Create open_range/models.py
  - [x] Create open_range/physics/constants.py
  - [x] Match docs/PHYSICS.md specifications

- [x] **Prompt 13**: Aerodynamics Module
  - [x] Write tests for Cd, Cl, air density
  - [x] Create open_range/physics/aerodynamics.py
  - [x] Implement Reynolds number calculation
  - [x] Implement drag coefficient (piecewise linear)
  - [x] Implement lift coefficient (quadratic formula)
  - [x] Implement air density calculation

- [x] **Prompt 14**: Trajectory Simulation (RK4)
  - [x] Write tests for flight physics
  - [x] Create open_range/physics/trajectory.py
  - [x] Implement RK4 integration
  - [x] Implement force calculations (gravity, drag, Magnus)
  - [x] Implement wind model
  - [x] Validate against Nathan model data

- [x] **Prompt 15**: Ground Physics (Bounce/Roll)
  - [x] Write tests for bounce and roll
  - [x] Create open_range/physics/ground.py
  - [x] Implement bounce physics (COR, friction)
  - [x] Implement roll physics (deceleration)
  - [x] Test surface types (Fairway, Rough, Green)

- [x] **Prompt 16**: Physics Engine Integration
  - [x] Write validation tests (driver, 7-iron, wedge)
  - [x] Create open_range/physics/engine.py (PhysicsEngine)
  - [x] Create open_range/engine.py (OpenRangeEngine)
  - [x] Performance test < 100ms per shot
  - [x] Validate carry distances within 5% tolerance

### Mode Selection & Settings

- [x] **Prompt 17**: Mode Selection & Shot Router
  - [x] Write tests for shot router
  - [x] Create services/shot_router.py
  - [x] Implement AppMode enum
  - [x] Implement mode switching
  - [x] Implement shot routing

- [x] **Prompt 18**: Open Range Settings
  - [x] Write tests for settings migration
  - [x] Add OpenRangeSettings to Settings class
  - [x] Add ConditionsSettings (temp, elevation, wind)
  - [x] Implement v1 -> v2 migration
  - [x] Update schema version

### Visualization & UI

- [x] **Prompt 19**: 3D Driving Range Visualization
  - [x] Write tests for visualization
  - [x] Create open_range/visualization/range_scene.py
  - [x] Create ground plane and distance markers
  - [x] Create target greens
  - [x] Create open_range/visualization/ball_animation.py
  - [x] Implement ball flight animation

- [x] **Prompt 20**: Open Range UI Panel
  - [x] Write integration tests
  - [x] Create ui/components/mode_selector.py
  - [x] Create ui/components/open_range_view.py
  - [x] Implement phase indicators
  - [x] Implement shot data display

- [x] **Prompt 21**: Open Range Integration
  - [x] Write integration flow tests
  - [x] Update ui/app.py with mode selector
  - [x] Wire shot router to GC2 reader
  - [x] Wire shot router to GSPro and Open Range
  - [x] Handle mode-specific UI visibility
  - [x] Performance validation

- [x] **Prompt 21b**: Ball Trajectory Tracing
  - [x] Write tests for trajectory trace
  - [x] Implement draw_trajectory_line() in range_scene.py
  - [x] Update BallAnimator to draw trajectory progressively
  - [x] Use phase-appropriate colors (Flight=green, Bounce=orange, Rolling=blue)
  - [x] Ensure trace remains visible after animation

---

## Phase 6: Polish & Release

- [x] **Prompt 22**: End-to-End Tests
  - [x] Setup e2e infrastructure
  - [x] Test GSPro user flows
  - [x] Test Open Range user flows
  - [x] Test error handling

- [x] **Prompt 23**: Type Checking & Linting
  - [x] Fix all mypy errors
  - [x] Fix all ruff issues
  - [x] Add pre-commit hooks

- [x] **Prompt 24**: Documentation & Release
  - [x] Update README for Open Range
  - [x] Create CONTRIBUTING.md
  - [x] Create CHANGELOG.md
  - [x] USB setup guides
  - [x] Version bump to 1.1.0
  - [x] Full test suite with coverage
  - [x] Build package

---

## Quick Reference

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=gc2_connect

# Type checking
uv run mypy src/

# Linting
uv run ruff check .

# Run the app
uv run python -m gc2_connect.main

# Run mock GSPro server
uv run python tools/mock_gspro_server.py
```

---

## Notes

- Each prompt should be run sequentially
- Mark items complete with [x] as you finish them
- Add any issues or blockers below

### Issues/Blockers

(none yet)

### Decisions Made

- **0M Message Handling (2026-01-02)**: Added parsing of 0M messages for ball status. FLAGS=7 means ready (green light), BALLS>0 means ball detected. Status sent to GSPro via `LaunchMonitorIsReady` and `LaunchMonitorBallDetected` flags.
- **Shot Validation (2026-01-02)**: Updated validation to match gc2_to_TGC: reject only when back_spin=0 AND side_spin=0 (not just total_spin=0). Also reject back_spin=2222 error code. Allow any positive ball speed (chip shots are valid).
- **GSPro Socket Configuration (2026-01-03)**: Must use `TCP_NODELAY` socket option for immediate sends. Use `socket.create_connection()` for cleaner handling.
- **GSPro Response Handling (2026-01-03)**: GSPro doesn't respond to heartbeat or status messages - don't wait for response. Only wait for response on shot data. Clear buffer before sending to handle concatenated responses.
- **GSPro Buffer Management (2026-01-03)**: Use `json.JSONDecoder.raw_decode()` to parse only first JSON object (handles concatenated responses from buffered messages).
- **Ball Speed Units (2026-01-03)**: GSPro expects ball speed in mph (not m/s). The debug window may show wrong values but actual game uses mph correctly.
- **Shutdown Handling (2026-01-03)**: Added proper shutdown handlers to disconnect GSPro and GC2 cleanly. Uses NiceGUI `app.on_shutdown()`, signal handlers (SIGINT, SIGTERM), and atexit fallback.
- **Open Range Physics (2026-01-03)**: Using Nathan model + WSU aerodynamics. Cd uses piecewise linear with spin term. Cl uses quadratic formula (not table lookup). Validated against libgolf reference implementation.
- **Open Range Visualization (2026-01-03)**: Using NiceGUI's Three.js integration (ui.scene). Ball animation follows trajectory points with phase indicators.
- **Auto-Reconnection (2026-01-03)**: ReconnectionManager uses exponential backoff (1s, 2s, 4s, 8s, 16s). GC2 USB disconnects detected via error messages (no device, io error, etc). GSPro disconnects detected via socket errors. UI shows yellow "Reconnecting..." status during attempts.
- **Incomplete Shot Handling (2026-01-03)**: GC2 sometimes doesn't send complete spin data (ball moves out of view before calculation completes). Added SPIN_WAIT_TIMEOUT_SEC (1.5s) - if we have basic shot data (SHOT_ID, SPEED_MPH, ELEVATION_DEG) but no spin after timeout, process the shot anyway with estimated spin. Shots are logged as "INCOMPLETE" so users know spin data may be inaccurate.
- **Interrupted Shot Handling (2026-01-03)**: GC2 sometimes abandons multi-packet shot data transmission when ball status changes (0M message interrupts 0H message). Fixed by: (1) clearing line_buffer when new 0H message starts (prevents data corruption), (2) detecting when 0M interrupts 0H and salvaging/discarding incomplete data immediately rather than letting it pollute subsequent shots, (3) allowing shots with just SHOT_ID+SPEED_MPH to be processed with estimated launch angle (20°) when ELEVATION_DEG is missing.
- **GC2 Two-Phase Transmission (2026-01-03)**: GC2 sends shot data twice per shot: preliminary (~140ms, estimated spin) and refined (~1000ms, accurate spin). We now skip preliminary data (MSEC_SINCE_CONTACT < 500) and wait for refined data to get accurate spin measurements. If refined is interrupted, salvage logic kicks in.

### Architecture Decisions

- **Physics Engine Location**: `src/gc2_connect/open_range/physics/` - Separate from UI for testability
- **Mode Switching**: ShotRouter handles routing, UI handles visibility
- **Settings Migration**: Automatic v1 -> v2 migration on load
- **Coordinate System**: X=forward (yards), Y=height (feet), Z=lateral (yards)
- **Test Simulator Infrastructure (2026-01-03)**: Created comprehensive test infrastructure in `tests/simulators/` with:
  - **GC2 USB Simulator**: Generates realistic 64-byte USB packets matching real GC2 behavior. Supports two-phase transmission (preliminary at ~200ms, refined at ~1000ms), field splitting across packet boundaries, and status message interruptions. Uses `PacketSource` protocol for dependency injection into `GC2USBReader`.
  - **Mock GSPro Server**: Async TCP server with configurable response types (SUCCESS, ERROR, TIMEOUT, DISCONNECT, INVALID_JSON), delays, and shot tracking. Supports dynamic config updates during tests.
  - **TimeController**: Enables INSTANT mode for fast deterministic tests vs REAL mode for actual timing behavior.
  - **Pre-built Scenarios**: `create_two_phase_transmission_sequence()`, `create_status_interrupted_sequence()`, `create_split_field_sequence()`, `create_rapid_fire_sequence()` for common test patterns.
  - **Key Benefit**: All 682 tests pass including integration tests that verify no packets are dropped during rapid fire sequences (5/5 shots received in correct order).
