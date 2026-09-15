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

`internal/api/server.go` and `embed.go`

Depends on: [device-detection](device-detection.md).

## Purpose

Bring up the local web server that handles the REST API, WebSocket connections, and serves the embedded React UI.

## Scope

**In scope:** HTTP server bootstrap, Go `embed.FS` static asset serving, `/api/device` endpoints, WebSocket upgrades.

## Requirements

### Server Bootstrap (`server.go`)
- `Serve(host string, port int, openBrowser bool) error`
- Gracefully shut down on SIGINT/SIGTERM.
- `openBrowser` attempts to launch the default OS browser to `http://host:port`.

### Server-wide conventions
- Catch per-request exceptions and return JSON error bodies (`{"success": false, "error": "..."}`).
- All API responses MUST be JSON.
- Open CORS headers.

### Static file serving
- Serve all files from the `ui/dist` directory using Go's `//go:embed` directive.
- `GET /` serves `index.html`.
- Unrecognized paths (e.g., client-side routing) must fallback to `index.html`.

### `GET /api/device`
- Detect the first device (via `device.GetFirstDevice()`).
- Connected: `{"connected": true, "model_name": "...", "unit_id": "...", "mount_point": "..."}`.
- Not connected: `{"connected": false, "model_name": null}`.
- MUST always return HTTP 200.

### WebSocket Endpoint: `WS /api/ws`
- Upgrade incoming HTTP requests to a WebSocket connection.
- Push state changes emitted by the OS watcher (e.g., watch mounted/unmounted) directly to connected clients in real-time.

## Data Shapes / Interfaces

```json
GET /api/device -> 200
  {"connected": true, "model_name": "Garmin Venu", "unit_id": "...", "mount_point": "/Volumes/GARMIN"}
  {"connected": false, "model_name": null}
```

WebSocket Messages:
```json
// From Server -> Client
{"type": "device_status", "payload": {"connected": true, "model_name": "Garmin Venu"}}
```
