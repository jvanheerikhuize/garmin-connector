---
id: device-discovery
title: Device Discovery and Metadata Extraction
namespace: core
status: implemented
owners: [jerry]
depends_on: []
implements_requirements: [FR-1, FR-2]
relies_on_facts: [FCT-1, FCT-2, FCT-3, FCT-4, FCT-5, FCT-6, FCT-7, FCT-8, FCT-9, FCT-18]
relies_on_assumptions: [ASM-3, ASM-4]
last_updated: 2026-09-17
---

# Device Discovery and Metadata Extraction

`internal/device/discover.go`
`internal/device/xml.go`

## Constitution Alignment

- **Implements Requirements:** `FR-1` (Linux Device Discovery), `FR-2` (Device Metadata Extraction)
- **Relies on Facts:** `FCT-3` (GARMIN structure), `FCT-4` (GVFS paths), `FCT-5` (XML fields), `FCT-6` (XML namespaces), `FCT-7` (Mount fragmentation), `FCT-8` (MTP Casing), `FCT-9` (Multi-user EACCES), `FCT-18` (mount-enumeration APIs unreliable; scan paths directly)
- **Relies on Assumptions:** `ASM-3` (Single device workflow), `ASM-4` (Graceful metadata fallback)

## Purpose

Responsible for scanning the local Linux filesystem for MTP mounts that look like a Garmin watch, and parsing its internal `GarminDevice.xml` file to extract identifying metadata.

## Scope

**In scope:**
- Scanning standard Linux mount points (`/run/user/<uid>/gvfs`, `/media`, `/mnt`).
- Path and directory resolution for the `GARMIN` folder.
- Parsing `GarminDevice.xml`.

**Out of scope:**
- HTTP, WebSockets, or UI presentation.
- Modifying or writing files to the watch.
- Managing multiple simultaneously connected watches (only the first found is returned).

## Requirements

### Filesystem Discovery (FR-1, FCT-4, FCT-7)
- MUST scan candidate paths:
  1. `/run/user/*/gvfs/*`
  2. `/media/*/*`
  3. `/mnt/*`
- A candidate path qualifies if it contains a `GARMIN` directory (case-insensitive). Only directories qualify; a plain file named `GARMIN` MUST be ignored.
- MUST search up to 2 directory levels deep within the candidate path, as MTP often hides `GARMIN` behind logical volume folders like `Internal Storage/` (FCT-3). Precisely: `GARMIN` MAY be a direct child of the candidate (`<candidate>/GARMIN`) or nested beneath at most two intermediate directories (`<candidate>/a/GARMIN`, `<candidate>/a/b/GARMIN`); deeper matches MUST NOT be considered.
- Candidates MUST be examined in the order of the pattern list above (glob results in lexical order); the first candidate containing a `GARMIN` directory wins (ASM-3).
- MUST gracefully skip paths that suffer from permission denied errors — or any other read error — without failing the overall search (FCT-9). Discovery never fails: the result is either one device or "none".
- The resulting `mount_path` is the candidate path (e.g. the GVFS `mtp:host=...` mount), not the `GARMIN` directory. Discovery MUST also retain the **storage root** (the parent directory of `GARMIN`, e.g. `<mount_path>/Internal Storage`) and the resolved `GARMIN` directory path for downstream specs ([file-browser](../cli/file-browser.md) lists relative to the storage root; [device-info](../cli/device-info.md) re-reads the XML; [course-upload](../cli/course-upload.md) transfers files to `GARMIN/NewFiles`). These two paths are internal and MUST NOT appear in the JSON output.

### Metadata Extraction (FR-2, FCT-2, FCT-3, FCT-5, FCT-6)
- Once a `GARMIN` directory is found, MUST read the `GarminDevice.xml` file located directly inside it (case-insensitive filename match, e.g. `garmindevice.XML`).
- MUST strip or ignore XML namespaces during unmarshaling (`encoding/xml` handles this when tags don't specify namespaces).
- MUST extract the following fields from the XML:
  - `Model/Description` -> `model`
  - `Id` -> `id`
  - `Model/SoftwareVersion` -> `software_version`
  - `Model/PartNumber` -> `part_number`
- If the XML file is missing, empty, or fails to parse, MUST fallback gracefully, yielding a partial device struct (`model="Generic Garmin"`, all other metadata fields empty strings) rather than throwing an error (ASM-4). The same `"Generic Garmin"` fallback applies to `model` alone when the XML parses but `Model/Description` is blank; the other fields are then taken from the XML as-is.

## Data Shapes / Interfaces

```yaml
DeviceInfo:
  model: string            # Device model name or description
  id: string               # Unique device ID
  software_version: string # Main software version
  part_number: string      # Device part number
  mount_path: string       # Detected local mount path
```

## Non-Goals

- macOS or Windows drive letter scanning.
- Subscribing to OS events (e.g., `inotify` or `dbus`) for real-time mount detection (this is a one-shot CLI).
