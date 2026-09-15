---
id: connection-status-shell
title: Connection Status Shell
tier: skeleton
status: implemented
owners: [jerry]
depends_on: [gui-bootstrap]
last_updated: 2026-09-15
---

# Connection Status Shell

`src/garmin_connector/gui/static/{index.html,app.js}` (partial — header + polling only)

Depends on: [gui-bootstrap](gui-bootstrap.md).

## Purpose

The minimum frontend needed to prove the walking skeleton end-to-end: load a page, ask the server whether a watch is connected, and reflect that truthfully and continuously. 

## Scope

**In scope:** the header/status markup, the device-status polling loop, and the seams (`enableMap()`, `disableAndResetMap()`, `fetchCourses()`) it calls into on feature-owned code.

## Requirements

### Page shell markup
- MUST render a header containing a brand title and a connection status indicator: a status dot element (`#statusDot`) and a status text element (`#deviceStatus`).
- MUST render the overall page structure (header + main content area).

### Device status polling (`checkDeviceStatus`)
- MUST poll `GET /api/device` every **3000ms**, plus once immediately on `DOMContentLoaded`.
- **Connected**: reset a "missing cycles" debounce counter to 0; set internal state to `connected`; set the status dot to the connected (green) style; call the feature-owned `enableMap()` hook; call `fetchCourses()` if the course list is empty. Status text becomes `"Connected: <model_name or 'Garmin Watch'>"` — but only on the *transition* into `connected` (or if the text does not currently start with `Connected`); on subsequent connected polls the text is left alone so the course-count suffix appended by the feature-owned `fetchCourses()` is not clobbered every 3 seconds.
- **Disconnected, with debounce**: if fewer than **7** consecutive missing/error polls have occurred, skip the UI update (smooths over blips). After 7 misses: status dot to disconnected (red/neutral) style; status text `"No watch connected"`; call `disableAndResetMap()`.
- MUST NOT let a failed poll throw an uncaught exception that stops future polling.

### Status dot styling
- Driven entirely by a CSS class name:
  - `status-dot connected` (green)
  - `status-dot disconnected` (grey/neutral)

## Data Shapes / Interfaces

Internal state machine:
```
lastKnownState: "connected" | "disconnected"
missingCycles: int   # debounce threshold = 7
```

Hooks this shell calls but does not define:
```
enableMap()             # called on "connected"
disableAndResetMap()    # called on "disconnected"
fetchCourses()          # called on "connected" if list is empty
```
