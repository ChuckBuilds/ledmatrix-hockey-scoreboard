# Changelog

## [1.0.2] - 2025-10-20

### Added
- **Proper Font Loading**: Load PressStart2P and 4x6 fonts matching original managers
- **Logo Loading**: Full logo path resolution with case-insensitive matching
- **Logo Sizing**: Logos properly scaled to display dimensions (width/height * 1.5)
- **Scoreboard Rendering**: Professional scoreboard layout with team logos, scores, and status
- **Text Outline**: Text rendering with black outlines for better readability

### Changed
- **Replaced Placeholder**: Removed TODO comments and placeholder text rendering
- **Visual Parity**: Now matches original hockey manager layout and appearance

## [1.0.1] - 2025-10-20

### Fixed
- **Live Priority Integration**: Implemented `has_live_content()` method to properly integrate with display controller
- **Display Logic**: Plugin now only shows "hockey_live" mode when there are actual live games
- **No More "No Live Games"**: Plugin won't be called when there are no live games to display
- **Mode Filtering**: Added `get_live_modes()` to only show live mode during live priority takeover

## [1.0.0] - 2025-10-19

### Initial
- Initial release with basic hockey scoreboard functionality

