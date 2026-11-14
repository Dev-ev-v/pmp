# Changelog

All notable changes to this project will be documented in this file.

This project follows "Keep a Changelog" (https://keepachangelog.com/en/1.1.0/), and adheres to "Semantic Versioning" (https://semver.org/spec/v2.0.0.html).

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