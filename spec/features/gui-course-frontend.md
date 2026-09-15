---
id: gui-course-frontend
title: Course Management & Map Preview Frontend
tier: feature
status: implemented
owners: [jerry]
depends_on: [connection-status-shell, course-management-api]
last_updated: 2026-09-15
---

# Course Management & Map Preview Frontend (Cyberpunk Terminal UI)

`src/garmin_connector/gui/static/{index.html,app.js,styles.css,cybercore.min.css}` (partial — everything except the header/polling shell)

Depends on: [connection-status-shell](../connection-status-shell.md), [course-management-api](course-management-api.md).

## Purpose

Everything a user can actually *do* once the [connection-status-shell](../connection-status-shell.md) has confirmed a watch is connected: browse and manage courses, drag/drop GPX ingest with sport selection, delete, and preview a selected course's path on a Leaflet map — themed with the vendored CYBERCORE CSS design system (CRT scanlines, neon glow, chamfered "HUD" cards).

## Scope

**In scope:** the storage sidebar (toolbar, course list), the ingest modal and drop zone, the delete confirmation modal, the map's feature-facing behavior (draw/clear a route, empty states beyond the bare "no watch" state), toasts.

**Out of scope:** the header, status dot/text, and the `checkDeviceStatus` polling loop that drives this feature's `enableMap`/`disableAndResetMap`/`fetchCourses` hooks — see [connection-status-shell](../connection-status-shell.md), which this feature implements the hooks for.

## Page structure (`index.html`)
- Main grid, two columns:
  - **Sidebar**: "Watch Storage" card with `Ingest Route` and `Refresh` buttons (both `disabled` until a device is connected) above a course list container.
  - **Map area**: "Route Preview" card containing a Leaflet map (`#map`), an empty-state overlay (`#mapEmptyOverlay`), and a status line (`#mapInfo`).
- Modals: **Ingest Route** (sport pills + drag/drop zone), **Confirm Delete**, both CYBERCORE `cyber-modal` components toggled via a `cyber-modal--open` class.
- Toast notification stack (`#toastContainer`) for success/error/warning messages.
- External assets loaded via CDN: Google Fonts (Exo 2, JetBrains Mono, Orbitron, Rajdhani), Leaflet 1.9.4 (JS+CSS) — plus locally vendored `cybercore.min.css` and `styles.css`.

## Requirements

### Map behavior
- Initialized centered on `[51.505, -0.09]` (London) at zoom 4, with zoom and attribution controls enabled.
- Basemap tile layer: keyless OpenStreetMap standard tiles `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, `maxZoom: 19`, attribution `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors`. The tiles are light; the dark look comes entirely from the CSS filter on `.leaflet-tile-pane` defined in [ui-design](ui-design.md) §11.
- **`disableAndResetMap()`** (implements the hook [connection-status-shell](../connection-status-shell.md) calls on disconnected/error): removes any drawn track, resets view to the default center/zoom, disables all interaction (drag/zoom/keyboard), adds `map-disabled` to the viewport container, shows the empty overlay with "Connect watch via USB to enable route preview", sets `mapInfo` to "No watch connected", and disables the `Ingest Route`/`Refresh` buttons and the drop zone.
- **`enableMap()`** (implements the hook called on connected): re-enables interaction, removes `map-disabled`, and enables the `Ingest Route`/`Refresh` buttons and the drop zone; if no track is currently drawn, shows the empty overlay with "Select a course to preview route" and `mapInfo` "No route selected" (but only overwrites `mapInfo` if it currently reads "No watch connected", to avoid clobbering an in-progress/loaded-route message); if a track *is* drawn, hides the overlay.
- **Mapping a course** (`mapCourse(filename)`): sets a loading message, calls `GET /api/fetch-course/<filename>`, throws on `success: false`. Clears any existing track layer first. If points returned: draws a cyan (`#00f0ff`) polyline (weight 4, opacity 0.9, class `glowing-track`), fits the map bounds to it with 30px padding, hides the overlay, sets `mapInfo` to `"Showing: <filename> (<n> trackpoints)"`. If zero points: shows the overlay with `"No GPS trackpoints found in <filename>"` and mirrors that in `mapInfo`. On any fetch/parse error: shows the overlay and `mapInfo` with `"Failed to load route: <error>"` and raises an error toast.

### Startup
- On `DOMContentLoaded`, before the first status poll: initialize the Leaflet map, bind all event handlers, then call `disableAndResetMap()` so the page starts in the disconnected state instead of waiting for the shell's 7-poll debounce to reach it.

### Ingest flow
- Sport selector: three pill buttons (Cycling/Hiking/Running), single-select, `selectedSport` defaults to `"cycling"`.
- Drop zone: click-to-browse (via hidden `<input type="file" accept=".gpx">`) or drag-and-drop; visually and functionally disabled (`pointerEvents: none`, dimmed) whenever no device is connected (toggled by `enableMap()`/`disableAndResetMap()`, see above).
- On file selection/drop (`handleFileUpload`):
  - Rejects (toast error, no request sent) any filename not ending in `.gpx` (case-insensitive).
  - Shows an in-progress toast `"Ingesting <file> for <sport>..."`.
  - Reads the file as text (`FileReader.readAsText`), then `POST /api/sideload` with `{gpx_content, course_name: <filename without .gpx>, sport: selectedSport}`.
  - Success: success toast `"Successfully converted & sideloaded: <filename>"`, closes the ingest modal after a 500ms delay, refreshes the course list and device status.
  - API-reported failure (`success: false`): error toast with the server's `error` message; modal stays open.
  - Network/transport error: error toast `"Network error: <message>"`.

### Course list rendering (`fetchCourses`) (implements the hook [connection-status-shell](../connection-status-shell.md) calls when connected and the list is still empty)
- `GET /api/courses`. Empty/no courses → placeholder text "No courses found in watch storage"; if the status text currently starts with "Connected", appends `" (0 courses)"`.
- Non-empty: counts entries whose `location` (uppercased) contains `"NEWFILES"` vs `"COURSES"` separately; status text (only if currently starting with "Connected") becomes `"Connected: <model> (<total> courses<, N pending sync if any>)"`.
- Each course renders as a row: a format badge (`FIT`/`GPX`, styled by extension), the `watch_path` (falls back to `/GARMIN/Courses/<filename>` if absent) as the primary label with the full local path as a tooltip, size in KB (rounded), and `Map`/`Delete` action buttons.
- Fetch errors are logged to console only (no user-facing toast) — this is considered a secondary/background refresh, consistent with the connection-status-shell's polling error handling.

### Deletion flow
- `Delete` button opens the confirm modal with a message naming the file; the actual filename is held in a module-level `courseToDelete` variable, cleared on cancel/close.
- Confirm → `DELETE /api/courses/<filename>` (percent-encoded). On success: clears any drawn map track and resets the map overlay/info text to the "no route selected" state, refreshes the course list and device status, success toast `"Deleted <filename>"`. On non-OK response: error toast `"Failed to delete <filename>"`. On network error: error toast `"Delete failed: <message>"`.

### Misc UX
- `Escape` key closes both modals (whichever is open) globally.
- Clicking a modal's backdrop (the modal root element itself, not its dialog) closes it.
- Toasts (`showMessage(msg, type)`): appended to a stack, auto-slide-out and remove after 4.5s; `type` is `"success" | "error" | "warning"` (anything else defaults to the warning/"Notice" styling).

## Non-Goals
- No favicon — the browser's `/favicon.ico` probe gets the server's JSON 404, which is harmless.
- No offline/service-worker support — requires a live connection to the local server.
- No client-side GPX validation beyond the file-extension check — malformed GPX content surfaces only as a server-side error toast.
- No elevation profile chart, despite the GUI module's docstring mentioning one — not implemented in the current frontend.
- No client-side persistence (no localStorage) — full state is re-fetched from the server on every page load.

