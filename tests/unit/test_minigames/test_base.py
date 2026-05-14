# ABOUTME: Unit tests for BaseMinigame abstract class.
# ABOUTME: Tests game lifecycle, state transitions, and player management.
"""Unit tests for BaseMinigame abstract class."""

from __future__ import annotations

from gc2_connect.minigames.base import BaseMinigame
from gc2_connect.minigames.models import (
    GameConfig,
    GameResult,
    GameScore,
    GameState,
    GameType,
)
from gc2_connect.models import GC2ShotData


class MockMinigame(BaseMinigame):
    """Mock minigame implementation for testing."""

    def __init__(self, config: GameConfig) -> None:
        super().__init__(config)
        self._shots_received: list[GC2ShotData] = []

    def start_game(self) -> None:
        """Start the game."""
        self._state = GameState.PLAYING
        self._shots_received = []
        self._scores = [GameScore(player_name=name) for name in self.config.player_names]

    def process_shot(self, shot: GC2ShotData) -> GameResult:
        """Process a shot and return result."""
        self._shots_received.append(shot)

        # Simple scoring: 10 points per shot
        current_score = self._get_current_player_score()
        if current_score:
            current_score.shots_taken += 1
            current_score.score += 10

        # Check for max shots
        total_shots = sum(s.shots_taken for s in self._scores)
        game_over = self.config.max_shots is not None and total_shots >= self.config.max_shots

        if game_over:
            self._state = GameState.FINISHED

        return GameResult(
            points_earned=10,
            message=f"Shot processed for {self.current_player}",
            game_over=game_over,
        )

    def get_scores(self) -> list[GameScore]:
        """Get current scores."""
        return self._scores.copy()

    def _get_current_player_score(self) -> GameScore | None:
        """Get the score object for current player."""
        for score in self._scores:
            if score.player_name == self.current_player:
                return score
        return None


class TestBaseMinigameInitialization:
    """Tests for BaseMinigame initialization."""

    def test_initial_state_is_setup(self) -> None:
        """Test that initial state is SETUP."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)
        assert game.state == GameState.SETUP

    def test_config_stored(self) -> None:
        """Test that config is stored correctly."""
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            player_names=["Alice", "Bob"],
        )
        game = MockMinigame(config)
        assert game.config == config
        assert game.config.player_names == ["Alice", "Bob"]

    def test_current_player_initial(self) -> None:
        """Test that current player starts at first player."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["First", "Second", "Third"],
        )
        game = MockMinigame(config)
        assert game.current_player == "First"

    def test_current_player_index_initial(self) -> None:
        """Test that current player index starts at 0."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)
        assert game.current_player_index == 0


class TestBaseMinigameStateTransitions:
    """Tests for BaseMinigame state transitions."""

    def test_start_game_changes_state_to_playing(self) -> None:
        """Test that start_game changes state to PLAYING."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        assert game.state == GameState.SETUP
        game.start_game()
        assert game.state == GameState.PLAYING

    def test_pause_game_from_playing(self) -> None:
        """Test that pause_game changes state to PAUSED from PLAYING."""
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        game.start_game()
        assert game.state == GameState.PLAYING

        game.pause_game()
        assert game.state == GameState.PAUSED

    def test_pause_game_only_from_playing(self) -> None:
        """Test that pause_game only works from PLAYING state."""
        config = GameConfig(game_type=GameType.GOLF_DARTS)
        game = MockMinigame(config)

        # Try to pause from SETUP - should not change state
        game.pause_game()
        assert game.state == GameState.SETUP

    def test_resume_game_from_paused(self) -> None:
        """Test that resume_game changes state from PAUSED to PLAYING."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        game.start_game()
        game.pause_game()
        assert game.state == GameState.PAUSED

        game.resume_game()
        assert game.state == GameState.PLAYING

    def test_resume_game_only_from_paused(self) -> None:
        """Test that resume_game only works from PAUSED state."""
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        game.start_game()
        assert game.state == GameState.PLAYING

        # Try to resume from PLAYING - should not change state
        game.resume_game()
        assert game.state == GameState.PLAYING

    def test_end_game_changes_state_to_finished(self) -> None:
        """Test that end_game changes state to FINISHED."""
        config = GameConfig(game_type=GameType.GOLF_DARTS)
        game = MockMinigame(config)

        game.start_game()
        game.end_game()
        assert game.state == GameState.FINISHED

    def test_end_game_from_paused(self) -> None:
        """Test that end_game works from PAUSED state."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)

        game.start_game()
        game.pause_game()
        game.end_game()
        assert game.state == GameState.FINISHED

    def test_reset_game_returns_to_setup(self) -> None:
        """Test that reset_game returns state to SETUP."""
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)

        game.start_game()
        game.reset_game()
        assert game.state == GameState.SETUP

    def test_reset_game_clears_player_index(self) -> None:
        """Test that reset_game resets player index to 0."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["Alice", "Bob", "Charlie"],
        )
        game = MockMinigame(config)

        game.start_game()
        game.next_player()
        game.next_player()
        assert game.current_player == "Charlie"

        game.reset_game()
        assert game.current_player == "Alice"
        assert game.current_player_index == 0


class TestBaseMinigamePlayerManagement:
    """Tests for BaseMinigame player management."""

    def test_next_player_advances(self) -> None:
        """Test that next_player advances to next player."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["Alice", "Bob"],
        )
        game = MockMinigame(config)

        assert game.current_player == "Alice"
        result = game.next_player()
        assert result == "Bob"
        assert game.current_player == "Bob"

    def test_next_player_wraps_around(self) -> None:
        """Test that next_player wraps around to first player."""
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            player_names=["One", "Two", "Three"],
        )
        game = MockMinigame(config)

        assert game.current_player == "One"
        game.next_player()
        assert game.current_player == "Two"
        game.next_player()
        assert game.current_player == "Three"
        game.next_player()
        assert game.current_player == "One"  # Wrapped around

    def test_single_player_next_stays_same(self) -> None:
        """Test that next_player with single player stays the same."""
        config = GameConfig(
            game_type=GameType.PUTTING_GREEN,
            player_names=["Solo"],
        )
        game = MockMinigame(config)

        assert game.current_player == "Solo"
        game.next_player()
        assert game.current_player == "Solo"

    def test_player_count_property(self) -> None:
        """Test player_count property."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["A", "B", "C", "D"],
        )
        game = MockMinigame(config)
        assert game.player_count == 4


class TestBaseMinigameShotProcessing:
    """Tests for BaseMinigame shot processing."""

    def test_process_shot_returns_result(self) -> None:
        """Test that process_shot returns a GameResult."""
        config = GameConfig(game_type=GameType.TARGET_RANGE)
        game = MockMinigame(config)
        game.start_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=12.0,
            horizontal_launch_angle=1.0,
            back_spin=3000.0,
            side_spin=500.0,
        )
        result = game.process_shot(shot)

        assert isinstance(result, GameResult)
        assert result.points_earned == 10

    def test_process_shot_updates_score(self) -> None:
        """Test that process_shot updates player score."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)
        game.start_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=15.0,
            launch_angle=5.0,
            horizontal_launch_angle=0.0,
            back_spin=500.0,
            side_spin=0.0,
        )
        game.process_shot(shot)

        scores = game.get_scores()
        assert len(scores) == 1
        assert scores[0].shots_taken == 1
        assert scores[0].score == 10

    def test_process_shot_with_max_shots(self) -> None:
        """Test that game ends when max_shots reached."""
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            max_shots=3,
        )
        game = MockMinigame(config)
        game.start_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=10.0,
            horizontal_launch_angle=0.0,
            back_spin=2500.0,
            side_spin=0.0,
        )

        # First two shots - not game over
        result1 = game.process_shot(shot)
        assert not result1.game_over
        assert game.state == GameState.PLAYING

        result2 = game.process_shot(shot)
        assert not result2.game_over

        # Third shot - game over
        result3 = game.process_shot(shot)
        assert result3.game_over
        assert game.state == GameState.FINISHED


class TestBaseMinigameScoring:
    """Tests for BaseMinigame scoring."""

    def test_get_scores_returns_all_players(self) -> None:
        """Test that get_scores returns scores for all players."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["Alice", "Bob", "Charlie"],
        )
        game = MockMinigame(config)
        game.start_game()

        scores = game.get_scores()
        assert len(scores) == 3
        names = [s.player_name for s in scores]
        assert "Alice" in names
        assert "Bob" in names
        assert "Charlie" in names

    def test_get_scores_returns_copy(self) -> None:
        """Test that get_scores returns a copy, not original."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        game = MockMinigame(config)
        game.start_game()

        scores1 = game.get_scores()
        scores2 = game.get_scores()

        assert scores1 is not scores2

    def test_scores_track_per_player(self) -> None:
        """Test that scores are tracked per player."""
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            player_names=["Alice", "Bob"],
        )
        game = MockMinigame(config)
        game.start_game()

        shot = GC2ShotData(
            shot_id=1,
            ball_speed=100.0,
            launch_angle=10.0,
            horizontal_launch_angle=0.0,
            back_spin=2500.0,
            side_spin=0.0,
        )

        # Alice shoots twice
        game.process_shot(shot)
        game.process_shot(shot)
        game.next_player()

        # Bob shoots once
        game.process_shot(shot)

        scores = game.get_scores()
        alice_score = next(s for s in scores if s.player_name == "Alice")
        bob_score = next(s for s in scores if s.player_name == "Bob")

        assert alice_score.shots_taken == 2
        assert alice_score.score == 20
        assert bob_score.shots_taken == 1
        assert bob_score.score == 10
