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

`ui/src/` (React Components)

Depends on: [connection-status-shell](../connection-status-shell.md), [course-management-api](course-management-api.md).

## Purpose

Everything a user can actually *do* once the [connection-status-shell](../connection-status-shell.md) has confirmed a watch is connected: browse and manage courses, drag/drop GPX ingest with sport selection, delete, and preview a selected course's path on a Leaflet map.

## Scope

**In scope:** `Workspace` component (sidebar, course list), ingest modal and drop zone, delete confirmation modal, map component, toasts.

## Page structure (`App.tsx` & Components)
- `Workspace.tsx` conditionally rendered when a device is connected.
  - **Sidebar (`Sidebar.tsx`)**: "Watch Storage" card with `Ingest Route` and `Refresh` buttons above a `CourseList` component.
  - **Map area (`MapPreview.tsx`)**: "Route Preview" card containing a React-Leaflet map, an empty-state overlay, and a status line.
- Modals: `IngestModal.tsx` (sport pills + drag/drop zone), `ConfirmDeleteModal.tsx`.
- Toast notification context/provider (`ToastContext.tsx`).
- External libraries: `react-leaflet`, `leaflet`, `lucide-react` for icons.

## Requirements

### Map behavior (`MapPreview.tsx`)
- Initialized centered on `[51.505, -0.09]` (London) at zoom 4.
- Basemap tile layer: CARTO dark matter (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`).
- Disconnected state: handled by `App.tsx` unmounting the workspace.
- Connected but no course selected: displays an overlay "Select a course to preview route".
- Selected course (`selectedCourse` state): 
  - Calls `GET /api/fetch-course/{filename}`.
  - Clears existing `<Polyline>`.
  - On points returned: renders a cyan (`#00f0ff`) `<Polyline>` and calls `map.fitBounds(bounds)`.
  - On zero points/error: shows error overlay.

### Ingest flow (`IngestModal.tsx`)
- Sport selector: three pill buttons (Cycling/Hiking/Running), `selectedSport` state defaults to `"cycling"`.
- Drop zone: uses `react-dropzone` or native HTML drag events.
- On file selection/drop:
  - Rejects if not `.gpx`.
  - Reads as text, POSTs to `/api/sideload`.
  - On success: closes modal, triggers a refresh of the `CourseList` via a shared `refreshTrigger` context or callback, shows success toast.
  - On failure: shows error toast.

### Course list rendering (`CourseList.tsx`)
- Fetches `GET /api/courses` on mount and when triggered.
- Empty/no courses → placeholder text.
- Each course renders as a row component with format badge (`FIT`/`GPX`), `watch_path`, size, and `Map` (Preview) / `Delete` action buttons.

### Deletion flow (`ConfirmDeleteModal.tsx`)
- `Delete` button sets `courseToDelete` state and opens modal.
- Confirm → `DELETE /api/courses/{filename}`.
- On success: closes modal, clears `selectedCourse` if it matches, triggers list refresh, shows success toast.

### Misc UX
- Toasts (`useToast` hook): stacked bottom-right, auto-dismiss.
- Modals trap focus and close on Escape or backdrop click.

## Non-Goals
- No offline/service-worker support.
- No elevation profile chart.
- No client-side persistence (no localStorage) — full state is re-fetched from the server on every page load.
