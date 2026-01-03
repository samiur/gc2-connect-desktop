# ABOUTME: Settings persistence module for GC2 Connect application.
# ABOUTME: Handles loading, saving, and platform-specific paths for user settings.
"""Settings persistence for GC2 Connect."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GSProSettings(BaseModel):
    """Settings for GSPro connection."""

    host: Annotated[str, Field(description="GSPro server host")] = "127.0.0.1"
    port: Annotated[int, Field(gt=0, description="GSPro server port")] = 921
    auto_connect: Annotated[bool, Field(description="Auto-connect to GSPro on startup")] = False


class GC2Settings(BaseModel):
    """Settings for GC2 launch monitor."""

    auto_connect: Annotated[bool, Field(description="Auto-connect to GC2 on startup")] = True
    reject_zero_spin: Annotated[
        bool, Field(description="Reject shots with zero spin as misreads")
    ] = True
    use_mock: Annotated[bool, Field(description="Use mock GC2 reader for testing")] = False


class UISettings(BaseModel):
    """Settings for user interface."""

    theme: Annotated[str, Field(description="UI theme (dark or light)")] = "dark"
    show_history: Annotated[bool, Field(description="Show shot history panel")] = True
    history_limit: Annotated[int, Field(gt=0, description="Maximum shots to keep in history")] = 50


class ConditionsSettings(BaseModel):
    """Environmental conditions for Open Range simulation."""

    temp_f: Annotated[float, Field(description="Temperature in Fahrenheit")] = 70.0
    elevation_ft: Annotated[float, Field(description="Elevation in feet")] = 0.0
    humidity_pct: Annotated[float, Field(description="Humidity percentage")] = 50.0
    wind_speed_mph: Annotated[float, Field(description="Wind speed in mph")] = 0.0
    wind_dir_deg: Annotated[
        float, Field(description="Wind direction in degrees (0=from north/headwind)")
    ] = 0.0


class OpenRangeSettings(BaseModel):
    """Settings for Open Range driving range simulator."""

    conditions: Annotated[ConditionsSettings, Field(description="Environmental conditions")] = (
        ConditionsSettings()
    )
    surface: Annotated[str, Field(description="Ground surface type")] = "Fairway"
    show_trajectory: Annotated[bool, Field(description="Show trajectory line")] = True
    camera_follow: Annotated[bool, Field(description="Camera follows ball")] = True


class Settings(BaseModel):
    """Application settings with persistence."""

    version: Annotated[int, Field(description="Settings schema version")] = 2
    mode: Annotated[str, Field(description="Current app mode (gspro or open_range)")] = "gspro"
    gspro: Annotated[GSProSettings, Field(description="GSPro settings")] = GSProSettings()
    gc2: Annotated[GC2Settings, Field(description="GC2 settings")] = GC2Settings()
    ui: Annotated[UISettings, Field(description="UI settings")] = UISettings()
    open_range: Annotated[OpenRangeSettings, Field(description="Open Range settings")] = (
        OpenRangeSettings()
    )

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        """Load settings from file, returning defaults if file doesn't exist.

        Handles migration from v1 to v2 automatically.

        Args:
            path: Optional custom path to load from. Uses platform default if None.

        Returns:
            Settings instance with loaded or default values.
        """
        settings_path = path or get_settings_path()

        if not settings_path.exists():
            logger.info(f"Settings file not found at {settings_path}, using defaults")
            return cls()

        try:
            data = json.loads(settings_path.read_text())
            data = cls._migrate(data)
            return cls(**data)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in settings file: {e}, using defaults")
            return cls()
        except Exception as e:
            logger.warning(f"Error loading settings: {e}, using defaults")
            return cls()

    @classmethod
    def _migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate settings from older versions to current version.

        Args:
            data: Raw settings data from file.

        Returns:
            Migrated settings data.
        """
        version = data.get("version", 1)

        if version < 2:
            logger.info(f"Migrating settings from v{version} to v2")
            # Add mode field (default to gspro for existing users)
            if "mode" not in data:
                data["mode"] = "gspro"
            # Add open_range settings with defaults
            if "open_range" not in data:
                data["open_range"] = OpenRangeSettings().model_dump()
            # Update version
            data["version"] = 2

        return data

    def save(self, path: Path | None = None) -> None:
        """Save settings to file.

        Args:
            path: Optional custom path to save to. Uses platform default if None.
        """
        settings_path = path or get_settings_path()

        # Create parent directories if needed
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            settings_path.write_text(json.dumps(self.to_dict(), indent=2))
            logger.info(f"Settings saved to {settings_path}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            raise

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary for JSON serialization.

        Returns:
            Dictionary representation of settings.
        """
        return {
            "version": self.version,
            "mode": self.mode,
            "gspro": self.gspro.model_dump(),
            "gc2": self.gc2.model_dump(),
            "ui": self.ui.model_dump(),
            "open_range": self.open_range.model_dump(),
        }


def get_settings_path() -> Path:
    """Get the platform-specific settings file path.

    Returns:
        Path to settings.json file.
        - macOS: ~/Library/Application Support/GC2 Connect/settings.json
        - Linux: ~/.config/gc2-connect/settings.json
    """
    home = Path.home()

    if sys.platform == "darwin":
        # macOS
        return home / "Library" / "Application Support" / "GC2 Connect" / "settings.json"
    else:
        # Linux and others
        return home / ".config" / "gc2-connect" / "settings.json"
