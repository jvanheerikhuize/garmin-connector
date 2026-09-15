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
- `find_free_port(start_port=8080) -> int`
- `open_desktop_window(url)`
- `launch_gui(host="127.0.0.1", port=8080, open_browser=True)`

### Server-wide conventions (`server.py`)
- Catch per-request exceptions and return JSON error bodies.
- All API responses MUST be JSON.
- Open CORS headers.
- Request logging suppressed.

### Static file serving
- `GET /` or `GET /index.html` → serves `index.html`.
- `GET /static/<path>` → serves files from `static/`.

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
