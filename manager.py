"""
Hockey Scoreboard Plugin for LEDMatrix - Using Existing Managers

This plugin provides NHL, NCAA Men's, and NCAA Women's hockey scoreboard functionality by reusing
the proven, working manager classes from the LEDMatrix core project.
"""

import logging
import time
from typing import Dict, Any

try:
    from src.plugin_system.base_plugin import BasePlugin
except ImportError:
    BasePlugin = None

# Import local background service
try:
    from background_data_service import get_background_service
except ImportError:
    get_background_service = None

# Import the copied manager classes
from nhl_managers import NHLLiveManager, NHLRecentManager, NHLUpcomingManager
from ncaam_hockey_managers import (
    NCAAMHockeyLiveManager,
    NCAAMHockeyRecentManager,
    NCAAMHockeyUpcomingManager,
)
from ncaaw_hockey_managers import (
    NCAAWHockeyLiveManager,
    NCAAWHockeyRecentManager,
    NCAAWHockeyUpcomingManager,
)

logger = logging.getLogger(__name__)


class HockeyScoreboardPlugin(BasePlugin if BasePlugin else object):
    """
    Hockey scoreboard plugin using existing manager classes.

    This plugin provides NHL, NCAA Men's, and NCAA Women's hockey scoreboard functionality by
    delegating to the proven manager classes from LEDMatrix core.
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict[str, Any],
        display_manager,
        cache_manager,
        plugin_manager,
    ):
        """Initialize the hockey scoreboard plugin."""
        if BasePlugin:
            super().__init__(
                plugin_id, config, display_manager, cache_manager, plugin_manager
            )

        self.plugin_id = plugin_id
        self.config = config
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.plugin_manager = plugin_manager

        self.logger = logger

        # Basic configuration
        self.is_enabled = config.get("enabled", True)
        self.display_width = getattr(display_manager, "display_width", 128)
        self.display_height = getattr(display_manager, "display_height", 32)

        # League configurations
        self.nhl_enabled = config.get("nhl", {}).get("enabled", False)
        self.ncaa_mens_enabled = config.get("ncaa_mens", {}).get("enabled", False)
        self.ncaa_womens_enabled = config.get("ncaa_womens", {}).get("enabled", False)

        # Global settings
        self.display_duration = float(config.get("display_duration", 30))
        self.game_display_duration = float(config.get("game_display_duration", 15))

        # Additional settings
        self.show_records = config.get("show_records", False)
        self.show_ranking = config.get("show_ranking", False)
        self.show_odds = config.get("show_odds", False)

        # Initialize background service if available
        self.background_service = None
        if get_background_service:
            try:
                self.background_service = get_background_service(
                    self.cache_manager, max_workers=1
                )
            except Exception as e:
                self.logger.warning(f"Could not initialize background service: {e}")

        # Mode cycling (like football plugin)
        self.current_mode_index = 0
        self.last_mode_switch = 0
        self.modes = self._get_available_modes()

        # Initialize managers
        self._initialize_managers()

        self.logger.info(
            f"Hockey scoreboard plugin initialized - {self.display_width}x{self.display_height}"
        )
        self.logger.info(
            f"NHL enabled: {self.nhl_enabled}, NCAA Men's enabled: {self.ncaa_mens_enabled}, NCAA Women's enabled: {self.ncaa_womens_enabled}"
        )

    def _initialize_managers(self):
        """Initialize all manager instances."""
        try:
            # Create adapted configs for managers
            nhl_config = self._adapt_config_for_manager("nhl")
            ncaa_mens_config = self._adapt_config_for_manager("ncaa_mens")
            ncaa_womens_config = self._adapt_config_for_manager("ncaa_womens")

            # Initialize NHL managers if enabled
            if self.nhl_enabled:
                self.nhl_live = NHLLiveManager(
                    nhl_config, self.display_manager, self.cache_manager
                )
                self.nhl_recent = NHLRecentManager(
                    nhl_config, self.display_manager, self.cache_manager
                )
                self.nhl_upcoming = NHLUpcomingManager(
                    nhl_config, self.display_manager, self.cache_manager
                )
                self.logger.info("NHL managers initialized")

            # Initialize NCAA Men's managers if enabled
            if self.ncaa_mens_enabled:
                self.ncaa_mens_live = NCAAMHockeyLiveManager(
                    ncaa_mens_config, self.display_manager, self.cache_manager
                )
                self.ncaa_mens_recent = NCAAMHockeyRecentManager(
                    ncaa_mens_config, self.display_manager, self.cache_manager
                )
                self.ncaa_mens_upcoming = NCAAMHockeyUpcomingManager(
                    ncaa_mens_config, self.display_manager, self.cache_manager
                )
                self.logger.info("NCAA Men's Hockey managers initialized")

            # Initialize NCAA Women's managers if enabled
            if self.ncaa_womens_enabled:
                self.ncaa_womens_live = NCAAWHockeyLiveManager(
                    ncaa_womens_config, self.display_manager, self.cache_manager
                )
                self.ncaa_womens_recent = NCAAWHockeyRecentManager(
                    ncaa_womens_config, self.display_manager, self.cache_manager
                )
                self.ncaa_womens_upcoming = NCAAWHockeyUpcomingManager(
                    ncaa_womens_config, self.display_manager, self.cache_manager
                )
                self.logger.info("NCAA Women's Hockey managers initialized")

        except Exception as e:
            self.logger.error(f"Error initializing managers: {e}", exc_info=True)

    def _get_default_logo_dir(self, league: str) -> str:
        """
        Get the default logo directory for a league.
        Matches the directories used in src/logo_downloader.py.
        """
        # Map leagues to their logo directories (matching logo_downloader.py)
        logo_dir_map = {
            'nhl': 'assets/sports/nhl_logos',
            'ncaa_mens': 'assets/sports/ncaa_logos',  # NCAA Men's Hockey uses ncaa_logos
            'ncaa_womens': 'assets/sports/ncaa_logos',  # NCAA Women's Hockey uses ncaa_logos
        }
        # Default to league-specific directory if not in map
        return logo_dir_map.get(league, f"assets/sports/{league}_logos")

    def _adapt_config_for_manager(self, league: str) -> Dict[str, Any]:
        """
        Adapt plugin config format to manager expected format.

        Plugin uses: nhl: {...}, ncaa_mens: {...}, ncaa_womens: {...}
        Managers expect: nhl_scoreboard: {...}, ncaa_mens_hockey_scoreboard: {...}, etc.
        """
        league_config = self.config.get(league, {})

        # Map league names to sport_key format expected by managers
        sport_key_map = {
            "nhl": "nhl",
            "ncaa_mens": "ncaam_hockey",
            "ncaa_womens": "ncaaw_hockey",
        }
        sport_key = sport_key_map.get(league, league)

        # Extract nested configurations
        display_modes = league_config.get("display_modes", {})

        # Create manager config with expected structure
        manager_config = {
            f"{sport_key}_scoreboard": {
                "enabled": league_config.get("enabled", False),
                "favorite_teams": league_config.get("favorite_teams", []),
                "display_modes": {
                    "hockey_live": display_modes.get("live", True),
                    "hockey_recent": display_modes.get("recent", True),
                    "hockey_upcoming": display_modes.get("upcoming", True),
                },
                "recent_games_to_show": league_config.get("recent_games_to_show", 5),
                "upcoming_games_to_show": league_config.get("upcoming_games_to_show", 10),
                "logo_dir": league_config.get(
                    "logo_dir", self._get_default_logo_dir(league)
                ),
                "show_records": league_config.get("show_records", self.show_records),
                "show_ranking": league_config.get("show_ranking", self.show_ranking),
                "show_odds": league_config.get("show_odds", self.show_odds),
                "show_shots_on_goal": league_config.get("show_shots_on_goal", False),
                "show_favorite_teams_only": league_config.get("favorite_teams_only", False),
                "show_all_live": league_config.get("show_all_live", True),
                "test_mode": league_config.get("test_mode", False),
                "update_interval_seconds": league_config.get(
                    "update_interval_seconds", 60
                ),
                "live_update_interval": league_config.get("live_update_interval", 15),
                "live_game_duration": league_config.get("live_game_duration", 20),
                "background_service": {
                    "request_timeout": 30,
                    "max_retries": 3,
                    "priority": 2,
                },
            }
        }

        # Add global config
        manager_config.update(
            {
                "timezone": self.config.get("timezone", "UTC"),
                "display": self.config.get("display", {}),
            }
        )

        return manager_config

    def _get_available_modes(self) -> list:
        """Get list of available display modes based on enabled leagues (like football plugin)."""
        modes = []

        if self.nhl_enabled:
            modes.extend(["nhl_live", "nhl_recent", "nhl_upcoming"])

        if self.ncaa_mens_enabled:
            modes.extend(["ncaa_mens_live", "ncaa_mens_recent", "ncaa_mens_upcoming"])

        if self.ncaa_womens_enabled:
            modes.extend(["ncaa_womens_live", "ncaa_womens_recent", "ncaa_womens_upcoming"])

        # Default to NHL if no leagues enabled
        if not modes:
            modes = ["nhl_live", "nhl_recent", "nhl_upcoming"]

        return modes

    def _get_current_manager(self):
        """Get the current manager based on the current mode (like football plugin)."""
        if not self.modes:
            return None

        current_mode = self.modes[self.current_mode_index]

        if current_mode.startswith("nhl_"):
            if not self.nhl_enabled:
                return None
            mode_type = current_mode.split("_", 1)[1]  # "live", "recent", "upcoming"
            if mode_type == "live":
                return self.nhl_live
            elif mode_type == "recent":
                return self.nhl_recent
            elif mode_type == "upcoming":
                return self.nhl_upcoming

        elif current_mode.startswith("ncaa_mens_"):
            if not self.ncaa_mens_enabled:
                return None
            mode_type = current_mode.split("_", 2)[2]  # "live", "recent", "upcoming"
            if mode_type == "live":
                return self.ncaa_mens_live
            elif mode_type == "recent":
                return self.ncaa_mens_recent
            elif mode_type == "upcoming":
                return self.ncaa_mens_upcoming

        elif current_mode.startswith("ncaa_womens_"):
            if not self.ncaa_womens_enabled:
                return None
            mode_type = current_mode.split("_", 2)[2]  # "live", "recent", "upcoming"
            if mode_type == "live":
                return self.ncaa_womens_live
            elif mode_type == "recent":
                return self.ncaa_womens_recent
            elif mode_type == "upcoming":
                return self.ncaa_womens_upcoming

        return None

    def update(self) -> None:
        """Update hockey game data."""
        if not self.is_enabled:
            return

        try:
            # Update NHL managers if enabled
            if self.nhl_enabled:
                if hasattr(self, "nhl_live"):
                    self.nhl_live.update()
                if hasattr(self, "nhl_recent"):
                    self.nhl_recent.update()
                if hasattr(self, "nhl_upcoming"):
                    self.nhl_upcoming.update()

            # Update NCAA Men's managers if enabled
            if self.ncaa_mens_enabled:
                if hasattr(self, "ncaa_mens_live"):
                    self.ncaa_mens_live.update()
                if hasattr(self, "ncaa_mens_recent"):
                    self.ncaa_mens_recent.update()
                if hasattr(self, "ncaa_mens_upcoming"):
                    self.ncaa_mens_upcoming.update()

            # Update NCAA Women's managers if enabled
            if self.ncaa_womens_enabled:
                if hasattr(self, "ncaa_womens_live"):
                    self.ncaa_womens_live.update()
                if hasattr(self, "ncaa_womens_recent"):
                    self.ncaa_womens_recent.update()
                if hasattr(self, "ncaa_womens_upcoming"):
                    self.ncaa_womens_upcoming.update()

        except Exception as e:
            self.logger.error(f"Error updating managers: {e}", exc_info=True)

    def display(self, force_clear: bool = False) -> None:
        """Display hockey games with mode cycling (like football plugin)."""
        if not self.is_enabled:
            return

        try:
            current_time = time.time()

            # Handle mode cycling
            if current_time - self.last_mode_switch >= self.display_duration:
                self.current_mode_index = (self.current_mode_index + 1) % len(
                    self.modes
                )
                self.last_mode_switch = current_time
                force_clear = True

                current_mode = self.modes[self.current_mode_index]
                self.logger.info(f"Switching to display mode: {current_mode}")

            # Get current manager and display
            current_manager = self._get_current_manager()
            if current_manager:
                current_manager.display(force_clear)
            else:
                self.logger.warning("No manager available for current mode")

        except Exception as e:
            self.logger.error(f"Error in display method: {e}", exc_info=True)

    def _get_manager_for_mode(self, mode_type: str):
        """Get the manager for a specific mode type (live, recent, upcoming)."""
        # Priority: NHL > NCAA Men's > NCAA Women's
        # Try NHL first
        if self.nhl_enabled:
            if mode_type == "live" and hasattr(self, "nhl_live"):
                return self.nhl_live
            elif mode_type == "recent" and hasattr(self, "nhl_recent"):
                return self.nhl_recent
            elif mode_type == "upcoming" and hasattr(self, "nhl_upcoming"):
                return self.nhl_upcoming

        # Try NCAA Men's
        if self.ncaa_mens_enabled:
            if mode_type == "live" and hasattr(self, "ncaa_mens_live"):
                return self.ncaa_mens_live
            elif mode_type == "recent" and hasattr(self, "ncaa_mens_recent"):
                return self.ncaa_mens_recent
            elif mode_type == "upcoming" and hasattr(self, "ncaa_mens_upcoming"):
                return self.ncaa_mens_upcoming

        # Try NCAA Women's
        if self.ncaa_womens_enabled:
            if mode_type == "live" and hasattr(self, "ncaa_womens_live"):
                return self.ncaa_womens_live
            elif mode_type == "recent" and hasattr(self, "ncaa_womens_recent"):
                return self.ncaa_womens_recent
            elif mode_type == "upcoming" and hasattr(self, "ncaa_womens_upcoming"):
                return self.ncaa_womens_upcoming

        return None

    def validate_config(self) -> bool:
        """Validate plugin configuration."""
        try:
            # Check that at least one league is enabled
            if not (self.nhl_enabled or self.ncaa_mens_enabled or self.ncaa_womens_enabled):
                self.logger.warning("No leagues enabled in hockey scoreboard plugin")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating config: {e}")
            return False

    def get_duration(self) -> float:
        """Get the display duration for this plugin."""
        return float(self.display_duration)

    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        try:
            current_manager = self._get_current_manager()
            current_mode = self.modes[self.current_mode_index] if self.modes else "none"

            info = {
                "plugin_id": self.plugin_id,
                "name": "Hockey Scoreboard",
                "version": "1.0.0",
                "enabled": self.is_enabled,
                "display_size": f"{self.display_width}x{self.display_height}",
                "nhl_enabled": self.nhl_enabled,
                "ncaa_mens_enabled": self.ncaa_mens_enabled,
                "ncaa_womens_enabled": self.ncaa_womens_enabled,
                "current_mode": current_mode,
                "available_modes": self.modes,
                "display_duration": self.display_duration,
                "game_display_duration": self.game_display_duration,
                "show_records": getattr(self, 'show_records', False),
                "show_ranking": getattr(self, 'show_ranking', False),
                "show_odds": getattr(self, 'show_odds', False),
                "managers_initialized": {
                    "nhl_live": hasattr(self, "nhl_live"),
                    "nhl_recent": hasattr(self, "nhl_recent"),
                    "nhl_upcoming": hasattr(self, "nhl_upcoming"),
                    "ncaa_mens_live": hasattr(self, "ncaa_mens_live"),
                    "ncaa_mens_recent": hasattr(self, "ncaa_mens_recent"),
                    "ncaa_mens_upcoming": hasattr(self, "ncaa_mens_upcoming"),
                    "ncaa_womens_live": hasattr(self, "ncaa_womens_live"),
                    "ncaa_womens_recent": hasattr(self, "ncaa_womens_recent"),
                    "ncaa_womens_upcoming": hasattr(self, "ncaa_womens_upcoming"),
                },
            }

            # Add manager-specific info if available
            if current_manager and hasattr(current_manager, "get_info"):
                try:
                    manager_info = current_manager.get_info()
                    info["current_manager_info"] = manager_info
                except Exception as e:
                    info["current_manager_info"] = f"Error getting manager info: {e}"

            return info

        except Exception as e:
            self.logger.error(f"Error getting plugin info: {e}")
            return {
                "plugin_id": self.plugin_id,
                "name": "Hockey Scoreboard",
                "error": str(e),
            }

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if hasattr(self, "background_service") and self.background_service:
                # Clean up background service if needed
                pass
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
