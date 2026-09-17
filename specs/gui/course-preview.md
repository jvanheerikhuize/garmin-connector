---
id: gui-course-preview
title: Web GUI Course Route & Elevation Preview
namespace: gui
status: implemented
owners: [jerry]
depends_on: [dashboard, gui-file-browser, gui-course-upload]
implements_requirements: [FR-10]
relies_on_facts: [FCT-8, FCT-12, FCT-14]
relies_on_assumptions: [ASM-5, ASM-7, ASM-8, ASM-9, ASM-10]
last_updated: 2026-09-17
---

# Web GUI Course Route & Elevation Preview

`internal/web/server.go`
`internal/web/api.go`
`internal/device/course.go`
`internal/web/static/index.html`
`internal/web/static/app.css`
`internal/web/static/app.js`

Depends on: [Web GUI Dashboard](dashboard.md), [Web GUI Column View File Browser](file-browser.md), [Web GUI Course Upload](course-upload.md)

## Constitution Alignment

- **Implements Requirements:** `FR-10` (Web GUI Course Route & Elevation Preview)
- **Relies on Facts:** `FCT-8` (MTP character casing), `FCT-12` (Garmin course files in `GARMIN/NewFiles/` and `GARMIN/Courses/`), `FCT-14` (GPX XML coordinate standards `<trkpt>` / `<rtept>`)
- **Relies on Assumptions:** `ASM-5` (Basic metadata sufficiency), `ASM-7` (File extension validation sufficient), `ASM-8` (Local web interface preference, offline execution without external CDNs), `ASM-9` (Point downsampling to <= 500 points for browser rendering performance), `ASM-10` (Canvas coordinate normalization for bounded vector rendering)

## Purpose

Enables visual and spatial previewing of Garmin course files (`.gpx`, `.fit`) directly in the Web GUI without external map services or internet connectivity. Users can preview route geometry, track statistics (distance, elevation gain/loss, min/max elevation), and elevation profile graphs both when inspecting files on the watch (via the File Browser) and prior to uploading new routes (via Course Upload).

## Scope

**In scope:**
- Backend Course Parsing & Metrics Engine:
  - Parsing XML-based `.gpx` course tracks (`<trkpt lat="..." lon="...">`, `<ele>`).
  - Calculating geodesic distance along track points using the Haversine formula.
  - Calculating total distance, total elevation gain, total elevation loss, min elevation, and max elevation.
  - Coordinate downsampling / decimation to a maximum of 500 points for fast network payload transfer and smooth browser rendering.
  - Bounding box computation (min/max latitude and longitude).
- HTTP API Endpoints:
  - `GET /api/course/preview?path=<device_path>`: Parses and previews a course stored on the connected Garmin watch.
  - `POST /api/course/preview`: Accepts a `multipart/form-data` file upload to preview a local course file prior to uploading.
- Offline Frontend Vector Visualizer:
  - **Vector Route Map:** Self-contained 2D SVG track projection preserving true geographic aspect ratio, featuring:
    - Projected route polyline with gradient or accent styling.
    - Start point indicator (green pin/circle).
    - Finish point indicator (red/checkered pin/circle).
    - Synchronized interactive hover dot tracking the scrubber position.
  - **Elevation Profile Chart:** Vector SVG area chart rendering elevation (y-axis) against cumulative distance (x-axis), with:
    - Min and max elevation axis labels.
    - Shaded area fill beneath the elevation curve.
    - Hover scrubbing: moving the cursor across the elevation graph highlights the corresponding geographic location on the 2D route map.
  - **Key Metrics Overview:**
    - Total Distance (km or miles).
    - Elevation Gain (+m or +ft).
    - Elevation Loss (-m or -ft).
    - Elevation Range (min/max).
    - Trackpoint count.
- UI Integration:
  - **File Browser Integration:** Displays the route map, elevation chart, and metrics inside the Preview / Inspector column when a `.gpx` file is selected on the watch.
  - **Course Upload Integration:** Displays the route map and metrics immediately upon staging a file in the dropzone, giving users confidence before clicking "Upload to Watch".

**Out of scope:**
- External raster satellite/street map tiles requiring external API keys or active internet access (`NFR-2`, `ADR 0003`).
- Editing, adding, or deleting waypoints on the route.
- Turn-by-turn routing instruction generation.

## Requirements

### Backend Course Parsing & Route Metrics
- The backend MUST parse `.gpx` files containing track points (`<trkpt>` elements with `lat` and `lon` attributes, and optional `<ele>` children).
- If track points are absent from `<trkpt>`, the backend SHOULD attempt parsing route points (`<rtept>`).
- If no valid GPS coordinates are found, the endpoint MUST return `422 Unprocessable Entity` with `{"error": "no GPS trackpoints found in course file"}`.
- **Metrics Calculation:**
  - MUST calculate total distance in meters by accumulating great-circle distances between successive valid track points using the Haversine formula:
    $$d = 2r \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$
  - MUST calculate elevation gain and loss in meters by summing elevation differences between consecutive points with a minimum delta threshold (e.g. 1.0 meter) to filter sensor noise.
  - MUST determine minimum and maximum elevation values along the track.
- **Point Resampling:**
  - If the raw track contains more than 500 trackpoints, the response points array MUST be uniformly downsampled to at most 500 points to keep payload size under 50 KB and ensure 60fps rendering in the browser.
  - Each downsampled point MUST include: `lat` (float64), `lon` (float64), `ele` (float64), and `dist` (cumulative meters from start, float64).
  - `points_count` in the response reports the raw (pre-downsampling) trackpoint count, not `len(points)`, so the UI can show true track density independent of the payload-size cap.

### HTTP API Endpoints

#### `GET /api/course/preview`
- **Query Parameter:** `path` (string, required): Device-relative path to the course file (e.g., `GARMIN/Courses/loop.gpx` or `GARMIN/NewFiles/route.gpx`).
- **Behavior:**
  - If no device is connected, MUST return `503 Service Unavailable` with `{"error": "no device connected"}`.
  - Resolves path using `device.ResolvePath` (case-insensitive, storage-root clamped per `FCT-8`).
  - If file does not exist, MUST return `404 Not Found`.
  - Parses the course and returns `200 OK` with `CoursePreviewResponse` JSON schema below.

#### `POST /api/course/preview`
- **Request:** `multipart/form-data` with part name `file`.
- **Behavior:**
  - Accepts uploaded `.gpx` (or course) file up to 32 MB.
  - Validates file extension; returns `400 Bad Request` if unsupported.
  - Parses course trackpoints and returns `200 OK` with `CoursePreviewResponse` JSON schema.
  - Does NOT write the file to the watch.

### Offline Vector Route & Elevation Visualizer
- The course preview MUST execute 100% offline without remote map tile servers, Google Maps API, or CDN scripts (`NFR-2`, `ADR 0003`).
- **2D Route Map Projection:**
  - Latitude and longitude coordinates MUST be projected into 2D Cartesian space using an equirectangular projection centered on the route bounding box:
    $$x = (\lambda - \lambda_{\min}) \cdot \cos\left(\frac{\phi_{\min} + \phi_{\max}}{2}\right), \quad y = -(\phi - \phi_{\min})$$
  - To prevent raw geographic degree coordinates (fractions of a degree) from distorting SVG circle marker radii and stroke rendering (ASM-10), projected coordinates MUST be normalized onto a fixed canvas coordinate space (e.g. `viewBox="0 0 300 180"`) using a uniform aspect-ratio scale factor $\text{scale} = \min(\text{availWidth} / \Delta x, \text{availHeight} / \Delta y)$, with padding and centering.
  - The route track MUST be drawn with a crisp vector stroke (accent color `#38bdf8`, stroke-width 3px, round cap and join).
  - A green circular marker (5px radius) MUST indicate the start point; a red circular marker (5px radius) MUST indicate the end point.
- **Elevation Profile Chart:**
  - MUST render beneath the route map as an SVG area graph plotting cumulative distance on the horizontal axis and elevation on the vertical axis.
  - The elevation path MUST be filled with a subtle vertical gradient (e.g. `rgba(56, 189, 248, 0.2)` to transparent).
  - Y-axis MUST display minimum and maximum elevation labels (formatted in meters, e.g. `245 m`).
  - X-axis MUST display total distance (formatted in km, e.g. `14.2 km`).
- **Interactive Scrubber:**
  - Moving the cursor across the elevation graph or route map MUST render a highlighted scrubber line and position a corresponding marker dot at the synchronized geographic position on the 2D route map.
  - A tooltip SHOULD display distance along the route and current elevation at the cursor position.

### UI Integration

#### File Browser Integration
- When a `.gpx` file is selected in the File Browser Column View:
  - The Preview Pane MUST fetch course preview data via `GET /api/course/preview?path=<file_path>`.
  - While loading, displays a subtle inline spinner.
  - Upon completion, renders the summary metrics badges (Distance, Elev Gain/Loss, Min/Max Elev), the 2D vector route map, and the elevation profile chart directly above the Download button.
  - If course parsing fails (e.g. malformed GPX or text log), falls back gracefully to standard file metadata and text preview.

#### Course Upload View Integration
- When a `.gpx` file is dropped or selected in the Course Upload dropzone:
  - The interface MUST immediately issue a `POST /api/course/preview` with the staged file.
  - Displays the rendered 2D route map, elevation profile, and metrics inside the staged file card before the user commits the upload.
  - Confirms to the user that the file contains valid route data before transferring it to the watch.

## Data Shapes / Interfaces

### Course Preview Response Schema

```yaml
CoursePreviewResponse:
  filename: string            # e.g., "alpine-ridge.gpx"
  total_distance_meters: float # e.g., 14850.5
  elevation_gain_meters: float # e.g., 620.0
  elevation_loss_meters: float # e.g., 615.0
  min_elevation_meters: float  # e.g., 340.0
  max_elevation_meters: float  # e.g., 960.0
  points_count: integer        # Total raw trackpoint count before downsampling (may exceed len(points)); e.g., 350
  bounds:
    min_lat: float            # e.g., 46.512
    max_lat: float            # e.g., 46.598
    min_lon: float            # e.g., 8.120
    max_lon: float            # e.g., 8.245
  points:
    - lat: float              # Latitude in degrees
      lon: float              # Longitude in degrees
      ele: float              # Elevation in meters
      dist: float             # Cumulative distance in meters from start

CoursePreviewErrorResponse:
  error: string               # Human-readable error description
```

## Non-Goals

- External raster map tiles (satellite, OpenStreetMap, Mapbox, Google Maps).
- Heart rate, cadence, or power analysis.
- Live GPS tracking.

## Open Questions

None.
