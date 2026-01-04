# GC2 Connect Desktop

A cross-platform desktop application to read Foresight GC2 launch monitor data and send shots to GSPro, with a built-in driving range simulator.

## Features

- **GSPro Mode**
  - USB connection to GC2 launch monitor
  - Real-time shot data display
  - Ball status indicators (ready/ball detected) synced with GC2 LEDs
  - Remote connection to GSPro via Open Connect API v1
  - Shot history tracking with CSV export

- **Open Range Mode** (New in v1.1.0)
  - Built-in 3D driving range simulator
  - Physics-accurate ball flight using Nathan model + WSU aerodynamics
  - Realistic bounce and roll behavior
  - Real-time shot data display (carry, total, offline, max height)
  - Phase indicators (Flight, Bounce, Rolling, Stopped)
  - Trajectory tracing with phase-colored path
  - No external software required

- **Common Features**
  - Mode switching without restart
  - Mock mode for testing without hardware
  - Persistent settings

## Requirements

- Python 3.10+
- macOS or Linux
- libusb (for USB communication)

### macOS

```bash
brew install libusb
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install libusb-1.0-0-dev
```

## Installation

```bash
# Clone or download the project
cd gc2-connect-desktop

# Install dependencies using uv
uv sync

# Or if you don't have uv, install it first:
# curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Usage

### Running the App

```bash
# Run the app
uv run python -m gc2_connect.main

# Or using the entry point (after install)
uv run gc2-connect
```

The app starts a web server at `http://localhost:8080` and opens in your browser.

### USB Permissions (Linux)

On Linux, you need to add a udev rule for USB access. See [docs/LINUX_USB_SETUP.md](docs/LINUX_USB_SETUP.md) for detailed instructions.

Quick setup:

```bash
# Create udev rule
sudo tee /etc/udev/rules.d/99-gc2.rules << EOF
SUBSYSTEM=="usb", ATTR{idVendor}=="2c79", ATTR{idProduct}=="0110", MODE="0666"
EOF

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Mode Selection

GC2 Connect supports two modes:

1. **GSPro Mode**: Connect to GSPro on a Windows PC for full course simulation
2. **Open Range Mode**: Use the built-in driving range simulator

Switch modes using the toggle at the top of the application. Your preference is saved between sessions.

### GSPro Mode

1. Make sure GSPro is running with **Open Connect API v1** enabled
2. Enter the IP address of your Windows PC running GSPro
3. Port should be 921 (default)
4. Click "Connect"
5. Shots from your GC2 will appear in GSPro

### Open Range Mode

1. Select "Open Range" from the mode selector
2. Connect your GC2 (or use Mock mode for testing)
3. Hit shots and watch them fly!
4. View shot data including:
   - Carry distance
   - Total distance (carry + roll)
   - Offline distance (left/right)
   - Max height
   - Flight time

The trajectory line shows:
- **Green**: Ball in flight
- **Orange**: Ball bouncing
- **Blue**: Ball rolling

### Testing Without Hardware

1. Check "Use Mock GC2"
2. Click "Connect"
3. Click "Send Test Shot" to simulate shots

## Configuration

Settings are stored in platform-specific locations:
- **macOS**: `~/Library/Application Support/GC2 Connect/settings.json`
- **Linux**: `~/.config/gc2-connect/settings.json`

### Settings Schema (v2)

```json
{
  "version": 2,
  "mode": "gspro",
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
  },
  "open_range": {
    "conditions": {
      "temp_f": 70.0,
      "elevation_ft": 0.0,
      "humidity_pct": 50.0,
      "wind_speed_mph": 0.0,
      "wind_dir_deg": 0.0
    },
    "surface": "Fairway",
    "show_trajectory": true,
    "camera_follow": true
  }
}
```

## Project Structure

```
gc2-connect-desktop/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── docs/
│   ├── PRD.md                # Product requirements
│   ├── PRD_OPEN_RANGE.md     # Open Range requirements
│   ├── TRD.md                # Technical requirements
│   ├── TRD_OPEN_RANGE.md     # Open Range technical design
│   ├── GC2_PROTOCOL.md       # GC2 USB protocol specification
│   ├── GSPRO_CONNECT.md      # GSPro API implementation guide
│   ├── PHYSICS.md            # Golf ball physics specification
│   ├── LINUX_USB_SETUP.md    # Linux USB permissions guide
│   └── MACOS_USB_SETUP.md    # macOS USB notes
└── src/
    └── gc2_connect/
        ├── main.py           # Entry point
        ├── models.py         # Data models
        ├── ui/
        │   ├── app.py        # NiceGUI application
        │   └── components/   # UI components
        ├── gc2/
        │   └── usb_reader.py # GC2 USB communication
        ├── gspro/
        │   └── client.py     # GSPro API client
        ├── open_range/       # Open Range feature
        │   ├── models.py     # Trajectory/shot models
        │   ├── engine.py     # High-level engine
        │   ├── physics/      # Physics simulation
        │   └── visualization/# 3D rendering
        ├── services/
        │   ├── shot_router.py # Mode-based shot routing
        │   ├── history.py    # Shot history manager
        │   └── export.py     # CSV export
        └── config/
            └── settings.py   # Settings management
```

## Troubleshooting

### GC2 Not Found

1. Make sure the GC2 is powered on and connected via USB
2. Check USB permissions (see [docs/LINUX_USB_SETUP.md](docs/LINUX_USB_SETUP.md) for Linux)
3. Try running with `sudo` (not recommended for regular use)
4. Verify VID/PID: `lsusb | grep -i foresight` or check System Information on macOS

### GSPro Connection Failed

1. Verify GSPro is running with **Open Connect API v1** enabled (not v2)
2. Check that GSPro shows "Waiting for LM to connect" status
3. Check firewall settings on the Windows PC (port 921 must be open)
4. Ensure both devices are on the same network
5. Try pinging the Windows PC from your Mac/Linux machine

### No Shot Data

1. Make sure the GC2 is detecting balls
2. Check the GC2's LED status (green = ready)
3. Try hitting a few shots to verify the GC2 is working

### Open Range Issues

1. **Ball not animating**: Ensure the 3D scene has loaded (wait 2 seconds after switching modes)
2. **Unrealistic distances**: Verify the physics settings match expected conditions
3. **Performance issues**: Close other browser tabs; the app uses WebGL for 3D rendering

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

```bash
# Install dependencies (includes dev deps)
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=gc2_connect --cov-report=html

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Run all CI checks
uv run pytest && uv run mypy src/ && uv run ruff check . && uv run ruff format --check .
```

### Test Simulators

The project includes a comprehensive test simulator infrastructure for testing without hardware:

- **GC2 USB Simulator** (`tests/simulators/gc2/`): Generates realistic USB packets matching the real GC2 device behavior, including two-phase transmission (preliminary + refined data), field splitting across packets, and status message interruptions.

- **Mock GSPro Server** (`tests/simulators/gspro/`): Configurable TCP server that simulates GSPro responses with support for delays, errors, and shot tracking.

- **Time Controller** (`tests/simulators/timing.py`): Allows tests to run in INSTANT mode (fast, deterministic) or REAL mode (actual timing).

See `CLAUDE.md` for detailed usage examples.

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
- [docs/PRD.md](docs/PRD.md) - Product requirements
- [docs/PRD_OPEN_RANGE.md](docs/PRD_OPEN_RANGE.md) - Open Range feature requirements
- [docs/TRD.md](docs/TRD.md) - Technical requirements
- [docs/TRD_OPEN_RANGE.md](docs/TRD_OPEN_RANGE.md) - Open Range technical design
- [docs/GC2_PROTOCOL.md](docs/GC2_PROTOCOL.md) - GC2 USB protocol specification
- [docs/GSPRO_CONNECT.md](docs/GSPRO_CONNECT.md) - GSPro Open Connect API guide
- [docs/PHYSICS.md](docs/PHYSICS.md) - Golf ball physics model
- [docs/LINUX_USB_SETUP.md](docs/LINUX_USB_SETUP.md) - Linux USB permissions
- [docs/MACOS_USB_SETUP.md](docs/MACOS_USB_SETUP.md) - macOS USB notes

## License

MIT License
