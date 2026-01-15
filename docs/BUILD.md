# Building GC2 Connect

This document describes how to build standalone executables for GC2 Connect on different platforms.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Platform-specific dependencies (see below)

## Quick Start

### macOS

```bash
# Install dependencies
uv sync --locked
uv add pyinstaller pillow

# Build the app
uv run pyinstaller gc2connect.spec --noconfirm

# Output: dist/GC2Connect.app
```

### Windows

```bash
# Install dependencies
uv sync --locked
uv add pyinstaller pillow pythonnet

# Generate Windows icon (if not present)
uv run python scripts/create_windows_icon.py

# Build the app
uv run pyinstaller gc2connect_windows.spec --noconfirm

# Output: dist/GC2Connect/GC2Connect.exe
```

## Platform-Specific Details

### macOS

The macOS build creates a `.app` bundle that can be:
- Dragged to Applications folder
- Distributed via DMG (disk image)

**Requirements:**
- Xcode Command Line Tools (for codesigning, optional)
- libusb: `brew install libusb`

**Build output:**
- `dist/GC2Connect.app` - The application bundle

**Creating a DMG for distribution:**
```bash
hdiutil create -volname "GC2Connect" -srcfolder dist/GC2Connect.app -ov -format UDZO dist/GC2Connect-macOS.dmg
```

### Windows

The Windows build creates a single standalone `.exe` file with all dependencies bundled.

**Requirements:**
- Visual C++ Redistributable (usually already installed)
- libusb-win32 or WinUSB driver for the GC2 device

**Build output:**
- `dist/GC2Connect.exe` - Single standalone executable

**Note:** The single-exe mode extracts files to a temporary directory at runtime. First launch may be slightly slower as files are extracted.

**Creating an installer (optional):**
You can use [NSIS](https://nsis.sourceforge.io/) or [Inno Setup](https://jrsoftware.org/isinfo.php) to create a proper Windows installer.

### Linux

Linux builds are not included in the automated workflow because:
1. Linux users typically prefer package managers or running from source
2. There are many distributions with different requirements
3. USB permissions require system configuration anyway

To build on Linux:
```bash
# Install system dependencies
sudo apt install libusb-1.0-0-dev  # Ubuntu/Debian
# or
sudo dnf install libusb-devel      # Fedora

# Install Python dependencies
uv sync --locked
uv add pyinstaller pillow

# Build (uses macOS spec as base, adjust hidden imports)
uv run pyinstaller gc2connect.spec --noconfirm
```

## CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/build.yml`) that automatically builds releases for macOS and Windows when a version tag is pushed.

### Triggering a Release

```bash
# Tag a release
git tag v1.2.0
git push origin v1.2.0
```

This will:
1. Build macOS `.app` and `.dmg`
2. Build Windows executable and `.zip`
3. Create a GitHub Release with the artifacts

### Manual Build

You can also trigger the build workflow manually from the GitHub Actions tab without creating a release.

## Troubleshooting

### macOS: "App is damaged and can't be opened"

This happens when the app isn't signed. To fix:
```bash
xattr -cr /path/to/GC2Connect.app
```

### Windows: Missing DLLs

If you get errors about missing DLLs:
1. Install [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
2. Ensure libusb DLL is in the same directory as the executable

### Windows: USB Device Not Found

You need to install a USB driver for the GC2:
1. Download [Zadig](https://zadig.akeo.ie/)
2. Connect the GC2
3. Select the GC2 device in Zadig
4. Install WinUSB driver

### Build Fails with "ModuleNotFoundError"

The PyInstaller spec files include hidden imports for common modules. If you get import errors:
1. Identify the missing module
2. Add it to the `hiddenimports` list in the spec file
3. Rebuild

## Development Builds

For development, you don't need to build - just run directly:

```bash
uv run python -m gc2_connect.main
```

## File Structure

```
gc2-connect-desktop/
├── gc2connect.spec           # macOS PyInstaller spec
├── gc2connect_windows.spec   # Windows PyInstaller spec
├── scripts/
│   └── create_windows_icon.py # Generate .ico from PNG
├── assets/
│   ├── icon.png              # Source icon
│   ├── GC2Connect.icns       # macOS icon
│   ├── GC2Connect.ico        # Windows icon
│   └── GC2Connect.iconset/   # macOS icon sizes
└── .github/workflows/
    └── build.yml             # CI/CD build workflow
```
