# ABOUTME: Abstract base class for all minigames.
# ABOUTME: Defines the interface for game lifecycle, shot processing, and scoring.
"""Abstract base class for minigames.

This module provides:
- BaseMinigame: Abstract class that all minigames must inherit from

Concrete implementations must override:
- start_game(): Initialize game state and begin play
- process_shot(): Handle incoming shot data and return result
- get_scores(): Return current scores for all players
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from gc2_connect.minigames.models import GameConfig, GameResult, GameScore, GameState

if TYPE_CHECKING:
    from gc2_connect.models import GC2ShotData

logger = logging.getLogger(__name__)


class BaseMinigame(ABC):
    """Abstract base class for all minigames.

    Provides common functionality for game lifecycle management,
    player rotation, and state tracking. Concrete implementations
    must implement the abstract methods for game-specific logic.

    Example:
        class PuttingGreen(BaseMinigame):
            def start_game(self) -> None:
                self._state = GameState.PLAYING
                self._scores = [GameScore(player_name=n) for n in self.config.player_names]

            def process_shot(self, shot: GC2ShotData) -> GameResult:
                # Putting-specific logic
                ...

            def get_scores(self) -> list[GameScore]:
                return self._scores.copy()
    """

    def __init__(self, config: GameConfig) -> None:
        """Initialize the minigame.

        Args:
            config: Game configuration including type, players, and settings.
        """
        self.config = config
        self._state = GameState.SETUP
        self._scores: list[GameScore] = []
        self._current_player_index = 0

        logger.debug(
            f"Initialized {config.game_type.value} with {len(config.player_names)} player(s)"
        )

    @property
    def state(self) -> GameState:
        """Get the current game state."""
        return self._state

    @property
    def current_player(self) -> str:
        """Get the name of the current player."""
        return self.config.player_names[self._current_player_index]

    @property
    def current_player_index(self) -> int:
        """Get the index of the current player (0-based)."""
        return self._current_player_index

    @property
    def player_count(self) -> int:
        """Get the number of players in the game."""
        return len(self.config.player_names)

    @abstractmethod
    def start_game(self) -> None:
        """Start or restart the game.

        Implementations must:
        - Set _state to GameState.PLAYING
        - Initialize _scores for all players
        - Reset any game-specific state
        """

    @abstractmethod
    def process_shot(self, shot: GC2ShotData) -> GameResult:
        """Process incoming shot data and return the result.

        Implementations must:
        - Calculate score/result based on shot data
        - Update player scores
        - Check for game-over conditions
        - Return a GameResult with outcome

        Args:
            shot: The shot data from the GC2 launch monitor.

        Returns:
            GameResult containing points, message, and game_over flag.
        """

    @abstractmethod
    def get_scores(self) -> list[GameScore]:
        """Get current scores for all players.

        Returns:
            List of GameScore objects, one per player.
        """

    def pause_game(self) -> None:
        """Pause the game.

        Only transitions to PAUSED if currently PLAYING.
        """
        if self._state == GameState.PLAYING:
            self._state = GameState.PAUSED
            logger.debug(f"Game paused - {self.config.game_type.value}")

    def resume_game(self) -> None:
        """Resume a paused game.

        Only transitions to PLAYING if currently PAUSED.
        """
        if self._state == GameState.PAUSED:
            self._state = GameState.PLAYING
            logger.debug(f"Game resumed - {self.config.game_type.value}")

    def end_game(self) -> None:
        """End the game.

        Transitions to FINISHED regardless of current state.
        """
        self._state = GameState.FINISHED
        logger.debug(f"Game ended - {self.config.game_type.value}")

    def reset_game(self) -> None:
        """Reset the game to initial state.

        Returns to SETUP state and resets player index.
        Does not clear scores - call start_game() to reinitialize.
        """
        self._state = GameState.SETUP
        self._current_player_index = 0
        logger.debug(f"Game reset - {self.config.game_type.value}")

    def next_player(self) -> str:
        """Advance to the next player and return their name.

        Wraps around to the first player after the last.

        Returns:
            Name of the new current player.
        """
        self._current_player_index = (self._current_player_index + 1) % self.player_count
        logger.debug(f"Next player: {self.current_player}")
        return self.current_player
