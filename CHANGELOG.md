# Changelog

All notable changes to this project will be documented in this file.

This project follows "Keep a Changelog" (https://keepachangelog.com/en/1.1.0/), and adheres to "Semantic Versioning" (https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-20

### Added

- Added the `--title` option to `pmp stats` to sort statistics alphabetically by song title.

### Changed

- Song selection statistics now count only songs explicitly selected by the user. Tracks automatically added to the queue and songs selected by default playback no longer inflate selection counts.
- Listening-time tracking now checks playback-position changes against expected playback progress, avoiding counting skipped audio as listening time.
- Improved daemon and IPC lifecycle management with readiness checks, bounded requests, connection timeouts, structured error responses, and graceful shutdown handling.
- Playback runtime now checks for unexpected worker termination and attempts to persist the final session and statistics during shutdown.
- Statistics rendering now sorts entries without modifying the underlying statistics data.

### Fixed

- Fixed the renderer's unresolved `Playlist` annotation, which prevented the CLI from importing.
- Fixed statistics output when only song-selection data is available.

## [0.1.1] - 2026-11-14

### Changed

- Renamed the PyPI package to `platypus-music`. The `pmp` command is unchanged.

## [0.1.0] - 2026-11-14

First public release of PMP.

### Added

- Music source selection with three strategies:
  - "playlist": Select tracks from the current collection.
  - "universal": Rotate between available playlists and root directory tracks.
  - "smart": Prioritize tracks based on listening statistics.
- Independent track ordering with sequential and random modes.
- Runtime commands to change music source and track ordering during playback.
- Playback controls for source selection and track ordering in the interactive interface.
- Unit tests for source selection strategies.

### Changed

- Playback queue management now uses the selected source strategy to determine subsequent tracks.
- Source selection and track ordering are handled independently, allowing different playback configurations.
- Playback behavior now supports preserving already queued tracks when changing the selected source.

### Fixed

- Fixed default playback configuration values when no configuration file exists.
- Fixed the interactive interface's track ordering key binding.
