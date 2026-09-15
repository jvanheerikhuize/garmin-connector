---
id: constitution
title: Constitution
last_updated: 2026-09-15
---

# Constitution

The constitution is not itself a spec with requirements to implement — it is the **sum of the walking-skeleton specs**, plus the scope, tech stack, and architecture that frame every spec in this repository. It changes rarely and deliberately.

## 1. Purpose, Goal & Requirements

### 1.1 Purpose & Goal

- **Purpose**: A lightweight, cross-platform (Linux, Windows, macOS) CLI tool with an integrated local web GUI to connect to a Garmin Venu (or compatible) watch over USB, view connection status, ingest GPX routes (auto-converted to FIT), manage course files on the watch, and preview a selected course's path on a map — featuring a Cyberpunk Terminal aesthetic.
- **Goal**: To deliver a strictly spec-driven, fault-tolerant MVP that adheres to a "walking skeleton" architecture. The specification corpus serves as the single source of truth and blueprint for single-shot AI code generation, enforcing rigid architectural boundaries—keeping device detection read-only, isolating HTTP concerns, and maintaining zero-dependency frontend code—so the resulting application degrades gracefully and remains resilient.

### 1.2 Functional Requirements (FR)

The system fulfills the following functional requirements across its walking skeleton and feature layers:

- **FR-1: Cross-Platform Device Discovery**: Automatically detect connected Garmin watches across supported OS mount points (Linux GVFS/MTP & `/media`/`/mnt`, macOS `/Volumes`, Windows drive letters `A:\`–`Z:\`) without manual mount path configuration. An optional `custom_path` / `--mount` override must bypass auto-discovery.
- **FR-2: Device Metadata Extraction**: Read and parse `GarminDevice.xml` (case-insensitive, XML namespaces stripped) to extract identifying metadata (`model_name`, `unit_id`, `software_version`, `part_number`) with graceful fallbacks on missing or malformed XML.
- **FR-3: Subdirectory Resolution**: Locate `NEWFILES`, `COURSES`, and `ACTIVITY` directories case-insensitively, automatically inferring default paths for `NEWFILES` and `COURSES` if absent.
- **FR-4: Route Ingestion & FIT Conversion**: Ingest `.gpx` and `.fit` route files via GUI drag-and-drop or file selection. Automatically parse GPX trackpoints/waypoints (using stdlib XML parsing) and encode them into valid Garmin binary FIT format (`.fit`) adhering to Garmin string field limits (≤ 15 bytes UTF-8) and protocol CRC checks.
- **FR-5: Device Sideloading**: Write converted `.fit` files directly into the connected watch's `NEWFILES/` directory to trigger native Garmin course synchronization.
- **FR-6: Watch Course Management**: List all course files residing in `COURSES/` (active) and `NEWFILES/` (pending sync) with filenames, locations, byte sizes, and UTC modified timestamps. Support deleting specific courses from device storage by filename.
- **FR-7: Interactive Map Preview**: Parse course trackpoints from watch files or incoming routes, extract coordinate polyline arrays, and render an interactive Leaflet map preview with dark telemetry tiles and an auto-centered bounding box.
- **FR-8: Continuous Connection Telemetry**: Provide a non-blocking 3-second client polling loop against `GET /api/device` reflecting real-time connection status (`disconnected`, `mounting`, `connected`, `model_name`).
- **FR-9: Process & Server Management**: Provide a CLI entrypoint (`garmin-connector gui`) to launch the local HTTP server on a configurable host/port, handle auto-opening the browser, and cleanly shut down on SIGINT/SIGTERM.

### 1.3 Non-Functional Requirements (NFR)

The system complies with the following non-functional constraints and quality attributes:

- **NFR-1: Architectural Isolation & Boundaries**:
  - `device/detector.py` is strictly read-only (zero file write, delete, or mutation).
  - `converter/*` is completely decoupled from device and transport logic (in-memory data structures and local file I/O only).
  - `gui/server.py` encapsulates all HTTP/JSON transport concerns; underlying modules remain usable as a pure Python library.
  - `gui/static/*` requires zero build steps (vanilla HTML/CSS/JS served as-is with no npm, bundlers, or transpilers).
- **NFR-2: Fault Tolerance & Graceful Degradation**:
  - Never terminate or crash the server process on per-request errors (invalid uploads, conversion errors, premature watch disconnection).
  - Absence of a connected watch is a standard valid state, never an exception or HTTP 500 error.
  - Endpoints dynamically re-resolve device state on every mutating request (`get_first_device()`) to prevent stale mount references.
- **NFR-3: Minimal Footprint & Zero Web Frameworks**:
  - Runtime dependencies restricted strictly to `fitparse` (for reading binary FIT files) and standard library modules (`http.server`, `xml.etree.ElementTree`).
  - No heavyweight web frameworks (Flask, FastAPI, Django) or backend databases.
  - Low CPU and memory footprint suited for low-power host devices.
- **NFR-4: Hardware Protocol Conformance**:
  - Strict adherence to Garmin FIT binary format, byte endianness, and string length limits (course and course point names null-terminated within 16-byte fields).
  - Robust tolerance of FAT32/MTP directory casing variations.
- **NFR-5: Spec-Driven Single-Shot Rebuildability**:
  - The specification corpus serves as the deterministic oracle; specs must remain unambiguous enough for an autonomous agent to regenerate `src/` end-to-end.
  - No dead code: every module described in the specs must be reachable from the CLI or HTTP API.
  - Continuous verification: all walking-skeleton and feature contracts must pass automated tests (`pytest`) upon generation.

### 1.4 Target Release & Scope

**Target release:** v1.0.0 — the first single-shot generation from this spec corpus is the MVP. `pyproject.toml`'s version bumps to `1.0.0` as part of that generation.

**In scope:** everything described by a spec in this directory (skeleton or feature).
**Out of scope:** see §6.

## 2. The Walking Skeleton

The walking skeleton is not prose here — it is the sum of the specs tagged `tier: skeleton`. Each is independently maintained; this section only enumerates and orders them. A spec earns skeleton tier if the app cannot prove "it runs, end-to-end, at all" without it — removing any one of these breaks the whole chain, not just a feature.

| Order | Spec | Proves |
|---|---|---|
| 1 | [cli-entrypoint](cli-entrypoint.md) | The process starts. |
| 2 | [gui-bootstrap](gui-bootstrap.md) | It serves a page and answers `/api/device`, without crashing. |
| 3 | [device-detection](device-detection.md) | It can truthfully sense whether a watch is attached. |
| 4 | [connection-status-shell](connection-status-shell.md) | The page reflects that truth (disconnected / mounting / connected), continuously, without getting stuck. |

Every `tier: feature` spec (under `features/`) is layered on top of this chain and must degrade gracefully to "not available" if the skeleton is intact but the feature is missing or broken — never the other way around.

## 3. Architecture

```mermaid
flowchart TD
    subgraph Browser["Browser"]
        FE["gui/static frontend<br/>index.html + app.js"]
    end

    subgraph Process["garmin-connector process"]
        CLI["cli.py"] --> Launcher["gui/launcher.py"]
        Launcher --> Server["gui/server.py<br/>HTTP + JSON API"]
        Server -. serves .-> FE
        Server --> Detector["device/detector.py<br/>(read-only)"]
        Server --> Manager["device/manager.py"]
        Manager --> Detector
        Manager --> Converter["converter/*<br/>gpx_parser · fit_encoder"]
    end

    subgraph HostOS["Host OS filesystem"]
        LinuxGVFS["/run/user/uid/gvfs (Linux MTP)"]
        LinuxMedia["/media · /mnt (Linux USB)"]
        MacMounts["/Volumes (macOS)"]
        WinMounts["D:\, E:\, etc. (Windows)"]
    end

    subgraph Watch["Garmin watch"]
        GarminDir["GARMIN/<br/>NEWFILES · COURSES · ACTIVITY"]
    end

    FE <-- "fetch() JSON, 3s poll" --> Server
    Detector --> LinuxGVFS
    Detector --> LinuxMedia
    Detector --> MacMounts
    Detector --> WinMounts
    Manager --> LinuxGVFS
    Manager --> LinuxMedia
    Manager --> MacMounts
    Manager --> WinMounts
    LinuxGVFS --- GarminDir
    LinuxMedia --- GarminDir
    MacMounts --- GarminDir
    WinMounts --- GarminDir

    classDef skeleton fill:#0b3d91,stroke:#5b9bff,color:#fff
    class CLI,Launcher,Server,Detector,FE skeleton
```

Darker/highlighted nodes are on the walking skeleton's critical path.

### Repository layout

```
garmin-venu-x1/
├── spec/                          # source of truth — see spec/README.md
│   ├── constitution.md            # this file
│   ├── regeneration.md            # single-shot rewrite runbook
│   ├── cli-entrypoint.md          # [skeleton]
│   ├── gui-bootstrap.md           # [skeleton]
│   ├── device-detection.md        # [skeleton]
│   ├── connection-status-shell.md # [skeleton]
│   ├── templates/
│   │   └── spec-template.md
│   └── features/
│       ├── device-manager.md
│       ├── gpx-fit-conversion.md
│       ├── course-management-api.md
│       ├── gui-course-frontend.md
│       └── ui-design.md
├── src/garmin_connector/
│   ├── cli.py
│   ├── device/
│   │   ├── detector.py
│   │   └── manager.py
│   ├── converter/
│   │   ├── gpx_parser.py
│   │   ├── fit_encoder.py
│   │   └── gpx_to_fit.py
│   └── gui/
│       ├── launcher.py
│       ├── server.py
│       └── static/
│           ├── index.html
│           ├── app.js
│           ├── styles.css
│           └── cybercore.min.css
├── tests/                         # regression oracle; test_skeleton.py covers constitution §7
├── examples/                      # fixtures
└── pyproject.toml
```

### Architecture boundaries (non-negotiable)

- **`device/detector.py` is read-only.** It must never write, move, or delete anything on the watch or host filesystem.
- **`converter/*` has zero device knowledge.** It only ever deals with in-memory data (`CourseData`, GPX text, FIT bytes) and local file I/O — never touches `device/*`.
- **`gui/server.py` is the only place HTTP concerns exist.** `device/*` and `converter/*` must remain usable as a plain Python library with no HTTP/JSON dependency.
- **`gui/static/*` has no build step.** Plain HTML/CSS/JS served as-is from disk; no bundler, no npm dependency, no transpilation.
- **The CLI has exactly one subcommand today: `gui`.** Any new subcommand is a feature-level spec addition, not a constitution change.

## 4. Tech Stack (fixed)

- Python ≥ 3.10, packaged via `setuptools`, `src/` layout (`src/garmin_connector/`).
- Runtime dependency: `fitparse` only (used solely for reading `.fit` files back out in the course-management API's fetch-course endpoint — not for writing). `gpxpy` was previously declared but never imported; it is dropped under the "no dead code" invariant — GPX parsing is stdlib `xml.etree.ElementTree`.
- Dev dependency: `pytest`.
- No web framework (Flask/FastAPI/etc.) — `http.server.HTTPServer` + `BaseHTTPRequestHandler` only.
- No frontend framework/bundler — vanilla JS, Leaflet.js (CDN) for mapping, CYBERCORE CSS (vendored `cybercore.min.css`) for styling, Google Fonts (Exo 2, JetBrains Mono, Orbitron, Rajdhani) via CDN.

## 5. Cross-cutting invariants

- **Never crash the server process on a per-request error.** Every API handler must catch exceptions and return a JSON error body (`{"success": false, "error": "..."}` or `{"connected": false, ...}`) with an appropriate HTTP status, not propagate.
- **No device present is not an error state.** Every endpoint must degrade gracefully (empty course list, `connected: false`, etc.) rather than 500 when no watch is attached.
- **Garmin string field limits are respected wherever names are written into FIT data**: course name ≤ 15 bytes UTF-8, course point name ≤ 15 bytes UTF-8 (16-byte field, null-terminated).
- **Filesystem paths under a device's `GARMIN/` directory are case-insensitive matched** (`NEWFILES`, `COURSES`, `ACTIVITY`) since Garmin devices are inconsistent about casing across models/firmware.
- **CORS is fully open** (`Access-Control-Allow-Origin: *`) on all API responses — this is a local-only tool, not intended for multi-origin exposure.
- **The GUI must never assume a device stays connected between requests.** Every mutating endpoint re-resolves `GarminDeviceDetector.get_first_device()` itself rather than trusting cached state.
- **All diagrams in this repository's specs are Mermaid.** No ASCII art, no external image tools — see [spec/README.md](README.md).
- **No dead code.** Every module described by a spec MUST be reachable from the CLI or the HTTP API (directly or transitively). A capability with no caller is not part of this spec corpus — cut it, or wire it in and describe the entry point that reaches it.

## 6. Explicitly out of scope (until a spec says otherwise)

- Multiple simultaneously connected watches (only the first detected device is ever used).
- Activity file (`.fit` in `ACTIVITY/`) download/analysis — only `COURSES/` and `NEWFILES/` are managed.
- Authentication/multi-user access to the GUI.
- Course backup/verification and a direct USB/PTP transfer client were both cut from v1 for having no reachable entry point (see §5's "no dead code" invariant) — either may return as a real feature spec, with a UI/CLI surface, post-v1.
- DEM-based elevation enrichment (see [gpx-fit-conversion](features/gpx-fit-conversion.md) Non-Goals).

## 7. Regeneration & Testing Requirement

Per [spec/README.md](README.md)'s "rebuild test," a single-shot (re)generation from this corpus — run per [regeneration.md](regeneration.md) — is not done until it passes a concrete check, not just a manual read-through:

- The **walking skeleton chain** (§2) MUST have a passing automated test (`tests/test_skeleton.py`) that: starts the server on a free port, requests `/api/device` and gets a well-formed response (connected or not), and requests `/` and gets the index page. `tests/test_gui_server.py`'s existing check stays as-is alongside it.
- Every `tier: feature` spec's stated requirements SHOULD have at least one corresponding test (unit-level for `converter/*` and `device/*`, integration-level for the HTTP API) before that feature is considered implemented, not just present in `src/`.
- `pytest` MUST pass in full before a single-shot generation is reported as complete.
