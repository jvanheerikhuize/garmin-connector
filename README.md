# garmin-venu-x1

A lightweight, Linux-first tool to connect to a Garmin Venu (or compatible) watch over USB, view its connection status, ingest GPX routes (auto-converted to Garmin FIT courses), manage the course files on the watch, and preview a selected course's path on a map — all from a local web GUI with a Cyberpunk Terminal look.

The behaviour of this project is defined by the specifications under [`spec/`](spec/README.md); the code is generated from them.

## Install

Requires Python 3.10+.

```bash
uv venv && uv pip install -e ".[dev]"
# or
pip install -e ".[dev]"
```

## Usage

Plug the watch in over USB, wait for it to mount, then:

```bash
garmin-connector gui                # starts on http://127.0.0.1:8080 and opens your browser
garmin-connector gui --no-browser   # just print the URL
garmin-connector gui --port 9000    # pick a different port (falls forward if busy)
```

In the GUI:

1. The header shows whether a watch is connected (polled every 3 seconds).
2. **Ingest Route** converts a `.gpx` file to `.fit` and drops it in the watch's `GARMIN/NEWFILES/` folder, where the watch picks it up on its next sync.
3. **Map** previews a course's track on the map; **Delete** removes it from the watch.

## Development

```bash
pytest
```

`tests/test_skeleton.py` covers the walking skeleton (server start, `/api/device`, index page); the remaining tests cover the converter, device manager and course API.
