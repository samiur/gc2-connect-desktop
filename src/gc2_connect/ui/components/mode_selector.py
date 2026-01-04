# ABOUTME: Mode selector component for switching between GSPro and Open Range.
# ABOUTME: Provides toggle UI and handles mode change callbacks.
"""Mode selector component for GC2 Connect.

This module provides the ModeSelector component that allows users to
switch between GSPro and Open Range modes. The selector can be built
into any NiceGUI context and invokes a callback when the mode changes.

Example:
    selector = ModeSelector(on_change=handle_mode_change)
    selector.build()  # Call within NiceGUI context
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from gc2_connect.services.shot_router import AppMode

if TYPE_CHECKING:
    pass


class ModeSelector:
    """Toggle between GSPro and Open Range modes.

    The selector displays two options and invokes a callback when the
    user changes the mode. The current mode can be queried or set
    programmatically.

    Attributes:
        current_mode: The currently selected AppMode.
        on_change: Async callback invoked when mode changes.
    """

    def __init__(
        self,
        on_change: Callable[[AppMode], Awaitable[None]],
        initial_mode: AppMode = AppMode.GSPRO,
    ) -> None:
        """Initialize the mode selector.

        Args:
            on_change: Async callback function to invoke when mode changes.
            initial_mode: The initial mode to display. Defaults to GSPRO.
        """
        self.on_change = on_change
        self._current_mode = initial_mode
        self._toggle: Any = None
        self._container: Any = None

    @property
    def current_mode(self) -> AppMode:
        """Get the currently selected mode."""
        return self._current_mode

    def set_mode(self, mode: AppMode) -> None:
        """Set the current mode programmatically.

        This updates the internal state but does NOT invoke the callback.
        Use this for external state synchronization.

        Args:
            mode: The mode to set.
        """
        self._current_mode = mode
        if self._toggle is not None:
            self._toggle.value = mode.value

    async def _on_mode_changed(self, mode: AppMode) -> None:
        """Handle mode change from UI or programmatic call.

        Updates internal state and invokes the callback.

        Args:
            mode: The new mode.
        """
        self._current_mode = mode
        if self.on_change is not None:
            await self.on_change(mode)

    def _on_toggle_change(self, e: Any) -> None:
        """Handle toggle UI change event.

        Args:
            e: The NiceGUI change event.
        """
        import asyncio

        new_mode = AppMode(e.value)
        # Run the async callback
        asyncio.create_task(self._on_mode_changed(new_mode))

    def build(self) -> Any:
        """Create the mode selector UI.

        Must be called within a NiceGUI context. Creates a toggle
        button group with GSPro and Open Range options.

        Returns:
            The container element, or None if not in NiceGUI context.
        """
        try:
            from nicegui import ui

            with ui.row().classes("gap-4 items-center") as container:
                self._container = container
                ui.label("Mode:").classes("text-lg font-semibold")

                # Create toggle with mode options
                options = {
                    AppMode.GSPRO.value: "GSPro",
                    AppMode.OPEN_RANGE.value: "Open Range",
                }
                self._toggle = ui.toggle(
                    options,
                    value=self._current_mode.value,
                    on_change=self._on_toggle_change,
                ).classes("bg-gray-700")

            return container

        except ImportError:
            # Not in NiceGUI context - return None for testing
            return None

    def hide(self) -> None:
        """Hide the mode selector."""
        if self._container is not None:
            self._container.classes(add="hidden")

    def show(self) -> None:
        """Show the mode selector."""
        if self._container is not None:
            self._container.classes(remove="hidden")
