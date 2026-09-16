---
id: device-info
title: Device Detailed Information (info command)
tier: feature
status: implemented
owners: [jerry]
depends_on: [cli-entrypoint, device-discovery]
implements_requirements: [FR-5]
relies_on_facts: [FCT-2, FCT-4, FCT-5, FCT-6]
relies_on_assumptions: [ASM-1, ASM-2, ASM-3, ASM-4]
last_updated: 2026-09-16
---

# Device Detailed Information (`info`)

`internal/cli/info.go`
`internal/device/detailed.go`
`internal/device/storage.go`
`internal/device/apps.go`

Depends on: [CLI Entrypoint](../skeleton/cli-entrypoint.md), [Device Discovery](../skeleton/device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-5` (Detailed Diagnostics and Storage Inspection)
- **Relies on Facts:** `FCT-2` (`GarminDevice.xml`), `FCT-4` (GVFS paths), `FCT-5` (XML fields), `FCT-6` (XML namespaces)
- **Relies on Assumptions:** `ASM-1` (On-demand execution), `ASM-2` (Structured output), `ASM-3` (Single device workflow), `ASM-4` (Graceful degradation)

## Purpose

Extracts rich hardware, storage, and software inventory from a connected Garmin watch without modifying device state. While `status` provides a quick connection check and basic identification, `info` aggregates filesystem capacity metrics, installed Connect IQ applications, and sub-component firmware versions into a comprehensive report for diagnostics and user inspection.

## Scope

**In scope:**
- Querying filesystem storage statistics (total capacity, used bytes, free bytes, and utilization percentage) via OS filesystem stat calls on the watch mount point.
- Parsing `<IQAppExt>` from `GarminDevice.xml` to list installed Connect IQ apps, app types, versions, and app space limits.
- Extracting sub-component firmware versions (e.g. GPS, wireless chipset, sensor hub) from `<UpdateFile>` entries in `GarminDevice.xml`.
- Human-readable formatted terminal output and machine-readable `--json` output.
- Graceful degradation if XML extension sections (like Connect IQ) are absent.

**Out of scope:**
- Modifying, installing, or deleting Connect IQ applications.
- Transferring activity or map files (covered by separate sync/export specs).
- Over-the-air or USB firmware flashing.

## Requirements

### Subcommand Definition
- MUST expose a CLI subcommand: `garmin-connector info`.
- MUST support the `--json` flag to emit the full structured dataset.
- When no device is connected:
  - If `--json` is specified: MUST output `{"connected": false, "device": null}` and exit code `0`.
  - If `--json` is omitted: MUST output `"No Garmin device detected."` and exit code `0`.

### Storage Inspection
- MUST query filesystem statistics for the device mount path using standard OS stat calls (`statfs`).
- MUST report:
  - `total_bytes` (uint64)
  - `free_bytes` (uint64)
  - `used_bytes` (uint64)
  - `used_percentage` (float64, 0.0 to 100.0, rounded to 1 decimal place)
- In human-readable output, storage sizes MUST be formatted in human-friendly units (e.g. `GB` or `MB`).

### Connect IQ App Inventory
- MUST parse the `<IQAppExt>` block inside `<Extensions>` in `GarminDevice.xml` if present.
- MUST extract:
  - `vm_version` (string)
  - `max_apps` (int)
  - `app_space_bytes` (int64)
  - `apps`: list of installed apps, each containing:
    - `name` (string)
    - `type` (string, e.g. `watchface`, `watch-app`, `data-field`, `audio-content-provider-app`)
    - `version` (string)
    - `app_id` (string)
    - `file_name` (string)
- If `<IQAppExt>` is not present, `apps` MUST default to an empty list rather than failing.

### Component Firmware Versions
- MUST extract subsystem firmware versions from `<UpdateFile>` entries located inside `<MassStorageMode>` in `GarminDevice.xml`:
  - `gps_version` (string): from entry where `<FileName>` contains `gup4603` or `gps`. Format is `<Major>.<Minor>`.
  - `wireless_version` (string): from entry where `<FileName>` contains `gup3651`, `ble`, or `ant`. Format is `<Major>.<Minor>`.
  - `sensor_hub_version` (string): from entry where `<FileName>` contains `gup4605` or `sensor`. Format is `<Major>.<Minor>`.
- If specific component records are absent, their version fields MUST be empty strings.

## Data Shapes / Interfaces

```go
package device

type StorageInfo struct {
	TotalBytes     uint64  `json:"total_bytes"`
	UsedBytes      uint64  `json:"used_bytes"`
	FreeBytes      uint64  `json:"free_bytes"`
	UsedPercentage float64 `json:"used_percentage"`
}

type AppInfo struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	Version  string `json:"version"`
	AppID    string `json:"app_id"`
	FileName string `json:"file_name"`
}

type ConnectIQInfo struct {
	VMVersion     string    `json:"vm_version"`
	MaxApps       int       `json:"max_apps"`
	AppSpaceBytes int64     `json:"app_space_bytes"`
	Apps          []AppInfo `json:"apps"`
}

type ComponentVersions struct {
	GPS       string `json:"gps,omitempty"`
	Wireless  string `json:"wireless,omitempty"`
	SensorHub string `json:"sensor_hub,omitempty"`
}

type DetailedInfo struct {
	Info                     // Embedded base metadata (Model, ID, SoftwareVersion, PartNumber, MountPath)
	Storage    StorageInfo   `json:"storage"`
	ConnectIQ  ConnectIQInfo `json:"connect_iq"`
	Components ComponentVersions `json:"components"`
}

// GetDetailedInfo gathers comprehensive device, storage, and app metrics.
func GetDetailedInfo(dev *Info) (*DetailedInfo, error)
```

### JSON Output Contract

```json
{
  "connected": true,
  "device": {
    "model": "Venu X1",
    "id": "3617019779",
    "software_version": "1829",
    "part_number": "006-B4603-00",
    "mount_path": "/run/user/1000/gvfs/mtp:host=091e_51fb_0000d7975783",
    "storage": {
      "total_bytes": 31058427904,
      "used_bytes": 14691237888,
      "free_bytes": 16367190016,
      "used_percentage": 47.3
    },
    "connect_iq": {
      "vm_version": "6.0.3",
      "max_apps": 32,
      "app_space_bytes": 67108864,
      "apps": [
        {
          "name": "Spotify",
          "type": "audio-content-provider-app",
          "version": "72",
          "app_id": "6eb48a8f-9bd8-4fe0-99e7-28d787c8a711",
          "file_name": "G8TI4826.PRG"
        }
      ]
    },
    "components": {
      "gps": "11.02",
      "wireless": "29.27",
      "sensor_hub": "1.02"
    }
  }
}
```

## Non-Goals

- Writing or uploading apps to the Connect IQ store.
- Interactive app configuration or settings editing (`.SET` file editing).
