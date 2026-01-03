-----------------------------------------------------------------------------------
### Connect with ChuckBuilds

- Show support on Youtube: https://www.youtube.com/@ChuckBuilds
- Stay in touch on Instagram: https://www.instagram.com/ChuckBuilds/
- Want to chat or need support? Reach out on the ChuckBuilds Discord: https://discord.com/invite/uW36dVAtcT
- Feeling Generous? Support the project:
  - Github Sponsorship: https://github.com/sponsors/ChuckBuilds
  - Buy Me a Coffee: https://buymeacoffee.com/chuckbuilds
  - Ko-fi: https://ko-fi.com/chuckbuilds/ 

-----------------------------------------------------------------------------------

# Hockey Scoreboard Plugin

Display live, recent, and upcoming hockey games across NHL, NCAA Men's, and NCAA Women's hockey on your LED matrix.


Recent Game:

<img width="768" height="192" alt="led_matrix_1764889670771" src="https://github.com/user-attachments/assets/1d32b4d9-7d01-4cb2-896b-bc9c889bf188" />

Upcoming Game:

<img width="768" height="192" alt="led_matrix_1764889695301" src="https://github.com/user-attachments/assets/5e6dd53c-0486-4d42-bdaa-6d486729bcc4" />




## Features

- **Multi-League Support**: NHL, NCAA Men's Hockey, NCAA Women's Hockey
- **Live Game Tracking**: Real-time scores, periods, time remaining
- **Recent Games**: View recently completed game results
- **Upcoming Games**: See scheduled games with start times
- **Favorite Teams**: Prioritize your favorite teams across all leagues
- **Power Play Indicators**: Highlight power play situations
- **Shots on Goal**: Optional SOG statistics display
- **Team Logos**: Display team logos when available
- **Background Data Fetching**: Efficient API calls with caching
- **Font Customization**: Override fonts via Web UI

## Requirements

- LEDMatrix 2.0.0+
- Display: Minimum 64x32 pixels (recommended)
- No API key required (uses ESPN public API)
- Internet connection for live data


#### League Selection

- **`leagues.nhl`**: Enable NHL games (default: true)
- **`leagues.ncaa_mens`**: Enable NCAA Men's Hockey (default: false)
- **`leagues.ncaa_womens`**: Enable NCAA Women's Hockey (default: false)

  (note: College Club Hockey is not tracked - team like UGA does not have D1 hockey and cannot be shown)

Enable multiple leagues to see games from all selected leagues in rotation.

#### Display Modes

- **`display_modes.hockey_live`**: Show live games in progress (default: true)
- **`display_modes.hockey_recent`**: Show recently completed games (default: true)
- **`display_modes.hockey_upcoming`**: Show upcoming scheduled games (default: true)

#### Favorite Teams

Specify team abbreviations for each league:

```json
"favorite_teams": {
  "nhl": ["TB", "TOR", "BOS", "DET"],
  "ncaa_mens": ["BU", "BC", "MICH"],
  "ncaa_womens": ["WISC", "MINN"]
}
```


#### Display Settings

- **`prioritize_favorites`**: Show favorite team games first (default: true)
- **`show_shots_on_goal`**: Display SOG statistics (default: false)
- **`show_powerplay`**: Highlight power play situations (default: true)
- **`update_interval`**: Data refresh interval in seconds (15-300, default: 60)
- **`display_duration`**: How long to show each game in seconds (5-60, default: 15)

quest priority 1-5, where 1 is highest (default: 2)

## Display Modes

### Live Games (`hockey_live`)

Shows games currently in progress with:
- Current score
- Period (P1, P2, P3, OT, OT2, etc.)
- Time remaining in period
- Power play indicator (if enabled)
- Shots on goal (if enabled)

### Recent Games (`hockey_recent`)

Shows completed games from the last X hours with:
- Final score
- Game status ("Final", "Final/OT", "Final/SO")
- Team logos

### Upcoming Games (`hockey_upcoming`)

Shows scheduled games for the next X hours with:
- Game start time
- Venue information
- Team matchup

## Setup Instructions

### 1. Install Plugin

Install from the Plugin Store in the LEDMatrix Web UI:

1. Go to Plugin Store tab
2. Search for "Hockey Scoreboard"
3. Click Install
4. Configure via Plugin Configuration page

### 2. Configure Leagues

Enable the leagues you want to track:

- **NHL Only**: Set `leagues.nhl: true`, others false
- **All Leagues**: Set all to true
- **NCAA Only**: Enable `ncaa_mens` and/or `ncaa_womens`

### 3. Add Favorite Teams

Add your favorite team abbreviations to the `favorite_teams` object for each league. Games involving these teams will be shown first if `prioritize_favorites` is enabled.

### 4. Adjust Display Settings

- Set `display_duration` based on how many games you expect (shorter = more games shown)
- Adjust `update_interval` based on desired freshness (60s recommended for live games)
- Enable/disable display modes based on preference

### 5. Enable Plugin

Make sure `enabled: true` in the configuration and the plugin is activated in the rotation.


## Troubleshooting

**No games showing:**
- Check that at least one league is enabled in config
- Verify the season is active for enabled leagues
- Check `recent_games_hours` and `upcoming_games_hours` settings
- Ensure internet connection is working

**Games not updating:**
- Check `update_interval` setting
- Verify API is responding (check logs)
- Try clearing cache: restart plugin or clear cache manually
- Check background service is enabled

**Favorite teams not showing:**
- Verify team abbreviations are correct (case-sensitive)
- Ensure `prioritize_favorites` is true
- Check that favorite teams have games in current time window

**Logos not displaying:**
- Verify logo assets are available in LEDMatrix installation
- Check `assets/sports/nhl_logos` and `assets/sports/ncaa_logos` directories
- Some NCAA teams may not have logos available

**Power play not showing:**
- Enable `show_powerplay` in config
- Verify ESPN API includes situation data (may not be available for all leagues)

**SOG not accurate:**
- Enable `show_shots_on_goal` in config
- ESPN API may have delayed SOG updates
- Some leagues may not provide SOG data

## Advanced Configuration

### Custom Fonts

Override default fonts via config or Web UI:

```json
"fonts": {
  "team_name": {
    "family": "press_start",
    "size": 10,
    "color": "#FFFFFF"
  },
  "score": {
    "family": "press_start",
    "size": 12,
    "color": "#FFC800"
  },
  "status": {
    "family": "four_by_six",
    "size": 6,
    "color": "#00FF00"
  }
}
```

### Layout Customization

The plugin supports fine-tuning element positioning for custom display sizes. All offsets are relative to the default calculated positions, allowing you to adjust elements without breaking the layout.

#### Accessing Layout Settings

Layout customization is available in the web UI under the plugin configuration section:
1. Navigate to **Plugins** → **Hockey Scoreboard** → **Configuration**
2. Expand the **Customization** section
3. Find the **Layout Positioning** subsection

#### Offset Values

- **Positive values**: Move element right (x_offset) or down (y_offset)
- **Negative values**: Move element left (x_offset) or up (y_offset)
- **Default (0)**: No change from calculated position

#### Available Elements

- **home_logo**: Home team logo position (x_offset, y_offset)
- **away_logo**: Away team logo position (x_offset, y_offset)
- **score**: Game score position (x_offset, y_offset)
- **status_text**: Status/period text position (x_offset, y_offset)
- **date**: Game date position (x_offset, y_offset)
- **time**: Game time position (x_offset, y_offset)
- **records**: Team records/rankings position (away_x_offset, home_x_offset, y_offset)

#### Example Adjustments

**Move logos inward for smaller displays:**
```json
{
  "customization": {
    "layout": {
      "home_logo": { "x_offset": -5 },
      "away_logo": { "x_offset": 5 }
    }
  }
}
```

**Adjust score position:**
```json
{
  "customization": {
    "layout": {
      "score": { "x_offset": 0, "y_offset": -2 }
    }
  }
}
```

**Shift records upward:**
```json
{
  "customization": {
    "layout": {
      "records": { "y_offset": -3 }
    }
  }
}
```

#### Display Size Compatibility

Layout offsets work across different display sizes. The plugin calculates default positions based on your display dimensions, and offsets are applied relative to those defaults. This ensures compatibility with various LED matrix configurations.

### Multi-League Strategy

Enable all three leagues for comprehensive coverage:

```json
"leagues": {
  "nhl": true,
  "ncaa_mens": true,
  "ncaa_womens": true
}
```

Games from all leagues will be mixed and sorted by:
1. Live games first
2. Favorite teams (if enabled)
3. Start time

## Data Source

This plugin uses the **ESPN public API** for all hockey data:

- **NHL**: `https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard`
- **NCAA M**: `https://site.api.espn.com/apis/site/v2/sports/hockey/mens-college-hockey/scoreboard`
- **NCAA W**: `https://site.api.espn.com/apis/site/v2/sports/hockey/womens-college-hockey/scoreboard`

**Note**: No API key required. Please use responsibly and respect ESPN's rate limits.

## Examples

### NHL Only Configuration

```json
{
  "enabled": true,
  "leagues": {
    "nhl": true,
    "ncaa_mens": false,
    "ncaa_womens": false
  },
  "favorite_teams": {
    "nhl": ["TB", "TOR", "BOS"]
  },
  "display_modes": {
    "hockey_live": true,
    "hockey_recent": true,
    "hockey_upcoming": false
  },
  "update_interval": 60,
  "display_duration": 15
}
```

### NCAA Men's Only Configuration

```json
{
  "enabled": true,
  "leagues": {
    "nhl": false,
    "ncaa_mens": true,
    "ncaa_womens": false
  },
  "favorite_teams": {
    "ncaa_mens": ["BU", "BC", "MICH", "WISC"]
  },
  "display_modes": {
    "hockey_live": true,
    "hockey_recent": true,
    "hockey_upcoming": true
  },
  "upcoming_games_hours": 168,
  "update_interval": 120
}
```

### All Leagues Configuration

```json
{
  "enabled": true,
  "leagues": {
    "nhl": true,
    "ncaa_mens": true,
    "ncaa_womens": true
  },
  "favorite_teams": {
    "nhl": ["TB", "DET"],
    "ncaa_mens": ["MICH"],
    "ncaa_womens": ["WISC"]
  },
  "prioritize_favorites": true,
  "show_shots_on_goal": true,
  "show_powerplay": true,
  "display_modes": {
    "hockey_live": true,
    "hockey_recent": true,
    "hockey_upcoming": true
  }
}
```

## Integration Notes

### Base Classes

This plugin uses LEDMatrix base classes:
- `Hockey` - Base hockey functionality
- `HockeyLive` - Live game display logic
- `SportsRecent` - Recent games display
- `SportsUpcoming` - Upcoming games display

These are imported from the main LEDMatrix installation at `src/base_classes/`.

### Caching

The plugin uses LEDMatrix's `CacheManager` to cache API responses:
- Cache duration: 5 minutes for live data
- Cache key format: `hockey_{league}_{date}`
- Automatic cache invalidation on date change

### Background Service

Uses LEDMatrix's `BackgroundDataService` for:
- Non-blocking API requests
- Automatic retries on failure
- Request prioritization
- Timeout handling

## Performance

### Resource Usage

- **CPU**: Low (background fetching, cached data)
- **Memory**: ~5-10MB for game data
- **Network**: ~1-5 KB per API call per league
- **API Calls**: 3 leagues × 12 calls/hour = 36 calls/hour (max)

### Optimization Tips

1. **Disable Unused Leagues**: Only enable leagues you follow
2. **Increase Update Interval**: Use 120-300s during off-season
3. **Reduce Time Windows**: Lower `recent_games_hours` and `upcoming_games_hours`
4. **Enable Caching**: Keep `background_service.enabled: true`

## License

GPL-3.0 License - see main LEDMatrix repository for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ChuckBuilds/ledmatrix-plugins/issues)
- **Documentation**: [LEDMatrix Wiki](https://github.com/ChuckBuilds/LEDMatrix/wiki)
- **Community**: [Discussions](https://github.com/ChuckBuilds/LEDMatrix/discussions)

---

**Version**: 1.0.0  
**Author**: ChuckBuilds  
**Category**: Sports  
**Tags**: hockey, nhl, ncaa, sports, scoreboard, live-scores

