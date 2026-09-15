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

`internal/device/detector.go` and `internal/device/watcher.go`

## Purpose

Read-only discovery of connected Garmin watches across Windows, Linux, and macOS. Provides both a one-shot polling method and an event-driven `fsnotify` / OS hook watcher that feeds WebSockets for real-time reactivity.

## Scope

**In scope:** Locating a connected watch's `GARMIN/` directory, reading its identifying metadata, and emitting connect/disconnect events to a Go channel.

**Out of scope:** File mutation, HTTP/WebSocket transports.

## Requirements

### Candidate mount root discovery
- On Linux: Scan `/run/user/<uid>/gvfs/` for entries containing `mtp:` or `garmin` (case-insensitive). Scan `/media/<user>`, `/media`, `/run/media/<user>`, `/mnt`.
- On macOS: Scan `/Volumes`.
- On Windows: Iterate available drive letters (`A:\` to `Z:\`).
- MUST support an explicit `custom_path` override that bypasses auto-discovery entirely.

### GARMIN directory resolution
- A candidate root qualifies if it either *is* a directory named `GARMIN` (case-insensitive) or *contains* one as an immediate child.

### Device metadata parsing
- Parse `GarminDevice.xml` (case-insensitive) inside the `GARMIN` directory.
- Extract `Model/Description`, `Id`, `SoftwareVersion`, `PartNumber`.
- Fallbacks: If no XML, return `"Garmin Generic"`.

### Event-Driven Watcher (`watcher.go`)
- Must expose a `Watch(ctx context.Context, updates chan<- DeviceEvent)` function.
- `DeviceEvent` struct: `{ Connected bool, Device *GarminDeviceInfo }`.
- Under the hood, this can use a periodic ticker (e.g., 2 seconds) *internally* to avoid complex OS-specific volume mount hook setups, but it must only emit to the channel when the state *changes*. This abstracts the polling away from the HTTP/WebSocket layer.

### Public API
- `DetectDevices(customPath string) ([]GarminDeviceInfo, error)`
- `GetFirstDevice(customPath string) (*GarminDeviceInfo, error)`
- `WatchDevices(ctx context.Context) <-chan DeviceEvent`

## Data Shapes / Interfaces

```go
type GarminDeviceInfo struct {
    ModelName       string `json:"model_name"`
    UnitID          string `json:"unit_id,omitempty"`
    SoftwareVersion string `json:"software_version,omitempty"`
    PartNumber      string `json:"part_number,omitempty"`
    MountPoint      string `json:"mount_point"`
    GarminDir       string `json:"-"`
    NewFilesDir     string `json:"-"`
    CoursesDir      string `json:"-"`
}

type DeviceEvent struct {
    Connected bool
    Device    *GarminDeviceInfo
}
```

## Non-Goals
- No disambiguation UI when multiple devices match — only the first is surfaced.
