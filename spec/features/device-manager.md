---
id: device-manager
title: Device Manager (Course File Operations)
tier: feature
status: implemented
owners: [jerry]
depends_on: [device-detection, gpx-fit-conversion]
last_updated: 2026-09-15
---

# Device Manager (Course File Operations)

`src/garmin_connector/device/manager.py` — `GarminDeviceManager`

Depends on: [device-detection](../device-detection.md), [gpx-fit-conversion](gpx-fit-conversion.md).

## Purpose

Sideload, list, and delete course files (`.fit`/`.gpx`) on a detected Garmin watch using standard POSIX filesystem operations, relying on the OS to handle mounts (FUSE for GVFS or standard mass storage).

## Requirements

### Construction
- `GarminDeviceManager(device=None, custom_mount=None)`:
  - If `device` is passed, use it directly (no re-detection).
  - Otherwise call `GarminDeviceDetector.get_first_device(custom_mount)`; if nothing is found, raise `ConnectionError` with a message instructing the user to connect via USB or pass `--mount`.

### Sideloading (`sideload_route`)
- Accepts a `.gpx` or `.fit` source path, a `Sport` (default `CYCLING`), and an optional `course_name`.
- Raises `FileNotFoundError` if the source doesn't exist.
- `.gpx` input: convert to FIT via a temp directory (`convert_gpx_to_fit`) using the given `course_name`/`sport`, then transfer the resulting temp `.fit` file.
- `.fit` input: transfer as-is, no conversion.
- Any other extension: raise `ValueError` naming the unsupported format; only `.gpx` and `.fit` are supported.
- Returns the destination `Path` the file was written to (on the watch's NEWFILES directory naming).

### Transfer strategy (`_transfer_to_newfiles`, internal)
Target directory is `device.newfiles_dir`, falling back to `device.garmin_dir / "NEWFILES"` if unset.

- Create the NEWFILES dir if missing, then use standard `Path.write_bytes()` to copy the file.
- If that raises an `OSError`, it propagates as a `RuntimeError` or original exception.

### Listing (`list_courses`)
- Returns a `List[CourseFileSummary]` combining:
  1. Files directly in `courses_dir` (if it exists) with `.fit`/`.gpx` extension (case-insensitive) — `location="COURSES"`.
  2. Files directly in `newfiles_dir` (if it exists) with the same extension filter — `location="NEWFILES (Pending Sync)"` (the single canonical value; MUST NOT vary).
- Each entry: `filename`, `full_path`, `size_bytes`, `modified_at` (UTC, from mtime), `location`.
- Both groups are sorted by filename; COURSES entries always precede NEWFILES entries in the combined list.
- Non-file entries and non-`.fit`/`.gpx` files are silently skipped.

### Deletion (`delete_course`)
- Given a filename, attempt POSIX unlink in `courses_dir` and `newfiles_dir`.
- Both directories are checked; any successful unlink counts as deleted (returns `True`). 
- Returns `False` if the file was not found in either directory.

## Data Shapes / Interfaces

`device/manager.py`:
```
class GarminDeviceManager:
    __init__(self, device: Optional[GarminDeviceInfo] = None, custom_mount: Optional[str | Path] = None)
    device: GarminDeviceInfo
    sideload_route(self, source_path: str | Path, sport: Sport = Sport.CYCLING, course_name: Optional[str] = None) -> Path
    list_courses(self) -> List[CourseFileSummary]
    delete_course(self, filename: str) -> bool
```

`CourseFileSummary`:
```
filename: str
full_path: Path
size_bytes: int
modified_at: datetime   # UTC
location: str            # "COURSES" | "NEWFILES (Pending Sync)"
```

## Non-Goals
- No fallback transfer mechanisms (like MTP over `gio`). We strictly rely on the FUSE mount provided by the OS.
- No conflict resolution when a file of the same name already exists at the destination (silently overwritten).
- No progress reporting/streaming for large transfers.
