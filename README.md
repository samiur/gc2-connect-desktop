# GC2 Connect Desktop

A cross-platform desktop application to read Foresight GC2 launch monitor data and send shots to GSPro.

## Features

- 📡 USB connection to GC2 launch monitor
- 🎯 Real-time shot data display
- 🌐 Remote connection to GSPro via Open Connect API v1
- 📊 Shot history tracking
- 🧪 Mock mode for testing without hardware

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

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .

# Or install dependencies directly
pip install nicegui pyusb pydantic pydantic-settings
```

## Usage

### Running the App

```bash
# Using the entry point
gc2-connect

# Or run directly
python -m gc2_connect.main

# Or
python src/gc2_connect/main.py
```

The app will start a web server at `http://localhost:8080` and open in your browser.

### USB Permissions (Linux)

On Linux, you may need to add a udev rule for USB access:

```bash
# Create udev rule
sudo tee /etc/udev/rules.d/99-gc2.rules << EOF
SUBSYSTEM=="usb", ATTR{idVendor}=="2c79", ATTR{idProduct}=="0110", MODE="0666"
EOF

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Connecting to GC2

1. Connect your GC2 via USB
2. Click "Connect" in the GC2 panel
3. The status should change to "Connected"

### Connecting to GSPro

1. Make sure GSPro is running with Open Connect API v1 enabled
2. Enter the IP address of your Windows PC running GSPro
3. Port should be 921 (default)
4. Click "Connect"

### Testing Without Hardware

1. Check "Use Mock GC2"
2. Click "Connect" 
3. Click "Send Test Shot" to simulate shots

## Configuration

Settings are stored in `~/.gc2-connect/config.json`:

```json
{
  "gspro": {
    "host": "192.168.1.100",
    "port": 921
  },
  "auto_send": true
}
```

## Project Structure

```
gc2-connect-desktop/
├── pyproject.toml
├── README.md
└── src/
    └── gc2_connect/
        ├── main.py           # Entry point
        ├── models.py         # Data models
        ├── ui/
        │   └── app.py        # NiceGUI application
        ├── gc2/
        │   └── usb_reader.py # GC2 USB communication
        └── gspro/
            └── client.py     # GSPro API client
```

## Troubleshooting

### GC2 Not Found

1. Make sure the GC2 is powered on and connected via USB
2. Check USB permissions (see above for Linux)
3. Try running with `sudo` (not recommended for regular use)
4. Verify VID/PID: `lsusb | grep -i foresight` or check System Information on macOS

### GSPro Connection Failed

1. Verify GSPro is running with Open Connect API enabled
2. Check firewall settings on the Windows PC
3. Ensure both devices are on the same network
4. Try pinging the Windows PC from your Mac/Linux machine

### No Shot Data

1. Make sure the GC2 is detecting balls
2. Check the GC2's LED status
3. Try hitting a few shots to verify the GC2 is working

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .
```

## License

MIT License
