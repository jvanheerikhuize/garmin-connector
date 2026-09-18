---
id: dashboard
title: Web GUI Dashboard
namespace: gui
status: implemented
owners: [jerry]
depends_on: [cli-entrypoint, device-discovery, device-info]
implements_requirements: [FR-7, NFR-4]
relies_on_facts: [FCT-2, FCT-4, FCT-5, FCT-6, FCT-16, FCT-22]
relies_on_assumptions: [ASM-1, ASM-2, ASM-3, ASM-4, ASM-8, ASM-11, ASM-15]
last_updated: 2026-09-18
---

# Web GUI Dashboard

`internal/web/server.go`
`internal/web/api.go`
`internal/web/static/`
`cmd/garmin-connector/main.go`

Depends on: [CLI Entrypoint](../cli/cli-entrypoint.md), [Device Discovery](../core/device-discovery.md), [Device Detailed Information](../cli/device-info.md)

## Constitution Alignment

- **Implements Requirements:** `FR-7` (Web-Based GUI Dashboard), `NFR-4` (Same-Origin Enforcement — this spec owns the server, so the gate defined here applies to every `/api/*` endpoint declared in any dependent GUI spec)
- **Relies on Facts:** `FCT-2` (`GarminDevice.xml`), `FCT-4` (GVFS mount paths), `FCT-5` (XML fields), `FCT-6` (XML namespaces), `FCT-16` (no universal in-process browser-launch mechanism), `FCT-22` (cross-origin browser requests reach loopback listeners)
- **Relies on Assumptions:** `ASM-1` (On-demand execution), `ASM-2` (Structured output format), `ASM-3` (Single device workflow), `ASM-4` (Graceful degradation on missing metadata), `ASM-8` (Local web interface preference), `ASM-11` (browser-launch mechanism assumed present), `ASM-15` (other sites in the same browser are hostile)

## Purpose

Provides a standalone, local web server and responsive browser-based dashboard for interacting with a connected Garmin watch. The dashboard displays real-time connection status, device identification, storage capacity metrics, sub-component firmware versions, and installed Connect IQ apps, eliminating the need to memorize CLI subcommands or parse terminal output.

## Scope

**In scope:**
- CLI subcommand `garmin-connector web` to launch a local HTTP server.
- Configurable host binding (`--host`, default `127.0.0.1`) and port binding (`--port`, default `8080`).
- Automatic browser launch upon server startup (`--no-browser` flag to suppress).
- Embedded frontend static assets (HTML, CSS, vanilla JS) served directly from the compiled application with zero external runtime file dependencies.
- Local JSON REST API endpoints:
  - `GET /api/status`: Returns current device connection status and basic metadata.
  - `GET /api/info`: Returns detailed hardware info, storage metrics, component versions, and Connect IQ inventory.
- Responsive dashboard UI:
  - Visual connection indicator (Connected / Disconnected) with graceful disconnected state.
  - Device identification overview card (Model, Unit ID, Software version, Part number, Mount path).
  - Storage usage gauge bar with human-readable byte sizes (Used, Free, Total, and Used %).
  - Component firmware versions card (GPS, Wireless, Sensor Hub).
  - Connect IQ application table with VM version, slot allocation, and app space utilization.
  - Interactive refresh button and optional periodic polling toggle (e.g. every 5 seconds) to automatically detect device plug/unplug events.
- A request-origin gate applied to every route, so that only the served page itself can reach the API (`NFR-4`).
- Graceful server shutdown on OS interrupt signals (`SIGINT`, `SIGTERM`).

**Out of scope:**
- Uploading routes/courses via web UI (specified in [Web GUI Course Upload](course-upload.md)).
- Filesystem file browser / explorer UI (specified in [Web GUI Column View File Browser](file-browser.md)).
- Multi-user authentication, passwords, or session tokens (single-user local loopback tool). Note this does **not** exclude same-origin enforcement, which is a separate concern and is in scope (`NFR-4`).
- Remote Internet exposure or reverse-proxy TLS termination.

## Requirements

### Subcommand Definition (`web`)
- MUST expose a CLI subcommand: `garmin-connector web`.
- MUST support the following flags:
  - `--port <int>`: Port to bind the HTTP server to (default: `8080`).
  - `--host <string>`: Network address to bind the HTTP server to (default: `127.0.0.1`). MUST NOT default to `0.0.0.0`.
  - `--no-browser`: Boolean flag (default: `false`). When omitted or false, the command SHOULD attempt to open `http://<host>:<port>/` in the default system browser via `xdg-open` upon server startup.
- Upon successful socket binding, MUST output the active URL to stdout:
  `Web GUI running at http://<host>:<port>/ (Press Ctrl+C to stop)`
- MUST intercept `SIGINT` (Ctrl+C) and `SIGTERM` signals and perform a graceful HTTP server shutdown, closing the listener socket and exiting with status code `0`.
- If the configured port cannot be bound (e.g. port already in use), MUST write a descriptive error message to stderr and exit with non-zero exit code.
- If `--host` is set to anything other than a loopback address (`127.0.0.1`, `::1`, `localhost`), MUST print a one-line warning to stderr before serving, stating that the API is reachable from the network and carries no authentication (`NFR-4`). Serving MUST still proceed; the flag is the user's explicit choice.

### Request Origin Gate (`NFR-4`, `FCT-22`, `ASM-15`)
The gate runs before routing, before device discovery, and before any request body is read, on **every** path the server exposes (`/`, `/static/*`, and every `/api/*` endpoint defined here or in [file-browser.md](file-browser.md), [course-upload.md](course-upload.md), [course-preview.md](course-preview.md), and [filesystem-manipulation.md](filesystem-manipulation.md)).
- **Host check (all methods):** The request's `Host` header, with any port suffix, MUST equal the address the server printed at startup (`<host>:<port>`), or be one of the loopback spellings of it (`127.0.0.1`, `localhost`, `[::1]`) when the server is bound to loopback. Any other value MUST be rejected with `403 Forbidden` and JSON body `{"error": "forbidden host"}`. This closes DNS rebinding.
- **Origin check (state-changing methods):** For any method other than `GET`, `HEAD`, or `OPTIONS`, if an `Origin` header is present it MUST equal `http://<Host>` for the accepted `Host` above. If `Origin` is absent, the `Referer` header (when present) MUST have that same origin. Mismatch MUST be rejected with `403 Forbidden` and `{"error": "forbidden origin"}`. A state-changing request with neither header MUST be accepted (non-browser clients such as `curl` send neither and are not the threat; `FCT-22` describes browsers, which always send `Origin` on cross-origin `POST`).
- **Content-Type check (state-changing methods):** Each endpoint declares exactly one accepted media type — `application/json` for JSON-body endpoints, `multipart/form-data` for file uploads. A state-changing request whose `Content-Type` does not match (including `text/plain`, `application/x-www-form-urlencoded`, or a missing header) MUST be rejected with `415 Unsupported Media Type` and `{"error": "unsupported content type"}` before the body is parsed. The served frontend MUST therefore always set `Content-Type: application/json` explicitly on JSON requests.
- **Cross-origin responses:** The server MUST NOT emit `Access-Control-Allow-Origin` or any other CORS-enabling header; there is no legitimate cross-origin consumer.
- **Response hardening:** Every response SHOULD carry `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` (equivalently `Content-Security-Policy: frame-ancestors 'none'`) so the dashboard cannot be framed by another site.

### Embedded Static Asset Serving
- All web assets (HTML, CSS, JS, icons) MUST be embedded directly into the compiled executable with zero external runtime file dependencies.
- Root path `GET /` MUST serve the main dashboard HTML document with header `Content-Type: text/html; charset=utf-8`.
- Static files served from `GET /static/*` MUST be served with appropriate MIME types (`text/css`, `application/javascript`, `image/svg+xml`).
- Assets MUST NOT reference external CDNs, remote web fonts, or third-party hosted scripts; all styling and logic MUST execute fully offline without active internet connectivity.

### HTTP API Endpoints
- MUST expose `GET /api/status`:
  - Executes device discovery matching the behavior of `garmin-connector status --json`.
  - Emits `Content-Type: application/json`.
  - HTTP response code MUST be `200 OK` regardless of whether a device is connected (NFR-1).
  - Response body MUST adhere to the `StatusResponse` schema below.
- MUST expose `GET /api/info`:
  - Executes device discovery, storage statfs queries, and XML inspection matching `garmin-connector info --json`.
  - Emits `Content-Type: application/json`.
  - HTTP response code MUST be `200 OK` regardless of whether a device is connected.
  - Response body MUST adhere to the `InfoResponse` schema below.
- All API endpoints MUST set the `Cache-Control: no-store, no-cache, must-revalidate` header to prevent stale browser responses.

### Dashboard UI Behavior
- **Initial Load:** Upon page load, the frontend script MUST issue a request to `GET /api/info` and render the retrieved state.
- **Disconnected State:**
  - When `connected: false`, the dashboard MUST display a clear "No Garmin Device Detected" banner with guidance to connect the watch via USB.
  - When disconnected, detail sections (Storage, Components, Connect IQ) MUST display a dormant/inactive state rather than rendering broken or `NaN` values.
- **Connected State:**
  - When `connected: true`, the header MUST display an active "Connected" indicator alongside the device model name (e.g., `Venu X1`).
  - **Device Summary Card:** Displays Model, Unit ID, Software Version, Part Number, and Mount Path.
  - **Storage Gauge:** Displays a visual progress/capacity bar representing `used_percentage`, alongside formatted text showing `used_bytes` of `total_bytes` used and `free_bytes` available, formatted in human-readable binary units (`GB`, `MB`).
  - **Hardware Subsystems Card:** Displays table of component versions: GPS, Wireless, and Sensor Hub. If any version string is empty, renders `-`.
  - **Connect IQ Card:** Displays VM version, app slot counter (e.g. `3 / 32 Apps`), total app space allocated, and a table listing installed apps (Name, Type, Version, File Name). If no apps are installed, renders a descriptive notice (`No Connect IQ apps installed`).
- **Refresh & Auto-Poll:**
  - The UI MUST provide a manual "Refresh" button.
  - The UI SHOULD include an "Auto-Refresh" toggle switch (default: enabled, polling every 5 seconds) so that plugging in or disconnecting the watch automatically updates the dashboard without manual page reloads.
  - During network fetch, the UI SHOULD indicate a subtle loading indicator without blanking out existing content.

## Data Shapes / Interfaces

### CLI Command Flags

```yaml
WebFlags:
  host: string       # default: "127.0.0.1"
  port: integer      # default: 8080
  no_browser: boolean # default: false
```

### JSON API Schemas

```yaml
StatusResponse:
  connected: boolean
  device:
    model: string
    id: string
    software_version: string
    part_number: string
    mount_path: string
  # null when connected == false

InfoResponse:
  connected: boolean
  device:
    model: string
    id: string
    software_version: string
    part_number: string
    mount_path: string
    storage:
      total_bytes: integer
      used_bytes: integer
      free_bytes: integer
      used_percentage: float
    connect_iq:
      vm_version: string
      max_apps: integer
      app_space_bytes: integer
      apps:
        - name: string
          type: string
          version: string
          app_id: string
          file_name: string
    components:
      gps: string
      wireless: string
      sensor_hub: string
  # null when connected == false
```

## Non-Goals

- Remote network access or proxying beyond localhost.
- Managing Connect IQ store purchases, synchronization, or app deletion.
- Background OS daemon or systemd service setup.
- Writing files to the device (handled by future dedicated upload specs).

## Open Questions

None.
