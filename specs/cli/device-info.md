---
id: device-info
title: Device Detailed Information (info command)
namespace: cli
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

Depends on: [CLI Entrypoint](cli-entrypoint.md), [Device Discovery](../core/device-discovery.md)

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
  - `total_bytes` (uint64): block count × block size
  - `free_bytes` (uint64): blocks available to an unprivileged user (`f_bavail`) × block size
  - `used_bytes` (uint64): `total_bytes − free_bytes` (so `used + free == total` always holds)
  - `used_percentage` (float64, 0.0 to 100.0, rounded to 1 decimal place; `0.0` when `total_bytes` is `0`)
- If the stat call fails, the storage section MUST degrade to all zeros rather than failing the command (ASM-4).
- In human-readable output, storage sizes MUST be formatted in human-friendly units using binary multiples (1 KB = 1024 bytes) with one decimal, e.g. `28.9 GB`, `64.0 MB`; values below 1 KB are printed as plain bytes (`512 B`).

### Connect IQ App Inventory
- MUST parse the `<IQAppExt>` block inside `<Extensions>` in `GarminDevice.xml` if present. Element names (verified against a Venu X1 on 2026-09-16, namespace `http://www.garmin.com/xmlschemas/IqExt/v1`):
  - `vm_version` (string) ← `<IQAppExt>/<VmVersion>`
  - `max_apps` (int) ← `<IQAppExt>/<MaxApps>`
  - `app_space_bytes` (int64) ← `<IQAppExt>/<AppSpace>`
  - `apps`: list of installed apps, one per `<IQAppExt>/<Apps>/<App>`, each containing:
    - `name` (string) ← `<AppName>`
    - `type` (string, e.g. `watchface`, `watch-app`, `data-field`, `audio-content-provider-app`) ← `<AppType>`
    - `version` (string) ← `<Version>`
    - `app_id` (string) ← `<AppId>` (not `<StoreId>`, which is the store listing identifier)
    - `file_name` (string) ← `<FileName>`
- The sibling `<IQAppExt>/<Preloads>/<App>` list (store preloads, carrying only `<StoreId>`/`<Version>`) and `<StoreKey>` MUST be ignored.
- If `<IQAppExt>` is not present, `apps` MUST default to an empty list (`[]`, never `null`) and the scalar fields to their zero values rather than failing.

### Component Firmware Versions
- MUST extract subsystem firmware versions from `<UpdateFile>` entries located inside `<MassStorageMode>` in `GarminDevice.xml` (each entry carries `<PartNumber>`, `<Version><Major/><Minor/></Version>`, `<Path>` and `<FileName>`):
  - `gps_version` (string): from entry where `<FileName>` contains `gup4603` or `gps`. Format is `<Major>.<Minor>`.
  - `wireless_version` (string): from entry where `<FileName>` contains `gup3651`, `ble`, or `ant`. Format is `<Major>.<Minor>`.
  - `sensor_hub_version` (string): from entry where `<FileName>` contains `gup4605` or `sensor`. Format is `<Major>.<Minor>`.
- The `<FileName>` substring match is case-insensitive (the device mixes `gup4603.gcd` and `GUPDATE.GCD`); entries are scanned in document order and the first match for a component wins.
- `<Major>.<Minor>` is rendered with `<Minor>` zero-padded to two digits (`11.02`, `29.27`, `1.02`), matching how the device writes it.
- If specific component records are absent, their version fields MUST be empty strings.

### Human-Readable Output
When `--json` is omitted the report MUST contain, in order: the same device summary block as `status`; a `Storage` section with `Total`, `Used` (with percentage) and `Free` lines (or `(unavailable)` when total is zero); a `Components` section with `GPS`, `Wireless` and `Sensor hub` lines (`-` when empty); and a `Connect IQ` section headed by `VM <vm_version>`, `<installed>/<max_apps> apps` and the app space, followed by a table of apps (name, type, version, file, app id) or `No Connect IQ apps installed.`.

## Data Shapes / Interfaces

```yaml
StorageInfo:
  total_bytes: integer
  used_bytes: integer
  free_bytes: integer
  used_percentage: float   # 0.0 to 100.0

AppInfo:
  name: string
  type: string             # watchface, watch-app, data-field, etc.
  version: string
  app_id: string
  file_name: string

ConnectIQInfo:
  vm_version: string
  max_apps: integer
  app_space_bytes: integer
  apps: array              # List of AppInfo objects

ComponentVersions:
  gps: string              # Optional
  wireless: string         # Optional
  sensor_hub: string       # Optional

DetailedInfo:
  device: DeviceInfo       # From device-discovery schema
  storage: StorageInfo
  connect_iq: ConnectIQInfo
  components: ComponentVersions
```

In the JSON contract below, `DeviceInfo`'s five fields are **flattened** into the `device` object alongside `storage`, `connect_iq` and `components` (there is no nested `device.device`). The `components` keys are `gps`, `wireless` and `sensor_hub` (the `*_version` names above are the requirement labels, not JSON keys).

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
