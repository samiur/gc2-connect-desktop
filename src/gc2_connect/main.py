# ABOUTME: Main entry point for the GC2 Connect Desktop application.
# ABOUTME: Launches the NiceGUI web interface for GC2-to-GSPro integration.
"""GC2 Connect - Main entry point."""

import multiprocessing

# Required for PyInstaller on macOS/Windows to prevent infinite process spawning
multiprocessing.freeze_support()

from gc2_connect.ui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
