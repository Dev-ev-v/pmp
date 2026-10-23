# PMP

## A lightweight, local music player for the terminal.

PMP is an open-source command-line music player built for people who want to listen to their own music without relying on streaming platforms, online accounts, or cloud-based music libraries.

It focuses on local playback, a simple terminal workflow, and keeping your music library under your control.

PMP is currently in alpha. It is usable, actively developed, and not yet tested across every intended platform.

## Features

- Local music library: Scan and organize music stored on your device.
- Playlist organization: Organize music through local directories.
- Search: Find songs and playlists in your library.
- Playback queue: Manage the songs waiting to be played.
- Playback controls: Navigate between tracks, seek within songs, and control playback volume.
- Shuffle and loop: Listen in randomized order or repeat playback.
- Session recovery: Resume a saved playback session.
- Listening statistics: Track playback activity and listening habits.
- Terminal miniplayer: Monitor the current track and playback progress.

PMP is designed for music you already have locally. It does not provide a streaming catalog, host music files, or replace music distribution services.

## Requirements

- Python 3.10 or newer.
- "mpv" (https://mpv.io/), installed separately and available to PMP.
- A local collection of supported audio files.

PMP uses mpv as its playback engine. Installing the Python package alone does not install the external player.

PMP is intended to support Linux, Windows, and macOS, but compatibility has not yet been fully verified on every platform.

## Installation

### From PyPI

Install PMP using pip:

```bash
python -m pip install pmp
```

Make sure mpv is installed separately before attempting playback.

Verify the installation:

```bash
pmp --help
```

### From GitHub

To install a development version, clone the PMP repository and install the local project:

```bash
git clone <repository-url>
cd <repository-directory>
python -m pip install .
```

Replace the placeholders with the actual repository URL and directory name.

Development versions may contain unfinished features or bugs. Use them accordingly.

## Getting started

After installing PMP and mpv, run:

```bash
pmp --help
```

This displays the commands and options available in your installed version.

### Play music

```bash
pmp play
```

If no music directory is configured, PMP will prompt you to configure one. Choose a directory containing supported audio files.

If a music directory is already configured, PMP plays a random track from your library.

To play a specific song or playlist:

```bash
pmp play "My song"
```

### Stop playback

```bash
pmp stop
```

Stops playback and ends the current session.

### Open the miniplayer

```bash
pmp watch
```

Opens a miniplayer for easier playback and queue control.

### View listening statistics

```bash
pmp stats
```

Displays statistics for previously played tracks.

### Reset the session

```bash
pmp reset
```

Use this command to reset the current session if playback gets stuck or behaves unexpectedly.

## Supported audio

PMP is intended for local audio playback. The current implementation recognizes these file extensions:

- MP3 (".mp3")
- M4A (".m4a")
- FLAC (".flac")
- Ogg (".ogg")
- WAV (".wav")

Actual playback compatibility also depends on the codecs and formats supported by the installed mpv build.

Video playback is not currently part of PMP's scope.

## Privacy and philosophy

PMP is built around a simple idea: your local music library should remain yours.

The project aims to provide a lightweight way to play music without requiring a streaming account or depending on a centralized music catalog.

PMP is intended for local playback, not music hosting or distribution. Users are responsible for ensuring that their use of audio files complies with applicable laws and licenses.

## Roadmap

- Replace file paths with stable song identifiers, such as unique IDs.
- Improve and verify support for Windows and macOS.
- Add support for video files.
- Add support for basic audio effects.
- Improve error handling when MPV is misding or fails to start.

## Contributing

Contributions, bug reports, and suggestions are welcome.
