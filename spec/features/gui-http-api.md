# Feature: GUI HTTP/JSON API & Server

`src/garmin_connector/gui/{server,launcher}.py`

Depends on: [device-detection](device-detection.md), [device-manager](device-manager.md), [gpx-fit-conversion](gpx-fit-conversion.md).

## Purpose

Serve the static frontend and a small JSON API over the stdlib `http.server`, with no external web framework, backing the [gui-frontend](gui-frontend.md) feature.

## Launcher (`launcher.py`)

- `find_free_port(start_port=8080) -> int`: probes ports `start_port..start_port+49` on `127.0.0.1`, returns the first that refuses a connection (i.e. is free); if none are free in that range, returns `start_port` anyway (caller will fail loudly when binding).
- `open_desktop_window(url)`: tries, in order, `google-chrome`, `chromium-browser`, `chromium`, `brave-browser` in app-window mode (`--app=<url>`) via `subprocess.Popen` (stdout/stderr discarded); on failure of all four (none found on PATH, or launch raised), falls back to `webbrowser.open(url)`.
- `launch_gui(host="127.0.0.1", port=8080, open_browser=True)`:
  - Resolves an actual free port starting from `port` (may differ from the requested port).
  - Starts the HTTP server, prints a banner with the resolved URL.
  - If `open_browser`, opens the browser in a daemon thread after a 0.4s delay (lets the server bind first).
  - Calls `server.serve_forever()`; on `KeyboardInterrupt`, closes the server and exits cleanly (prints shutdown messages, no traceback).

## HTTP server (`server.py`)

Every handler must be individually resilient: an exception raised handling one request must not take down the process or other in-flight requests (`http.server` handles requests synchronously per-connection by default here — no threading mixin is used, so requests are inherently serialized).

### Common response conventions
- All API responses are JSON, `Content-Type: application/json`.
- CORS: every response includes `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS`, `Access-Control-Allow-Headers: Content-Type`. `OPTIONS` requests get a bare `204 No Content` with those headers.
- Errors use the shape `{"success": false, "error": "<message>"}` with a non-2xx status (400/404/500/503 depending on cause) — except `/api/device` and `/api/courses`, which use their own always-200 shapes described below (they signal absence-of-device via a `connected: false` field, not an HTTP error).
- Request logging is suppressed (`log_message` overridden to no-op).

### Static file serving
- `GET /` or `GET /index.html` → serves `gui/static/index.html` as `text/html; charset=utf-8`; `404` JSON error if missing.
- `GET /static/<path>` → serves `gui/static/<path>`, MIME type guessed via `mimetypes`; falls back to `application/octet-stream` if unknown.
  - MUST resolve the path and verify it stays within `STATIC_DIR` (`.resolve()` + parent check) before serving — directory traversal outside `static/` is rejected as a `404`.
  - Nonexistent or non-file paths → `404` JSON error.

### `GET /api/device`
- Detect the first device.
- Connected: `{"connected": true, "model_name", "unit_id", "mount_point": str(path), "is_mtp", "mounting": false}`.
- Not connected but `check_raw_usb()` reports a Garmin USB device present: `{"connected": false, "mounting": true, "model_name": null}` (device physically attached, waiting for OS to finish mounting).
- Not connected and no raw USB device: `{"connected": false, "mounting": false, "model_name": null}`.
- Always HTTP 200 — absence of a device is not an error.

### `GET /api/courses`
- No device detected → `{"connected": false, "courses": []}`, HTTP 200.
- Device detected → construct a `GarminDeviceManager`, list courses, map each to:
  ```
  {
    "filename", "full_path": str(path),
    "watch_path": f"/GARMIN/{'NewFiles' if 'NEWFILES' in location.upper() else 'Courses'}/{filename}",
    "size_bytes", "location", "modified_at": isoformat
  }
  ```
  → `{"connected": true, "courses": [...]}`, HTTP 200.
- Any exception while listing → `500` JSON error with the exception's string message.

### `GET /api/fetch-course/<filename>` (URL-decoded)
Used by the map-preview UI to get a `[lat, lon]` polyline for a course already on the watch.
- No device → `503` JSON error `"No Garmin device connected"`.
- Course not found in `list_courses()` (exact filename match) → `404` JSON error `"Course not found on watch"`.
- File missing from disk despite being listed → `404` JSON error `"File missing from watch storage"`.
- `.fit` files: parsed via `fitparse.FitFile`, extracting `position_lat`/`position_long` from every `record` message present (values are semicircle ints, converted to degrees via `value * (180.0 / 2**31)`); points missing either coordinate are skipped.
- `.gpx` files: parsed via `gpx_parser.parse_gpx_file`, using each `TrackPoint`'s `lat`/`lon` (points missing either are skipped — though the parser doesn't currently produce points with a missing lat/lon).
- Success → `{"success": true, "points": [[lat, lon], ...]}` (may be an empty list — the frontend handles that as "no GPS trackpoints found", not an error).
- Any other exception → `500` JSON error with the exception's string message.

### `POST /api/sideload`
Request body: JSON `{"gpx_content": "<raw gpx xml>", "course_name": "<optional, default 'MVP_Course'>", "sport": "cycling"|"hiking"|"running" (default cycling, unrecognized values also fall back to cycling)}`.
- Empty body (`Content-Length: 0`) → `400` JSON error `"Empty request"`.
- No device → `503` JSON error `"No Garmin device connected"`.
- Missing `gpx_content` key/empty → `400` JSON error `"Missing gpx_content"`.
- Otherwise:
  1. Parse the GPX content string directly (not via a file) with the given name/sport.
  2. Derive a filesystem-safe filename from `course_name` by replacing every character outside `[a-zA-Z0-9_-]` with `_`; if that yields an empty string, use `"Course"`.
  3. Encode to FIT bytes in a temp directory, write the temp `.fit` file.
  4. Sideload that temp file via `GarminDeviceManager.sideload_route` (device already known to be present; a fresh `GarminDeviceManager(device=device)` is constructed here, not reused from elsewhere).
  5. Success → `{"success": true, "filename": <dest.name>, "course_name": <parsed course name>, "distance_meters": <total_distance>}`.
- Any exception during parse/encode/transfer → `500` JSON error with the exception's string message.

### `DELETE /api/courses/<filename>`
- No device → `503` JSON error `"No Garmin device connected"`.
- Deleted successfully → `{"success": true, "filename": <filename>}`.
- Not found/deletion failed → `404` JSON error `"Course '<filename>' not found"`.
- (Note: unlike the other mutating handlers, this one does not currently wrap `GarminDeviceManager(...)` construction or `delete_course` in a try/except — an unexpected exception here would propagate to `http.server`'s default error handling rather than returning clean JSON. This is a known inconsistency versus the "never crash on a per-request error" invariant in the constitution, flagged here for the next implementation pass to reconcile.)

### Everything else
- Any unmatched `GET`/`POST`/`DELETE` path → `404` JSON error `"Not found"`.

## Non-goals
- No pagination, filtering, or sorting parameters on `/api/courses`.
- No authentication/session/rate-limiting — single local user assumed.
- No streaming/chunked upload for `/api/sideload` — the whole GPX body is read into memory at once.
- No WebSocket/SSE push for device status — the frontend polls (see [gui-frontend](gui-frontend.md)).
