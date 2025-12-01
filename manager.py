"""
Hockey Scoreboard Plugin for LEDMatrix - Using Existing Managers

This plugin provides NHL, NCAA Men's, and NCAA Women's hockey scoreboard functionality by reusing
the proven, working manager classes from the LEDMatrix core project.
"""

import logging
import time
from typing import Dict, Any, Optional

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
        # Get display dimensions from display_manager properties
        if hasattr(display_manager, 'matrix') and display_manager.matrix is not None:
            self.display_width = display_manager.matrix.width
            self.display_height = display_manager.matrix.height
        else:
            self.display_width = getattr(display_manager, "width", 128)
            self.display_height = getattr(display_manager, "height", 32)

        # League configurations (defaults come from schema via plugin_manager merge)
        # Debug: Log what config we received
        self.logger.debug(f"Hockey plugin received config keys: {list(config.keys())}")
        self.logger.debug(f"NHL config: {config.get('nhl', {})}")
        
        self.nhl_enabled = config.get("nhl", {}).get("enabled", False)
        self.ncaa_mens_enabled = config.get("ncaa_mens", {}).get("enabled", False)
        self.ncaa_womens_enabled = config.get("ncaa_womens", {}).get("enabled", False)
        
        self.logger.info(f"League enabled states - NHL: {self.nhl_enabled}, NCAA Men's: {self.ncaa_mens_enabled}, NCAA Women's: {self.ncaa_womens_enabled}")

        # Live priority settings
        self.nhl_live_priority = self.config.get("nhl", {}).get("live_priority", False)
        self.ncaa_mens_live_priority = self.config.get("ncaa_mens", {}).get(
            "live_priority", False
        )
        self.ncaa_womens_live_priority = self.config.get("ncaa_womens", {}).get(
            "live_priority", False
        )

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
        self.last_mode_switch = time.time()
        self.modes = self._get_available_modes()

        # Track current display context for granular dynamic duration
        self._current_display_league: Optional[str] = None  # 'nhl', 'ncaa_mens', or 'ncaa_womens'
        self._current_display_mode_type: Optional[str] = None  # 'live', 'recent', 'upcoming'

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
        filtering_config = league_config.get("filtering", {})

        def resolve_mode_flag(*keys: str, default: bool = True) -> bool:
            for key in keys:
                if key in display_modes:
                    return bool(display_modes[key])
            return default

        live_flag = resolve_mode_flag("live", "show_live", "hockey_live")
        recent_flag = resolve_mode_flag("recent", "show_recent", "hockey_recent")
        upcoming_flag = resolve_mode_flag("upcoming", "show_upcoming", "hockey_upcoming")

        def resolve_bool(default_key: str, *extra_keys: str, default: bool = False) -> bool:
            keys = (default_key,) + extra_keys
            for key in keys:
                if key in league_config:
                    return bool(league_config[key])
                if key in filtering_config:
                    return bool(filtering_config[key])
            return default

        favorite_only = resolve_bool("favorite_teams_only", "show_favorite_teams_only")
        show_all_live = resolve_bool("show_all_live")

        def resolve_live_duration() -> int:
            if "live_game_duration" in league_config:
                return int(league_config["live_game_duration"])
            if "game_rotation_interval_seconds" in league_config:
                return int(league_config["game_rotation_interval_seconds"])
            if "live_display_duration" in league_config:
                return int(league_config["live_display_duration"])
            return 20

        # Create manager config with expected structure
        manager_config = {
            f"{sport_key}_scoreboard": {
                "enabled": league_config.get("enabled", False),
                "favorite_teams": league_config.get("favorite_teams", []),
                "display_modes": {
                    "hockey_live": live_flag,
                    "hockey_recent": recent_flag,
                    "hockey_upcoming": upcoming_flag,
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
                "show_favorite_teams_only": favorite_only,
                "show_all_live": show_all_live,
                "live_priority": league_config.get("live_priority", False),
                "test_mode": league_config.get("test_mode", False),
                "update_interval_seconds": league_config.get(
                    "update_interval_seconds", 60
                ),
                "live_update_interval": league_config.get("live_update_interval", 15),
                "live_game_duration": resolve_live_duration(),
                "background_service": {
                    "request_timeout": 30,
                    "max_retries": 3,
                    "priority": 2,
                },
            }
        }

        # Add global config - get timezone from cache_manager's config_manager if available
        timezone_str = self.config.get("timezone")
        if not timezone_str and hasattr(self.cache_manager, 'config_manager'):
            timezone_str = self.cache_manager.config_manager.get_timezone()
        if not timezone_str:
            timezone_str = "UTC"
        
        # Get display config from main config if available
        display_config = self.config.get("display", {})
        if not display_config and hasattr(self.cache_manager, 'config_manager'):
            display_config = self.cache_manager.config_manager.get_display_config()
        
        manager_config.update(
            {
                "timezone": timezone_str,
                "display": display_config,
            }
        )

        return manager_config

    def _get_available_modes(self) -> list:
        """Get list of available display modes based on enabled leagues (like football plugin)."""
        modes = []

        def league_modes(league: str, key_prefix: str) -> Dict[str, bool]:
            league_config = self.config.get(league, {})
            display_modes = league_config.get("display_modes", {})

            def resolve(*candidates: str) -> bool:
                for key in candidates:
                    if key in display_modes:
                        return bool(display_modes[key])
                return True

            return {
                "live": resolve("live", "show_live", f"{key_prefix}_live"),
                "recent": resolve("recent", "show_recent", f"{key_prefix}_recent"),
                "upcoming": resolve("upcoming", "show_upcoming", f"{key_prefix}_upcoming"),
            }

        if self.nhl_enabled:
            flags = league_modes("nhl", "hockey")
            if flags["live"]:
                modes.append("nhl_live")
            if flags["recent"]:
                modes.append("nhl_recent")
            if flags["upcoming"]:
                modes.append("nhl_upcoming")

        if self.ncaa_mens_enabled:
            flags = league_modes("ncaa_mens", "hockey")
            if flags["live"]:
                modes.append("ncaa_mens_live")
            if flags["recent"]:
                modes.append("ncaa_mens_recent")
            if flags["upcoming"]:
                modes.append("ncaa_mens_upcoming")

        if self.ncaa_womens_enabled:
            flags = league_modes("ncaa_womens", "hockey")
            if flags["live"]:
                modes.append("ncaa_womens_live")
            if flags["recent"]:
                modes.append("ncaa_womens_recent")
            if flags["upcoming"]:
                modes.append("ncaa_womens_upcoming")

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

    def _ensure_manager_updated(self, manager) -> None:
        """Trigger an update when the delegated manager is stale."""
        last_update = getattr(manager, "last_update", None)
        update_interval = getattr(manager, "update_interval", None)
        if last_update is None or update_interval is None:
            return

        interval = update_interval
        no_data_interval = getattr(manager, "no_data_interval", None)
        live_games = getattr(manager, "live_games", None)
        if no_data_interval and not live_games:
            interval = no_data_interval

        try:
            if interval and time.time() - last_update >= interval:
                manager.update()
        except Exception as exc:
            self.logger.debug(f"Auto-refresh failed for manager {manager}: {exc}")

    def update(self) -> None:
        """Update hockey game data."""
        if not self.is_enabled:
            return

        try:
            # Update NHL managers if enabled
            if self.nhl_enabled:
                for attr in ("nhl_live", "nhl_recent", "nhl_upcoming"):
                    manager = getattr(self, attr, None)
                    if manager:
                        manager.update()

            # Update NCAA Men's managers if enabled
            if self.ncaa_mens_enabled:
                for attr in ("ncaa_mens_live", "ncaa_mens_recent", "ncaa_mens_upcoming"):
                    manager = getattr(self, attr, None)
                    if manager:
                        manager.update()

            # Update NCAA Women's managers if enabled
            if self.ncaa_womens_enabled:
                for attr in (
                    "ncaa_womens_live",
                    "ncaa_womens_recent",
                    "ncaa_womens_upcoming",
                ):
                    manager = getattr(self, attr, None)
                    if manager:
                        manager.update()

        except Exception as e:
            self.logger.error(f"Error updating managers: {e}", exc_info=True)

    def display(self, force_clear: bool = False, display_mode: Optional[str] = None) -> bool:
        """Display hockey games with mode cycling (like football plugin)."""
        if not self.is_enabled:
            return False

        try:
            current_time = time.time()

            # If display_mode is provided, use it to determine which manager to call
            if display_mode:
                # Parse display_mode (e.g., "nhl_live", "ncaa_mens_recent", "ncaa_womens_upcoming")
                parts = display_mode.split("_", 1)
                if len(parts) == 2:
                    league_prefix, mode_type = parts
                    # Map league prefixes to league names
                    league_map = {
                        "nhl": "nhl",
                        "ncaa": "ncaa_mens",  # Default to mens if just "ncaa"
                    }
                    # Handle ncaa_mens and ncaa_womens explicitly
                    if display_mode.startswith("ncaa_mens_"):
                        league = "ncaa_mens"
                        mode_type = display_mode.replace("ncaa_mens_", "")
                    elif display_mode.startswith("ncaa_womens_"):
                        league = "ncaa_womens"
                        mode_type = display_mode.replace("ncaa_womens_", "")
                    else:
                        league = league_map.get(league_prefix, "nhl")
                    
                    # Track which league/mode we're displaying for granular dynamic duration
                    self._current_display_league = league
                    self._current_display_mode_type = mode_type
                    
                    # Get the appropriate manager
                    managers_to_try = []
                    if league == "nhl" and self.nhl_enabled:
                        if mode_type == "live":
                            managers_to_try.append(self.nhl_live)
                        elif mode_type == "recent":
                            managers_to_try.append(self.nhl_recent)
                        elif mode_type == "upcoming":
                            managers_to_try.append(self.nhl_upcoming)
                    elif league == "ncaa_mens" and self.ncaa_mens_enabled:
                        if mode_type == "live":
                            managers_to_try.append(self.ncaa_mens_live)
                        elif mode_type == "recent":
                            managers_to_try.append(self.ncaa_mens_recent)
                        elif mode_type == "upcoming":
                            managers_to_try.append(self.ncaa_mens_upcoming)
                    elif league == "ncaa_womens" and self.ncaa_womens_enabled:
                        if mode_type == "live":
                            managers_to_try.append(self.ncaa_womens_live)
                        elif mode_type == "recent":
                            managers_to_try.append(self.ncaa_womens_recent)
                        elif mode_type == "upcoming":
                            managers_to_try.append(self.ncaa_womens_upcoming)
                    
                    for current_manager in managers_to_try:
                        if current_manager:
                            self._ensure_manager_updated(current_manager)
                            return current_manager.display(force_clear)
                    
                    return False
            else:
                # Fall back to internal mode cycling
                # Check if we should stay on live mode
                should_stay_on_live = False
                if self.has_live_content():
                    # Get current mode name
                    current_mode = self.modes[self.current_mode_index] if self.modes else None
                    # If we're on a live mode, stay there
                    if current_mode and current_mode.endswith('_live'):
                        should_stay_on_live = True
                    # If we're not on a live mode but have live content, switch to it
                    elif not (current_mode and current_mode.endswith('_live')):
                        # Find the first live mode
                        for i, mode in enumerate(self.modes):
                            if mode.endswith('_live'):
                                self.current_mode_index = i
                                force_clear = True
                                self.last_mode_switch = current_time
                                self.logger.info(f"Live content detected - switching to display mode: {mode}")
                                break

                # Handle mode cycling only if not staying on live
                if not should_stay_on_live and current_time - self.last_mode_switch >= self.display_duration:
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
                    # Track which league/mode we're displaying for granular dynamic duration
                    current_mode = self.modes[self.current_mode_index] if self.modes else None
                    if current_mode:
                        if current_mode.startswith("nhl_"):
                            self._current_display_league = 'nhl'
                            self._current_display_mode_type = current_mode.split("_", 1)[1]
                        elif current_mode.startswith("ncaa_mens_"):
                            self._current_display_league = 'ncaa_mens'
                            self._current_display_mode_type = current_mode.split("_", 2)[2]
                        elif current_mode.startswith("ncaa_womens_"):
                            self._current_display_league = 'ncaa_womens'
                            self._current_display_mode_type = current_mode.split("_", 2)[2]
                    
                    self._ensure_manager_updated(current_manager)
                    return current_manager.display(force_clear)
                else:
                    self.logger.warning("No manager available for current mode")
                    return False

        except Exception as e:
            self.logger.error(f"Error in display method: {e}", exc_info=True)
            return False

    def supports_dynamic_duration(self) -> bool:
        """
        Check if dynamic duration is enabled for the current display context.
        Checks granular settings: per-league/per-mode > per-mode > per-league > global.
        """
        if not self.is_enabled:
            return False
        
        # If no current display context, check global setting
        if not self._current_display_league or not self._current_display_mode_type:
            return super().supports_dynamic_duration() if hasattr(super(), 'supports_dynamic_duration') else False
        
        league = self._current_display_league
        mode_type = self._current_display_mode_type
        
        # Check per-league/per-mode setting first (most specific)
        league_config = self.config.get(league, {})
        league_dynamic = league_config.get("dynamic_duration", {})
        league_modes = league_dynamic.get("modes", {})
        mode_config = league_modes.get(mode_type, {})
        if "enabled" in mode_config:
            return bool(mode_config.get("enabled", False))
        
        # Check per-league setting
        if "enabled" in league_dynamic:
            return bool(league_dynamic.get("enabled", False))
        
        # Check global per-mode setting
        global_dynamic = self.config.get("dynamic_duration", {})
        global_modes = global_dynamic.get("modes", {})
        global_mode_config = global_modes.get(mode_type, {})
        if "enabled" in global_mode_config:
            return bool(global_mode_config.get("enabled", False))
        
        # Fall back to global setting
        return bool(global_dynamic.get("enabled", False))
    
    def get_dynamic_duration_cap(self) -> Optional[float]:
        """
        Get dynamic duration cap for the current display context.
        Checks granular settings: per-league/per-mode > per-mode > per-league > global.
        """
        if not self.is_enabled:
            return None
        
        # If no current display context, check global setting
        if not self._current_display_league or not self._current_display_mode_type:
            if hasattr(super(), 'get_dynamic_duration_cap'):
                return super().get_dynamic_duration_cap()
            global_dynamic = self.config.get("dynamic_duration", {})
            try:
                cap = float(global_dynamic.get("max_duration_seconds", 300))
                return cap if cap > 0 else None
            except (TypeError, ValueError):
                return None
        
        league = self._current_display_league
        mode_type = self._current_display_mode_type
        
        # Check per-league/per-mode setting first (most specific)
        league_config = self.config.get(league, {})
        league_dynamic = league_config.get("dynamic_duration", {})
        league_modes = league_dynamic.get("modes", {})
        mode_config = league_modes.get(mode_type, {})
        if "max_duration_seconds" in mode_config:
            try:
                cap = float(mode_config.get("max_duration_seconds"))
                if cap > 0:
                    return cap
            except (TypeError, ValueError):
                pass
        
        # Check per-league setting
        if "max_duration_seconds" in league_dynamic:
            try:
                cap = float(league_dynamic.get("max_duration_seconds"))
                if cap > 0:
                    return cap
            except (TypeError, ValueError):
                pass
        
        # Check global per-mode setting
        global_dynamic = self.config.get("dynamic_duration", {})
        global_modes = global_dynamic.get("modes", {})
        global_mode_config = global_modes.get(mode_type, {})
        if "max_duration_seconds" in global_mode_config:
            try:
                cap = float(global_mode_config.get("max_duration_seconds"))
                if cap > 0:
                    return cap
            except (TypeError, ValueError):
                pass
        
        # Fall back to global setting
        try:
            cap = float(global_dynamic.get("max_duration_seconds", 300))
            return cap if cap > 0 else None
        except (TypeError, ValueError):
            return None

    def has_live_priority(self) -> bool:
        if not self.is_enabled:
            return False

        return any(
            [
                self.nhl_enabled and self.nhl_live_priority,
                self.ncaa_mens_enabled and self.ncaa_mens_live_priority,
                self.ncaa_womens_enabled and self.ncaa_womens_live_priority,
            ]
        )

    def has_live_content(self) -> bool:
        if not self.is_enabled:
            return False

        nhl_live = (
            self.nhl_enabled
            and self.nhl_live_priority
            and hasattr(self, "nhl_live")
            and bool(getattr(self.nhl_live, "live_games", []))
        )
        ncaa_mens_live = (
            self.ncaa_mens_enabled
            and self.ncaa_mens_live_priority
            and hasattr(self, "ncaa_mens_live")
            and bool(getattr(self.ncaa_mens_live, "live_games", []))
        )
        ncaa_womens_live = (
            self.ncaa_womens_enabled
            and self.ncaa_womens_live_priority
            and hasattr(self, "ncaa_womens_live")
            and bool(getattr(self.ncaa_womens_live, "live_games", []))
        )

        return nhl_live or ncaa_mens_live or ncaa_womens_live

    def get_live_modes(self) -> list:
        if not self.is_enabled:
            return []

        prioritized_modes = []
        if self.nhl_enabled and self.nhl_live_priority and "nhl_live" in self.modes:
            prioritized_modes.append("nhl_live")

        if (
            self.ncaa_mens_enabled
            and self.ncaa_mens_live_priority
            and "ncaa_mens_live" in self.modes
        ):
            prioritized_modes.append("ncaa_mens_live")

        if (
            self.ncaa_womens_enabled
            and self.ncaa_womens_live_priority
            and "ncaa_womens_live" in self.modes
        ):
            prioritized_modes.append("ncaa_womens_live")

        if prioritized_modes:
            return prioritized_modes

        return [mode for mode in self.modes if mode.endswith("_live")]

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

    def get_display_duration(self) -> float:
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
                "live_priority": {
                    "nhl": self.nhl_enabled and self.nhl_live_priority,
                    "ncaa_mens": self.ncaa_mens_enabled
                    and self.ncaa_mens_live_priority,
                    "ncaa_womens": self.ncaa_womens_enabled
                    and self.ncaa_womens_live_priority,
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
