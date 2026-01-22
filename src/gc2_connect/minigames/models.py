# ABOUTME: Data models for the minigames framework.
# ABOUTME: Defines GameType, GameState, GameConfig, GameScore, and GameResult.
"""Data models for the minigames framework.

This module provides:
- GameType: Enum of available minigame types
- GameState: Enum of game states (setup, playing, paused, finished)
- GameConfig: Configuration for starting a minigame
- GameScore: Player score tracking
- GameResult: Result of processing a shot
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class GameType(str, Enum):
    """Types of minigames available.

    Each minigame type has unique mechanics and scoring:
    - PUTTING_GREEN: Practice putting with stimpmeter physics
    - TARGET_RANGE: Hit targets at various distances for points
    - GOLF_DARTS: Map shot VLA/HLA to dartboard positions
    """

    PUTTING_GREEN = "putting_green"
    TARGET_RANGE = "target_range"
    GOLF_DARTS = "golf_darts"


class GameState(str, Enum):
    """Current state of a minigame.

    State transitions:
    - SETUP → PLAYING (start_game)
    - PLAYING → PAUSED (pause_game)
    - PAUSED → PLAYING (resume_game)
    - PLAYING/PAUSED → FINISHED (end_game or game_over)
    - Any → SETUP (reset_game)
    """

    SETUP = "setup"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


class GameConfig(BaseModel):
    """Configuration for starting a minigame.

    Provides common settings for all minigames including player setup
    and optional shot limits. Specific minigames may extend this with
    game-specific configuration.

    Example:
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["Alice", "Bob"],
            max_shots=21,  # 7 rounds of 3 darts
        )
    """

    game_type: Annotated[GameType, Field(description="Type of minigame to play")]
    player_names: Annotated[list[str], Field(description="Names of players in order of play")] = [
        "Player 1"
    ]
    max_shots: Annotated[
        int | None,
        Field(description="Maximum total shots before game ends (None = unlimited)"),
    ] = None


class GameScore(BaseModel):
    """Score tracking for a player in a minigame.

    Tracks basic metrics (shots and score) plus game-specific data
    in the extra_data field.

    Example:
        score = GameScore(
            player_name="Alice",
            shots_taken=9,
            score=180,
            extra_data={"triples": 3, "doubles": 2},
        )
    """

    player_name: Annotated[str, Field(description="Name of the player")]
    shots_taken: Annotated[int, Field(description="Number of shots taken")] = 0
    score: Annotated[int, Field(description="Current score (can be negative)")] = 0
    extra_data: Annotated[
        dict[str, Any], Field(default_factory=dict, description="Game-specific additional data")
    ]


class GameResult(BaseModel):
    """Result of processing a shot in a minigame.

    Returned by BaseMinigame.process_shot() to communicate the outcome
    of a shot back to the game manager and UI.

    Example:
        result = GameResult(
            points_earned=60,
            message="Triple 20!",
            game_over=False,
            extra_data={"ring": "triple", "number": 20},
        )
    """

    points_earned: Annotated[
        int, Field(description="Points earned (can be negative for busts)")
    ] = 0
    message: Annotated[str, Field(description="Human-readable result message")] = ""
    game_over: Annotated[bool, Field(description="Whether the game has ended")] = False
    extra_data: Annotated[
        dict[str, Any], Field(default_factory=dict, description="Game-specific additional data")
    ]
