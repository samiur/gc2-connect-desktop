# GC2 Connect Desktop - Implementation Plan

> **Related Documentation:**
> - `docs/PRD.md` - Product requirements
> - `docs/TRD.md` - Technical requirements
> - `docs/GC2_PROTOCOL.md` - USB protocol specification
> - `todo.md` - Implementation tracking

## Project Summary

GC2 Connect Desktop is a Python application that reads shot data from a Foresight GC2 golf launch monitor via USB and sends it to GSPro golf simulation software over the network. The target platforms are macOS and Linux.

## Current State Analysis

The project has an initial implementation with the following components:

### Already Implemented
- **models.py**: Data models (GC2ShotData, GSProShotMessage, GSProResponse, etc.)
- **gc2/usb_reader.py**: USB reader with GC2USBReader and MockGC2Reader classes
- **gspro/client.py**: GSPro TCP client for Open Connect API v1
- **ui/app.py**: NiceGUI interface with connection panels, shot display, shot history
- **tools/mock_gspro_server.py**: Mock GSPro server for testing

### Missing/Incomplete
- **Tests**: No unit, integration, or e2e tests exist
- **Configuration persistence**: Settings not saved between sessions
- **Type checking**: mypy not configured
- **ABOUTME comments**: Files missing required header comments
- **Auto-reconnection**: Not fully implemented
- **Settings module**: config/ folder is empty
- **Linting**: ruff/mypy dependencies incomplete

## Implementation Phases

### Phase 1: Foundation & Testing Infrastructure
Set up proper testing, linting, and type checking. Add tests for existing code.

### Phase 2: Configuration & Settings
Implement settings persistence so users don't need to reconfigure each session.

### Phase 3: Reliability & Error Handling
Add auto-reconnection logic and improve error handling.

### Phase 4: P1 Features
Implement "should have" features from PRD (shot history improvements, mock mode UI).

### Phase 5: Polish & Packaging
Final testing, documentation, and packaging for distribution.

---

# Prompts

## Prompt 1: Project Setup & Testing Infrastructure

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

## Prompt 2: Add ABOUTME Comments to Existing Files

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

## Prompt 3: Unit Tests for Data Models

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

## Prompt 4: Unit Tests for GC2 Protocol Parsing

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

## Prompt 5: Unit Tests for GSPro Client

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

## Prompt 6: Settings Module Implementation

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

## Prompt 7: Integrate Settings into UI

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

## Prompt 12: End-to-End Tests

```text
Create end-to-end tests that verify the complete application works correctly.

CONTEXT:
- E2E tests should test the actual NiceGUI application
- Use browser automation or NiceGUI's test utilities
- Focus on critical user flows

TASK:

1. Set up e2e test infrastructure:
   - Create tests/e2e/__init__.py
   - Add any needed dependencies (playwright or nicegui test utils)
   - Create fixtures for app lifecycle

2. Create tests/e2e/test_user_flows.py:
   - Test: App loads and displays correctly
   - Test: Can connect to mock GC2
   - Test: Can configure GSPro connection settings
   - Test: Mock shot appears in UI
   - Test: Shot history updates
   - Test: Settings persist after restart

3. Create tests/e2e/test_error_handling.py:
   - Test: Clear error when GC2 not found
   - Test: Clear error when GSPro connection fails
   - Test: App recovers from errors gracefully

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

## Prompt 13: Type Checking & Linting Cleanup

```text
Fix all type checking and linting issues in the codebase.

CONTEXT:
- mypy is configured but may have errors
- ruff is configured for linting
- All code should pass both checks

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

## Prompt 14: Documentation & README

```text
Create comprehensive documentation for users and developers.

CONTEXT:
- README.md exists but may need updates
- Users need setup instructions
- Developers need contribution guidelines

TASK:

1. Update README.md:
   - Clear project description
   - Screenshots of the UI (describe where to add them)
   - Installation instructions (macOS and Linux)
   - Quick start guide
   - Configuration options
   - Troubleshooting section (USB permissions, network issues)

2. Create CONTRIBUTING.md:
   - Development setup
   - Running tests
   - Code style guide
   - Pull request process

3. Update docs/:
   - Verify PRD.md is current
   - Verify TRD.md is current
   - Add any new technical decisions

4. Add inline documentation:
   - Ensure all public functions have docstrings
   - Add module-level docstrings
   - Document any complex logic

5. Create USB permission guides:
   - docs/LINUX_USB_SETUP.md with udev rules
   - docs/MACOS_USB_SETUP.md if needed

REQUIREMENTS:
- Documentation should be clear for non-technical users
- Include actual commands that can be copy/pasted
- Test that all documented commands work
```

---

## Prompt 15: Final Testing & Packaging

```text
Perform final testing and prepare for distribution.

CONTEXT:
- All features are implemented
- All tests should pass
- Need to package for distribution

TASK:

1. Run full test suite with coverage:
   - uv run pytest --cov=gc2_connect --cov-report=html
   - Review coverage report
   - Add tests for any uncovered critical paths
   - Target: >80% coverage

2. Manual testing checklist:
   - [ ] App starts without errors
   - [ ] Mock GC2 connects and sends test shots
   - [ ] Test shots appear in UI
   - [ ] Settings are saved and loaded
   - [ ] GSPro connection works (with mock server)
   - [ ] Shot history displays correctly
   - [ ] CSV export works
   - [ ] Error messages are clear

3. Packaging:
   - Verify pyproject.toml is complete
   - Test: uv build
   - Verify package installs correctly
   - Test entry point: gc2-connect command

4. Create GitHub release assets:
   - Source distribution
   - Wheel
   - (Optional) PyInstaller executable

5. Final cleanup:
   - Remove any debug code
   - Verify no hardcoded test values
   - Check for TODO comments that need addressing

REQUIREMENTS:
- All tests pass
- No linting errors
- Package builds successfully
- App runs from installed package
```

---

# Implementation Order Summary

1. **Prompt 1**: Testing infrastructure setup
2. **Prompt 2**: Add ABOUTME comments
3. **Prompt 3**: Unit tests for models
4. **Prompt 4**: Unit tests for GC2 protocol
5. **Prompt 5**: Unit tests for GSPro client
6. **Prompt 6**: Settings module (TDD)
7. **Prompt 7**: Integrate settings into UI
8. **Prompt 8**: Auto-reconnection logic
9. **Prompt 9**: Integration tests
10. **Prompt 10**: Shot history improvements
11. **Prompt 11**: CSV export
12. **Prompt 12**: End-to-end tests
13. **Prompt 13**: Type checking cleanup
14. **Prompt 14**: Documentation
15. **Prompt 15**: Final testing & packaging

Each prompt builds on previous work. No orphaned code - everything is integrated.
