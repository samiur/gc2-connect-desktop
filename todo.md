# GC2 Connect Desktop - Implementation TODO

## Current Status: Planning Complete

Started: 2025-12-30

---

## Phase 1: Foundation & Testing Infrastructure

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

## Phase 2: Configuration & Settings

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

## Phase 3: Reliability & Error Handling

- [ ] **Prompt 8**: Auto-Reconnection Logic
  - [ ] Create ReconnectionManager
  - [ ] Integrate with GC2 reader
  - [ ] Integrate with GSPro client
  - [ ] Update UI for status

---

## Phase 4: Integration & Features

- [ ] **Prompt 9**: Integration Tests
  - [ ] Test full shot flow
  - [ ] Test connection handling
  - [ ] Create test fixtures

- [ ] **Prompt 10**: Shot History Improvements
  - [ ] Create ShotHistoryManager
  - [ ] Add session statistics
  - [ ] Improve UI performance

- [ ] **Prompt 11**: CSV Export
  - [ ] Implement export function
  - [ ] Add UI export button
  - [ ] Test file output

---

## Phase 5: Testing & Polish

- [ ] **Prompt 12**: End-to-End Tests
  - [ ] Setup e2e infrastructure
  - [ ] Test user flows
  - [ ] Test error handling

- [ ] **Prompt 13**: Type Checking & Linting
  - [ ] Fix all mypy errors
  - [ ] Fix all ruff issues
  - [ ] Add pre-commit hooks

- [ ] **Prompt 14**: Documentation
  - [ ] Update README
  - [ ] Create CONTRIBUTING.md
  - [ ] USB setup guides

- [ ] **Prompt 15**: Final Testing & Packaging
  - [ ] Full test suite with coverage
  - [ ] Manual testing
  - [ ] Build packages
  - [ ] Create release

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
