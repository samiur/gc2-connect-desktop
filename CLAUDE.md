# CLAUDE.md - GC2 Connect Desktop

## Project Overview

This is a Python desktop application for Mac and Linux that reads shot data from a Foresight GC2 golf launch monitor via USB and sends it to GSPro golf simulation software over the network.

## Quick Context

- **Language**: Python 3.10+
- **UI Framework**: NiceGUI (web-based, runs locally)
- **USB Library**: pyusb (requires libusb)
- **Target Platforms**: macOS, Linux (not Windows - FSX handles that)
- **Primary Use Case**: Allow Mac/Linux users to use their GC2 with GSPro

## Key Technical Details

### GC2 USB Communication
- VID: 0x2C79 (11385), PID: 0x0110 (272)
- Protocol: ASCII text, key=value pairs, newline-separated
- Interface: USB Interrupt Transfer (endpoint 0x82)
- Message types:
  - `0H`: Shot data (ball speed, spin, launch angles)
  - `0M`: Ball status (device readiness, ball detection)
- Message terminator: `\n\t` indicates complete message
- See `docs/GC2_PROTOCOL.md` for full specification

### GSPro Integration
- Protocol: TCP socket, JSON messages
- Default port: 921
- API: GSPro Open Connect API v1
- Messages are newline-delimited JSON

## Directory Structure

```
src/gc2_connect/
├── main.py              # Entry point
├── models.py            # Pydantic data models
├── gc2/
│   └── usb_reader.py    # USB communication
├── gspro/
│   └── client.py        # TCP client
├── ui/
│   └── app.py           # NiceGUI interface
└── config/              # Settings management

tools/
└── mock_gspro_server.py # Testing utility
```

## Development Commands

```bash
# Install dependencies (using uv)
uv sync

# Add a new package
uv add <package>

# Run the app
uv run python -m gc2_connect.main

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run mock GSPro server (for testing)
uv run python tools/mock_gspro_server.py --host 0.0.0.0 --port 921
```

## Package Management

- We use **uv** for Python package management (not pip or poetry)
- No requirements.txt needed - dependencies are in `pyproject.toml`
- Run any script with `uv run <script.py>`
- Add packages with `uv add <package>`

## Workflow

- If a `todo.md` exists, check off completed work
- **Tests must pass** before any task is considered done
- **Linting must pass** before any task is considered done

## Important Considerations

1. **USB Permissions**: Linux may require udev rules for non-root USB access
2. **Mock Mode**: Built-in mock GC2 for testing without hardware
3. **Shot Validation**: Zero spin (back_spin=0 AND side_spin=0) and 2222 backspin are misreads - reject them
4. **Reconnection**: Both USB and network should auto-reconnect
5. **Ball Status**: GC2 sends 0M messages with FLAGS (1=red light, 7=green light) and BALLS count for UI indicators

## Related Documentation

- `docs/PRD.md` - Product requirements
- `docs/TRD.md` - Technical requirements  
- `docs/GC2_PROTOCOL.md` - USB protocol specification
- `README.md` - User documentation

## Code Style

- Use type hints throughout
- Async/await for I/O operations
- Pydantic for data validation
- Follow PEP 8 conventions
