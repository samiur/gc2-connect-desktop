# GC2 Connect Desktop - Implementation TODO

## Current Status: OpenGolfCoach Integration (Phase 5b)

Started: 2025-12-30
Target Release: v1.1.0 (with Open Range)

---

## Completed Phases ✅

### Phase 1: Foundation & Testing Infrastructure ✅
- [x] Prompts 1-5: Setup, ABOUTME comments, unit tests

### Phase 2: Configuration & Settings ✅
- [x] Prompts 6-7: Settings module and UI integration

### Phase 3: Reliability & Error Handling ✅
- [x] Prompts 7b-7d: GSPro disconnect, reader loop, heartbeat
- [x] Prompt 8: Auto-reconnection logic

### Phase 4: GSPro Features ✅
- [x] Prompts 9-11: Integration tests, shot history, CSV export

### Phase 5: Open Range Feature ✅
- [x] Prompts 12-16: Physics engine (models, aerodynamics, trajectory, ground, integration)
- [x] Prompts 17-18: Mode selection, shot router, settings
- [x] Prompts 19-21b: Visualization, UI, integration, trajectory tracing

### Phase 6: Polish & Release ✅
- [x] Prompts 22-24: E2E tests, type checking, documentation

---

## Phase 5b: OpenGolfCoach Integration (IN PROGRESS)

- [x] **Prompt 21c**: Add OpenGolfCoach Dependency
  - [x] Add opengolfcoach package via uv add
  - [x] Create opengolfcoach_wrapper.py with OpenGolfCoachInput/Result dataclasses
  - [x] Implement calculate_shot() function
  - [x] Implement calculate_shot_from_gc2() convenience function
  - [x] Write tests in tests/unit/test_opengolfcoach_wrapper.py
  - [x] Handle import errors gracefully (fallback to custom physics)

- [x] **Prompt 21d**: Integrate OpenGolfCoach into ShotSummary
  - [x] Write tests for extended models
  - [x] Create DerivedShotData model (shot_name, shot_rank, shot_color_rgb, etc.)
  - [x] Update ShotResult to include optional derived field
  - [x] Ensure backwards compatibility (derived is optional)

- [x] **Prompt 21e**: Update OpenRangeEngine to Use OpenGolfCoach
  - [x] Write tests for engine integration
  - [x] Update simulate_shot() to enrich results with OpenGolfCoach data
  - [x] Add _enrich_with_opengolfcoach() method
  - [x] Graceful fallback if OpenGolfCoach unavailable
  - [x] Keep trajectory from custom physics engine (OGC doesn't provide trajectory)

- [ ] **Prompt 21f**: Update Open Range UI for Shot Classification ← NEXT
  - [ ] Write integration tests for classification UI
  - [ ] Add shot classification panel (shot_name, shot_rank)
  - [ ] Add rank badge with color coding (S+=gold, S=silver, A=green, etc.)
  - [ ] Update _update_data_display() to show classification
  - [ ] Handle missing derived data gracefully

- [ ] **Prompt 21g**: Validate OpenGolfCoach vs Physics Engine
  - [ ] Write comparison tests (driver, 7-iron, wedge shots)
  - [ ] Verify both engines within 15% tolerance
  - [ ] Add distance comparison logging
  - [ ] Skip tests gracefully if OpenGolfCoach not installed

---

## Phase 5c: Enhanced Driving Range Visuals (PLANNED)

- [ ] **Prompt 25**: Procedural Terrain and Atmosphere
- [ ] **Prompt 26**: Multiple Camera Views and Minimap

---

## Phase 5d: Minigames Framework (PLANNED)

- [ ] **Prompt 27**: Minigames Base Architecture
- [ ] **Prompt 28**: Putting Green Minigame
- [ ] **Prompt 29**: Target Range Minigame
- [ ] **Prompt 30**: Golf Darts Minigame
- [ ] **Prompt 31**: Minigames UI and Game Selector

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

# Run all CI checks locally
uv run pytest && uv run mypy src/ && uv run ruff check . && uv run ruff format --check .
```

---

## Key Decisions Made

- **OpenGolfCoach Integration (2026-01-21)**: Replacing custom shot calculations with the OpenGolfCoach library. Key benefits: shot classification, quality ranking (S+ to E), smash factor, estimated club data. Custom physics engine KEPT for trajectory visualization (OpenGolfCoach doesn't provide trajectory points).
- **Shanktuary Golf Research (2026-01-21)**: Adopted enhanced driving range visuals (terrain, fog, trees, cameras, minimap), then minigames framework.
- **GSPro Response Reader and Heartbeat Timer (2026-01-15)**: Background reader loop for codes 201/202/203, match state tracking, 6-second heartbeat intervals.
- **Open Range Physics**: Nathan model + WSU aerodynamics. RK4 integration, validated against libgolf reference.
- **Test Simulator Infrastructure**: GC2 USB packet simulator, Mock GSPro server, TimeController for deterministic tests.

---

## Architecture Notes

- **Physics Engine**: `src/gc2_connect/open_range/physics/`
- **Mode Switching**: ShotRouter handles routing, UI handles visibility
- **Settings Migration**: Automatic v1 -> v2 migration on load
- **Coordinate System**: X=forward (yards), Y=height (feet), Z=lateral (yards)
