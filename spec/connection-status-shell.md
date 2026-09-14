---
id: connection-status-shell
title: Connection Status Shell
tier: skeleton
status: implemented
owners: [jerry]
depends_on: [gui-bootstrap]
last_updated: 2026-09-14
---

# Connection Status Shell

`src/garmin_connector/gui/static/{index.html,app.js}` (partial — header + polling only)

Depends on: [gui-bootstrap](gui-bootstrap.md).

## Purpose

The minimum frontend needed to prove the walking skeleton end-to-end: load a page, ask the server whether a watch is connected, and reflect that truthfully and continuously without ever getting stuck or crashing the page. Everything a user can actually *do* with a connected watch (list/ingest/delete/map courses) is a feature layered on top — this shell only has to answer "is a watch here right now?".

## Scope

**In scope:** the header/status markup, the device-status polling loop and its state machine, and the seams (`enableMap()`, `disableAndResetMap()`, `fetchCourses()`) it calls into on feature-owned code without needing to know their internals.

**Out of scope:** what `enableMap`/`disableAndResetMap`/`fetchCourses` actually do — that's feature behavior, see [gui-course-frontend](features/gui-course-frontend.md).

## Requirements

### Page shell markup
- MUST render a header containing a brand title and a connection status indicator: a status dot element (`#statusDot`) and a status text element (`#deviceStatus`).
- MUST render the overall page structure (header + main content area) so that feature-owned sections (storage sidebar, map area, modals, toasts) have somewhere to mount — this shell does not itself define their internals.

### Device status polling (`checkDeviceStatus`)
- MUST poll `GET /api/device` every **3000ms**, plus once immediately on `DOMContentLoaded`.
- **Connected**: reset a "missing cycles" debounce counter to 0; set internal state to `connected`; set the status dot to the connected (green) style; call the feature-owned `enableMap()` hook; call the feature-owned course-list refresh (`fetchCourses()`) if the course list container is still showing its initial empty-state placeholder. Status text becomes `"Connected: <model_name or 'Garmin Watch'>"` — but only if the text doesn't already contain the word "courses" (must not stomp the richer "(N courses)" text a feature sets).
- **Mounting** (`mounting: true` in the response): reset the debounce counter; set internal state to `mounting`; status dot set to an orange/"pending" style; status text `"Watch detected, waiting for storage mount..."`; call the feature-owned `disableAndResetMap()` hook.
- **Disconnected, with debounce**: if the *previous* known state was not already `disconnected` and fewer than **7** consecutive missing polls have occurred, increment the counter and skip the UI update entirely — this smooths over transient USB re-enumeration blips without flashing the UI to "disconnected" and back. Only after 7 consecutive misses (or if the state was already `disconnected`) does it transition: status dot to disconnected (red/neutral) style; status text `"No watch connected"`; call `disableAndResetMap()`.
- **Fetch/network error**: treated the same as a disconnected poll for debounce purposes; on transition (after the debounce window) also calls `disableAndResetMap()` and logs the error to console — MUST NOT surface a toast (this is a background poll, not a user-initiated action, per the constitution's UX conventions).
- MUST NOT let a failed poll (network error, non-2xx, malformed JSON) throw an uncaught exception that stops future polling — the `setInterval` loop must keep running indefinitely.

## Data Shapes / Interfaces

Internal state machine (module-level, not persisted):
```
lastKnownState: "connected" | "mounting" | "disconnected"
missingCycles: int   # consecutive disconnected/error polls since last known-good state; debounce threshold = 7
```

Hooks this shell calls but does not define (owned by [gui-course-frontend](features/gui-course-frontend.md)):
```
enableMap()             # called on "connected"
disableAndResetMap()    # called on "mounting", "disconnected" (post-debounce), and fetch errors (post-debounce)
fetchCourses()          # called on "connected" only if the course list is still in its empty/initial state
```

## Non-Goals
- No exponential backoff on polling — fixed 3000ms interval regardless of connection state or error rate.
- No user-visible error messaging for transient poll failures — only a debounced state transition after 7 misses.
- No persistence of `lastKnownState`/`missingCycles` across page reloads.
