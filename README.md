# Garmin Connector (`garmin-venu-x1`) (Lean MVP)

A lightweight MVP tool to connect to your Garmin Venu (and other watches), view its status, ingest GPX routes, and preview routes directly from the watch.

## Features

- **Connect & View Status**: Detects Garmin watch (via USB Mass Storage or MTP) and shows connection status and course counts in a lean web GUI.
- **Ingest GPX**: Drag and drop GPX files to auto-convert to FIT and sideload directly onto the watch.
- **Course Manager**: List and delete existing `.fit` and `.gpx` files on the watch.
- **Map Preview**: Select a GPX file stored on the watch to preview its path on an interactive Leaflet map.

## Installation

```bash
cd ~/Repos/garmin-venu-x1
uv pip install -e .
```

## Usage

Start the GUI server:
```bash
garmin-connector gui
```
Then open `http://127.0.0.1:8080` in your browser.
