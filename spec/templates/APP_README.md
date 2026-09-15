# Garmin Connector (`garmin-venu-x1`)

A lightning-fast, cross-platform (Linux, Windows, macOS) single-binary CLI tool to connect to your Garmin Venu (and other watches), view its status, ingest GPX routes, and preview routes directly from the watch, featuring an embedded local web GUI wrapped in a Cyberpunk Terminal UI.

## Features

- **Connect & View Status**: Detects Garmin watch (via USB Mass Storage or MTP) and pushes real-time connection telemetry to the GUI via WebSockets.
- **Ingest GPX**: Drag and drop GPX files to auto-convert to FIT and sideload directly onto the watch.
- **Course Manager**: List and delete existing `.fit` and `.gpx` files on the watch.
- **Map Preview**: Select a course stored on the watch to preview its path on an interactive Leaflet map.
- **Single Binary Distribution**: The React frontend is compiled and embedded into the Go binary. No Python, Node.js, or local web servers needed to run.
- **Headless CLI**: Includes subcommands to sideload routes and list courses directly from the terminal without opening a browser.

## Installation

Download the latest binary release for your operating system (macOS, Windows, Linux) from the Releases page, or install via Go:

```bash
go install github.com/jvanheerikhuize/garmin-venu-x1/cmd/garmin-connector@latest
```

## Usage

### 1. Launch the GUI

Start the GUI server and automatically open your browser:
```bash
garmin-connector gui
```
*(By default, this binds to 127.0.0.1:8080. Use `--port` to change).*

### 2. Headless Sideloading

Sideload a GPX file directly to your connected watch:
```bash
garmin-connector sideload my_route.gpx
```

### 3. List Courses

List courses currently on your connected watch:
```bash
garmin-connector list
```
