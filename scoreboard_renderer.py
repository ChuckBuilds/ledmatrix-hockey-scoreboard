"""
Scoreboard Renderer for Hockey Scoreboard Plugin

Handles all display and rendering logic for the hockey scoreboard plugin.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont


class HockeyScoreboardRenderer:
    """Handles rendering for hockey scoreboard plugin."""
    
    def __init__(self, display_manager, logger: logging.Logger, 
                 logo_dir: str = "assets/sports/ncaa_logos"):
        """Initialize the scoreboard renderer."""
        self.display_manager = display_manager
        self.logger = logger
        self.logo_dir = Path(logo_dir)
        self._logo_cache = {}
        
        # Load fonts
        self.fonts = self._load_fonts()
    
    def _load_fonts(self):
        """Load fonts used by the scoreboard."""
        fonts = {}
        try:
            fonts['score'] = ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", 10)
            fonts['time'] = ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", 8)
            fonts['team'] = ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", 8)
            fonts['status'] = ImageFont.truetype("assets/fonts/4x6-font.ttf", 6)
            fonts['detail'] = ImageFont.truetype("assets/fonts/4x6-font.ttf", 6)
            fonts['rank'] = ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", 10)
            self.logger.info("Successfully loaded fonts")
        except IOError:
            self.logger.warning("Fonts not found, using default PIL font.")
            fonts['score'] = ImageFont.load_default()
            fonts['time'] = ImageFont.load_default()
            fonts['team'] = ImageFont.load_default()
            fonts['status'] = ImageFont.load_default()
            fonts['detail'] = ImageFont.load_default()
            fonts['rank'] = ImageFont.load_default()
        return fonts
    
    def _load_and_resize_logo(self, team_abbrev: str, logo_path: Path) -> Optional[Image.Image]:
        """Load and resize a team logo, with caching."""
        if team_abbrev in self._logo_cache:
            return self._logo_cache[team_abbrev]
        
        try:
            if not logo_path.exists():
                self.logger.warning(f"Logo not found for {team_abbrev} at {logo_path}")
                return None
                
            logo = Image.open(logo_path)
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Resize logo to fit display
            max_width = int(self.display_manager.matrix.width * 1.5)
            max_height = int(self.display_manager.matrix.height * 1.5)
            logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            self._logo_cache[team_abbrev] = logo
            return logo
            
        except Exception as e:
            self.logger.error(f"Error loading logo for {team_abbrev}: {e}")
            return None
    
    def _draw_text_with_outline(self, draw, text, position, font, 
                               fill=(255, 255, 255), outline_color=(0, 0, 0)):
        """Draw text with a black outline for better readability."""
        x, y = position
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=fill)
    
    def render_live_game(self, game: Dict, show_shots: bool = False, 
                        show_powerplay: bool = True) -> None:
        """Render a live hockey game with proper scorebug layout matching NHL manager."""
        try:
            matrix_width = self.display_manager.matrix.width
            matrix_height = self.display_manager.matrix.height
            
            # Create main image with transparency (matching NHL manager)
            main_img = Image.new("RGBA", (matrix_width, matrix_height), (0, 0, 0, 255))
            overlay = Image.new("RGBA", (matrix_width, matrix_height), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            # Get team info (matching NHL manager field names)
            home_team = game.get('home_team', {})
            away_team = game.get('away_team', {})
            status = game.get('status', {})
            
            # Load and resize team logos (matching NHL manager parameters)
            home_logo = self._load_and_resize_logo(
                home_team.get('abbrev', ''),
                self.logo_dir / f"{home_team.get('abbrev', '')}.png"
            )
            away_logo = self._load_and_resize_logo(
                away_team.get('abbrev', ''),
                self.logo_dir / f"{away_team.get('abbrev', '')}.png"
            )
            
            # Error handling for logos (matching NHL manager)
            if not home_logo or not away_logo:
                self.logger.error(f"Failed to load logos for live game: {game.get('id')}")
                draw_final = ImageDraw.Draw(main_img.convert("RGB"))
                self._draw_text_with_outline(draw_final, "Logo Error", (5, 5), self.fonts['status'])
                self.display_manager.image.paste(main_img.convert("RGB"), (0, 0))
                self.display_manager.update_display()
                return
            
            center_y = matrix_height // 2
            
            # Draw logos (matching NHL manager positioning)
            home_x = matrix_width - home_logo.width + 10  # adjusted from 18
            home_y = center_y - (home_logo.height // 2)
            main_img.paste(home_logo, (home_x, home_y), home_logo)
            
            away_x = -10  # adjusted from 18
            away_y = center_y - (away_logo.height // 2)
            main_img.paste(away_logo, (away_x, away_y), away_logo)
            
            # Draw period and clock (matching NHL manager)
            status = game.get('status', {})
            period = status.get('period', 0)
            clock = status.get('display_clock', '')
            state = status.get('state', '')
            
            if state == 'in':
                period_clock_text = f"P{period} {clock}".strip()
            elif state == 'post':
                period_clock_text = "Final"
            else:
                period_clock_text = status.get('short_detail', '')
            
            status_width = draw_overlay.textlength(period_clock_text, font=self.fonts['time'])
            status_x = (matrix_width - status_width) // 2
            status_y = 1
            self._draw_text_with_outline(draw_overlay, period_clock_text, (status_x, status_y), self.fonts['time'])
            
            # Draw scores (matching NHL manager positioning)
            home_team = game.get('home_team', {})
            away_team = game.get('away_team', {})
            home_score = str(home_team.get("score", "0"))
            away_score = str(away_team.get("score", "0"))
            score_text = f"{away_score}-{home_score}"
            score_width = draw_overlay.textlength(score_text, font=self.fonts['score'])
            score_x = (matrix_width - score_width) // 2
            score_y = (matrix_height // 2) - 3
            self._draw_text_with_outline(draw_overlay, score_text, (score_x, score_y), self.fonts['score'])
            
            # Draw shots on goal (matching NHL manager)
            if show_shots:
                shots_font = ImageFont.truetype("assets/fonts/4x6-font.ttf", 6)
                home_shots = str(game.get("home_shots", "0"))
                away_shots = str(game.get("away_shots", "0"))
                shots_text = f"{away_shots}   SHOTS   {home_shots}"
                shots_bbox = draw_overlay.textbbox((0, 0), shots_text, font=shots_font)
                shots_height = shots_bbox[3] - shots_bbox[1]
                shots_y = matrix_height - shots_height - 1
                shots_width = draw_overlay.textlength(shots_text, font=shots_font)
                shots_x = (matrix_width - shots_width) // 2
                self._draw_text_with_outline(draw_overlay, shots_text, (shots_x, shots_y), shots_font)
            
            # Composite the text overlay onto the main image
            main_img = Image.alpha_composite(main_img, overlay)
            main_img = main_img.convert("RGB")
            
            # Update display
            self.display_manager.image.paste(main_img, (0, 0))
            self.display_manager.update_display()
            
        except Exception as e:
            self.logger.error(f"Error rendering live game: {e}")
            self._display_error("Display error")
    
    def render_recent_game(self, game: Dict) -> None:
        """Render a recent hockey game with proper scorebug layout matching NHL manager."""
        try:
            matrix_width = self.display_manager.matrix.width
            matrix_height = self.display_manager.matrix.height
            
            # Create main image with transparency (matching NHL manager)
            main_img = Image.new("RGBA", (matrix_width, matrix_height), (0, 0, 0, 255))
            overlay = Image.new("RGBA", (matrix_width, matrix_height), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            # Get team info (matching NHL manager field names)
            home_team = game.get('home_team', {})
            away_team = game.get('away_team', {})
            
            # Load and resize team logos (matching NHL manager parameters)
            home_logo = self._load_and_resize_logo(
                home_team.get('abbrev', ''),
                self.logo_dir / f"{home_team.get('abbrev', '')}.png"
            )
            away_logo = self._load_and_resize_logo(
                away_team.get('abbrev', ''),
                self.logo_dir / f"{away_team.get('abbrev', '')}.png"
            )
            
            # Error handling for logos (matching NHL manager)
            if not home_logo or not away_logo:
                self.logger.error(f"Failed to load logos for recent game: {game.get('id')}")
                draw_final = ImageDraw.Draw(main_img.convert("RGB"))
                self._draw_text_with_outline(draw_final, "Logo Error", (5, 5), self.fonts['status'])
                self.display_manager.image.paste(main_img.convert("RGB"), (0, 0))
                self.display_manager.update_display()
                return
            
            center_y = matrix_height // 2
            
            # Draw logos (matching NHL manager positioning)
            home_x = matrix_width - home_logo.width + 10  # adjusted from 18
            home_y = center_y - (home_logo.height // 2)
            main_img.paste(home_logo, (home_x, home_y), home_logo)
            
            away_x = -10  # adjusted from 18
            away_y = center_y - (away_logo.height // 2)
            main_img.paste(away_logo, (away_x, away_y), away_logo)
            
            # Draw "Final" status (matching NHL manager)
            status_text = "Final"
            status_width = draw_overlay.textlength(status_text, font=self.fonts['time'])
            status_x = (matrix_width - status_width) // 2
            status_y = 1
            self._draw_text_with_outline(draw_overlay, status_text, (status_x, status_y), self.fonts['time'])
            
            # Draw final scores (matching NHL manager positioning)
            home_team = game.get('home_team', {})
            away_team = game.get('away_team', {})
            home_score = str(home_team.get("score", "0"))
            away_score = str(away_team.get("score", "0"))
            score_text = f"{away_score}-{home_score}"
            score_width = draw_overlay.textlength(score_text, font=self.fonts['score'])
            score_x = (matrix_width - score_width) // 2
            score_y = (matrix_height // 2) - 3
            self._draw_text_with_outline(draw_overlay, score_text, (score_x, score_y), self.fonts['score'])
            
            # Composite the text overlay onto the main image
            main_img = Image.alpha_composite(main_img, overlay)
            main_img = main_img.convert("RGB")
            
            # Update display
            self.display_manager.image.paste(main_img, (0, 0))
            self.display_manager.update_display()
            
        except Exception as e:
            self.logger.error(f"Error rendering recent game: {e}")
            self._display_error("Display error")
    
    def render_upcoming_game(self, game: Dict) -> None:
        """Render an upcoming hockey game with proper scorebug layout matching NHL manager."""
        try:
            matrix_width = self.display_manager.matrix.width
            matrix_height = self.display_manager.matrix.height
            
            # Create main image with transparency (matching NHL manager)
            main_img = Image.new("RGBA", (matrix_width, matrix_height), (0, 0, 0, 255))
            overlay = Image.new("RGBA", (matrix_width, matrix_height), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            # Get team info (matching NHL manager field names)
            home_team = game.get('home_team', {})
            away_team = game.get('away_team', {})
            
            # Load and resize team logos (matching NHL manager parameters)
            home_logo = self._load_and_resize_logo(
                home_team.get('abbrev', ''),
                self.logo_dir / f"{home_team.get('abbrev', '')}.png"
            )
            away_logo = self._load_and_resize_logo(
                away_team.get('abbrev', ''),
                self.logo_dir / f"{away_team.get('abbrev', '')}.png"
            )
            
            # Error handling for logos (matching NHL manager)
            if not home_logo or not away_logo:
                self.logger.error(f"Failed to load logos for upcoming game: {game.get('id')}")
                draw_final = ImageDraw.Draw(main_img.convert("RGB"))
                self._draw_text_with_outline(draw_final, "Logo Error", (5, 5), self.fonts['status'])
                self.display_manager.image.paste(main_img.convert("RGB"), (0, 0))
                self.display_manager.update_display()
                return
            
            center_y = matrix_height // 2
            
            # Draw logos (matching NHL manager positioning)
            home_x = matrix_width - home_logo.width + 2  # MLB-style positioning
            home_y = center_y - (home_logo.height // 2)
            main_img.paste(home_logo, (home_x, home_y), home_logo)
            
            away_x = -2  # MLB-style positioning
            away_y = center_y - (away_logo.height // 2)
            main_img.paste(away_logo, (away_x, away_y), away_logo)
            
            # Draw game time and date (matching NHL manager)
            start_time = game.get("start_time", "")
            if start_time:
                # Parse the start time and format it nicely
                try:
                    from datetime import datetime
                    import pytz
                    
                    # Parse the ISO format time
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    
                    # Convert to local time
                    local_tz = pytz.timezone('America/New_York')  # Default to Eastern
                    local_dt = dt.astimezone(local_tz)
                    
                    # Format as "Oct 22 7:00 PM"
                    time_text = local_dt.strftime("%b %d %I:%M %p")
                    
                    time_width = draw_overlay.textlength(time_text, font=self.fonts['time'])
                    time_x = (matrix_width - time_width) // 2
                    time_y = 1
                    self._draw_text_with_outline(draw_overlay, time_text, (time_x, time_y), self.fonts['time'])
                except Exception as e:
                    # Fallback to raw time if parsing fails
                    time_text = start_time[:16]  # Truncate to reasonable length
                    time_width = draw_overlay.textlength(time_text, font=self.fonts['time'])
                    time_x = (matrix_width - time_width) // 2
                    time_y = 1
                    self._draw_text_with_outline(draw_overlay, time_text, (time_x, time_y), self.fonts['time'])
            
            # Draw "VS" in center (matching NHL manager)
            vs_text = "VS"
            vs_width = draw_overlay.textlength(vs_text, font=self.fonts['score'])
            vs_x = (matrix_width - vs_width) // 2
            vs_y = (matrix_height // 2) - 3
            self._draw_text_with_outline(draw_overlay, vs_text, (vs_x, vs_y), self.fonts['score'])
            
            # Composite the text overlay onto the main image
            main_img = Image.alpha_composite(main_img, overlay)
            main_img = main_img.convert("RGB")
            
            # Update display
            self.display_manager.image.paste(main_img, (0, 0))
            self.display_manager.update_display()
            
        except Exception as e:
            self.logger.error(f"Error rendering upcoming game: {e}")
            self._display_error("Display error")
    
    def render_no_games(self, mode: str) -> None:
        """Render message when no games are available."""
        matrix_width = self.display_manager.matrix.width
        matrix_height = self.display_manager.matrix.height
        
        img = Image.new('RGB', (matrix_width, matrix_height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        message = {
            'hockey_live': "No Live Games",
            'hockey_recent': "No Recent Games", 
            'hockey_upcoming': "No Upcoming Games"
        }.get(mode, "No Games")
        
        message_width = draw.textlength(message, font=self.fonts['status'])
        message_x = (matrix_width - message_width) // 2
        message_y = matrix_height // 2
        
        self._draw_text_with_outline(draw, message, (message_x, message_y), self.fonts['status'], fill=(150, 150, 150))
        
        self.display_manager.image = img.copy()
        self.display_manager.update_display()
    
    def _display_error(self, message: str):
        """Display error message."""
        matrix_width = self.display_manager.matrix.width
        matrix_height = self.display_manager.matrix.height
        
        img = Image.new('RGB', (matrix_width, matrix_height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        message_width = draw.textlength(message, font=self.fonts['status'])
        message_x = (matrix_width - message_width) // 2
        message_y = matrix_height // 2
        
        self._draw_text_with_outline(draw, message, (message_x, message_y), self.fonts['status'], fill=(255, 0, 0))
        
        self.display_manager.image = img.copy()
        self.display_manager.update_display()
