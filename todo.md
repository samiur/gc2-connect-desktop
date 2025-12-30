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

- [ ] **Prompt 3**: Unit Tests for Data Models
  - [ ] Test GC2ShotData
  - [ ] Test GSProShotMessage
  - [ ] Test GSProResponse

- [ ] **Prompt 4**: Unit Tests for GC2 Protocol
  - [ ] Test basic parsing
  - [ ] Test validation
  - [ ] Test edge cases

- [ ] **Prompt 5**: Unit Tests for GSPro Client
  - [ ] Test initialization
  - [ ] Test connection state
  - [ ] Test message formatting
  - [ ] Mock socket operations

---

## Phase 2: Configuration & Settings

- [ ] **Prompt 6**: Settings Module Implementation
  - [ ] Write tests first (TDD)
  - [ ] Implement Settings class
  - [ ] Platform-specific paths
  - [ ] Load/save functionality

- [ ] **Prompt 7**: Integrate Settings into UI
  - [ ] Load settings on startup
  - [ ] Save settings on change
  - [ ] Add settings panel

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

(track any architectural decisions here)
