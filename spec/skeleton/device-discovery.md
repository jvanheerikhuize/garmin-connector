---
id: device-discovery
title: Device Discovery and Metadata Extraction
tier: skeleton
status: implemented
owners: [jerry]
depends_on: []
implements_requirements: [FR-1, FR-2]
relies_on_facts: [FCT-1, FCT-2, FCT-3, FCT-4, FCT-5, FCT-6, FCT-7, FCT-8, FCT-9]
relies_on_assumptions: [ASM-3, ASM-4]
last_updated: 2026-09-15
---

# Device Discovery and Metadata Extraction

`internal/device/discover.go`
`internal/device/xml.go`

## Constitution Alignment

- **Implements Requirements:** `FR-1` (Linux Device Discovery), `FR-2` (Device Metadata Extraction)
- **Relies on Facts:** `FCT-3` (GARMIN structure), `FCT-4` (GVFS paths), `FCT-5` (XML fields), `FCT-6` (XML namespaces), `FCT-7` (Mount fragmentation), `FCT-8` (MTP Casing), `FCT-9` (Multi-user EACCES)
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
- A candidate path qualifies if it contains a `GARMIN` directory (case-insensitive).
- MUST search up to 2 directory levels deep within the candidate path, as MTP often hides `GARMIN` behind logical volume folders like `Internal Storage/` (FCT-3).
- MUST gracefully skip paths that suffer from permission denied errors without failing the overall search (FCT-9).

### Metadata Extraction (FR-2, FCT-2, FCT-3, FCT-5, FCT-6)
- Once a `GARMIN` directory is found, MUST read the `GarminDevice.xml` file (case-insensitive filename match).
- MUST strip or ignore XML namespaces during unmarshaling (`encoding/xml` handles this when tags don't specify namespaces).
- MUST extract the following fields from the XML:
  - `Model/Description` -> `model`
  - `Id` -> `id`
  - `Model/SoftwareVersion` -> `software_version`
  - `Model/PartNumber` -> `part_number`
- If the XML file is missing, empty, or fails to parse, MUST fallback gracefully, yielding a partial device struct (e.g., `model="Generic Garmin"`, empty ID) rather than throwing an error (ASM-4).

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
