---
id: gui-file-browser
title: Web GUI Column View File Browser
namespace: gui
status: implemented
owners: [jerry]
depends_on: [dashboard, device-discovery, file-browser, content-insight]
implements_requirements: [FR-8, FR-13, NFR-4]
relies_on_facts: [FCT-3, FCT-4, FCT-8, FCT-10, FCT-11, FCT-22, FCT-24, FCT-25, FCT-26]
relies_on_assumptions: [ASM-1, ASM-3, ASM-5, ASM-6, ASM-8, ASM-15]
last_updated: 2026-11-08
---

# Web GUI Column View File Browser

`internal/web/server.go`
`internal/web/api.go`
`internal/web/static/index.html`
`internal/web/static/app.css`
`internal/web/static/app.js`

Depends on: [Web GUI Dashboard](dashboard.md), [Device Discovery](../core/device-discovery.md), [File Browser (ls / tree)](../cli/file-browser.md), [Folder Purpose & File Content Inspection](../core/content-insight.md)

## Constitution Alignment

- **Implements Requirements:** `FR-8` (Web GUI Column View File Browser), `FR-13` (Folder & File Insight — the GUI half; the inspection rules are in [core/content-insight.md](../core/content-insight.md))
- **Relies on Facts:** `FCT-3` (GARMIN directory structure), `FCT-4` (GVFS MTP mount paths), `FCT-8` (MTP character casing), `FCT-10` (MTP traversal latency), `FCT-11` (MTP metadata limits), `FCT-24` (GPX import naming & waypoints), `FCT-25` (data-type declarations), `FCT-26` (FIT format)
- **Relies on Assumptions:** `ASM-1` (On-demand execution), `ASM-3` (Single device workflow), `ASM-5` (Basic metadata sufficiency), `ASM-6` (Depth/latency prevention via lazy loading), `ASM-8` (Local web interface preference)

## Purpose

Provides a macOS Finder-style Column View (Miller Columns) file browser inside the local Web GUI for exploring the connected Garmin watch's filesystem. Because MTP filesystem traversal is slow (`FCT-10`), Column View offers an optimal browsing experience by lazily querying directory contents one level at a time upon user selection, visualizing the folder hierarchy across horizontal columns, offering keyboard navigation, providing a detailed file inspector preview pane, and enabling one-click file downloads directly to the user's computer.

## Scope

**In scope:**
- Top-level view switcher in the Web GUI allowing seamless toggling between **Dashboard** and **File Browser** views.
- Interactive Miller Columns layout:
  - Horizontally scrollable container appending child columns to the right as directories are selected.
  - Column 0 rooted at the watch storage root (parent of `GARMIN`).
  - Lazy loading of directory contents on click/selection via backend REST API.
  - Distinct visual indicators and icons for directories, Garmin `.FIT` activity files, `.GPX` courses, `.XML` documents, `.TXT`/`.LOG` files, and generic binary assets.
  - Disclosure chevrons (`›`) for directories.
  - Active selection highlighting maintaining the selected path trail across all parent columns.
- Dedicated Preview / Inspector column (rightmost column when a file is selected):
  - Large file icon and formatted name.
  - File kind/type description based on extension.
  - Exact file size in bytes and human-readable units (`KB`, `MB`).
  - Modification timestamp formatted in local date and time.
  - Device-relative canonical path.
  - "Download" button to save the file from the watch to the local computer.
  - Quick text preview for any file that reads as text (first 64 KB), e.g. `GarminDevice.xml`, `.json`, `.log`.
  - **About** and **Contents** sections: the folder the file belongs to and its purpose, the type the watch declares for it, and a decoded summary of the file (FIT, GPX, image, byte peek) per [core/content-insight.md](../core/content-insight.md).
- Folder insight: an **About this folder** card at the top of every directory column and a one-line purpose under each folder name (`FR-13`).
- Finder-compatible keyboard navigation (Arrow keys: Up, Down, Left, Right; Enter).
- Path breadcrumb bar displaying the full active path hierarchy with clickable segments to navigate back to any ancestor level.
- Toolbar controls:
  - Toggle to show/hide hidden files (names starting with `.`).
  - Refresh button to re-read the current directory column from the watch.
- Backend REST API endpoints:
  - `GET /api/fs/ls?path=<path>&all=<bool>`: Returns directory entries for the specified relative path.
  - `GET /api/fs/download?path=<path>`: Streams the requested file with `Content-Disposition: attachment`.
  - `GET /api/fs/inspect?path=<path>`: Returns the content summary of one file.
- Strict path traversal security: Preventing directory traversal attacks escaping the watch storage root.
- Handling edge states: Loading spinners per column, empty folders ("Folder is empty"), read errors, and device disconnection.

**Out of scope:**
- File write, upload, rename, or delete operations (covered by [Web GUI Filesystem Manipulation](filesystem-manipulation.md) and [Web GUI Course Upload](course-upload.md)).
- Visualizing `.FIT` data streams (heart rate curves, GPS maps); only the summary defined in [core/content-insight.md](../core/content-insight.md) is shown.
- Multi-file selection or batch archiving/downloading.
- Searching or indexing files across the watch storage.

## Requirements

### View Navigation & Header Integration
- The Web GUI MUST provide a top-level tab/navigation bar to switch between the existing **Dashboard** view and the new **File Browser** view without reloading the page.
- When the File Browser tab is active, the interface MUST display:
  - A breadcrumb path bar displaying the active path hierarchy starting from root `/` (e.g., `/ > GARMIN > Activity > 2026-09-14.FIT`).
  - Clicking any breadcrumb segment MUST navigate the view directly to that folder level, truncating deeper columns.
  - A "Show Hidden Files" toggle checkbox (default: unchecked). Toggling it MUST reload the active columns respecting the hidden files setting.
  - A "Refresh" button that re-fetches the contents of the currently active/visible columns from the device.
- If no device is connected, the File Browser view MUST display a dormant/disconnected banner matching the Dashboard disconnected state ("No Garmin Device Detected"), disabling column navigation until a device is connected.

### Miller Columns Layout & Interaction
- Directory hierarchy MUST be rendered as a sequence of vertical columns positioned side-by-side inside a horizontally scrollable container.
- **Column 0 (Root Column):**
  - Upon initial load or device connection, the browser MUST fetch the contents of the storage root (`path=""`) and populate Column 0.
- **Column Dimensions & Scrolling:**
  - Each column MUST have a fixed min-width (e.g., `240px` to `280px`) and vertical scrolling for entries exceeding the viewport height (`overflow-y: auto`).
  - When a new column is opened to the right, the container MUST automatically scroll horizontally to ensure the newly active column and selected item are visible.
- **Entry Rows:**
  - Each entry row MUST display an icon representing the item type:
    - Directory: Folder icon.
    - FIT file (`.fit`): Activity / Workout icon.
    - GPX file (`.gpx`): Route / Track icon.
    - XML file (`.xml`): XML code / Document icon.
    - Text / Log file (`.txt`, `.log`, `.bak`): Text document icon.
    - Other files: Generic file icon.
  - Each entry row MUST display the item name (truncated with text overflow ellipsis if exceeding column width).
  - Directory rows MUST display a right-facing disclosure indicator (e.g., `›`).
  - A directory row whose entry carries a `purpose` MUST show it as a second, muted, single-line (ellipsised) text under the name, unless it equals the name case-insensitively (e.g. `Music`). The row's tooltip is `<name> — <purpose>` (or just the name).
  - File rows MUST display the human-readable file size (e.g., `42 KB`, `1.2 MB`) right-aligned or in secondary text.
  - Hidden files (names starting with `.`) MUST be excluded unless "Show Hidden Files" is active.
- **Item Selection:**
  - Clicking a directory in column `N`:
    - MUST mark the directory item as active/selected in column `N`.
    - MUST remove all existing columns at indices `> N`.
    - MUST spawn column `N + 1` displaying a loading indicator while fetching the directory contents via `GET /api/fs/ls?path=<dir_path>`.
    - Once loaded, column `N + 1` MUST render the retrieved directory entries.
    - If the directory contains 0 items (or 0 non-hidden items when hidden files are toggled off), column `N + 1` MUST display a centered message: `Folder is empty`.
  - Clicking a file in column `N`:
    - MUST mark the file item as active/selected in column `N`.
    - MUST remove all existing columns at indices `> N`.
    - MUST spawn the **Preview / Inspector Pane** in column `N + 1`.
  - Clicking an already-selected directory in column `N` MUST NOT re-fetch or collapse column `N + 1`.

### Folder Insight Card (FR-13)
- When a directory column's listing carries a non-null `folder`, the column MUST start with a collapsible **About this folder** card above its entries (also above `Folder is empty`). The listing provides it, so no extra request is made.
- The card summary line shows the folder `title` and a **basis badge**: `documented`, `observed`, `device`, or — for `inferred` — the word `likely`, styled distinctly; the badge tooltip explains the basis (`Documented by Garmin`, `Observed on a real watch`, `Declared by the watch itself`, `Likely — inferred from the name`).
- The card body shows the `description`, then `<d> folders · <f> files · <total size of the listed files>` computed from the listed entries, then the declared data types: with one or two, under the heading `The watch declares this folder for:`; with three or more, inside a nested collapsed section titled `The watch declares <n> data types here`. Each data type reads `<label> .<EXT> … · <direction>`, where direction is `written by the watch`, `imported by the watch`, or `written and read by the watch`; beyond the first 8 a `+ <k> more` item reveals the rest.
- The open/closed state of the card is shared by all columns and SHOULD be remembered in the browser's local storage (`gc.folderInfoOpen`); storage being unavailable MUST NOT break the view. Default: open.

### File Preview / Inspector Pane
- When a file is selected in column `N`, column `N + 1` MUST render as a dedicated Preview / Inspector column, wider than a directory column: at least 420px and at most 600px, growing into free space.
- The Preview Pane MUST include:
  - A prominent file icon badge at the top matching the file type.
  - The full file name with word breaking enabled.
  - A formatted metadata table detailing:
    - **Kind:** Human-readable file type description (e.g. `Garmin FIT Activity File`, `GPX Course File`, `Garmin Device XML`, `Text Document`, `Binary File`).
    - **Size:** Human-readable size alongside exact byte count in parentheses (e.g., `1.45 MB (1,520,432 bytes)`).
    - **Modified:** Formatted local date and time (e.g., `2026-09-14 14:32:05`).
    - **Device Path:** Full canonical path on the device (e.g., `/GARMIN/Activity/2026-09-14-143205.FIT`).
  - A primary **Download** button:
    - Clicking the button MUST trigger a browser file download via `GET /api/fs/download?path=<file_path>`.
  - Below the actions the pane MUST request `GET /api/fs/inspect?path=<file_path>` (a spinner shows meanwhile; a failure shows `Contents unavailable: <error>` and leaves the rest of the pane intact) and render, omitting any row whose value is empty:
    - **About:** `Part of <folder title>` with its basis badge, and `Declared by the watch as <label>, <direction>.`
    - **FIT contents** (when `fit` is present): Type (`<name> (<number>)`), Name, Created, Device (`<manufacturer> · <product_name or "product <n>">`), Serial, Format (`FIT <protocol>, profile <profile>`), Integrity (`Checksum OK` / `Checksum mismatch` / `No checksum`, plus ` · partly decoded` when not complete). Then **Session** when present: Sport, Start, Duration (`[h:]mm:ss`), Distance (km, 2 decimals), Calories (`kcal`), Heart rate (`avg <a> · max <m> bpm`). Then **Messages**: the first 8 message counts, and `+ <k> more message types` beyond that. The **Kind** row is replaced by `Garmin FIT <file type name> File`.
    - **GPX contents** (when `gpx` is present): Metadata name, Track name(s), Route name(s), Tracks (`<n> (<points> points)`), Routes, Waypoints, Creator; then a notice that on import the watch names the course after the name(s) inside the file — listing them — not after the file name (`FCT-24`); and, if there are waypoints, a notice that they become Saved Locations on the watch, not course points, followed by the waypoint names (with ` …` if more exist than were returned).
    - **Image** (format `image`): an inline image loaded from the download endpoint, scaled to the pane width. The **Kind** row becomes `Image` (`Audio` for format `audio`).
    - **Text** (when `text` is present): a read-only monospace block with the excerpt, and `Showing the first 64 KB. Download the file for the rest.` when truncated.
    - **First bytes** (when `hex_head` is non-empty): the bytes as space-separated hex pairs, 16 per line.
    - An `error` value is shown as an error line; the remaining sections still render.
  - Responses for a file that is no longer selected MUST be ignored.
  - For course files (`.gpx`), the Preview Pane SHOULD render the interactive 2D vector route map and elevation profile per [Web GUI Course Route & Elevation Preview](course-preview.md).

### Keyboard Navigation (macOS Finder Parity)
- When the File Browser view has focus, the interface MUST support the following keyboard controls:
  - `ArrowDown`: Select the next item down in the currently focused column.
  - `ArrowUp`: Select the previous item up in the currently focused column.
  - `ArrowRight`:
    - If a directory is selected: Shifts focus into the next column (`N + 1`) and automatically selects its first entry.
    - If a file is selected: Shifts focus to the "Download" button in the Preview Pane.
  - `ArrowLeft`: Shifts focus back to the parent directory item in the previous column (`N - 1`).
  - `Enter`: If a file is selected, triggers file download. If a directory is selected, expands the directory.

### HTTP API Endpoints

#### `GET /api/fs/ls`
- **Purpose:** Query directory contents on the connected watch.
- **Parameters:**
  - `path` (string, optional, default `""`): Watch-relative path. `""` or `/` represents the storage root.
  - `all` (boolean, optional, default `false`): When `true`, include files/directories whose names start with `.`.
- **Behavior:**
  - If no device is connected, MUST return `200 OK` with `{"connected": false, "path": "", "entries": []}`.
  - Resolves `path` relative to the watch storage root with case-insensitivity (`FCT-8`) and storage root clamping (`FCT-3`).
  - Path traversal attempts containing `..` segments MUST NOT escape above the storage root.
  - If `path` does not exist or points to a non-directory, MUST return `404 Not Found` with JSON error envelope `{"error": "directory not found"}`.
  - Returns `200 OK` with JSON envelope adhering to `FsLsResponse` schema below. Entries MUST be sorted case-insensitively by name with ties broken by byte order.
  - `folder` is the purpose of the listed directory and each directory entry's `purpose` is the title of that subfolder's purpose, both per [core/content-insight.md](../core/content-insight.md); they are null/omitted when unknown. Computing them MUST NOT list any additional directory (`FCT-10`).
  - A path that leaves the storage root through a symbolic link answers `404 {"error": "directory not found"}`. If the directory exists but cannot be read, the endpoint answers `500` with `{"error": "cannot read directory: <reason>"}`. An `all` value that is not a boolean is treated as `false`.

#### `GET /api/fs/inspect`
- **Purpose:** Summarise what one file on the watch contains (`FR-13`).
- **Parameters:** `path` (string, required): watch-relative path to a file.
- **Behavior:**
  - If no device is connected, MUST return `503 Service Unavailable` with `{"error": "no device connected"}`.
  - Path resolution, containment and errors are exactly those of `GET /api/fs/download`: missing/empty path, a directory, or a path leaving the storage root → `400 {"error": "invalid file path"}`; a missing file → `404 {"error": "file not found"}`.
  - A file that cannot be opened → `500 {"error": "cannot read file: <reason>"}`.
  - Otherwise `200 OK` with a `FileInsight` body as defined in [core/content-insight.md](../core/content-insight.md). A FIT/GPX file that cannot be decoded is still `200`, with `error` set.
  - Only `GET` is allowed (`405` otherwise, per [dashboard.md](dashboard.md)). The endpoint never writes to the watch.

#### `GET /api/fs/download`
- **Purpose:** Download a file from the watch to the user's local machine via browser download.
- **Parameters:**
  - `path` (string, required): Watch-relative path to the target file.
- **Behavior:**
  - If no device is connected, MUST return `503 Service Unavailable` with `{"error": "no device connected"}`.
  - Resolves `path` relative to the storage root with case-insensitivity (`FCT-8`).
  - If `path` resolves outside the watch storage root — including when it only leaves the root by following a symbolic link, which ordinary `/media` and `/mnt` filesystems can contain even though MTP cannot (`FCT-11`) — or points to a directory rather than a regular file, MUST return `400 Bad Request` with `{"error": "invalid file path"}`. The check MUST be made on the fully resolved (link-free) path.
  - If the file does not exist, MUST return `404 Not Found` with `{"error": "file not found"}`.
  - Sets HTTP response headers:
    - `Content-Type: application/octet-stream`, except `application/xml` for `.xml`, `text/plain; charset=utf-8` for `.txt`/`.log`, and the image type for `.png` (`image/png`), `.jpg`/`.jpeg` (`image/jpeg`), `.gif`, `.bmp`, `.webp` so the inspector can show images inline (extensions case-insensitive).
    - `Content-Disposition: attachment; filename="<basename>"`, where `<basename>` is encoded per RFC 6266 (any `"` or `\` escaped and, for non-ASCII names, a `filename*=UTF-8''<percent-encoded>` parameter added) so that a watch filename can never break or inject into the header.
    - `Content-Length: <size_bytes>`.
    - `Cache-Control: no-store, no-cache, must-revalidate`, the same value every API endpoint sets ([dashboard.md](dashboard.md)), which includes `no-cache`.
  - A missing or empty `path` (the storage root) answers `400 {"error": "invalid file path"}`.
  - Streams the file byte contents directly to the HTTP response writer.

### Request Gate
- Every `/api/fs/*` request first passes the **Request Origin Gate** defined in [dashboard.md](dashboard.md) (`NFR-4`, `FCT-22`, `ASM-15`); a foreign `Host` answers `403` before any device access.

### Error Handling & Performance
- In accordance with `FCT-10`, directory fetching operations MUST NOT block other web server operations.
- If an individual directory read fails (e.g. temporary MTP I/O error), that specific column MUST render an inline error message with a "Retry" button rather than breaking the entire view.
- When the watch is disconnected while browsing:
  - Active columns MUST be cleared or dimmed, and the "No Garmin Device Detected" banner MUST be displayed.
  - Polling or subsequent requests MUST fail gracefully without crashing the server (`NFR-1`).

## Data Shapes / Interfaces

### API Schemas

```yaml
FsLsResponse:
  connected: boolean
  path: string             # Canonical resolved relative path (e.g., "GARMIN/Activity")
  folder: FolderInfo       # Purpose of this directory (core/content-insight.md), or null
  entries:
    - name: string         # Entry filename
      is_dir: boolean      # True if entry is a directory
      size_bytes: integer  # Size in bytes (0 for directories)
      modified_time: string # RFC 3339 timestamp with local offset
      purpose: string      # Directories only: title of the subfolder's purpose; omitted when unknown

FsErrorResponse:
  error: string            # Human-readable failure description
```

### Preview Inspector Data Shape

```yaml
FilePreviewInfo:
  name: string             # Filename (e.g., "2026-09-14-143205.FIT")
  path: string             # Full canonical path (e.g., "GARMIN/Activity/2026-09-14-143205.FIT")
  kind: string             # Descriptive type (e.g., "Garmin FIT Activity")
  size_formatted: string   # Formatted human size (e.g., "1.45 MB")
  size_bytes: integer      # Raw byte count (e.g., 1520432)
  modified_formatted: string # Human formatted timestamp
  download_url: string     # Relative API download URL
  preview_text: string     # Optional text snippet for small plain-text / XML files (nullable)
  insight: FileInsight     # From GET /api/fs/inspect (core/content-insight.md)
```

## Non-Goals

- Writing, uploading, modifying, or deleting files in arbitrary directories.
- Recursive pre-fetching of all directories (would violate `FCT-10` and cause severe latency).
- Rendering rich telemetry charts (heart rate, pace, elevation) from raw `.FIT` files; the inspector shows a summary only.
- Drag-and-drop file movement between columns.

## Open Questions

None.
