---
id: course-management-api
title: Course Management API
tier: feature
status: implemented
owners: [jerry]
depends_on: [gui-bootstrap, device-detection, device-manager, gpx-fit-conversion]
last_updated: 2026-09-14
---

# Course Management API

`src/garmin_connector/gui/server.py` (partial — course/route endpoints only)

Depends on: [gui-bootstrap](../gui-bootstrap.md), [device-manager](device-manager.md), [gpx-fit-conversion](gpx-fit-conversion.md).

## Purpose

The JSON API endpoints that let a user actually do something with a connected watch beyond seeing that it's there: list courses, ingest a GPX route, delete a course, and fetch a course's points for map preview. Layered on the [gui-bootstrap](../gui-bootstrap.md) skeleton's response/error/CORS conventions, which this spec assumes and does not repeat.

## Scope

**In scope:** `/api/courses`, `/api/sideload`, `/api/courses/<filename>` (DELETE), `/api/fetch-course/<filename>`.

**Out of scope:** `/api/device`, static serving, and general server conventions (see [gui-bootstrap](../gui-bootstrap.md)).

## Requirements

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
- MUST wrap `GarminDeviceManager(...)` construction and `delete_course` in the same try/except-to-500-JSON pattern as every other mutating handler in this spec, per the constitution's "never crash on a per-request error" invariant. (v1 fix: the original implementation omitted this; regeneration must include it.)

## Data Shapes / Interfaces

```
GET /api/courses -> 200
  {"connected": false, "courses": []}
  {"connected": true, "courses": [{filename, full_path, watch_path, size_bytes, location, modified_at}]}

GET /api/fetch-course/<filename> -> 200 | 404 | 500 | 503
  {"success": true, "points": [[lat, lon], ...]}
  {"success": false, "error": str}

POST /api/sideload
  body:  {"gpx_content": str, "course_name"?: str, "sport"?: "cycling"|"hiking"|"running"}
  -> 200 {"success": true, "filename": str, "course_name": str, "distance_meters": float}
  -> 400 | 500 | 503 {"success": false, "error": str}

DELETE /api/courses/<filename> -> 200 | 404
  {"success": true, "filename": str}
  {"success": false, "error": str}
```

## Non-Goals
- No pagination, filtering, or sorting parameters on `/api/courses`.
- No authentication/session/rate-limiting — single local user assumed.
- No streaming/chunked upload for `/api/sideload` — the whole GPX body is read into memory at once.
