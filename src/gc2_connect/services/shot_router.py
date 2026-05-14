# ABOUTME: Routes shot data to GSPro, Open Range, or Minigames based on current mode.
# ABOUTME: Handles mode switching and destination management.
"""Shot routing service for GC2 Connect.

This module provides:
- AppMode: Enum for application modes (GSPRO, OPEN_RANGE, MINIGAME)
- ShotRouter: Routes shots between GSPro, Open Range, and Minigames

The ShotRouter acts as a central dispatcher for shot data from the GC2
launch monitor, directing shots to the appropriate destination based
on the current application mode.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gc2_connect.gspro.client import GSProClient
    from gc2_connect.minigames.manager import GameManager
    from gc2_connect.minigames.models import GameResult
    from gc2_connect.models import GC2ShotData
    from gc2_connect.open_range.engine import OpenRangeEngine
    from gc2_connect.open_range.models import ShotResult

logger = logging.getLogger(__name__)


class AppMode(str, Enum):
    """Application mode enum.

    Determines where shot data is routed:
    - GSPRO: Shots are sent to GSPro golf simulator
    - OPEN_RANGE: Shots are simulated locally in Open Range
    - MINIGAME: Shots are processed by the active minigame
    """

    GSPRO = "gspro"
    OPEN_RANGE = "open_range"
    MINIGAME = "minigame"


class ShotRouter:
    """Routes shots between GSPro, Open Range, and Minigame modes.

    The router maintains the current application mode and directs
    shot data to the appropriate destination. It supports:
    - Mode switching between GSPro, Open Range, and Minigame
    - Callbacks for mode changes and shot results
    - Graceful handling of missing clients/engines

    Example:
        router = ShotRouter()
        router.set_gspro_client(gspro_client)
        router.set_open_range_engine(open_range_engine)
        router.set_game_manager(game_manager)
        router.on_mode_change(handle_mode_change)
        router.on_shot_result(handle_open_range_result)

        await router.route_shot(gc2_shot)
    """

    def __init__(self) -> None:
        """Initialize the shot router with GSPRO mode as default."""
        self._mode = AppMode.GSPRO
        self._gspro_client: GSProClient | None = None
        self._open_range_engine: OpenRangeEngine | None = None
        self._game_manager: GameManager | None = None
        self._mode_change_callback: Callable[[AppMode], Awaitable[None]] | None = None
        self._shot_result_callback: Callable[[ShotResult], Awaitable[None]] | None = None
        self._game_result_callback: Callable[[GameResult], Awaitable[None]] | None = None

    @property
    def mode(self) -> AppMode:
        """Get the current application mode."""
        return self._mode

    async def set_mode(self, mode: AppMode) -> None:
        """Switch between modes.

        When switching modes:
        - GSPro connection is NOT disconnected (stays open for quick switching)
        - Mode change callback is invoked if registered
        - No action is taken if already in the requested mode

        Args:
            mode: The target mode to switch to.
        """
        if mode == self._mode:
            return

        old_mode = self._mode
        self._mode = mode

        logger.info(f"Mode changed from {old_mode.value} to {mode.value}")

        if self._mode_change_callback:
            await self._mode_change_callback(mode)

    def set_gspro_client(self, client: GSProClient) -> None:
        """Set the GSPro client for routing shots.

        Args:
            client: The GSPro client instance.
        """
        self._gspro_client = client

    def set_open_range_engine(self, engine: OpenRangeEngine) -> None:
        """Set the Open Range engine for local simulation.

        Args:
            engine: The Open Range engine instance.
        """
        self._open_range_engine = engine

    def set_game_manager(self, manager: GameManager) -> None:
        """Set the game manager for minigame shot routing.

        Args:
            manager: The GameManager instance.
        """
        self._game_manager = manager

    def on_mode_change(self, callback: Callable[[AppMode], Awaitable[None]]) -> None:
        """Register a callback for mode changes.

        The callback is invoked when the mode changes, receiving
        the new mode as an argument.

        Args:
            callback: Async function to call on mode change.
        """
        self._mode_change_callback = callback

    def on_shot_result(self, callback: Callable[[ShotResult], Awaitable[None]]) -> None:
        """Register a callback for Open Range shot results.

        The callback is invoked after a shot is simulated in Open Range,
        receiving the ShotResult with trajectory and summary.

        Args:
            callback: Async function to call with shot results.
        """
        self._shot_result_callback = callback

    def on_game_result(self, callback: Callable[[GameResult], Awaitable[None]]) -> None:
        """Register a callback for minigame results.

        The callback is invoked after a shot is processed in a minigame,
        receiving the GameResult with points and outcome.

        Args:
            callback: Async function to call with game results.
        """
        self._game_result_callback = callback

    async def route_shot(self, shot: GC2ShotData) -> None:
        """Route a shot to the appropriate destination.

        In GSPRO mode, the shot is sent to the GSPro client.
        In OPEN_RANGE mode, the shot is simulated locally.
        In MINIGAME mode, the shot is processed by the active minigame.

        Args:
            shot: The GC2 shot data to route.

        Raises:
            RuntimeError: If the required client/engine is not configured.
        """
        if self._mode == AppMode.GSPRO:
            await self._route_to_gspro(shot)
        elif self._mode == AppMode.OPEN_RANGE:
            await self._route_to_open_range(shot)
        else:
            await self._route_to_minigame(shot)

    async def _route_to_gspro(self, shot: GC2ShotData) -> None:
        """Send shot to GSPro.

        Args:
            shot: The GC2 shot data to send.

        Raises:
            RuntimeError: If GSPro client is not configured.
        """
        if not self._gspro_client:
            raise RuntimeError("GSPro client not configured")

        logger.debug(f"Routing shot {shot.shot_id} to GSPro")
        await self._gspro_client.send_shot(shot)

    async def _route_to_open_range(self, shot: GC2ShotData) -> None:
        """Process shot in Open Range.

        Args:
            shot: The GC2 shot data to simulate.

        Raises:
            RuntimeError: If Open Range engine is not configured.
        """
        if not self._open_range_engine:
            raise RuntimeError("Open Range engine not configured")

        logger.debug(f"Routing shot {shot.shot_id} to Open Range")
        result = self._open_range_engine.simulate_shot(shot)

        if self._shot_result_callback:
            await self._shot_result_callback(result)

    async def _route_to_minigame(self, shot: GC2ShotData) -> None:
        """Process shot in active minigame.

        Args:
            shot: The GC2 shot data to process.

        Raises:
            RuntimeError: If game manager is not configured.
        """
        if not self._game_manager:
            raise RuntimeError("Game manager not configured")

        logger.debug(f"Routing shot {shot.shot_id} to Minigame")
        result = await self._game_manager.process_shot(shot)

        if result is not None and self._game_result_callback:
            await self._game_result_callback(result)
