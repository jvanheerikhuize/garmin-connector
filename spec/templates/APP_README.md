# Garmin Connector (`garmin-venu-x1`)

A tool to connect a modern garmin watch to a laptop to exchange files over a USB connection.

## Features

- **Device Detection**: Detects connected Garmin watches over USB/MTP and extracts model and device metadata.
- **Single Binary Distribution**: Compiles to a single, lightweight Go binary with zero runtime dependencies.

## Installation

Download the latest binary release for Linux from the Releases page, or install via Go:

```bash
go install github.com/jvanheerikhuize/garmin-venu-x1/cmd/garmin-connector@latest
```

## Usage

### Check Watch Status

Check if a Garmin watch is connected and view its details:
```bash
garmin-connector status
```

For JSON output:
```bash
garmin-connector status --json
```
