# ABOUTME: Minigames framework package for GC2 Connect.
# ABOUTME: Provides base classes and models for implementing golf minigames.
"""Minigames framework for GC2 Connect.

This package provides the foundation for implementing golf minigames:
- BaseMinigame: Abstract base class for all minigames
- GameManager: Manages game lifecycle and shot routing
- Models: GameType, GameState, GameConfig, GameScore, GameResult

Example:
    from gc2_connect.minigames import GameManager, GameType, GameConfig

    manager = GameManager()
    config = GameConfig(game_type=GameType.PUTTING_GREEN, player_names=["Player 1"])
    # Set up concrete minigame implementation and start
"""

from gc2_connect.minigames.base import BaseMinigame
from gc2_connect.minigames.manager import GameManager
from gc2_connect.minigames.models import (
    GameConfig,
    GameResult,
    GameScore,
    GameState,
    GameType,
)

__all__ = [
    "BaseMinigame",
    "GameConfig",
    "GameManager",
    "GameResult",
    "GameScore",
    "GameState",
    "GameType",
]
