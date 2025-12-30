# Product Requirements Document (PRD)
# GC2 Connect Desktop

## Overview

### Product Name
GC2 Connect Desktop

### Version
1.0.0

### Last Updated
December 2024

### Author
Samiur Rahman

---

## Executive Summary

GC2 Connect Desktop is a cross-platform desktop application that enables Foresight GC2 launch monitor owners to use their device with GSPro golf simulation software on Mac and Linux systems. Currently, the GC2 only works with Windows via Foresight's proprietary FSX software, leaving Mac and Linux users without a native solution.

This application bridges that gap by reading shot data directly from the GC2 via USB and transmitting it to GSPro over the network using the GSPro Open Connect API v1.

---

## Problem Statement

### Current Situation
- Foresight GC2 launch monitors only work with Windows through FSX software
- Mac and Linux users must use complex workarounds (VirtualHere, VMs, etc.)
- The GC2's Bluetooth functionality is broken and unlikely to be fixed
- No official cross-platform solution exists from Foresight

### User Pain Points
1. Mac users cannot natively connect their GC2 to GSPro
2. Existing workarounds (VirtualHere + Windows VM) are cumbersome and unreliable
3. Additional latency introduced by virtualization affects the golf simulation experience
4. Setup complexity discourages casual users

### Opportunity
Provide a native, lightweight solution that allows Mac and Linux users to use their GC2 with GSPro without virtualization or complex network setups.

---

## Goals & Success Metrics

### Primary Goals
1. Enable native GC2 USB communication on Mac and Linux
2. Seamlessly transmit shot data to GSPro via network
3. Provide a simple, intuitive user interface
4. Achieve feature parity with Windows-based solutions

### Success Metrics
| Metric | Target |
|--------|--------|
| Shot detection accuracy | 100% (no missed shots) |
| Shot transmission latency | < 100ms |
| Application stability | No crashes during typical session |
| Setup time for new users | < 5 minutes |

---

## Target Users

### Primary Persona: Home Golf Simulator Owner
- **Demographics**: Golf enthusiast, 30-55 years old
- **Technical Level**: Moderate (comfortable with software installation)
- **Equipment**: Foresight GC2 (with or without HMT), Mac or Linux computer
- **Use Case**: Practice golf at home using GSPro simulation
- **Pain Point**: Cannot use GC2 on Mac without complex workarounds

### Secondary Persona: Golf Instructor
- **Demographics**: Teaching professional, uses launch monitor for lessons
- **Technical Level**: Low to moderate
- **Equipment**: GC2, MacBook for portability
- **Use Case**: Show students shot data during lessons
- **Pain Point**: Needs portable solution that works with Mac

---

## Features & Requirements

### P0 - Must Have (MVP)

#### F1: GC2 USB Connection
- **Description**: Detect and connect to GC2 via USB
- **Requirements**:
  - Auto-detect GC2 when connected (VID: 0x2C79, PID: 0x0110)
  - Handle USB permissions on Mac/Linux
  - Display connection status in UI
  - Reconnect automatically if connection is lost
- **Acceptance Criteria**:
  - App detects GC2 within 2 seconds of USB connection
  - Clear error message if GC2 not found
  - Connection survives brief USB interruptions

#### F2: Shot Data Reading
- **Description**: Read and parse shot data from GC2
- **Requirements**:
  - Parse GC2 text-based USB protocol
  - Extract ball data: speed, launch angle, spin rates
  - Extract club data (if HMT present): club speed, path, face angle
  - Validate shot data (reject misreads)
- **Acceptance Criteria**:
  - All valid shots are captured
  - Misreads (zero spin, known bad patterns) are rejected
  - Data matches what FSX displays for same shot

#### F3: GSPro Network Connection
- **Description**: Connect to GSPro via Open Connect API v1
- **Requirements**:
  - TCP socket connection to configurable IP:port
  - Support GSPro Open Connect API v1 protocol
  - Handle connection/disconnection gracefully
  - Queue shots if temporarily disconnected
- **Acceptance Criteria**:
  - Connects to GSPro on local network
  - Shots appear in GSPro within 100ms
  - Reconnects automatically after network interruption

#### F4: Shot Display
- **Description**: Display current shot data in the application
- **Requirements**:
  - Show ball speed, launch angle, spin rates
  - Show club data when HMT is present
  - Clear visual indication of new shot
  - Display units (mph, degrees, rpm)
- **Acceptance Criteria**:
  - Shot data updates immediately when received
  - All relevant metrics are displayed
  - UI is readable and well-organized

#### F5: Basic UI
- **Description**: Simple, functional user interface
- **Requirements**:
  - Connection status indicators (GC2, GSPro)
  - Connect/disconnect buttons
  - Settings for GSPro IP address and port
  - Dark theme suitable for simulator environments
- **Acceptance Criteria**:
  - User can configure and connect in under 1 minute
  - Status is always clear at a glance
  - Works well in low-light environments

### P1 - Should Have

#### F6: Shot History
- **Description**: View history of shots in current session
- **Requirements**:
  - List of all shots with key metrics
  - Scrollable list with newest shots at top
  - Shot count display
- **Acceptance Criteria**:
  - All shots from session are listed
  - Can scroll through history
  - Performance remains good with 100+ shots

#### F7: Settings Persistence
- **Description**: Remember user settings between sessions
- **Requirements**:
  - Save GSPro connection settings
  - Save UI preferences
  - Load settings on app start
- **Acceptance Criteria**:
  - Settings survive app restart
  - No need to reconfigure each session

#### F8: Mock Mode
- **Description**: Test mode without physical GC2
- **Requirements**:
  - Simulate shot data for testing
  - Test GSPro connection without hardware
  - Useful for development and troubleshooting
- **Acceptance Criteria**:
  - Can send test shots to GSPro
  - Clearly indicated as mock/test mode

### P2 - Nice to Have

#### F9: Session Statistics
- **Description**: Basic statistics for current session
- **Requirements**:
  - Average ball speed, launch angle, spin
  - Shot count by club (if detectable)
- **Acceptance Criteria**:
  - Stats update in real-time
  - Accurate calculations

#### F10: Data Export
- **Description**: Export shot data to file
- **Requirements**:
  - CSV export of session data
  - Include all shot metrics
- **Acceptance Criteria**:
  - File opens correctly in Excel/Sheets
  - All data is included

#### F11: Auto-start with GSPro
- **Description**: Launch app automatically when GSPro starts
- **Requirements**:
  - System tray/menu bar presence
  - Auto-connect when GC2 detected
- **Acceptance Criteria**:
  - Minimal user intervention needed

---

## User Flows

### Flow 1: First-Time Setup
1. User downloads and installs application
2. User connects GC2 via USB
3. App detects GC2 and shows "Connected"
4. User enters GSPro PC's IP address
5. User clicks "Connect to GSPro"
6. App connects and shows "Ready"
7. User hits a shot
8. Shot appears in app and GSPro simultaneously

### Flow 2: Typical Session
1. User opens app (settings remembered)
2. App auto-detects GC2
3. App auto-connects to GSPro
4. User plays golf, shots flow automatically
5. User closes app when done

### Flow 3: Troubleshooting Connection
1. User sees "GC2 Not Found" error
2. User checks USB connection
3. User clicks "Scan for Devices"
4. App finds GC2 and connects
5. Alternatively, user checks USB permissions

---

## Technical Constraints

### Platform Support
- **macOS**: 11.0 (Big Sur) and later
- **Linux**: Ubuntu 20.04+, Fedora 34+, other major distributions
- **Windows**: Not targeted (FSX already works)

### Dependencies
- Python 3.10+
- libusb (for USB communication)
- Network access to GSPro PC

### Hardware Requirements
- Foresight GC2 launch monitor
- USB-A or USB-C port
- Network connection (WiFi or Ethernet)

---

## Out of Scope (v1.0)

- Windows support (use FSX instead)
- Bluetooth connectivity (GC2 BT is broken)
- Direct integration with other simulators (E6, TGC, etc.)
- Shot video recording
- Cloud data sync
- Mobile companion app (separate project)

---

## Timeline

### Phase 1: Core Functionality (Weeks 1-2)
- USB communication layer
- GC2 protocol parsing
- GSPro client implementation
- Basic data models

### Phase 2: User Interface (Weeks 2-3)
- NiceGUI application shell
- Connection panels
- Shot display
- Settings management

### Phase 3: Polish & Testing (Weeks 3-4)
- Error handling
- Reconnection logic
- Testing with actual hardware
- Documentation

### Phase 4: Release (Week 4)
- Package as standalone app
- User documentation
- Initial release

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| GC2 USB protocol changes | High | Low | Protocol is stable; monitor for changes |
| USB permission issues on Linux | Medium | Medium | Clear documentation; udev rules |
| GSPro API changes | Medium | Low | API v1 is stable; support multiple versions |
| Poor app performance | Medium | Low | Use efficient async I/O; test thoroughly |

---

## Appendix

### Related Documents
- Technical Requirements Document (TRD)
- GC2 USB Protocol Specification
- GSPro Open Connect API v1 Documentation

### Glossary
- **GC2**: Foresight GC2 launch monitor
- **HMT**: Head Measurement Technology (club data add-on)
- **GSPro**: Golf simulation software
- **FSX**: Foresight Sports Experience (Windows software)
- **VID/PID**: USB Vendor ID / Product ID
