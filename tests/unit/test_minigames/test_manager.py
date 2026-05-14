# ABOUTME: Unit tests for GameManager class.
# ABOUTME: Tests game lifecycle management and shot routing to minigames.
"""Unit tests for GameManager class."""

from __future__ import annotations

import pytest

from gc2_connect.minigames.base import BaseMinigame
from gc2_connect.minigames.manager import GameManager
from gc2_connect.minigames.models import (
    GameConfig,
    GameResult,
    GameScore,
    GameState,
    GameType,
)
from gc2_connect.models import GC2ShotData


class MockMinigame(BaseMinigame):
    """Mock minigame for testing GameManager."""

    def __init__(self, config: GameConfig) -> None:
        super().__init__(config)
        self.shots_received: list[GC2ShotData] = []
        self._scores: list[GameScore] = []

    def start_game(self) -> None:
        """Start the game."""
        self._state = GameState.PLAYING
        self.shots_received = []
        self._scores = [GameScore(player_name=name) for name in self.config.player_names]

    def process_shot(self, shot: GC2ShotData) -> GameResult:
        """Process a shot."""
        self.shots_received.append(shot)
        return GameResult(
            points_earned=10,
            message="Test shot processed",
        )

    def get_scores(self) -> list[GameScore]:
        """Get scores."""
        return self._scores.copy()


class TestGameManagerInitialization:
    """Tests for GameManager initialization."""

    def test_initial_state(self) -> None:
        """Test GameManager initial state."""
        manager = GameManager()
        assert manager.active_game is None
        assert manager.has_active_game is False

    def test_game_type_none_initially(self) -> None:
        """Test that game_type is None when no game is set."""
        manager = GameManager()
        assert manager.game_type is None


class TestGameManagerGameLifecycle:
    """Tests for GameManager game lifecycle."""

    def test_set_game(self) -> None:
        """Test setting an active game."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        manager.set_game(game)
        assert manager.active_game is game
        assert manager.game_type == GameType.PUTTING_GREEN

    def test_start_game(self) -> None:
        """Test starting a game through manager."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()

        assert game.state == GameState.PLAYING
        assert manager.has_active_game is True

    def test_start_game_no_game_set(self) -> None:
        """Test that start_game does nothing when no game is set."""
        manager = GameManager()
        manager.start_game()  # Should not raise
        assert manager.has_active_game is False

    def test_pause_game(self) -> None:
        """Test pausing a game through manager."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.GOLF_DARTS)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()
        manager.pause_game()

        assert game.state == GameState.PAUSED
        assert manager.has_active_game is False  # Paused game not "active"

    def test_resume_game(self) -> None:
        """Test resuming a game through manager."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()
        manager.pause_game()
        manager.resume_game()

        assert game.state == GameState.PLAYING
        assert manager.has_active_game is True

    def test_end_game(self) -> None:
        """Test ending a game through manager."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()
        manager.end_game()

        assert game.state == GameState.FINISHED
        assert manager.has_active_game is False

    def test_reset_game(self) -> None:
        """Test resetting a game through manager."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.GOLF_DARTS)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()
        manager.reset_game()

        assert game.state == GameState.SETUP
        assert manager.has_active_game is False

    def test_clear_game(self) -> None:
        """Test clearing the active game."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.clear_game()

        assert manager.active_game is None
        assert manager.game_type is None


class TestGameManagerShotProcessing:
    """Tests for GameManager shot processing."""

    @pytest.mark.asyncio
    async def test_process_shot_routes_to_game(self) -> None:
        """Test that process_shot routes to active game."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=3000.0,
            side_spin=0.0,
        )
        result = await manager.process_shot(shot)

        assert result is not None
        assert result.points_earned == 10
        assert len(game.shots_received) == 1
        assert game.shots_received[0] == shot

    @pytest.mark.asyncio
    async def test_process_shot_no_game_returns_none(self) -> None:
        """Test that process_shot returns None when no game set."""
        manager = GameManager()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=3000.0,
            side_spin=0.0,
        )
        result = await manager.process_shot(shot)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_shot_game_not_playing_returns_none(self) -> None:
        """Test that process_shot returns None when game not playing."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.GOLF_DARTS)
        game = MockMinigame(config)

        manager.set_game(game)
        # Don't start the game

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=3000.0,
            side_spin=0.0,
        )
        result = await manager.process_shot(shot)

        assert result is None
        assert len(game.shots_received) == 0

    @pytest.mark.asyncio
    async def test_process_shot_game_paused_returns_none(self) -> None:
        """Test that process_shot returns None when game is paused."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()
        manager.pause_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=15.0,
            launch_angle=5.0,
            horizontal_launch_angle=0.0,
            back_spin=500.0,
            side_spin=0.0,
        )
        result = await manager.process_shot(shot)

        assert result is None


class TestGameManagerCallbacks:
    """Tests for GameManager callbacks."""

    @pytest.mark.asyncio
    async def test_game_result_callback_invoked(self) -> None:
        """Test that game result callback is invoked."""
        manager = GameManager()
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        received_results: list[GameResult] = []

        async def callback(result: GameResult) -> None:
            received_results.append(result)

        manager.on_game_result(callback)
        manager.set_game(game)
        manager.start_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=3000.0,
            side_spin=0.0,
        )
        await manager.process_shot(shot)

        assert len(received_results) == 1
        assert received_results[0].points_earned == 10

    @pytest.mark.asyncio
    async def test_callback_not_invoked_when_no_game(self) -> None:
        """Test that callback is not invoked when no active game."""
        manager = GameManager()

        received_results: list[GameResult] = []

        async def callback(result: GameResult) -> None:
            received_results.append(result)

        manager.on_game_result(callback)

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=12.0,
            horizontal_launch_angle=0.0,
            back_spin=3000.0,
            side_spin=0.0,
        )
        await manager.process_shot(shot)

        assert len(received_results) == 0


class TestGameManagerScoreAccess:
    """Tests for GameManager score access."""

    def test_get_scores_returns_game_scores(self) -> None:
        """Test that get_scores returns scores from active game."""
        manager = GameManager()
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["Alice", "Bob"],
        )
        game = MockMinigame(config)

        manager.set_game(game)
        manager.start_game()

        scores = manager.get_scores()
        assert scores is not None
        assert len(scores) == 2

    def test_get_scores_no_game_returns_none(self) -> None:
        """Test that get_scores returns None when no game set."""
        manager = GameManager()
        scores = manager.get_scores()
        assert scores is None

    def test_current_player_from_game(self) -> None:
        """Test that current_player returns from active game."""
        manager = GameManager()
        config = GameConfig(
            game_type=GameType.PUTTING_GREEN,
            player_names=["First", "Second"],
        )
        game = MockMinigame(config)

        manager.set_game(game)
        assert manager.current_player == "First"

    def test_current_player_no_game_returns_none(self) -> None:
        """Test that current_player returns None when no game set."""
        manager = GameManager()
        assert manager.current_player is None

    def test_next_player_from_game(self) -> None:
        """Test that next_player advances player in active game."""
        manager = GameManager()
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            player_names=["Alice", "Bob"],
        )
        game = MockMinigame(config)

        manager.set_game(game)
        assert manager.current_player == "Alice"

        result = manager.next_player()
        assert result == "Bob"
        assert manager.current_player == "Bob"

    def test_next_player_no_game_returns_none(self) -> None:
        """Test that next_player returns None when no game set."""
        manager = GameManager()
        result = manager.next_player()
        assert result is None
