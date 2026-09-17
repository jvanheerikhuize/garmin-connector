---
id: gui-course-upload
title: Web GUI Course Upload
namespace: gui
status: implemented
owners: [jerry]
depends_on: [dashboard, course-upload, device-discovery]
implements_requirements: [FR-9]
relies_on_facts: [FCT-8, FCT-12, FCT-13]
relies_on_assumptions: [ASM-1, ASM-3, ASM-7, ASM-8]
last_updated: 2026-09-17
---

# Web GUI Course Upload

`internal/web/server.go`
`internal/web/api.go`
`internal/web/static/index.html`
`internal/web/static/app.css`
`internal/web/static/app.js`

Depends on: [Web GUI Dashboard](dashboard.md), [Course Upload (upload command)](../cli/course-upload.md), [Device Discovery](../core/device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-9` (Web GUI Course Upload)
- **Relies on Facts:** `FCT-8` (MTP character casing), `FCT-12` (Watch imports from `GARMIN/NewFiles/`), `FCT-13` (GVFS MTP D-Bus Push requirement)
- **Relies on Assumptions:** `ASM-1` (On-demand execution), `ASM-3` (Single device workflow), `ASM-7` (File extension validation sufficient), `ASM-8` (Local web interface preference)

## Purpose

Provides a browser-based drag-and-drop and file-picker interface within the Web GUI for transferring route, workout, and course files (`.fit`, `.gpx`) from the host computer directly to the connected Garmin watch's incoming directory (`GARMIN/NewFiles/`). This eliminates the need to run CLI subcommands or navigate complex GVFS mount paths in desktop file managers when transferring courses exported from mapping tools (e.g., Komoot, Strava, Garmin Connect, GPX route builders).

## Scope

**In scope:**
- Top-level navigation integration in the Web GUI (access via tab navigation: **Dashboard**, **File Browser**, **Upload Course**).
- Interactive drag-and-drop dropzone:
  - Visual drag-and-drop target with distinct drag-over, active file selection, uploading, success, and error states.
  - File picker button (`<input type="file">`) as a fallback or alternative to drag-and-drop.
- Client-side validation:
  - Enforces `.fit` and `.gpx` file extensions (case-insensitive) before initiating upload.
  - Rejects unsupported file types with clear inline error messaging.
- Backend REST API endpoint `POST /api/upload`:
  - Accepts `multipart/form-data` with file payload under form key `file`.
  - Verifies device connection; returns `503 Service Unavailable` if no device is connected.
  - Validates file extension; returns `400 Bad Request` if not `.fit` or `.gpx`.
  - Transfers the file to `GARMIN/NewFiles/` on the device using existing `device.UploadCourse` logic (including GVFS D-Bus push support per `FCT-13` and casing tolerance per `FCT-8`).
  - Overwrites any existing file of the same name in `GARMIN/NewFiles/`.
  - Returns `200 OK` JSON response with filename, destination path, and transfer size.
- Post-upload user guidance:
  - Confirmation alert with filename and byte size.
  - Explicit notification informing the user that Garmin watches automatically process incoming files into courses/workouts once the watch is disconnected from USB (`FCT-12`).
  - Button to reset the dropzone and upload another file.
- Disconnected watch handling:
  - Disables upload interactions and renders a dormant/disconnected banner matching Dashboard and File Browser disconnected states.

**Out of scope:**
- Parsing or rendering course route lines, elevation profiles, or GPS waypoint maps in the browser.
- Converting non-supported formats (e.g., KML, TCX, GeoJSON) to GPX or FIT.
- Managing, renaming, or deleting courses already processed into the device's internal `Courses/` directory.

## Requirements

### Navigation & View Integration
- The Web GUI navigation tabs MUST include an **Upload Course** (or **Upload**) tab alongside **Dashboard** and **File Browser**.
- Clicking the tab MUST switch the active view to the Course Upload view without page reloads.
- If no Garmin watch is connected, the Course Upload view MUST display the dormant "No Garmin Device Detected" banner and disable upload interactions.

### File Dropzone & Interaction
- The upload interface MUST feature a prominent drag-and-drop dropzone box with:
  - An upload cloud/arrow icon.
  - Informative copy: `Drag & drop a course file (.fit, .gpx) here, or browse`.
  - A clickable "Browse File" button triggering the native OS file picker.
  - Supported format indicator: `Supported formats: .FIT, .GPX`.
- The native file picker MUST set `accept=".fit,.gpx"` to filter selectable files.
- **Drag Events:**
  - Dragging a file over the dropzone MUST highlight the container with an active border/background accent (`dragover` state).
  - Dragging out or cancelling MUST restore the default appearance.
- **File Selection:**
  - Dropping a file onto the dropzone or selecting a file via the file picker MUST immediately validate the file extension:
    - If the file extension is NOT `.fit` or `.gpx` (case-insensitive), the interface MUST NOT initiate an upload and MUST display an inline error: `Invalid file type. Please select a .fit or .gpx file.`
    - If valid, the interface MUST transition to the staged file state showing the filename and formatted size, with an "Upload to Watch" action button.
- **Upload Progress:**
  - Clicking "Upload to Watch" (or dropping a valid file) MUST display an upload progress/spinner indicator and disable buttons to prevent double submission.

### Backend HTTP API (`POST /api/upload`)
- **Endpoint:** `POST /api/upload`
- **Request Format:** `multipart/form-data` with part name `file`.
- **Validation & Handling:**
  - If request method is not `POST`, MUST return `405 Method Not Allowed`.
  - If no Garmin device is connected, MUST return `503 Service Unavailable` with JSON:
    `{"error": "no device connected"}`.
  - If the multipart payload is missing or empty, MUST return `400 Bad Request` with JSON:
    `{"error": "missing file payload"}`.
  - If the uploaded file extension is not `.fit` or `.gpx` (case-insensitive), MUST return `400 Bad Request` with JSON:
    `{"error": "invalid file type: must be .fit or .gpx"}`.
  - MUST write the incoming file bytes safely and execute transfer to the watch's `GARMIN/NewFiles` directory via `device.UploadCourse`.
  - MUST tolerate directory casing variations (`FCT-8`).
  - If standard POSIX write fails due to GVFS MTP FUSE limitations, MUST fall back to GVFS D-Bus push (`FCT-13`).
  - MUST overwrite any existing file with the same filename in `NewFiles`.
  - Upon successful transfer, MUST return `200 OK` with JSON envelope adhering to `UploadResponse` schema below.
  - If device transfer fails (e.g. `NewFiles` missing or disk write error), MUST return `500 Internal Server Error` with JSON error details.

### Post-Upload Feedback
- Upon receiving a `200 OK` response:
  - The dropzone MUST display a success state with a checkmark badge.
  - MUST display the transferred filename and size.
  - MUST display an informational notice: `File transferred to watch. The course will be processed automatically when you disconnect the USB cable.`
  - MUST provide an "Upload Another Course" button to reset the dropzone for another upload.

## Data Shapes / Interfaces

### HTTP API Schemas

```yaml
UploadResponse:
  connected: boolean       # true
  filename: string         # Transferred filename (e.g., "mountain-loop.gpx")
  destination_path: string # Full destination path on device (e.g., "/run/user/1000/gvfs/.../GARMIN/NewFiles/mountain-loop.gpx")
  size_bytes: integer      # Transferred byte size
  message: string          # "Course uploaded successfully"

UploadErrorResponse:
  error: string            # Human-readable failure description
```

## Non-Goals

- Deep validation or schema parsing of trackpoints or workout intervals.
- Automatic route conversion from other formats (KML, TCX).
- Deletion or editing of existing files on the watch.

## Open Questions

None.
