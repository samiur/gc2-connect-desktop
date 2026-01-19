# ABOUTME: PyInstaller runtime hook to prevent multiple dock icons on macOS.
# ABOUTME: Sets all processes as accessory apps; pywebview will reset for its window.
"""
Runtime hook for macOS to prevent multiple dock icons.

When NiceGUI runs in native mode, it spawns multiple processes:
1. Main uvicorn server process
2. pywebview native window process (via multiprocessing)

On macOS, each process that imports AppKit gets its own dock icon by default.
This hook sets ALL processes to "accessory" mode (no dock icon) BEFORE any
other imports happen. When pywebview's cocoa platform is later imported in
the window process, it will reset to "regular" mode and show the dock icon.

This ensures only ONE dock icon appears - for the actual native window.
"""

import sys


def _hide_from_dock() -> None:
    """Set this process as an accessory app (no dock icon, no menu bar)."""
    try:
        # Import PyObjC modules
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        # Get the shared application instance
        app = NSApplication.sharedApplication()

        # Set activation policy to accessory (no dock icon, no menu bar)
        # pywebview's cocoa platform will reset this to "regular" when it loads
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except ImportError:
        # PyObjC not available, skip
        pass
    except Exception:
        # Any other error, skip silently
        pass


# Only run on macOS - set ALL processes to accessory mode
# The pywebview window process will be reset to regular by pywebview itself
if sys.platform == "darwin":
    _hide_from_dock()
