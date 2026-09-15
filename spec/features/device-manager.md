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

`internal/device/manager.go`

Depends on: [device-detection](../device-detection.md), [gpx-fit-conversion](gpx-fit-conversion.md).

## Purpose

Sideload, list, and delete course files (`.fit`/`.gpx`) on a detected Garmin watch using standard Go `os` operations, relying on the host OS to handle mounts (FUSE for Linux GVFS, macOS Volumes, or Windows standard mass storage drives).

## Requirements

### Construction
- Manager functions should accept a `GarminDeviceInfo` struct.
- If no device is provided/found by the detector, functions should return a standard Go `error` instructing the user to connect via USB.

### Sideloading (`SideloadRoute`)
- Accepts a `.gpx` or `.fit` source path (or `io.Reader`), a `Sport` type (default `CYCLING`), and an optional `courseName`.
- Returns an error if the source is invalid or unreadable.
- `.gpx` input: pass to `converter.ConvertGPXToFIT` (in-memory `[]byte`), then transfer the resulting byte slice to the device.
- `.fit` input: transfer as-is, no conversion.
- Any other extension: return an error naming the unsupported format.
- Returns the destination `string` path the file was written to (on the watch's NEWFILES directory naming).

### Transfer strategy
Target directory is `device.NewFilesDir`, falling back to `filepath.Join(device.GarminDir, "NEWFILES")` if unset.

- Create the NEWFILES dir if missing (`os.MkdirAll`), then use `os.WriteFile` or `io.Copy` to copy the file.
- Propagate any `error`.

### Listing (`ListCourses`)
- Returns a `[]CourseFileSummary` combining:
  1. Files directly in `CoursesDir` (if it exists) with `.fit`/`.gpx` extension (case-insensitive) — `Location: "COURSES"`.
  2. Files directly in `NewFilesDir` (if it exists) with the same extension filter — `Location: "NEWFILES (Pending Sync)"`.
- Each entry: `Filename`, `FullPath`, `SizeBytes`, `ModifiedAt` (UTC, from `os.FileInfo`), `Location`.
- Both groups are sorted by filename; COURSES entries always precede NEWFILES entries in the combined list.
- Non-file entries and non-`.fit`/`.gpx` files are silently skipped.

### Deletion (`DeleteCourse`)
- Given a filename, attempt standard `os.Remove` in `CoursesDir` and `NewFilesDir`.
- Both directories are checked; any successful remove counts as deleted (returns `true`, `nil`). 
- Returns `false`, `nil` if the file was not found in either directory.

## Data Shapes / Interfaces

`internal/device/manager.go`:
```go
type CourseFileSummary struct {
    Filename   string    `json:"filename"`
    FullPath   string    `json:"full_path"`
    SizeBytes  int64     `json:"size_bytes"`
    ModifiedAt time.Time `json:"modified_at"` // UTC
    Location   string    `json:"location"`    // "COURSES" | "NEWFILES (Pending Sync)"
}

func SideloadRoute(device *GarminDeviceInfo, source []byte, ext string, sport converter.Sport, courseName string) (string, error)
func ListCourses(device *GarminDeviceInfo) ([]CourseFileSummary, error)
func DeleteCourse(device *GarminDeviceInfo, filename string) (bool, error)
```

## Non-Goals
- No fallback transfer mechanisms (like MTP over `libmtp`). We strictly rely on the FUSE mount provided by the OS.
- No conflict resolution when a file of the same name already exists at the destination (silently overwritten).
- No progress reporting/streaming for large transfers (Go's `os.WriteFile` handles local FUSE writes fast enough).
