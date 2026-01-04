# Changelog

All notable changes to GC2 Connect Desktop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-03

### Added

#### Open Range Feature
- Built-in 3D driving range simulator - practice without needing GSPro
- Physics-accurate ball flight using Nathan model + WSU aerodynamics
- Realistic bounce and roll behavior with configurable surface types
- Real-time shot data display (carry, total, offline, max height, flight time)
- Phase indicators showing ball state (Flight, Bounce, Rolling, Stopped)
- Trajectory tracing with phase-colored paths:
  - Green for flight
  - Orange for bounce
  - Blue for rolling
- Distance markers at 50, 100, 150, 200, 250, 300 yards
- Target greens at common distances

#### Mode Switching
- Toggle between GSPro Mode and Open Range Mode
- Seamless switching without restarting the app
- Mode preference persisted between sessions
- Shot history works in both modes

#### Settings (v2 Schema)
- Environmental conditions (temperature, elevation, humidity, wind)
- Surface type selection (Fairway, Rough, Green)
- Trajectory visibility toggle
- Camera follow toggle
- Automatic migration from v1 to v2 settings schema

#### Testing Infrastructure
- GC2 USB packet simulator for hardware-free testing
- Mock GSPro server with configurable responses
- Time controller for deterministic test timing
- Pre-built test scenarios for common patterns
- End-to-end tests for complete user flows

#### Developer Experience
- Pre-commit hooks for linting and type checking
- CONTRIBUTING.md with development guidelines
- Comprehensive test coverage

### Changed

- Settings schema version bumped to v2
- README updated with Open Range documentation
- Project structure reorganized with services layer

### Fixed

- GSPro connection improvements (TCP_NODELAY, proper buffer management)
- Graceful shutdown handling for connections
- Ball status (0M message) parsing for ready/ball detected indicators
- Shot validation to match gc2_to_TGC reference implementation

## [1.0.0] - 2024-12-30

### Added

- Initial release
- USB connection to GC2 launch monitor
- GSPro Open Connect API v1 integration
- Real-time shot data display
- Ball status indicators (ready/ball detected)
- Shot history tracking
- CSV export for shot data
- Mock mode for testing without hardware
- Persistent settings (platform-specific locations)
- Auto-reconnection with exponential backoff

### Platform Support

- macOS 11.0+
- Linux (Ubuntu 20.04+, Fedora 34+)

[1.1.0]: https://github.com/samiur/gc2-connect-desktop/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/samiur/gc2-connect-desktop/releases/tag/v1.0.0
