# ABOUTME: Unit tests for minigame data models.
# ABOUTME: Tests GameType, GameState, GameConfig, GameScore, and GameResult.
"""Unit tests for minigame models."""

from __future__ import annotations

from gc2_connect.minigames.models import (
    GameConfig,
    GameResult,
    GameScore,
    GameState,
    GameType,
)


class TestGameType:
    """Tests for GameType enum."""

    def test_putting_green_value(self) -> None:
        """Test PUTTING_GREEN enum value."""
        assert GameType.PUTTING_GREEN == "putting_green"
        assert GameType.PUTTING_GREEN.value == "putting_green"

    def test_target_range_value(self) -> None:
        """Test TARGET_RANGE enum value."""
        assert GameType.TARGET_RANGE == "target_range"
        assert GameType.TARGET_RANGE.value == "target_range"

    def test_golf_darts_value(self) -> None:
        """Test GOLF_DARTS enum value."""
        assert GameType.GOLF_DARTS == "golf_darts"
        assert GameType.GOLF_DARTS.value == "golf_darts"

    def test_all_types_unique(self) -> None:
        """Test that all game types have unique values."""
        values = [t.value for t in GameType]
        assert len(values) == len(set(values))

    def test_string_comparison(self) -> None:
        """Test that GameType can be compared to strings."""
        assert GameType.PUTTING_GREEN == "putting_green"
        assert GameType.TARGET_RANGE == "target_range"
        assert GameType.GOLF_DARTS == "golf_darts"


class TestGameState:
    """Tests for GameState enum."""

    def test_setup_state(self) -> None:
        """Test SETUP state value."""
        assert GameState.SETUP == "setup"
        assert GameState.SETUP.value == "setup"

    def test_playing_state(self) -> None:
        """Test PLAYING state value."""
        assert GameState.PLAYING == "playing"
        assert GameState.PLAYING.value == "playing"

    def test_paused_state(self) -> None:
        """Test PAUSED state value."""
        assert GameState.PAUSED == "paused"
        assert GameState.PAUSED.value == "paused"

    def test_finished_state(self) -> None:
        """Test FINISHED state value."""
        assert GameState.FINISHED == "finished"
        assert GameState.FINISHED.value == "finished"

    def test_all_states_unique(self) -> None:
        """Test that all game states have unique values."""
        values = [s.value for s in GameState]
        assert len(values) == len(set(values))


class TestGameConfig:
    """Tests for GameConfig model."""

    def test_default_values(self) -> None:
        """Test GameConfig with default values."""
        config = GameConfig(game_type=GameType.PUTTING_GREEN)
        assert config.game_type == GameType.PUTTING_GREEN
        assert config.player_names == ["Player 1"]
        assert config.max_shots is None

    def test_custom_player_names(self) -> None:
        """Test GameConfig with custom player names."""
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            player_names=["Alice", "Bob", "Charlie"],
        )
        assert config.player_names == ["Alice", "Bob", "Charlie"]

    def test_max_shots(self) -> None:
        """Test GameConfig with max_shots set."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            max_shots=21,  # 7 rounds of 3 darts
        )
        assert config.max_shots == 21

    def test_single_player(self) -> None:
        """Test GameConfig with single player."""
        config = GameConfig(
            game_type=GameType.PUTTING_GREEN,
            player_names=["Solo Player"],
        )
        assert len(config.player_names) == 1
        assert config.player_names[0] == "Solo Player"

    def test_multi_player(self) -> None:
        """Test GameConfig with multiple players."""
        config = GameConfig(
            game_type=GameType.GOLF_DARTS,
            player_names=["Player 1", "Player 2", "Player 3", "Player 4"],
        )
        assert len(config.player_names) == 4

    def test_serialization(self) -> None:
        """Test that GameConfig can be serialized to dict."""
        config = GameConfig(
            game_type=GameType.TARGET_RANGE,
            player_names=["Test"],
            max_shots=10,
        )
        data = config.model_dump()
        assert data["game_type"] == "target_range"
        assert data["player_names"] == ["Test"]
        assert data["max_shots"] == 10

    def test_deserialization(self) -> None:
        """Test that GameConfig can be deserialized from dict."""
        data = {
            "game_type": "putting_green",
            "player_names": ["Alice", "Bob"],
            "max_shots": 20,
        }
        config = GameConfig.model_validate(data)
        assert config.game_type == GameType.PUTTING_GREEN
        assert config.player_names == ["Alice", "Bob"]
        assert config.max_shots == 20


class TestGameScore:
    """Tests for GameScore model."""

    def test_default_values(self) -> None:
        """Test GameScore with default values."""
        score = GameScore(player_name="Test Player")
        assert score.player_name == "Test Player"
        assert score.shots_taken == 0
        assert score.score == 0
        assert score.extra_data == {}

    def test_with_shots_and_score(self) -> None:
        """Test GameScore with shots and score set."""
        score = GameScore(
            player_name="Alice",
            shots_taken=5,
            score=150,
        )
        assert score.shots_taken == 5
        assert score.score == 150

    def test_extra_data(self) -> None:
        """Test GameScore with extra game-specific data."""
        score = GameScore(
            player_name="Bob",
            shots_taken=3,
            score=60,
            extra_data={
                "triples": 2,
                "doubles": 1,
                "bullseyes": 0,
            },
        )
        assert score.extra_data["triples"] == 2
        assert score.extra_data["doubles"] == 1
        assert score.extra_data["bullseyes"] == 0

    def test_negative_score_allowed(self) -> None:
        """Test that negative scores are allowed (for some games)."""
        score = GameScore(
            player_name="Charlie",
            score=-10,
        )
        assert score.score == -10

    def test_serialization(self) -> None:
        """Test that GameScore can be serialized."""
        score = GameScore(
            player_name="Test",
            shots_taken=10,
            score=100,
            extra_data={"level": 5},
        )
        data = score.model_dump()
        assert data["player_name"] == "Test"
        assert data["shots_taken"] == 10
        assert data["score"] == 100
        assert data["extra_data"]["level"] == 5


class TestGameResult:
    """Tests for GameResult model."""

    def test_default_values(self) -> None:
        """Test GameResult with default values."""
        result = GameResult()
        assert result.points_earned == 0
        assert result.message == ""
        assert result.game_over is False
        assert result.extra_data == {}

    def test_with_points_and_message(self) -> None:
        """Test GameResult with points and message."""
        result = GameResult(
            points_earned=20,
            message="Triple 20!",
        )
        assert result.points_earned == 20
        assert result.message == "Triple 20!"

    def test_game_over_flag(self) -> None:
        """Test GameResult with game_over flag."""
        result = GameResult(
            points_earned=50,
            message="BULLSEYE! Game Over!",
            game_over=True,
        )
        assert result.game_over is True

    def test_extra_data(self) -> None:
        """Test GameResult with extra data."""
        result = GameResult(
            points_earned=60,
            message="Triple 20!",
            extra_data={
                "ring": "triple",
                "number": 20,
                "multiplier": 3,
            },
        )
        assert result.extra_data["ring"] == "triple"
        assert result.extra_data["number"] == 20
        assert result.extra_data["multiplier"] == 3

    def test_negative_points(self) -> None:
        """Test GameResult with negative points (bust in 301/501)."""
        result = GameResult(
            points_earned=-50,
            message="BUST! Score reset.",
        )
        assert result.points_earned == -50

    def test_serialization(self) -> None:
        """Test that GameResult can be serialized."""
        result = GameResult(
            points_earned=25,
            message="Inner bull!",
            game_over=False,
            extra_data={"ring": "outer_bull"},
        )
        data = result.model_dump()
        assert data["points_earned"] == 25
        assert data["message"] == "Inner bull!"
        assert data["game_over"] is False
        assert data["extra_data"]["ring"] == "outer_bull"
