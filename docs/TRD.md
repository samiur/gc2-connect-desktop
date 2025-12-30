# Technical Requirements Document (TRD)
# GC2 Connect Desktop

## Overview

### Document Purpose
This document defines the technical architecture, design decisions, and implementation details for the GC2 Connect Desktop application.

### Version
1.0.0

### Last Updated
December 2024

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GC2 Connect Desktop                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │   UI Layer   │    │  Service     │    │    Communication Layer   │  │
│  │   (NiceGUI)  │◄──►│  Layer       │◄──►│                          │  │
│  │              │    │              │    │  ┌────────┐ ┌──────────┐ │  │
│  │ • Connection │    │ • AppState   │    │  │ GC2    │ │ GSPro    │ │  │
│  │   Panels     │    │ • ShotMgr    │    │  │ USB    │ │ TCP      │ │  │
│  │ • Shot View  │    │ • Config     │    │  │ Reader │ │ Client   │ │  │
│  │ • Settings   │    │              │    │  └────┬───┘ └────┬─────┘ │  │
│  └──────────────┘    └──────────────┘    └───────┼──────────┼───────┘  │
│                                                   │          │          │
└───────────────────────────────────────────────────┼──────────┼──────────┘
                                                    │          │
                                              USB   │          │ TCP/IP
                                                    ▼          ▼
                                          ┌─────────────┐  ┌─────────────┐
                                          │ Foresight   │  │   GSPro     │
                                          │ GC2         │  │  (Windows)  │
                                          └─────────────┘  └─────────────┘
```

### Component Breakdown

#### 1. UI Layer (NiceGUI)
- Web-based UI framework running locally
- Reactive updates via WebSocket
- Dark theme optimized for simulator environments

#### 2. Service Layer
- Application state management
- Business logic (shot validation, data conversion)
- Configuration persistence

#### 3. Communication Layer
- GC2 USB Reader: libusb-based USB communication
- GSPro Client: TCP socket client for Open Connect API

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Language | Python | 3.10+ | Cross-platform, good USB/network libraries |
| UI Framework | NiceGUI | 1.4+ | Modern, reactive, easy deployment |
| USB Library | pyusb | 1.2+ | Cross-platform USB access via libusb |
| Async | asyncio | stdlib | Native async I/O for concurrent operations |
| Data Models | Pydantic | 2.0+ | Type-safe data validation |
| Config | JSON | stdlib | Simple, human-readable settings |

### Development Tools

| Tool | Purpose |
|------|---------|
| Poetry/pip | Dependency management |
| pytest | Testing |
| black | Code formatting |
| mypy | Type checking |
| PyInstaller | Standalone packaging |

---

## Module Design

### Directory Structure

```
gc2-connect-desktop/
├── pyproject.toml              # Project configuration
├── README.md                   # User documentation
├── docs/
│   ├── PRD.md                  # Product requirements
│   ├── TRD.md                  # Technical requirements
│   └── PROTOCOL.md             # GC2 protocol documentation
├── src/
│   └── gc2_connect/
│       ├── __init__.py
│       ├── main.py             # Application entry point
│       ├── models.py           # Data models (Pydantic)
│       ├── gc2/
│       │   ├── __init__.py
│       │   ├── usb_reader.py   # USB communication
│       │   └── protocol.py     # Protocol parsing
│       ├── gspro/
│       │   ├── __init__.py
│       │   ├── client.py       # TCP client
│       │   └── protocol.py     # API message formatting
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── app.py          # Main NiceGUI app
│       │   └── components/     # UI components
│       └── config/
│           ├── __init__.py
│           └── settings.py     # Configuration management
├── tests/
│   ├── test_gc2_protocol.py
│   ├── test_gspro_client.py
│   └── test_models.py
└── tools/
    └── mock_gspro_server.py    # Testing utility
```

### Module Specifications

#### models.py - Data Models

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GC2ShotData(BaseModel):
    """Raw shot data from GC2"""
    shot_id: int
    timestamp: datetime
    
    # Ball data (always present)
    ball_speed: float          # mph
    launch_angle: float        # degrees (vertical)
    horizontal_angle: float    # degrees (horizontal)
    total_spin: float          # rpm
    back_spin: float           # rpm
    side_spin: float           # rpm
    
    # Club data (HMT only)
    club_speed: Optional[float] = None      # mph
    swing_path: Optional[float] = None      # degrees
    angle_of_attack: Optional[float] = None # degrees
    face_to_target: Optional[float] = None  # degrees
    lie: Optional[float] = None             # degrees
    dynamic_loft: Optional[float] = None    # degrees
    
    @property
    def has_hmt(self) -> bool:
        return self.club_speed is not None

class GSProShotMessage(BaseModel):
    """GSPro Open Connect API v1 message format"""
    DeviceID: str = "GC2 Connect"
    Units: str = "Yards"
    ShotNumber: int
    APIversion: str = "1"
    BallData: dict
    ClubData: Optional[dict] = None
    ShotDataOptions: dict
```

#### gc2/usb_reader.py - USB Communication

```python
import usb.core
import usb.util
from typing import Optional, Callable
import asyncio

class GC2USBReader:
    """Handles USB communication with the GC2"""
    
    VENDOR_ID = 0x2C79   # Foresight Sports
    PRODUCT_ID = 0x0110  # GC2
    
    def __init__(self):
        self.device: Optional[usb.core.Device] = None
        self.endpoint_in: Optional[usb.core.Endpoint] = None
        self._running = False
        self._callback: Optional[Callable] = None
    
    def find_device(self) -> Optional[usb.core.Device]:
        """Find GC2 USB device"""
        return usb.core.find(
            idVendor=self.VENDOR_ID,
            idProduct=self.PRODUCT_ID
        )
    
    async def connect(self) -> bool:
        """Connect to the GC2"""
        # Find device, claim interface, set up endpoints
        ...
    
    async def disconnect(self):
        """Disconnect from the GC2"""
        ...
    
    async def read_loop(self, callback: Callable[[str], None]):
        """Continuously read data from the GC2"""
        ...
```

#### gspro/client.py - GSPro Client

```python
import asyncio
import json
from typing import Optional

class GSProClient:
    """TCP client for GSPro Open Connect API v1"""
    
    DEFAULT_PORT = 921
    
    def __init__(self, host: str, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
    
    async def connect(self) -> bool:
        """Connect to GSPro"""
        self._reader, self._writer = await asyncio.open_connection(
            self.host, self.port
        )
        return True
    
    async def send_shot(self, shot: GSProShotMessage) -> bool:
        """Send shot data to GSPro"""
        message = shot.model_dump_json()
        self._writer.write(message.encode() + b'\n')
        await self._writer.drain()
        return True
    
    async def disconnect(self):
        """Disconnect from GSPro"""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
```

#### ui/app.py - NiceGUI Application

```python
from nicegui import ui, app
from gc2_connect.gc2 import GC2USBReader
from gc2_connect.gspro import GSProClient

class GC2ConnectApp:
    """Main application class"""
    
    def __init__(self):
        self.gc2_reader = GC2USBReader()
        self.gspro_client: Optional[GSProClient] = None
        self.shots: list[GC2ShotData] = []
        self.settings = Settings.load()
    
    def build_ui(self):
        """Build the NiceGUI interface"""
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            self._build_header()
            with ui.row().classes('w-full gap-4'):
                self._build_gc2_panel()
                self._build_gspro_panel()
            self._build_shot_display()
            self._build_shot_history()
```

---

## GC2 USB Protocol

### Device Identification
- **Vendor ID**: 0x2C79 (11385) - Foresight Sports
- **Product ID**: 0x0110 (272) - GC2

### Communication
- **Interface**: USB Bulk Transfer
- **Direction**: Device to Host (IN endpoint)
- **Format**: ASCII text, key=value pairs, newline-separated

### Data Format

```
SHOT_ID=1
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
HIMPACT_MM=2.5
VIMPACT_MM=-1.2
CLOSING_RATE_DEGSEC=500.0
HMT=1
```

### Field Definitions

| Field | Unit | Description | Range |
|-------|------|-------------|-------|
| SHOT_ID | - | Unique shot identifier | 1+ |
| SPEED_MPH | mph | Ball speed | 0-250 |
| ELEVATION_DEG | degrees | Vertical launch angle | -10 to 60 |
| AZIMUTH_DEG | degrees | Horizontal launch angle | -45 to 45 |
| SPIN_RPM | rpm | Total spin rate | 0-15000 |
| BACK_RPM | rpm | Backspin component | 0-15000 |
| SIDE_RPM | rpm | Sidespin component | -5000 to 5000 |
| CLUBSPEED_MPH | mph | Club head speed (HMT) | 0-150 |
| HPATH_DEG | degrees | Swing path (HMT) | -15 to 15 |
| VPATH_DEG | degrees | Angle of attack (HMT) | -10 to 10 |
| FACE_T_DEG | degrees | Face to target (HMT) | -15 to 15 |
| LIE_DEG | degrees | Lie angle (HMT) | -10 to 10 |
| LOFT_DEG | degrees | Dynamic loft (HMT) | 0-60 |
| HMT | boolean | HMT data present | 0 or 1 |

### Validation Rules

1. **Reject if**: `SPIN_RPM == 0` (misread)
2. **Reject if**: `BACK_RPM == 2222` (known error pattern)
3. **Reject if**: `SPEED_MPH < 10 || SPEED_MPH > 250`
4. **Ignore if**: `SHOT_ID` same as previous (duplicate)

---

## GSPro Open Connect API v1

### Connection
- **Protocol**: TCP
- **Default Port**: 921
- **Format**: JSON, newline-delimited

### Message Format

```json
{
  "DeviceID": "GC2 Connect",
  "Units": "Yards",
  "ShotNumber": 1,
  "APIversion": "1",
  "BallData": {
    "Speed": 150.5,
    "SpinAxis": 5.2,
    "TotalSpin": 2800.0,
    "BackSpin": 2650.0,
    "SideSpin": -400.0,
    "HLA": 2.1,
    "VLA": 12.3
  },
  "ClubData": {
    "Speed": 105.2,
    "AngleOfAttack": -4.2,
    "FaceToTarget": 1.5,
    "Lie": 0.5,
    "Loft": 15.2,
    "Path": 3.1,
    "SpeedAtImpact": 105.2,
    "VerticalFaceImpact": -1.2,
    "HorizontalFaceImpact": 2.5,
    "ClosureRate": 500.0
  },
  "ShotDataOptions": {
    "ContainsBallData": true,
    "ContainsClubData": true,
    "LaunchMonitorIsReady": true,
    "LaunchMonitorBallDetected": true,
    "IsHeartBeat": false
  }
}
```

### Unit Conversions

| From GC2 | To GSPro | Conversion |
|----------|----------|------------|
| mph (ball speed) | mph | Direct |
| degrees (angles) | degrees | Direct |
| rpm (spin) | rpm | Direct |
| mm (impact) | inches | ÷ 25.4 |

### Spin Axis Calculation

```python
import math

def calculate_spin_axis(back_spin: float, side_spin: float) -> float:
    """Calculate spin axis from back/side spin components"""
    if back_spin == 0:
        return 0.0
    return math.degrees(math.atan2(side_spin, back_spin))
```

---

## Error Handling

### USB Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Device not found | GC2 not connected | Prompt user to connect |
| Permission denied | Insufficient privileges | Guide user to fix permissions |
| Device busy | Another app using device | Prompt to close other app |
| Read timeout | No data available | Continue polling |
| Device disconnected | USB cable removed | Auto-reconnect |

### Network Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Connection refused | GSPro not running | Show error, allow retry |
| Connection timeout | Network issue | Retry with backoff |
| Connection lost | Network interruption | Auto-reconnect, queue shots |

### Recovery Strategy

```python
async def auto_reconnect(connect_func, max_retries=5):
    """Automatic reconnection with exponential backoff"""
    for attempt in range(max_retries):
        try:
            await connect_func()
            return True
        except Exception as e:
            wait_time = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
            await asyncio.sleep(wait_time)
    return False
```

---

## Configuration

### Settings File Location
- **macOS**: `~/Library/Application Support/GC2 Connect/settings.json`
- **Linux**: `~/.config/gc2-connect/settings.json`

### Settings Schema

```json
{
  "version": 1,
  "gspro": {
    "host": "192.168.1.100",
    "port": 921,
    "auto_connect": true
  },
  "gc2": {
    "auto_connect": true,
    "reject_zero_spin": true
  },
  "ui": {
    "theme": "dark",
    "show_history": true,
    "history_limit": 100
  }
}
```

---

## Testing Strategy

### Unit Tests
- Protocol parsing (GC2 → internal model)
- Data conversion (internal → GSPro format)
- Validation logic
- Configuration loading/saving

### Integration Tests
- Mock USB device communication
- Mock TCP server for GSPro
- End-to-end shot flow

### Manual Testing
- Real GC2 hardware
- Real GSPro connection
- Various shot types and conditions

### Test Utilities

```bash
# Mock GSPro server for testing
python -m gc2_connect.tools.mock_gspro_server --host 0.0.0.0 --port 921
```

---

## Deployment

### Packaging
- Use PyInstaller for standalone executables
- Single-file distribution for ease of use
- Code signing for macOS (avoid Gatekeeper issues)

### Build Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Build standalone app
pyinstaller --onefile --windowed src/gc2_connect/main.py

# macOS: Create .app bundle
pyinstaller --onefile --windowed --name "GC2 Connect" \
  --icon assets/icon.icns src/gc2_connect/main.py
```

### Distribution
- GitHub releases with pre-built binaries
- Installation documentation
- USB permission setup guides per platform

---

## Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Shot detection latency | < 50ms |
| GSPro transmission latency | < 100ms |
| Memory usage | < 100MB |
| CPU usage (idle) | < 1% |
| CPU usage (active) | < 5% |
| Startup time | < 3 seconds |

---

## Security Considerations

- No sensitive data stored
- Local network communication only
- No external API calls
- USB access requires user permission

---

## Future Considerations

### Potential Enhancements
- Support for other launch monitors (Mevo, Skytrak)
- Support for other simulators (E6, TGC)
- Cloud sync for shot data
- Advanced analytics
- Multi-language support

### Technical Debt
- Consider migrating to Rust for better USB handling
- Evaluate alternative UI frameworks
- Add comprehensive logging system
