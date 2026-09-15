# Garmin Connector (`garmin-venu-x1`)

A lightweight, cross-platform (Linux, Windows, macOS) MVP tool to connect to your Garmin Venu (and other watches), view its status, ingest GPX routes, and preview routes directly from the watch, wrapped in a Cyberpunk Terminal UI.

## Features

- **Connect & View Status**: Detects Garmin watch (via USB Mass Storage or MTP) and shows connection status and course counts in a lean web GUI.
- **Ingest GPX**: Drag and drop GPX files to auto-convert to FIT and sideload directly onto the watch.
- **Course Manager**: List and delete existing `.fit` and `.gpx` files on the watch.
- **Map Preview**: Select a GPX file stored on the watch to preview its path on an interactive Leaflet map.
- **CYBERCORE Design System**: Styled with [CYBERCORE CSS](https://sebyx07.github.io/cybercore-css/) featuring CRT scanlines, neon glows, glitch effects, chamfered HUD cards, and dark telemetry map layers.

## Installation

```bash
uv pip install -e .
```

## Usage

Start the GUI server using `uv`:
```bash
uv run garmin-connector gui
```

Alternatively, activate the virtual environment first:
```bash
source .venv/bin/activate
garmin-connector gui
```
Then open `http://127.0.0.1:8080` in your browser.
