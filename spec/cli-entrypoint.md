---
id: cli-entrypoint
title: CLI Entrypoint
tier: skeleton
status: implemented
owners: [jerry]
depends_on: []
last_updated: 2026-09-14
---

# CLI Entrypoint

`src/garmin_connector/cli.py`

## Purpose

The single process entrypoint (`garmin-connector`, registered as a `pyproject.toml` console script) that a user or shell invokes. It exists to dispatch to subcommands — today, exactly one.

## Scope

**In scope:** argument parsing, subcommand dispatch, help text.

**Out of scope:** everything the `gui` subcommand actually does once dispatched (see [gui-bootstrap](gui-bootstrap.md)).

## Requirements

- MUST expose a single top-level parser (`argparse.ArgumentParser`, `prog="garmin-connector"`) with a subparsers group (`dest="command"`).
- MUST register exactly one subcommand today: `gui`.
  - `gui` accepts: `--host` (default `127.0.0.1`), `--port`/`-p` (int, default `8080`), `--no-browser` (flag; when set, suppresses auto-opening a browser).
  - `gui` dispatches to `launch_gui(host=args.host, port=args.port, open_browser=not args.no_browser)`.
- Invoking with no arguments at all (`len(sys.argv) == 1`) MUST print top-level help and exit `0` — MUST NOT error or hang.
- Invoking with an unrecognized subcommand MUST use argparse's default error behavior (prints usage to stderr, exits non-zero) — no custom handling.
- Invoking with a recognized subcommand but no matching `func` attribute set MUST fall back to printing help (defensive branch; in practice every registered subparser sets `func` via `set_defaults`).

## Data Shapes / Interfaces

```
garmin-connector gui [--host HOST] [--port PORT | -p PORT] [--no-browser]
```

## Non-Goals
- No subcommands beyond `gui` today (e.g. no headless `sideload`/`list`/`backup` CLI verbs) — the CLI is a thin launcher for the GUI, not a full CLI tool. Adding one is a new feature spec, not an edit to this file's requirements, since it changes the constitution's "CLI has exactly one subcommand" invariant.
- No config file support — all options are command-line flags with hardcoded defaults.
