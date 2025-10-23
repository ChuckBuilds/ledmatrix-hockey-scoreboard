"""
Hockey Scoreboard Plugin for LEDMatrix

Displays live, recent, and upcoming hockey games across NHL, NCAA Men's, and NCAA Women's hockey.
Shows real-time scores, game status, powerplay situations, and team logos.

Features:
- Multiple league support (NHL, NCAA M/W)
- Live game tracking with periods and time
- Recent game results
- Upcoming game schedules
- Favorite team prioritization
- Powerplay and penalty indicators
- Shots on goal statistics
- Background data fetching

API Version: 1.0.0
"""

import logging
import time
from typing import Dict, List, Any

try:
    from src.plugin_system.base_plugin import BasePlugin
except ImportError:
    # Fallback for standalone testing
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'LEDMatrix', 'src'))
    from plugin_system.base_plugin import BasePlugin

# Import local modules
try:
    from data_fetcher import HockeyDataFetcher
    from game_filter import HockeyGameFilter
    from scoreboard_renderer import HockeyScoreboardRenderer
except ImportError:
    # Fallback for when running as a plugin
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, plugin_dir)
    from data_fetcher import HockeyDataFetcher
    from game_filter import HockeyGameFilter
    from scoreboard_renderer import HockeyScoreboardRenderer

logger = logging.getLogger(__name__)


class HockeyScoreboardPlugin(BasePlugin):
    """
    Hockey scoreboard plugin for displaying games across multiple leagues.
    
    Supports NHL, NCAA Men's, and NCAA Women's hockey with live, recent,
    and upcoming game modes.
    
    Configuration options:
        leagues: Enable/disable NHL, NCAA M, NCAA W
        display_modes: Enable live, recent, upcoming modes
        favorite_teams: Team abbreviations per league
        show_shots_on_goal: Display SOG statistics
        show_powerplay: Highlight powerplay situations
        background_service: Data fetching configuration
    """
    
    # ESPN API endpoints for each league
    ESPN_API_URLS = {
        'nhl': 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard',
        'ncaa_mens': 'https://site.api.espn.com/apis/site/v2/sports/hockey/mens-college-hockey/scoreboard',
        'ncaa_womens': 'https://site.api.espn.com/apis/site/v2/sports/hockey/womens-college-hockey/scoreboard'
    }
    
    def __init__(self, plugin_id: str, config: Dict[str, Any],
                 display_manager, cache_manager, plugin_manager):
        """Initialize the hockey scoreboard plugin."""
        super().__init__(plugin_id, config, display_manager, cache_manager, plugin_manager)

        # Configuration - per-league structure like original managers
        self.leagues = {
            'nhl': config.get('nhl', {}),
            'ncaa_mens': config.get('ncaa_mens', {}),
            'ncaa_womens': config.get('ncaa_womens', {})
        }

        # Global settings
        self.global_config = config
        self.display_duration = config.get('display_duration', 15)
        
        # League-specific settings will be read per game
        self.default_show_records = False
        self.default_show_ranking = False
        self.default_show_shots_on_goal = False
        self.default_show_powerplay = True
        self.default_favorite_teams_only = False
        self.default_game_rotation_interval = 10
        
        # Display duration defaults
        self.default_live_display_duration = 20
        self.default_recent_display_duration = 15
        self.default_upcoming_display_duration = 15

        # Background service configuration (internal only)
        self.background_config = {
            'enabled': True,
            'request_timeout': 30,
            'max_retries': 3,
            'priority': 2
        }

        # Initialize modular components
        self.data_fetcher = HockeyDataFetcher(cache_manager, self.logger)
        self.game_filter = HockeyGameFilter(self.logger)
        self.scoreboard_renderer = HockeyScoreboardRenderer(
            display_manager, self.logger, 
            config.get('logo_dir', 'assets/sports/ncaa_logos')
        )

        # State
        self.current_games = []
        self.current_league = None
        self.current_display_mode = None
        self.last_update = 0
        self.initialized = True
        
        # Mode cycling for hockey display modes - specific order as requested
        self.all_display_modes = []
        
        # NHL modes
        if self.leagues.get("nhl", {}).get("enabled", False):
            self.all_display_modes.extend(["nhl_recent", "nhl_upcoming", "nhl_live"])
        
        # NCAA Men's modes
        if self.leagues.get("ncaa_mens", {}).get("enabled", False):
            self.all_display_modes.extend(["ncaa_mens_recent", "ncaa_mens_upcoming", "ncaa_mens_live"])
        
        # NCAA Women's modes
        if self.leagues.get("ncaa_womens", {}).get("enabled", False):
            self.all_display_modes.extend(["ncaa_womens_recent", "ncaa_womens_upcoming", "ncaa_womens_live"])
        
        # If no leagues enabled, default to NHL
        if not self.all_display_modes:
            self.all_display_modes = ["nhl_recent", "nhl_upcoming", "nhl_live"]
            
        # Set initial display mode
        self.current_display_mode = self.all_display_modes[0] if self.all_display_modes else "nhl_recent"
        self.mode_index = 0
        self.last_mode_switch = 0
        self.last_game_switch = 0
        self.current_game_index = 0
        
        # Display timing
        self.display_duration = config.get('display_duration', 15)
        self.game_display_duration = 10  # How long to show each game

        # Register fonts
        self._register_fonts()

        # Log enabled leagues and their settings
        enabled_leagues = []
        for league_key, league_config in self.leagues.items():
            if league_config.get('enabled', False):
                enabled_leagues.append(league_key)

        self.logger.info(f"Hockey scoreboard plugin initialized")
        self.logger.info(f"Enabled leagues: {enabled_leagues}")
        self.logger.info(f"Display modes: {self.all_display_modes}")
    
    def _register_fonts(self):
        """Register fonts with the font manager."""
        try:
            if not hasattr(self.plugin_manager, 'font_manager'):
                return
            
            font_manager = self.plugin_manager.font_manager
            
            # Team name font
            font_manager.register_manager_font(
                manager_id=self.plugin_id,
                element_key=f"{self.plugin_id}.team_name",
                family="press_start",
                size_px=10,
                color=(255, 255, 255)
            )
            
            # Score font
            font_manager.register_manager_font(
                manager_id=self.plugin_id,
                element_key=f"{self.plugin_id}.score",
                family="press_start",
                size_px=12,
                color=(255, 200, 0)
            )
            
            # Status font (period, time)
            font_manager.register_manager_font(
                manager_id=self.plugin_id,
                element_key=f"{self.plugin_id}.status",
                family="four_by_six",
                size_px=6,
                color=(0, 255, 0)
            )
            
            # Info font (shots, powerplay)
            font_manager.register_manager_font(
                manager_id=self.plugin_id,
                element_key=f"{self.plugin_id}.info",
                family="four_by_six",
                size_px=6,
                color=(200, 200, 200)
            )
            
            self.logger.info("Hockey scoreboard fonts registered")
        except Exception as e:
            self.logger.warning(f"Error registering fonts: {e}")
    
    def update(self) -> None:
        """Update hockey game data for all enabled leagues."""
        if not self.initialized:
            return

        try:
            self.current_games = []

            # Fetch data for each enabled league
            for league_key, league_config in self.leagues.items():
                if league_config.get('enabled', False):
                    games = self.data_fetcher.fetch_league_data(league_key, league_config, self.last_update)
                    if games:
                        # Add league info to each game
                        for game in games:
                            game['league_config'] = league_config
                        self.current_games.extend(games)

            # Sort games - prioritize live games and favorites
            # Note: We'll sort again in display() with the specific mode
            self.current_games = self.game_filter.sort_games(self.current_games)

            self.last_update = time.time()
            self.logger.debug(f"Updated hockey data: {len(self.current_games)} games")

        except Exception as e:
            self.logger.error(f"Error updating hockey data: {e}")

    
    def display(self, force_clear: bool = False) -> None:
        """Display hockey games with mode cycling."""
        if not self.initialized:
            self.scoreboard_renderer._display_error("Hockey plugin not initialized")
            return

        try:
            import time
            current_time = time.time()
            
            # Handle mode cycling
            if current_time - self.last_mode_switch >= self.display_duration:
                self.mode_index = (self.mode_index + 1) % len(self.all_display_modes)
                self.current_display_mode = self.all_display_modes[self.mode_index]
                self.last_mode_switch = current_time
                self.current_game_index = 0
                self.last_game_switch = current_time
                force_clear = True
                self.logger.info(f"Switching to display mode: {self.current_display_mode}")

            # Filter games for the current mode
            filtered_games = self._filter_games_for_mode(self.current_display_mode)
            
            # Debug logging for game selection
            if filtered_games:
                self.logger.info(f"Found {len(filtered_games)} games for {self.current_display_mode}")
                # Log the first few games for debugging
                for i, game in enumerate(filtered_games[:3]):
                    home_team = game.get('home_team', {}).get('abbrev', 'UNK')
                    away_team = game.get('away_team', {}).get('abbrev', 'UNK')
                    start_time = game.get('start_time', '')
                    status = game.get('status', {}).get('state', '')
                    self.logger.info(f"  Game {i+1}: {away_team} @ {home_team} ({start_time[:10]}) - {status}")
                
                # Special debugging for TB games
                if 'nhl' in self.current_display_mode:
                    tb_games = [g for g in filtered_games if 'TB' in [g.get('home_team', {}).get('abbrev', ''), g.get('away_team', {}).get('abbrev', '')]]
                    if tb_games:
                        self.logger.info(f"TB games found: {len(tb_games)}")
                        for i, game in enumerate(tb_games):
                            home_team = game.get('home_team', {}).get('abbrev', 'UNK')
                            away_team = game.get('away_team', {}).get('abbrev', 'UNK')
                            start_time = game.get('start_time', '')
                            status = game.get('status', {}).get('state', '')
                            self.logger.info(f"  TB Game {i+1}: {away_team} @ {home_team} ({start_time[:10]}) - {status}")
            
            if not filtered_games:
                self.logger.warning(f"No games available for mode: {self.current_display_mode}")
                # Skip to next mode immediately
                self.mode_index = (self.mode_index + 1) % len(self.all_display_modes)
                self.current_display_mode = self.all_display_modes[self.mode_index]
                self.last_mode_switch = current_time
                self.current_game_index = 0
                self.last_game_switch = current_time
                force_clear = True
                return

            # Handle game rotation within the current mode
            if len(filtered_games) > 1 and current_time - self.last_game_switch >= self.game_display_duration:
                self.current_game_index = (self.current_game_index + 1) % len(filtered_games)
                self.last_game_switch = current_time
                force_clear = True
                
                # Log game switching
                current_game = filtered_games[self.current_game_index]
                away_abbr = current_game.get('away_team', {}).get('abbrev', 'UNK')
                home_abbr = current_game.get('home_team', {}).get('abbrev', 'UNK')
                self.logger.info(f"[{self.current_display_mode}] Rotating to {away_abbr} vs {home_abbr}")

            # Display current game
            if filtered_games and self.current_game_index < len(filtered_games):
                current_game = filtered_games[self.current_game_index]
                self._display_game(current_game, self.current_display_mode)
            else:
                self.logger.warning("No games to display")

        except Exception as e:
            self.logger.error(f"Error in display: {e}")
            self.scoreboard_renderer._display_error("Display error")
    
    def _filter_games_for_mode(self, display_mode: str) -> List[Dict]:
        """Filter games for a specific display mode."""
        # Parse the display mode to get league and type
        if '_' in display_mode:
            parts = display_mode.split('_')
            if len(parts) >= 3:  # ncaa_mens_recent, ncaa_mens_live, ncaa_womens_recent, ncaa_womens_live
                league = f"{parts[0]}_{parts[1]}"  # ncaa_mens, ncaa_womens
                mode_type = parts[2]  # recent, upcoming, live
            else:  # nhl_recent, nhl_upcoming, nhl_live
                league = parts[0]  # nhl
                mode_type = parts[1]  # recent, upcoming, live
            hockey_mode = f"hockey_{mode_type}"
        else:
            league = 'nhl'
            hockey_mode = display_mode
        
        # Filter games by league and mode
        league_games = [game for game in self.current_games if game.get('league') == league]
        self.logger.info(f"League {league} games: {len(league_games)}")
        
        filtered_games = self.game_filter.filter_games_by_mode(league_games, hockey_mode)
        self.logger.info(f"After mode filtering: {len(filtered_games)} games")
        
        # Apply favorite teams filter if enabled
        if filtered_games:
            league_config = self.leagues.get(league, {})
            favorite_teams_only = league_config.get('favorite_teams_only', self.default_favorite_teams_only)
            self.logger.info(f"Favorite teams only: {favorite_teams_only}")
            
            if favorite_teams_only:
                before_count = len(filtered_games)
                filtered_games = self.game_filter.filter_favorite_teams_only(filtered_games, favorite_teams_only)
                self.logger.info(f"After favorite teams filter: {len(filtered_games)} games (was {before_count})")
        
        # Games are already sorted by filter_games_by_mode
        self.logger.info(f"Final filtered games: {len(filtered_games)}")
        
        return filtered_games
    
    def _get_display_duration(self, display_mode: str, league_config: Dict) -> int:
        """Get the display duration for a specific mode and league."""
        if display_mode == 'hockey_live':
            return league_config.get('live_display_duration', self.default_live_display_duration)
        elif display_mode == 'hockey_recent':
            return league_config.get('recent_display_duration', self.default_recent_display_duration)
        elif display_mode == 'hockey_upcoming':
            return league_config.get('upcoming_display_duration', self.default_upcoming_display_duration)
        else:
            return self.display_duration
    
    
    def _display_game(self, game: Dict, display_mode: str):
        """Display a single game."""
        try:
            # Parse the display mode to get the hockey mode
            if '_' in display_mode:
                parts = display_mode.split('_')
                if len(parts) >= 3:  # ncaa_mens_recent, ncaa_mens_live, ncaa_womens_recent, ncaa_womens_live
                    mode_type = parts[2]  # recent, upcoming, live
                else:  # nhl_recent, nhl_upcoming, nhl_live
                    mode_type = parts[1]  # recent, upcoming, live
                hockey_mode = f"hockey_{mode_type}"
            else:
                hockey_mode = display_mode
            
            # Get league-specific settings
            league_key = game.get('league', 'nhl')
            league_config = self.leagues.get(league_key, {})
            
            show_shots = league_config.get('show_shots_on_goal', self.default_show_shots_on_goal)
            show_powerplay = league_config.get('show_powerplay', self.default_show_powerplay)
            show_records = league_config.get('show_records', self.default_show_records)
            show_ranking = league_config.get('show_ranking', self.default_show_ranking)
            
            if hockey_mode == 'hockey_live':
                self.scoreboard_renderer.render_live_game(
                    game, 
                    show_shots=show_shots,
                    show_powerplay=show_powerplay
                )
            elif hockey_mode == 'hockey_recent':
                self.scoreboard_renderer.render_recent_game(game)
            elif hockey_mode == 'hockey_upcoming':
                self.scoreboard_renderer.render_upcoming_game(game)
            else:
                self.logger.warning(f"Unknown hockey mode: {hockey_mode}")
            
        except Exception as e:
            self.logger.error(f"Error displaying game: {e}")
            self.scoreboard_renderer._display_error("Display error")
    
    
    def get_display_duration(self) -> float:
        """Get display duration from config."""
        return self.display_duration
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin info for web UI."""
        info = super().get_info()

        # Get league-specific configurations
        leagues_config = {}
        for league_key, league_config in self.leagues.items():
            leagues_config[league_key] = {
                'enabled': league_config.get('enabled', False),
                'favorite_teams': league_config.get('favorite_teams', []),
                'display_modes': league_config.get('display_modes', {}),
                'recent_games_to_show': league_config.get('recent_games_to_show', 5),
                'upcoming_games_to_show': league_config.get('upcoming_games_to_show', 10),
                'update_interval_seconds': league_config.get('update_interval_seconds', 60)
            }

        info.update({
            'total_games': len(self.current_games),
            'enabled_leagues': [k for k, v in self.leagues.items() if v.get('enabled', False)],
            'current_mode': self.current_display_mode,
            'last_update': self.last_update,
            'display_duration': self.display_duration,
            'show_records': self.show_records,
            'show_ranking': self.show_ranking,
            'show_shots_on_goal': self.show_shots_on_goal,
            'show_powerplay': self.show_powerplay,
            'live_games': len([g for g in self.current_games if g.get('status', {}).get('state') == 'in']),
            'recent_games': len([g for g in self.current_games if g.get('status', {}).get('state') == 'post']),
            'upcoming_games': len([g for g in self.current_games if g.get('status', {}).get('state') == 'pre']),
            'leagues_config': leagues_config,
            'global_config': self.global_config
        })
        return info
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.current_games = []
        self.logger.info("Hockey scoreboard plugin cleaned up")

