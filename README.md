# Garmin Connector (`garmin-venu-x1`)

### Purpose
To provide a lightweight, cross-platform (Linux, Windows, macOS) local web tool that seamlessly connects to Garmin watches over USB. Wrapped in a Cyberpunk Terminal UI, it allows users to view connection status, automatically convert and sideload GPX routes to FIT format, manage existing files on the watch, and preview courses on an interactive map.

### Goal
To deliver a strictly spec-driven, fault-tolerant MVP that adheres to a "walking skeleton" architecture. The repository serves as a blueprint for single-shot AI code generation, enforcing rigid architectural boundaries—keeping device detection read-only, isolating HTTP concerns, and maintaining zero-dependency frontend code—so the resulting application degrades gracefully and remains resilient.

*(Note: This repository currently serves exclusively as a specification corpus. The code implementation is generated strictly based on the rules defined in the `spec/` directory.)*
## Features

- **Connect & View Status**: Detects Garmin watch (via USB Mass Storage or MTP) and shows connection status and course counts in a lean web GUI.
- **Ingest GPX**: Drag and drop GPX files to auto-convert to FIT and sideload directly onto the watch.
- **Course Manager**: List and delete existing `.fit` and `.gpx` files on the watch.
- **Map Preview**: Select a GPX file stored on the watch to preview its path on an interactive Leaflet map.
- **CYBERCORE Design System**: Styled with [CYBERCORE CSS](https://sebyx07.github.io/cybercore-css/) featuring CRT scanlines, neon glows, glitch effects, chamfered HUD cards, and dark telemetry map layers.

## Installation

```bash
cd ~/Repos/garmin-venu-x1
uv pip install -e .
```

*Note: For the best experience, it's recommended to use a [Nerd Font](https://www.nerdfonts.com/) (e.g. FiraCode Nerd Font, Hack Nerd Font, JetBrainsMono Nerd Font) installed on your system for the UI icons to render perfectly.*

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
