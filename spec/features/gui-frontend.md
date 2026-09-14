# Feature: GUI Frontend (Cyberpunk Terminal UI)

`src/garmin_connector/gui/static/{index.html,app.js,styles.css,cybercore.min.css}`

Depends on: [gui-http-api](gui-http-api.md).

## Purpose

A single-page, no-build vanilla JS/HTML/CSS frontend giving the user: live device connection status, a course list (on-watch + pending-sync), drag/drop GPX ingest with sport selection, course deletion, and a Leaflet map preview of a selected course's path — themed with the vendored CYBERCORE CSS design system (CRT scanlines, neon glow, chamfered "HUD" cards).

## Page structure (`index.html`)
- Header: brand icon/title + a connection status indicator (`statusDot` + `deviceStatus` text).
- Main grid, two columns:
  - **Sidebar**: "Watch Storage" card with `Ingest Route` and `Refresh` buttons (both `disabled` until a device is connected) above a course list container.
  - **Map area**: "Route Preview" card containing a Leaflet map (`#map`), an empty-state overlay (`#mapEmptyOverlay`), and a status line (`#mapInfo`).
- Modals: **Ingest Route** (sport pills + drag/drop zone), **Confirm Delete**, both CYBERCORE `cyber-modal` components toggled via a `cyber-modal--open` class.
- Toast notification stack (`#toastContainer`) for success/error/warning messages.
- External assets loaded via CDN: Google Fonts (Exo 2, JetBrains Mono, Orbitron, Rajdhani), Leaflet 1.9.4 (JS+CSS) — plus locally vendored `cybercore.min.css` and `styles.css`.

## Map behavior
- Initialized centered on `[51.505, -0.09]` (London) at zoom 4, dark CartoDB basemap tiles (`dark_all`).
- **Disabled state** (`disableAndResetMap`) — applied on page load and whenever the device is not connected: removes any drawn track, resets view to the default center/zoom, disables all interaction (drag/zoom/keyboard), shows the empty overlay with "Connect watch via USB to enable route preview", and sets `mapInfo` to "No watch connected".
- **Enabled state** (`enableMap`) — applied when a device is connected: re-enables interaction; if no track is currently drawn, shows the empty overlay with "Select a course to preview route" and `mapInfo` "No route selected" (but only overwrites `mapInfo` if it currently reads "No watch connected", to avoid clobbering an in-progress/loaded-route message); if a track *is* drawn, hides the overlay.
- **Mapping a course** (`mapCourse(filename)`): sets a loading message, calls `GET /api/fetch-course/<filename>`, throws on `success: false`. Clears any existing track layer first. If points returned: draws a cyan (`#00f0ff`) polyline (weight 4, opacity 0.9, class `glowing-track`), fits the map bounds to it with 30px padding, hides the overlay, sets `mapInfo` to `"Showing: <filename> (<n> trackpoints)"`. If zero points: shows the overlay with `"No GPS trackpoints found in <filename>"` and mirrors that in `mapInfo`. On any fetch/parse error: shows the overlay and `mapInfo` with `"Failed to load route: <error>"` and raises an error toast.

## Device status polling (`checkDeviceStatus`)
- Polls `GET /api/device` every **3000ms**, plus once immediately on `DOMContentLoaded`.
- **Connected**: resets a "missing cycles" debounce counter to 0, sets state to `connected`, green status dot, enables Refresh/Ingest buttons and the drop zone, calls `enableMap()`. Status text becomes `"Connected: <model_name or 'Garmin Watch'>"` — but only if the text doesn't already contain the word "courses" (i.e. this must not stomp the richer "(N courses)" text that `fetchCourses()` sets). If the course list container is still showing its empty-state placeholder, triggers `fetchCourses()`.
- **Mounting** (`mounting: true`): resets the debounce counter, sets state to `mounting`, disables Refresh/Ingest/drop zone, orange status dot, text `"Watch detected, waiting for storage mount..."`, course list shows a "waiting for OS to mount storage" placeholder, and the map is disabled/reset.
- **Disconnected, with debounce**: if the *previous* known state was not already `disconnected` and fewer than **7** consecutive missing polls have occurred, increments the counter and **skips the UI update entirely** — this smooths over transient USB re-enumeration blips (e.g. brief unmount/remount during a course sync) without flashing the UI to "disconnected" and back. Only after 7 consecutive misses (or if the state was already `disconnected`) does it actually transition: red status dot, disables Refresh/Ingest/drop zone, text `"No watch connected"`, course list shows the "no device connected" placeholder, map disabled/reset.
- **Fetch/network error**: treated the same as a disconnected poll for debounce purposes, but on transition (after the debounce window) also resets the map and logs the error to console — does not show a toast (this is a background poll, not a user action).

## Ingest flow
- Sport selector: three pill buttons (Cycling/Hiking/Running), single-select, `selectedSport` defaults to `"cycling"`.
- Drop zone: click-to-browse (via hidden `<input type="file" accept=".gpx">`) or drag-and-drop; visually and functionally disabled (`pointerEvents: none`, dimmed) whenever no device is connected/mounting.
- On file selection/drop (`handleFileUpload`):
  - Rejects (toast error, no request sent) any filename not ending in `.gpx` (case-insensitive).
  - Shows an in-progress toast `"Ingesting <file> for <sport>..."`.
  - Reads the file as text (`FileReader.readAsText`), then `POST /api/sideload` with `{gpx_content, course_name: <filename without .gpx>, sport: selectedSport}`.
  - Success: success toast `"Successfully converted & sideloaded: <filename>"`, closes the ingest modal after a 500ms delay, refreshes the course list and device status.
  - API-reported failure (`success: false`): error toast with the server's `error` message; modal stays open.
  - Network/transport error: error toast `"Network error: <message>"`.

## Course list rendering (`fetchCourses`)
- `GET /api/courses`. Empty/no courses → placeholder text "No courses found in watch storage"; if the status text currently starts with "Connected", appends `" (0 courses)"`.
- Non-empty: counts entries whose `location` (uppercased) contains `"NEWFILES"` vs `"COURSES"` separately; status text (only if currently starting with "Connected") becomes `"Connected: <model> (<total> courses<, N pending sync if any>)"`.
- Each course renders as a row: a format badge (`FIT`/`GPX`, styled by extension), the `watch_path` (falls back to `/GARMIN/Courses/<filename>` if absent) as the primary label with the full local path as a tooltip, size in KB (rounded), and `Map`/`Delete` action buttons.
- Fetch errors are logged to console only (no user-facing toast) — this is considered a secondary/background refresh, consistent with the polling error handling above.

## Deletion flow
- `Delete` button opens the confirm modal with a message naming the file; the actual filename is held in a module-level `courseToDelete` variable, cleared on cancel/close.
- Confirm → `DELETE /api/courses/<filename>` (percent-encoded). On success: clears any drawn map track and resets the map overlay/info text to the "no route selected" state, refreshes the course list and device status, success toast `"Deleted <filename>"`. On non-OK response: error toast `"Failed to delete <filename>"`. On network error: error toast `"Delete failed: <message>"`.

## Misc UX
- `Escape` key closes both modals (whichever is open) globally.
- Clicking a modal's backdrop (the modal root element itself, not its dialog) closes it.
- Toasts (`showMessage(msg, type)`): appended to a stack, auto-slide-out and remove after 4.5s; `type` is `"success" | "error" | "warning"` (anything else defaults to the warning/"Notice" styling).

## Non-goals
- No offline/service-worker support — requires a live connection to the local server.
- No client-side GPX validation beyond the file-extension check — malformed GPX content surfaces only as a server-side error toast.
- No elevation profile chart, despite the GUI module's docstring mentioning one — not implemented in the current frontend.
- No client-side persistence (no localStorage) — full state is re-fetched from the server on every page load.
