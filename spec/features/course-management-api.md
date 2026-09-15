---
id: course-management-api
title: Course Management API
tier: feature
status: implemented
owners: [jerry]
depends_on: [gui-bootstrap, device-detection, device-manager, gpx-fit-conversion]
last_updated: 2026-09-15
---

# Course Management API

`internal/api/courses.go`

Depends on: [gui-bootstrap](../gui-bootstrap.md), [device-manager](device-manager.md), [gpx-fit-conversion](gpx-fit-conversion.md).

## Purpose

The JSON API endpoints that let a user actually do something with a connected watch beyond seeing that it's there: list courses, ingest a GPX route, delete a course, and fetch a course's points for map preview. Layered on the [gui-bootstrap](../gui-bootstrap.md) skeleton's response/error/CORS conventions.

## Scope

**In scope:** `/api/courses`, `/api/sideload`, `/api/courses/{filename}` (DELETE), `/api/fetch-course/{filename}`.

**Out of scope:** `/api/device`, WebSocket handlers, static serving (see [gui-bootstrap](../gui-bootstrap.md)).

## Requirements

### `GET /api/courses`
- No device detected → `{"connected": false, "courses": []}`, HTTP 200.
- Device detected → construct a `device.Manager`, list courses, map each to JSON:
  ```json
  {
    "filename": "...", "full_path": "...",
    "watch_path": "/GARMIN/NEWFILES/...",
    "size_bytes": 1024, "location": "NEWFILES (Pending Sync)", "modified_at": "..."
  }
  ```
  → `{"connected": true, "courses": [...]}`, HTTP 200.
- Any exception while listing → `500` JSON error.

### `GET /api/fetch-course/{filename}`
Used by the map-preview UI to get a `[lat, lon]` polyline for a course already on the watch.
- No device → `503` JSON error `"No Garmin device connected"`.
- Course not found → `404` JSON error `"Course not found on watch"`.
- `.fit` files: decoded via the Go FIT library, extracting `position_lat`/`position_long` from every `record` message present (values are semicircle ints, converted to degrees via `value * (180.0 / 2**31)`).
- `.gpx` files: parsed via the Go GPX structs.
- Success → `{"success": true, "points": [[lat, lon], ...]}` (may be an empty list).

### `POST /api/sideload`
Request body: JSON `{"gpx_content": "<raw gpx xml>", "course_name": "<optional, default 'MVP_Course'>", "sport": "cycling"|"hiking"|"running"}`.
- Missing `gpx_content` key/empty → `400` JSON error `"Missing gpx_content"`.
- No device → `503` JSON error `"No Garmin device connected"`.
- Otherwise:
  1. Parse the GPX content string directly in memory.
  2. Encode to FIT bytes in memory.
  3. Sideload via `device.SideloadRoute`.
  4. Success → `{"success": true, "filename": "...", "course_name": "...", "distance_meters": 1000}`.
- Any exception during parse/encode/transfer → `500` JSON error.

### `DELETE /api/courses/{filename}`
- No device → `503` JSON error `"No Garmin device connected"`.
- Deleted successfully → `{"success": true, "filename": "<filename>"}`.
- Not found/deletion failed → `404` JSON error `"Course '<filename>' not found"`.

## Data Shapes / Interfaces

```json
GET /api/courses -> 200
  {"connected": false, "courses": []}
  {"connected": true, "courses": [{...}]}

GET /api/fetch-course/{filename} -> 200 | 404 | 500 | 503
  {"success": true, "points": [[lat, lon], ...]}

POST /api/sideload
  body:  {"gpx_content": "...", "course_name": "...", "sport": "..."}
  -> 200 {"success": true, "filename": "...", "course_name": "...", "distance_meters": 100.5}

DELETE /api/courses/{filename} -> 200 | 404
  {"success": true, "filename": "..."}
```

## Non-Goals
- No streaming/chunked upload for `/api/sideload` — the whole GPX body is read into memory at once.
