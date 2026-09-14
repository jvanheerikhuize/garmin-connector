---
id: gui-bootstrap
title: GUI Process Bootstrap & HTTP Shell
tier: skeleton
status: implemented
owners: [jerry]
depends_on: [device-detection]
last_updated: 2026-09-14
---

# GUI Process Bootstrap & HTTP Shell

`src/garmin_connector/gui/{launcher,server}.py`

Depends on: [device-detection](device-detection.md).

## Purpose

Bring up the local web server that everything else (course management, map preview) is served through, and prove the skeleton's core promise: the app starts, serves a page, and that page can find out whether a watch is connected — with nothing crashing if one isn't.

## Scope

**In scope:** process bootstrap (port selection, browser launch, serve loop), static asset serving, the `/api/device` endpoint, and the response/error conventions every other endpoint must follow.

**Out of scope:** course/route endpoints (see [course-management-api](features/course-management-api.md)); the frontend that consumes this API (see [connection-status-shell](connection-status-shell.md) and [gui-course-frontend](features/gui-course-frontend.md)).

## Requirements

### Launcher (`launcher.py`)
- `find_free_port(start_port=8080) -> int`: probes ports `start_port..start_port+49` on `127.0.0.1`, returns the first that refuses a connection (i.e. is free); if none are free in that range, returns `start_port` anyway (caller will fail loudly when binding).
- `open_desktop_window(url)`: tries, in order, `google-chrome`, `chromium-browser`, `chromium`, `brave-browser` in app-window mode (`--app=<url>`) via `subprocess.Popen` (stdout/stderr discarded); on failure of all four (none found on PATH, or launch raised), falls back to `webbrowser.open(url)`.
- `launch_gui(host="127.0.0.1", port=8080, open_browser=True)`:
  - Resolves an actual free port starting from `port` (may differ from the requested port).
  - Starts the HTTP server, prints a banner with the resolved URL.
  - If `open_browser`, opens the browser in a daemon thread after a 0.4s delay (lets the server bind first).
  - Calls `server.serve_forever()`; on `KeyboardInterrupt`, closes the server and exits cleanly (prints shutdown messages, no traceback).

### Server-wide conventions (`server.py`)
- MUST NOT let an exception raised handling one request take down the process or other in-flight requests. `http.server` handles requests synchronously per-connection here (no threading mixin), so requests are inherently serialized — but a per-request exception must still be caught within that request's handler.
- All API responses MUST be JSON, `Content-Type: application/json`.
- Every response MUST include open CORS headers: `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS`, `Access-Control-Allow-Headers: Content-Type`. `OPTIONS` requests get a bare `204 No Content` with those headers.
- Errors use the shape `{"success": false, "error": "<message>"}` with a non-2xx status (400/404/500/503 depending on cause) — except `/api/device` and `/api/courses`, which use their own always-200 shapes (they signal absence-of-device via a `connected: false` field, not an HTTP error; see [course-management-api](features/course-management-api.md) for `/api/courses`).
- Request logging MUST be suppressed (`log_message` overridden to no-op).
- Any unmatched `GET`/`POST`/`DELETE` path MUST return a `404` JSON error `"Not found"`.

### Static file serving
- `GET /` or `GET /index.html` → serves `gui/static/index.html` as `text/html; charset=utf-8`; `404` JSON error if missing.
- `GET /static/<path>` → serves `gui/static/<path>`, MIME type guessed via `mimetypes`; falls back to `application/octet-stream` if unknown.
  - MUST resolve the path and verify it stays within `STATIC_DIR` (`.resolve()` + parent check) before serving — directory traversal outside `static/` is rejected as a `404`.
  - Nonexistent or non-file paths → `404` JSON error.

### `GET /api/device`
- Detect the first device (via [device-detection](device-detection.md)).
- Connected: `{"connected": true, "model_name", "unit_id", "mount_point": str(path), "is_mtp", "mounting": false}`.
- Not connected but `check_raw_usb()` reports a Garmin USB device present: `{"connected": false, "mounting": true, "model_name": null}` (device physically attached, waiting for OS to finish mounting).
- Not connected and no raw USB device: `{"connected": false, "mounting": false, "model_name": null}`.
- MUST always return HTTP 200 — absence of a device is not an error.

## Data Shapes / Interfaces

```
GET /api/device -> 200
  {"connected": true,  "model_name": str, "unit_id": str|null, "mount_point": str, "is_mtp": bool, "mounting": false}
  {"connected": false, "mounting": bool, "model_name": null}
```

## Non-Goals
- No WebSocket/SSE push for device status — clients must poll (see [connection-status-shell](connection-status-shell.md)).
- No HTTPS/TLS — local loopback HTTP only.
- No multi-threaded request handling — one request at a time by design (simplicity over throughput for a single-user local tool).
