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

- [ ] **Prompt 13**: Aerodynamics Module
  - [ ] Write tests for Cd, Cl, air density
  - [ ] Create open_range/physics/aerodynamics.py
  - [ ] Implement Reynolds number calculation
  - [ ] Implement drag coefficient (piecewise linear)
  - [ ] Implement lift coefficient (quadratic formula)
  - [ ] Implement air density calculation

- [ ] **Prompt 14**: Trajectory Simulation (RK4)
  - [ ] Write tests for flight physics
  - [ ] Create open_range/physics/trajectory.py
  - [ ] Implement RK4 integration
  - [ ] Implement force calculations (gravity, drag, Magnus)
  - [ ] Implement wind model
  - [ ] Validate against Nathan model data

- [ ] **Prompt 15**: Ground Physics (Bounce/Roll)
  - [ ] Write tests for bounce and roll
  - [ ] Create open_range/physics/ground.py
  - [ ] Implement bounce physics (COR, friction)
  - [ ] Implement roll physics (deceleration)
  - [ ] Test surface types (Fairway, Rough, Green)

- [ ] **Prompt 16**: Physics Engine Integration
  - [ ] Write validation tests (driver, 7-iron, wedge)
  - [ ] Create open_range/physics/engine.py (PhysicsEngine)
  - [ ] Create open_range/engine.py (OpenRangeEngine)
  - [ ] Performance test < 100ms per shot
  - [ ] Validate carry distances within 5% tolerance

### Mode Selection & Settings

- [ ] **Prompt 17**: Mode Selection & Shot Router
  - [ ] Write tests for shot router
  - [ ] Create services/shot_router.py
  - [ ] Implement AppMode enum
  - [ ] Implement mode switching
  - [ ] Implement shot routing

- [ ] **Prompt 18**: Open Range Settings
  - [ ] Write tests for settings migration
  - [ ] Add OpenRangeSettings to Settings class
  - [ ] Add ConditionsSettings (temp, elevation, wind)
  - [ ] Implement v1 -> v2 migration
  - [ ] Update schema version

### Visualization & UI

- [ ] **Prompt 19**: 3D Driving Range Visualization
  - [ ] Write tests for visualization
  - [ ] Create open_range/visualization/range_scene.py
  - [ ] Create ground plane and distance markers
  - [ ] Create target greens
  - [ ] Create open_range/visualization/ball_animation.py
  - [ ] Implement ball flight animation

- [ ] **Prompt 20**: Open Range UI Panel
  - [ ] Write integration tests
  - [ ] Create ui/components/mode_selector.py
  - [ ] Create ui/components/open_range_view.py
  - [ ] Implement phase indicators
  - [ ] Implement shot data display

- [ ] **Prompt 21**: Open Range Integration
  - [ ] Write integration flow tests
  - [ ] Update ui/app.py with mode selector
  - [ ] Wire shot router to GC2 reader
  - [ ] Wire shot router to GSPro and Open Range
  - [ ] Handle mode-specific UI visibility
  - [ ] Performance validation

---

## Phase 6: Polish & Release

- [ ] **Prompt 22**: End-to-End Tests
  - [ ] Setup e2e infrastructure
  - [ ] Test GSPro user flows
  - [ ] Test Open Range user flows
  - [ ] Test error handling

- [ ] **Prompt 23**: Type Checking & Linting
  - [ ] Fix all mypy errors
  - [ ] Fix all ruff issues
  - [ ] Add pre-commit hooks

- [ ] **Prompt 24**: Documentation & Release
  - [ ] Update README for Open Range
  - [ ] Create CONTRIBUTING.md
  - [ ] Create CHANGELOG.md
  - [ ] USB setup guides
  - [ ] Version bump to 1.1.0
  - [ ] Full test suite with coverage
  - [ ] Build package

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

### Architecture Decisions

- **Physics Engine Location**: `src/gc2_connect/open_range/physics/` - Separate from UI for testability
- **Mode Switching**: ShotRouter handles routing, UI handles visibility
- **Settings Migration**: Automatic v1 -> v2 migration on load
- **Coordinate System**: X=forward (yards), Y=height (feet), Z=lateral (yards)
