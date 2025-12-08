# Game Limits Logic Documentation

## Overview

The `upcoming_games_to_show` and `recent_games_to_show` settings control how many games are displayed, but their behavior differs depending on whether favorite teams are configured.

## Behavior Modes

### Mode 1: With Favorite Teams (Per-Team Limit)

When favorite teams are configured and `favorite_teams_only: true`, the limits apply **per team**.

**Formula:**
```
Total Games = (Number of Favorite Teams) × (Games Per Team)
```

**Examples:**
- 2 favorite teams, `upcoming_games_to_show: 1` → **2 games total** (1 per team)
- 3 favorite teams, `upcoming_games_to_show: 2` → **Up to 6 games total** (2 per team)
- 4 favorite teams, `recent_games_to_show: 3` → **Up to 12 games total** (3 per team)

**How it works:**
1. For each favorite team, find all games where that team is playing
2. Sort games by time (earliest first for upcoming, most recent first for recent)
3. Take the first N games for that team (where N = `upcoming_games_to_show` or `recent_games_to_show`)
4. Combine all teams' games into one list
5. Remove duplicates (in case a game involves multiple favorite teams)
6. Sort the final list chronologically

**Use Case:** You want to see the next 2 upcoming games for each of your 3 favorite teams, giving you up to 6 games total.

### Mode 2: Without Favorite Teams (Total Limit)

When no favorite teams are configured or `favorite_teams_only: false`, the limits apply to the **total number of games** across all teams.

**Formula:**
```
Total Games = Limit Value (capped at configured maximum)
```

**Examples:**
- No favorite teams, `upcoming_games_to_show: 1` → **1 game total** (the next scheduled game)
- No favorite teams, `upcoming_games_to_show: 5` → **5 games total** (the next 5 scheduled games)
- No favorite teams, `recent_games_to_show: 10` → **10 games total** (the 10 most recent games)

**How it works:**
1. Collect all games (upcoming or recent, depending on mode)
2. Sort games by time (earliest first for upcoming, most recent first for recent)
3. Take the first N games from the sorted list (where N = the limit value)

**Use Case:** You want to see only the next 1 upcoming game across the entire league, not the whole season.

## Configuration Examples

### Example 1: Per-Team Behavior
```json
{
  "hockey-scoreboard": {
    "nhl": {
      "enabled": true,
      "favorite_teams": ["TB", "TOR", "BOS"],
      "favorite_teams_only": true,
      "upcoming_games_to_show": 2
    }
  }
}
```
**Result:** Shows up to 6 upcoming games (2 per team × 3 teams)

### Example 2: Total Limit Behavior
```json
{
  "hockey-scoreboard": {
    "nhl": {
      "enabled": true,
      "favorite_teams": [],
      "favorite_teams_only": false,
      "upcoming_games_to_show": 1
    }
  }
}
```
**Result:** Shows only 1 upcoming game total (the next scheduled game)

### Example 3: Mixed Configuration
```json
{
  "hockey-scoreboard": {
    "nhl": {
      "enabled": true,
      "favorite_teams": ["TB", "TOR"],
      "favorite_teams_only": true,
      "upcoming_games_to_show": 1,
      "recent_games_to_show": 2
    },
    "ncaa_mens": {
      "enabled": true,
      "favorite_teams": [],
      "favorite_teams_only": false,
      "upcoming_games_to_show": 3,
      "recent_games_to_show": 5
    }
  }
}
```
**Result:**
- NHL upcoming: 2 games (1 per team × 2 teams)
- NHL recent: 4 games (2 per team × 2 teams)
- NCAA Men's upcoming: 3 games total (no favorites, total limit)
- NCAA Men's recent: 5 games total (no favorites, total limit)

## Dynamic Duration Integration

Dynamic duration works seamlessly with both modes:

- **With per-team limits:** Cycles through all games from all favorite teams
- **With total limits:** Cycles through the limited number of games

**Example with dynamic duration:**
```json
{
  "hockey-scoreboard": {
    "nhl": {
      "favorite_teams": ["TB", "TOR", "BOS"],
      "favorite_teams_only": true,
      "upcoming_games_to_show": 2,
      "dynamic_duration": {
        "modes": {
          "upcoming": {
            "enabled": true
          }
        }
      }
    }
  }
}
```
**Behavior:** Shows each of the 6 upcoming games once, then moves to the next mode.

## Edge Cases

### Duplicate Games
If a game involves multiple favorite teams (e.g., TB vs TOR and both are favorites), the game appears only once in the final list. Duplicates are automatically removed.

### Insufficient Games
If a favorite team has fewer games than the limit (e.g., only 1 upcoming game but limit is 2), only the available games are shown for that team.

### No Games Available
If no games match the criteria, the mode returns `False` and the display controller skips to the next mode.

## Summary Table

| Scenario | Favorite Teams | Limit Value | Result |
|----------|---------------|-------------|--------|
| Per-team | 3 teams | `upcoming_games_to_show: 2` | Up to 6 games (2 per team) |
| Per-team | 2 teams | `recent_games_to_show: 1` | 2 games (1 per team) |
| Total | None | `upcoming_games_to_show: 1` | 1 game total |
| Total | None | `upcoming_games_to_show: 5` | 5 games total |
| Per-team | 1 team | `upcoming_games_to_show: 3` | Up to 3 games (3 for that team) |

## Best Practices

1. **For focused viewing:** Use favorite teams with per-team limits (e.g., `upcoming_games_to_show: 1` with 2-3 teams)
2. **For broad overview:** Use total limits without favorites (e.g., `upcoming_games_to_show: 5`)
3. **For comprehensive coverage:** Use higher per-team limits with dynamic duration enabled
4. **For minimal display:** Use `upcoming_games_to_show: 1` without favorites to show only the next game

