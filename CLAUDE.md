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
- Interface: USB Bulk Transfer (IN endpoint)
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
# Install dependencies
pip install -e .

# Run the app
python -m gc2_connect.main

# Run tests
pytest

# Run mock GSPro server (for testing)
python tools/mock_gspro_server.py --host 0.0.0.0 --port 921
```

## Important Considerations

1. **USB Permissions**: Linux may require udev rules for non-root USB access
2. **Mock Mode**: Built-in mock GC2 for testing without hardware
3. **Shot Validation**: Zero spin shots are misreads - reject them
4. **Reconnection**: Both USB and network should auto-reconnect

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
