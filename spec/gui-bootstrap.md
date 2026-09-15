---
id: gui-bootstrap
title: GUI Process Bootstrap & HTTP Shell
tier: skeleton
status: implemented
owners: [jerry]
depends_on: [device-detection]
last_updated: 2026-09-15
---

# GUI Process Bootstrap & HTTP Shell

`src/garmin_connector/gui/{launcher,server}.py`

Depends on: [device-detection](device-detection.md).

## Purpose

Bring up the local web server that everything else is served through.

## Scope

**In scope:** process bootstrap, static asset serving, `/api/device` endpoint.

## Requirements

### Launcher (`launcher.py`)
- `find_free_port(start_port=8080) -> int` — returns the first port ≥ `start_port` that can be bound on `127.0.0.1`; raises `RuntimeError` if none is found before 65535.
- `open_desktop_window(url)` — opens `url` in the user's default browser via stdlib `webbrowser.open`; failures are swallowed (a missing browser must not stop the server).
- `launch_gui(host="127.0.0.1", port=8080, open_browser=True)` — resolves `port` through `find_free_port`, builds the server via `run_gui_server(host, port)`, prints `Garmin Course Uploader running at http://<host>:<port>/` (plus a Ctrl+C hint), opens the browser if `open_browser`, then `serve_forever()`s until `KeyboardInterrupt`, closing the socket on exit.

### Server-wide conventions (`server.py`)
- `run_gui_server(host="127.0.0.1", port=8080) -> http.server.HTTPServer` — constructs and binds the server (handler class below) **without** starting it; callers (`launch_gui`, tests) call `serve_forever()`/`shutdown()` themselves. This name is pinned by `tests/test_gui_server.py`.
- Catch per-request exceptions and return JSON error bodies (`{"success": false, "error": "..."}`).
- All API responses MUST be JSON. Unknown paths → `404` JSON error.
- Open CORS headers (`Access-Control-Allow-Origin: *`, plus `-Methods: GET, POST, DELETE, OPTIONS` and `-Headers: Content-Type`); `OPTIONS` on any path answers `204` with those headers.
- Request logging suppressed (`log_message` overridden to a no-op).
- Query strings are ignored for routing.

### Static file serving
- `GET /` or `GET /index.html` → serves `index.html`.
- `GET /static/<path>` → serves files from `static/`, `Content-Type` guessed via `mimetypes`; paths that resolve outside `static/` or to a non-file → `404` JSON error.

### `GET /api/device`
- Detect the first device (via `GarminDeviceDetector.get_first_device()`).
- Connected: `{"connected": true, "model_name": "...", "unit_id": "...", "mount_point": "..."}`.
- Not connected: `{"connected": false, "model_name": null}`.
- MUST always return HTTP 200.

## Data Shapes / Interfaces

```
GET /api/device -> 200
  {"connected": true, "model_name": str, "unit_id": str|null, "mount_point": str}
  {"connected": false, "model_name": null}
```
