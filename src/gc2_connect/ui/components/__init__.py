# ABOUTME: UI components package for GC2 Connect.
# ABOUTME: Contains reusable components like mode selector and Open Range view.
"""UI components for GC2 Connect.

This package contains:
- ModeSelector: Toggle between GSPro and Open Range modes
- OpenRangeView: 3D driving range visualization panel
"""

from gc2_connect.ui.components.mode_selector import ModeSelector
from gc2_connect.ui.components.open_range_view import OpenRangeView

__all__ = ["ModeSelector", "OpenRangeView"]
