# ABOUTME: GameManager for managing minigame lifecycle and shot routing.
# ABOUTME: Acts as a façade between the application and active minigame instances.
"""GameManager for minigame lifecycle management.

This module provides:
- GameManager: Manages the active minigame instance and routes shots

The GameManager acts as a façade between the application (ShotRouter)
and concrete minigame implementations. It handles:
- Setting and clearing the active game
- Starting, pausing, resuming, and ending games
- Routing shots to the active game
- Providing access to scores and player state
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from gc2_connect.minigames.models import GameResult, GameScore, GameState, GameType

if TYPE_CHECKING:
    from gc2_connect.minigames.base import BaseMinigame
    from gc2_connect.models import GC2ShotData

logger = logging.getLogger(__name__)


class GameManager:
    """Manages minigame lifecycle and shot routing.

    The GameManager is the main integration point for minigames
    in the GC2 Connect application. It maintains a reference to
    the active minigame and provides methods for lifecycle management
    and shot processing.

    Example:
        manager = GameManager()
        manager.set_game(putting_green)
        manager.start_game()

        # Shot processing
        result = await manager.process_shot(shot_data)

        # Cleanup
        manager.end_game()
        manager.clear_game()
    """

    def __init__(self) -> None:
        """Initialize the GameManager with no active game."""
        self._active_game: BaseMinigame | None = None
        self._game_result_callback: Callable[[GameResult], Awaitable[None]] | None = None

        logger.debug("GameManager initialized")

    @property
    def active_game(self) -> BaseMinigame | None:
        """Get the currently active minigame, or None if none is set."""
        return self._active_game

    @property
    def has_active_game(self) -> bool:
        """Check if there is an active game in PLAYING state."""
        return self._active_game is not None and self._active_game.state == GameState.PLAYING

    @property
    def game_type(self) -> GameType | None:
        """Get the type of the active game, or None if no game is set."""
        if self._active_game is None:
            return None
        return self._active_game.config.game_type

    @property
    def current_player(self) -> str | None:
        """Get the current player name, or None if no game is set."""
        if self._active_game is None:
            return None
        return self._active_game.current_player

    def set_game(self, game: BaseMinigame) -> None:
        """Set the active minigame.

        If there is already an active game, it will be replaced.
        The new game starts in SETUP state until start_game() is called.

        Args:
            game: The minigame instance to activate.
        """
        self._active_game = game
        logger.info(f"Set active game: {game.config.game_type.value}")

    def clear_game(self) -> None:
        """Clear the active minigame.

        After calling this, there will be no active game and
        shot processing will return None.
        """
        if self._active_game:
            logger.info(f"Cleared active game: {self._active_game.config.game_type.value}")
        self._active_game = None

    def start_game(self) -> None:
        """Start the active game.

        Delegates to the active game's start_game() method.
        Does nothing if no game is set.
        """
        if self._active_game:
            self._active_game.start_game()
            logger.info(f"Started game: {self._active_game.config.game_type.value}")

    def pause_game(self) -> None:
        """Pause the active game.

        Delegates to the active game's pause_game() method.
        Does nothing if no game is set.
        """
        if self._active_game:
            self._active_game.pause_game()

    def resume_game(self) -> None:
        """Resume the active game.

        Delegates to the active game's resume_game() method.
        Does nothing if no game is set.
        """
        if self._active_game:
            self._active_game.resume_game()

    def end_game(self) -> None:
        """End the active game.

        Delegates to the active game's end_game() method.
        Does nothing if no game is set.
        """
        if self._active_game:
            self._active_game.end_game()
            logger.info(f"Ended game: {self._active_game.config.game_type.value}")

    def reset_game(self) -> None:
        """Reset the active game to SETUP state.

        Delegates to the active game's reset_game() method.
        Does nothing if no game is set.
        """
        if self._active_game:
            self._active_game.reset_game()
            logger.info(f"Reset game: {self._active_game.config.game_type.value}")

    async def process_shot(self, shot: GC2ShotData) -> GameResult | None:
        """Process a shot through the active minigame.

        Routes the shot to the active game if one is set and PLAYING.
        Invokes the game result callback if registered.

        Args:
            shot: The shot data from the GC2 launch monitor.

        Returns:
            GameResult from the minigame, or None if no active game
            or game is not in PLAYING state.
        """
        if self._active_game is None:
            logger.debug("No active game - shot ignored")
            return None

        if self._active_game.state != GameState.PLAYING:
            logger.debug(f"Game not playing (state={self._active_game.state.value}) - shot ignored")
            return None

        result = self._active_game.process_shot(shot)
        logger.debug(f"Shot processed: {result.points_earned} points, game_over={result.game_over}")

        if self._game_result_callback:
            await self._game_result_callback(result)

        return result

    def on_game_result(self, callback: Callable[[GameResult], Awaitable[None]]) -> None:
        """Register a callback for game results.

        The callback is invoked after each shot is processed,
        receiving the GameResult from the minigame.

        Args:
            callback: Async function to call with game results.
        """
        self._game_result_callback = callback
        logger.debug("Game result callback registered")

    def get_scores(self) -> list[GameScore] | None:
        """Get current scores from the active game.

        Returns:
            List of GameScore objects, or None if no active game.
        """
        if self._active_game is None:
            return None
        return self._active_game.get_scores()

    def next_player(self) -> str | None:
        """Advance to the next player in the active game.

        Returns:
            Name of the new current player, or None if no active game.
        """
        if self._active_game is None:
            return None
        return self._active_game.next_player()
