---
id: device-detection
title: Device Detection
tier: skeleton
status: implemented
owners: [jerry]
depends_on: []
last_updated: 2026-09-15
---

# Device Detection

`src/garmin_connector/device/detector.py` — `GarminDeviceDetector`

## Purpose

Read-only discovery of connected Garmin watches on Linux across filesystem mounts (FUSE/mass-storage), without requiring the user to know or supply a mount path. This is the sensing half of the walking skeleton: without it, nothing else in the app can know a watch exists.

## Scope

**In scope:** locating a connected watch's `GARMIN/` directory via POSIX mounts and reading its identifying metadata.

**Out of scope:** anything that writes to the watch or host filesystem (see [device-manager](features/device-manager.md)); anything HTTP-facing (see [gui-bootstrap](gui-bootstrap.md)).

## Requirements

### Candidate mount root discovery (`_find_candidate_roots`)
- MUST scan `/run/user/<uid>/gvfs/` for entries whose name contains `mtp:` or `garmin` (case-insensitive); for each match, also scan one level of subdirectories (handles the common `mtp:host=.../Internal Storage/GARMIN` or `Primary/GARMIN` nesting).
- MUST also scan these USB mass-storage style roots, one level deep, for any directory: `/media/<user>`, `/media`, `/run/media/<user>`, `/mnt`.
- MUST tolerate any of these roots not existing (skip silently).
- MUST support an explicit `custom_path` override that bypasses auto-discovery entirely.

### GARMIN directory resolution
- A candidate root qualifies if it either *is* a directory literally named `GARMIN` (case-insensitive) or *contains* one as an immediate child.
- Candidates without a `GARMIN` directory MUST be gracefully discarded without crashing or returning unbound variables. Watches mounted via MTP often expose sibling folders (like `Audiobooks`, `Music`, `Podcasts`) alongside `GARMIN` inside the `Internal Storage` or `Primary` volumes, and these must be cleanly ignored.

### Device metadata parsing (`_parse_garmin_xml`)
- MUST look for `GarminDevice.xml`, `GARMIN.XML`, `garmindevice.xml`, `garmin.xml` (first match wins) inside the `GARMIN` directory.
- MUST strip XML namespaces before querying so watches with differing namespace URIs still parse.
- Extracts, with fallbacks: model name (`Model/Description` → `Description`, default `"Garmin Device"`), unit ID (`Id` → `Unit/Id`), software version (`SoftwareVersion` → `App/Version/VersionRss`), part number (`Model/PartNumber`).
- MUST NOT raise if the XML is missing or malformed — return `("Garmin Device", None, None, None)` on any parse failure. If no XML file is found at all, use `("Garmin Generic", None, None, None)` instead.

### Subdirectory resolution
- Detects `NEWFILES`, `COURSES`, `ACTIVITY` subdirectories case-insensitively by scanning immediate children.
- If `NEWFILES` or `COURSES` don't exist yet, MUST still populate them as the *expected* path (`garmin_dir / "NEWFILES"` etc.) rather than `None`, so downstream code can create them on demand. `ACTIVITY` has no such fallback — stays `None` if absent.

### Public API
- `detect_devices(custom_path=None) -> List[GarminDeviceInfo]` — full scan, returns one entry per candidate root that resolved a GARMIN directory.
- `get_first_device(custom_path=None) -> Optional[GarminDeviceInfo]` — convenience wrapper returning the first result or `None`.
- MUST NOT raise for permission errors or missing paths anywhere in this scan — best-effort, silent skip.

## Data Shapes / Interfaces

`device/detector.py`:
```
class GarminDeviceDetector:        # all classmethods/staticmethods, no instance state
    detect_devices(custom_path=None) -> List[GarminDeviceInfo]
    get_first_device(custom_path=None) -> Optional[GarminDeviceInfo]
```

`device/__init__.py` re-exports: `GarminDeviceDetector, GarminDeviceInfo, GarminDeviceManager`.

`garmin_connector/__init__.py` exposes `__version__`.

`GarminDeviceInfo`:
```
model_name: str
unit_id: Optional[str]
software_version: Optional[str]
part_number: Optional[str]
mount_point: Path            # the candidate root (or its parent if GARMIN dir == candidate itself)
garmin_dir: Path
newfiles_dir: Optional[Path]
courses_dir: Optional[Path]
activities_dir: Optional[Path]
```

## Non-Goals
- No caching — every call re-scans the filesystem.
- No Windows/macOS mount conventions.
- No disambiguation UI when multiple devices/candidates match — only the first is ever surfaced to the rest of the app.
