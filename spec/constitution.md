# Constitution — Walking Skeleton & Invariants

## 1. Purpose

A lightweight, cross-platform (Linux-first) tool to connect to a Garmin Venu (or compatible) watch over USB, view connection status, ingest GPX routes (auto-converted to FIT), manage course files on the watch, and preview a selected course's path on a map — delivered as a local web GUI with a Cyberpunk Terminal aesthetic.

## 2. Walking skeleton

The thinnest end-to-end path that must always work, in order:

1. `garmin-connector gui` (CLI entrypoint) starts an embedded HTTP server on a free local port and opens it in a browser/app window.
2. The served page polls `GET /api/device` to detect whether a Garmin watch is connected.
3. Device detection scans known Linux mount locations (GVFS/MTP and USB mass-storage media roots) for a `GARMIN/` directory.
4. The GUI reflects connection state (disconnected / mounting / connected) without crashing regardless of whether a watch is attached.

Everything else (course listing, ingest, delete, map preview, MTP direct fallback) is a **feature** layered on this skeleton. The skeleton itself must keep working even if every feature above it is removed.

## 3. Architecture boundaries (non-negotiable)

```
cli.py                     — argparse entrypoint, dispatches to gui launcher
gui/launcher.py            — process bootstrap: free-port selection, browser/app-window launch, serve_forever loop
gui/server.py              — stdlib http.server request handler; ALL HTTP/JSON API surface lives here
gui/static/                — static frontend: index.html, app.js, styles.css, cybercore.min.css (no build step, no framework)
device/detector.py         — read-only filesystem discovery of connected Garmin device(s); no mutation
device/manager.py          — course file operations (list/sideload/delete/backup) against a detected device
device/mtp_client.py       — standalone, self-contained direct USB/PTP client; NOT currently wired into manager.py or server.py
converter/gpx_parser.py    — GPX XML -> CourseData (pure parsing, stdlib ElementTree, no gpxpy dependency despite it being installed)
converter/fit_encoder.py   — CourseData -> Garmin .FIT binary (pure Python, no external FIT library)
converter/gpx_to_fit.py    — glue: reads a GPX file, encodes it, writes a .FIT file
```

Rules:
- **`device/detector.py` is read-only.** It must never write, move, or delete anything on the watch or host filesystem.
- **`converter/*` has zero device knowledge.** It only ever deals with in-memory data (`CourseData`, GPX text, FIT bytes) and local file I/O — never touches `device/*`.
- **`gui/server.py` is the only place HTTP concerns exist.** `device/*` and `converter/*` must remain usable as a plain Python library with no HTTP/JSON dependency.
- **`gui/static/*` has no build step.** Plain HTML/CSS/JS served as-is from disk; no bundler, no npm dependency, no transpilation.
- **The CLI has exactly one subcommand today: `gui`.** Any new subcommand is a feature-level spec addition, not a constitution change.

## 4. Tech stack (fixed)

- Python ≥ 3.10, packaged via `setuptools`, `src/` layout (`src/garmin_connector/`).
- Runtime dependencies: `gpxpy`, `fitparse` (used only for reading `.fit` files back out in `gui/server.py`'s fetch-course endpoint — not for writing).
- Dev dependency: `pytest`.
- No web framework (Flask/FastAPI/etc.) — `http.server.HTTPServer` + `BaseHTTPRequestHandler` only.
- No frontend framework/bundler — vanilla JS, Leaflet.js (CDN) for mapping, CYBERCORE CSS (vendored `cybercore.min.css`) for styling, Google Fonts (Exo 2, JetBrains Mono, Orbitron, Rajdhani) via CDN.
- Optional runtime dependency `PyGObject`/`gi` (GIO/GVFS bindings) and the `gio` CLI, used opportunistically for MTP transfers on Linux; both have graceful fallbacks.
- Optional runtime dependency `pyusb`, used only by `device/mtp_client.py` (currently unwired — see feature spec).

## 5. Cross-cutting invariants

- **Never crash the server process on a per-request error.** Every API handler must catch exceptions and return a JSON error body (`{"success": false, "error": "..."}` or `{"connected": false, ...}`) with an appropriate HTTP status, not propagate.
- **No device present is not an error state.** Every endpoint must degrade gracefully (empty course list, `connected: false`, etc.) rather than 500 when no watch is attached.
- **Garmin string field limits are respected wherever names are written into FIT data**: course name ≤ 15 bytes UTF-8, course point name ≤ 15 bytes UTF-8 (16-byte field, null-terminated).
- **Filesystem paths under a device's `GARMIN/` directory are case-insensitive matched** (`NEWFILES`, `COURSES`, `ACTIVITY`) since Garmin devices are inconsistent about casing across models/firmware.
- **CORS is fully open** (`Access-Control-Allow-Origin: *`) on all API responses — this is a local-only tool, not intended for multi-origin exposure.
- **The GUI must never assume a device stays connected between requests.** Every mutating endpoint re-resolves `GarminDeviceDetector.get_first_device()` itself rather than trusting cached state.

## 6. Explicitly out of scope (until a feature spec says otherwise)

- Windows/macOS device detection (candidate mount roots are Linux-specific).
- Multiple simultaneously connected watches (only the first detected device is ever used).
- Activity file (`.fit` in `ACTIVITY/`) download/analysis — only `COURSES/` and `NEWFILES/` are managed.
- Authentication/multi-user access to the GUI.
- The direct MTP/PTP client (`device/mtp_client.py`) is not called from anywhere else in the app today; it is a standalone capability, not part of the skeleton's transfer path.
