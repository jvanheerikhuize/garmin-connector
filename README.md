# garmin-connector

A tool to connect a modern Garmin watch to a Linux laptop and exchange files over USB (MTP) — from the command line or a local web dashboard.

## Features

- **Device discovery** — automatically finds a connected Garmin watch across `/run/user/<uid>/gvfs`, `/media`, and `/mnt`, without manual mount configuration.
- **Status & diagnostics** — connection status, storage capacity, installed Connect IQ apps, and sub-component firmware versions.
- **Read-only filesystem browser** — `ls` and `tree` for exploring the watch's internal storage from the CLI.
- **Course upload** — transfer `.fit`/`.gpx` route files to the watch's `GARMIN/NewFiles/` directory.
- **Web GUI** — an on-demand local dashboard with a Finder-style column-view file browser, drag-and-drop course upload, and an offline vector route/elevation preview.

Everything runs on-demand, exits cleanly when no watch is connected, and ships as a single dependency-free binary.

## Install

Requires Go 1.22+.

```sh
go build -o garmin-connector ./cmd/garmin-connector
# or
go install ./cmd/garmin-connector
```

## Usage

```
garmin-connector <command> [flags]

Commands:
  status   Show connection status of a Garmin watch
  info     Show detailed device diagnostics
  ls       List files on the watch
  tree     Recursively list files on the watch
  upload   Upload a course file to the watch
  web      Launch the web GUI dashboard
```

### Examples

```sh
garmin-connector status                 # human-readable connection status
garmin-connector status --json          # machine-readable status
garmin-connector info --json            # storage, Connect IQ apps, firmware versions
garmin-connector ls GARMIN/Activity      # list a directory
garmin-connector tree --depth 2          # recursive listing
garmin-connector upload route.gpx        # copy a course to GARMIN/NewFiles/
garmin-connector web                     # launch the dashboard at http://127.0.0.1:8080/
```

Every command exits `0` when no watch is connected (a disconnected watch is a valid state, not an error) and supports `--help`.

## Web GUI

`garmin-connector web` starts a local HTTP server (default `127.0.0.1:8080`) and opens it in your default browser. It provides:

- A **Dashboard** with live connection status, storage gauge, firmware versions, and Connect IQ inventory (auto-refreshing).
- A **File Browser** with macOS Finder-style Miller columns, keyboard navigation, and file download.
- An **Upload Course** view with drag-and-drop, extension validation, and an offline route/elevation preview before transfer.

All frontend assets are embedded in the binary; nothing is fetched from the network.

## Development

```sh
go build ./...     # build
go test ./...       # run tests
go vet ./...        # static checks
gofmt -l .           # formatting check (should print nothing)
```

## Design

This repository is developed spec-first: behavior lives under [`specs/`](specs/) and the code in `cmd/`/`internal/` is a generated, derived artifact of those specs. See [`specs/README.md`](specs/README.md) for the working agreement and [`specs/constitution.md`](specs/constitution.md) for the system's purpose, grounding facts/assumptions, and requirements.
