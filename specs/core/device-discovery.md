---
id: device-discovery
title: Device Discovery and Metadata Extraction
namespace: core
status: implemented
owners: [jerry]
depends_on: []
implements_requirements: [FR-1, FR-2]
relies_on_facts: [FCT-1, FCT-2, FCT-3, FCT-4, FCT-5, FCT-6, FCT-7, FCT-8, FCT-9, FCT-13, FCT-18, FCT-20, FCT-27]
relies_on_assumptions: [ASM-3, ASM-4, ASM-13]
last_updated: 2026-11-08
---

# Device Discovery and Metadata Extraction

`internal/device/discover.go`
`internal/device/xml.go`

## Constitution Alignment

- **Implements Requirements:** `FR-1` (Linux Device Discovery), `FR-2` (Device Metadata Extraction)
- **Relies on Facts:** `FCT-3` (GARMIN structure), `FCT-4` (GVFS paths), `FCT-5` (XML fields), `FCT-6` (XML namespaces), `FCT-7` (Mount fragmentation), `FCT-8` (MTP Casing), `FCT-9` (Multi-user EACCES), `FCT-13`/`FCT-20` (GVFS client tooling and its module directory), `FCT-18` (mount-enumeration APIs unreliable; scan paths directly), `FCT-27` (stale MTP mount after a replug)
- **Relies on Assumptions:** `ASM-3` (Single device workflow), `ASM-4` (Graceful metadata fallback), `ASM-13` (GVFS client tooling installed)

## Purpose

Responsible for scanning the local Linux filesystem for MTP mounts that look like a Garmin watch, and parsing its internal `GarminDevice.xml` file to extract identifying metadata.

## Scope

**In scope:**
- Scanning standard Linux mount points (GVFS MTP mounts `/run/user/<uid>/gvfs/mtp:*`, `/media`, `/mnt`).
- Path and directory resolution for the `GARMIN` folder.
- Parsing `GarminDevice.xml`.
- Recovering a stale GVFS MTP mount by remounting it (`FCT-27`).

**Out of scope:**
- HTTP, WebSockets, or UI presentation.
- Modifying or writing files to the watch. (Remounting changes only the desktop's connection to the watch, never its contents.)
- Managing multiple simultaneously connected watches (only the first found is returned).

## Requirements

### Filesystem Discovery (FR-1, FCT-4, FCT-7)
- MUST scan candidate paths:
  1. `/run/user/*/gvfs/mtp:*`
  2. `/media/*/*`
  3. `/mnt/*`
- Only GVFS mounts of the MTP backend (`mtp:` prefix, FCT-4) are candidates. Other GVFS backends under the same directory (e.g. `google-drive:…`, `smb-share:…`, `sftp:…`) MUST NOT be listed or traversed, even if they contain a `GARMIN` directory (FR-1): they are not the watch, and walking a remote backend can take seconds.
- A candidate path qualifies if it contains a `GARMIN` directory (case-insensitive). Only directories qualify; a plain file named `GARMIN` MUST be ignored.
- MUST search up to 2 directory levels deep within the candidate path, as MTP often hides `GARMIN` behind logical volume folders like `Internal Storage/` (FCT-3). Precisely: `GARMIN` MAY be a direct child of the candidate (`<candidate>/GARMIN`) or nested beneath at most two intermediate directories (`<candidate>/a/GARMIN`, `<candidate>/a/b/GARMIN`); deeper matches MUST NOT be considered.
- Candidates MUST be examined in the order of the pattern list above (glob results in lexical order); the first candidate containing a `GARMIN` directory wins (ASM-3).
- Within one candidate the search is breadth-first: the candidate's own children are examined before any grandchild, and grandchildren before great-grandchildren; entries at each level are examined in lexical (byte) order. The first `GARMIN` directory reached this way wins. An entry qualifies as a directory (both for `GARMIN` itself and for intermediate levels) if it resolves to one, i.e. a symbolic link to a directory counts.
- MUST gracefully skip paths that suffer from permission denied errors — or any other read error — without failing the overall search (FCT-9). Discovery never fails: the result is either one device or "none".
- The resulting `mount_path` is the candidate path (e.g. the GVFS `mtp:host=...` mount), not the `GARMIN` directory. Discovery MUST also retain the **storage root** (the parent directory of `GARMIN`, e.g. `<mount_path>/Internal Storage`) and the resolved `GARMIN` directory path for downstream specs ([file-browser](../cli/file-browser.md) lists relative to the storage root; [device-info](../cli/device-info.md) re-reads the XML; [course-upload](../cli/course-upload.md) transfers files to `GARMIN/NewFiles`). These two paths are internal and MUST NOT appear in the JSON output.
- **Storage-root containment:** The storage root is the trust boundary for every downstream path operation (listing, download, preview, mutation). `/media/*` and `/mnt/*` candidates are ordinary filesystems that may contain symbolic links, unlike MTP (`FCT-11`). Downstream specs therefore resolve requested paths against the *real* (link-free) location and MUST refuse any path whose resolved form lies outside the storage root, treating it exactly like a non-existent path unless the downstream spec names a specific answer for that case (e.g. [gui/file-browser.md](../gui/file-browser.md) download answers `400 invalid file path`). Discovery MUST record the storage root in its resolved form so that comparison is well-defined. Read operations (listing, download, preview) resolve the full path including its final segment; mutations resolve every segment except the last, so that a symbolic link itself can be removed or replaced without acting on its target, while a link anywhere earlier in the path that leaves the root is refused.

### Stale MTP mount recovery (FR-1, FCT-27)
- A candidate is a **stale MTP mount** when its name is `mtp:host=<host>` with a non-empty `<host>`, and either its root cannot be listed, its root lists no entries, or none of its top-level entries can be listed. A readable MTP device without a `GARMIN` folder (e.g. a phone) is not stale and MUST NOT be remounted; non-MTP candidates are never stale.
- When a stale MTP candidate yields no `GARMIN` directory, discovery MUST attempt recovery before moving on to the next candidate:
  1. Unmount the GVFS location `mtp://<host>/` (with `<host>` percent-encoded per `FCT-23`) through the GVFS client tool, ignoring a failure (the mount may already be gone).
  2. Mount `mtp://<host>/` again through the same tool. If that fails, recovery has failed.
  3. Repeat the `GARMIN` search on the same candidate path every 250 ms until it succeeds or 5 seconds have passed since the mount command returned.
  If the `GARMIN` search then succeeds, the candidate is the device; otherwise discovery continues with the next candidate as usual.
- The GVFS client tool MUST be run with a repaired module directory exactly as for mutations (`FCT-20`, [cli/filesystem-manipulation.md](../cli/filesystem-manipulation.md)).
- Recovery MUST be attempted at most once per 30 seconds per `<host>` within one process, so that a dashboard polling a genuinely broken device does not remount it on every request. Concurrent discoveries MUST NOT start more than one recovery for the same host.
- Recovery never makes discovery fail: any error simply means "no device from this candidate".
- Tests MUST exercise recovery with a stand-in for the GVFS client tool (a stale empty `mtp:host=X` directory that the stand-in populates on `mount`), and MUST check the exact unmount/mount calls, the throttle, and that a readable non-Garmin MTP device is left alone.

### Metadata Extraction (FR-2, FCT-2, FCT-3, FCT-5, FCT-6)
- Once a `GARMIN` directory is found, MUST read the `GarminDevice.xml` file located directly inside it (case-insensitive filename match, e.g. `garmindevice.XML`).
- MUST strip or ignore XML namespaces during parsing, matching elements by local name only (`FCT-6`). The name of the document's root element is not checked.
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
- Mounting a watch that GVFS has not mounted at all (no `mtp:host=` directory exists); recovery only repairs an existing stale mount.
- Verifying that a candidate is really a Garmin device beyond the presence of a `GARMIN` directory (see Open Questions).

## Open Questions

- **Candidate qualification is by directory name only.** Any mounted volume under `/media/*/*` or `/mnt/*` that happens to contain a `GARMIN` folder — a USB stick with a backup of the watch, say — is reported as the connected watch, and every mutation surface will then operate on it. Should a candidate additionally require a readable `GARMIN/GarminDevice.xml` to qualify? That conflicts with `ASM-4`'s "Generic Garmin" fallback for a missing/unparseable XML, so it needs a product decision: either tighten qualification (and narrow `ASM-4` to *malformed* rather than *missing* XML), or accept the current looseness and document it as a known limitation. Raised by the 2026-09-18 audit.
