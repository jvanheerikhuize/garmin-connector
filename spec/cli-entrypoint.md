---
id: cli-entrypoint
title: CLI Entrypoint
tier: skeleton
status: implemented
owners: [jerry]
depends_on: []
last_updated: 2026-09-15
---

# CLI Entrypoint

`cmd/garmin-connector/main.go`

## Purpose

The single process entrypoint (`garmin-connector`) that a user or shell invokes. It uses the `cobra` library to dispatch subcommands.

## Scope

**In scope:** argument parsing, subcommand dispatch, help text.

**Out of scope:** everything the subcommands actually do once dispatched (see [gui-bootstrap](gui-bootstrap.md), [device-manager](features/device-manager.md)).

## Requirements

- MUST expose a root command (`garmin-connector`) using `github.com/spf13/cobra`.
- MUST register the following subcommands:
  - `gui`: Launches the web server.
    - Accepts: `--host` (default `127.0.0.1`), `--port`/`-p` (int, default `8080`), `--no-browser` (flag; when set, suppresses auto-opening a browser).
    - Dispatches to `api.Serve(host, port, !no_browser)`.
  - `list`: Connects to the watch headlessly and lists courses.
  - `sideload`: Accepts a `.gpx` file path, converts it to `.fit`, and pushes it to the watch headlessly.
- Invoking with no arguments at all MUST print top-level help and exit `0` — MUST NOT error or hang.
- Invoking with an unrecognized subcommand MUST use Cobra's default error behavior (prints usage to stderr, exits non-zero).

## Data Shapes / Interfaces

```
garmin-connector [command]

Available Commands:
  gui         Start the web GUI and local server
  list        List courses on the connected Garmin watch
  sideload    Convert and sideload a GPX file to the connected watch
  help        Help about any command

Flags:
  -h, --help   help for garmin-connector
```

## Non-Goals
- No config file support — all options are command-line flags with hardcoded defaults.
