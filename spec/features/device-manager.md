---
id: device-manager
title: Device Manager (Course File Operations)
tier: feature
status: implemented
owners: [jerry]
depends_on: [device-detection, gpx-fit-conversion]
last_updated: 2026-09-14
---

# Device Manager (Course File Operations)

`src/garmin_connector/device/manager.py` — `GarminDeviceManager`

Depends on: [device-detection](../device-detection.md), [gpx-fit-conversion](gpx-fit-conversion.md).

## Purpose

Sideload, list, and delete course files (`.fit`/`.gpx`) on a detected Garmin watch, transparently handling both direct POSIX filesystem access (USB mass storage) and GIO/MTP transfer (GVFS-mounted watches).

## Construction
- `GarminDeviceManager(device=None, custom_mount=None)`:
  - If `device` is passed, use it directly (no re-detection).
  - Otherwise call `GarminDeviceDetector.get_first_device(custom_mount)`; if nothing is found, raise `ConnectionError` with a message instructing the user to connect via USB or pass `--mount`.

## Requirements

### Sideloading (`sideload_route`)
- Accepts a `.gpx` or `.fit` source path, a `Sport` (default `CYCLING`), and an optional `course_name`.
- Raises `FileNotFoundError` if the source doesn't exist.
- `.gpx` input: convert to FIT via a temp directory (`convert_gpx_to_fit`) using the given `course_name`/`sport`, then transfer the resulting temp `.fit` file.
- `.fit` input: transfer as-is, no conversion.
- Any other extension: raise `ValueError` naming the unsupported format; only `.gpx` and `.fit` are supported.
- Returns the destination `Path` the file was written to (on the watch's NEWFILES directory naming).

### Transfer strategy (`_transfer_to_newfiles`, internal)
Target directory is `device.newfiles_dir`, falling back to `device.garmin_dir / "NEWFILES"` if unset.

1. **If device is MTP and a NEWFILES GIO URI is known:**
   a. Try native transfer via PyGObject (`gi.repository.Gio`) — `Gio.File.copy` with `OVERWRITE`.
   b. If that raises for any reason, fall back to shelling out to the `gio copy --default-permissions <src> <uri>` CLI.
   c. If both fail, propagate the last error.
2. **Otherwise (or as the non-MTP path):** create the NEWFILES dir if missing, then a direct `write_bytes` POSIX copy.
   - If that raises `OSError` with `errno == 95` (operation not supported — typical of some MTP FUSE mounts that reject direct writes) AND a GIO NEWFILES URI is known, retry via the `gio copy` CLI as a last-resort fallback.
   - Any other `OSError`, or failure of the last-resort fallback, propagates as a `RuntimeError`/original exception.

Filenames are percent-encoded (`urllib.parse.quote`) when building GIO target URIs.

### Listing (`list_courses`)
- Returns a `List[CourseFileSummary]` combining:
  1. Files directly in `courses_dir` (if it exists) with `.fit`/`.gpx` extension (case-insensitive) — `location="COURSES"`.
  2. Files directly in `newfiles_dir` (if it exists) with the same extension filter — `location="NEWFILES (Pending Sync)"` (the single canonical value; MUST NOT vary).
- Each entry: `filename`, `full_path`, `size_bytes`, `modified_at` (UTC, from mtime), `location`.
- Both groups are sorted by filename (via `sorted(dir.iterdir())`); COURSES entries always precede NEWFILES entries in the combined list.
- Non-file entries and non-`.fit`/`.gpx` files are silently skipped.

### Deletion (`delete_course`)
- Given a filename, attempt POSIX unlink in `courses_dir` and `newfiles_dir` (both checked; any successful unlink counts as deleted — first error on either path is swallowed and iteration continues).
- If neither POSIX path deleted the file AND the device is MTP, fall back to `gio remove <uri>/<filename>` against courses then newfiles GIO URIs, stopping at the first success.
- Returns `True` if deleted via any path, `False` otherwise. Never raises for a missing file — returns `False`.

## Data Shapes / Interfaces

`CourseFileSummary`:
```
filename: str
full_path: Path
size_bytes: int
modified_at: datetime   # UTC
location: str            # "COURSES" | "NEWFILES (Pending Sync)" -- exactly these two values, nothing else
```

## Non-Goals
- No conflict resolution when a file of the same name already exists at the destination (silently overwritten).
- No progress reporting/streaming for large transfers.
- No retry/backoff beyond the two-tier fallback described above.
- No verification/backup API (`verify_staged_course`, `backup_courses`) — cut from v1: neither was reachable from any CLI/HTTP surface. Reintroduce only alongside an actual UI/CLI entry point that calls them.
