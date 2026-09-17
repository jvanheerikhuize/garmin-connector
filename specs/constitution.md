---
id: constitution
title: Constitution
last_updated: 2026-09-17
---

# Constitution

## 1. Purpose

A tool to connect a modern garmin watch to a laptop to exchange files over a USB connection.

## 2. Grounding Reality

### 2.1 External Facts
Facts are objective, verifiable truths about the external environment (hardware, third-party APIs, operating systems) that exist independently of this software.

| ID | Source / Origin | Fact | Verification Method | Impact / Traces |
|---|---|---|---|---|
| **FCT-1** | Physical Reality | The Garmin Venu X1 only supports the MTP protocol (no USB Mass Storage support). | USB device descriptor inspection (`lsusb` / OS device query) | Informs `FR-1` |
| **FCT-2** | Filesystem | `GarminDevice.xml` is the file that holds the device's metadata. | File inspection within `GARMIN/` filesystem root | Informs `FR-2`, `FR-5` |
| **FCT-3** | MTP Protocol | Garmin devices expose a `GARMIN` directory, but MTP often abstracts this behind a logical volume folder (e.g., `Internal Storage/`), meaning it may be nested 1-2 levels deep. | Mount structure inspection | Informs `FR-1`, `FR-2`, `FR-4`, `FR-5` |
| **FCT-4** | OS (Linux) | Linux dynamically mounts MTP devices via GVFS under `/run/user/<uid>/gvfs` using an `mtp:` prefix. | Linux GVFS documentation/testing | Informs `FR-1` |
| **FCT-5** | Filesystem | `GarminDevice.xml` contains specific metadata fields. `Description`, `SoftwareVersion`, and `PartNumber` are nested inside the `<Model>` tag. `Id` is at the root. Subsystem versions and Connect IQ app definitions are nested under `<MassStorageMode>` and `<Extensions>`. | XML file inspection | Informs `FR-2`, `FR-5` |
| **FCT-6** | XML Standard | `GarminDevice.xml` utilizes XML namespaces, which complicates standard parsing if not stripped. | XML file inspection | Informs `FR-2`, `FR-5` |
| **FCT-7** | OS (Linux) | Linux USB mount paths are highly fragmented across Desktop Environments and volume managers (GVFS, udisks2, manual). | OS architecture | Informs `FR-1` |
| **FCT-8** | Filesystem | Garmin watches expose internal storage over MTP with unpredictable character casing (e.g., `GARMIN` vs `Garmin`). | Filesystem inspection | Informs `FR-1`, `FR-2`, `FR-4`, `FR-5` |
| **FCT-9** | OS Security | Scanning wildcard paths like `/run/user/*` on a multi-user Linux system triggers OS-level `EACCES` (Permission Denied) errors. | OS security model | Informs `FR-1` |
| **FCT-10** | MTP Protocol | MTP file traversal is significantly slower than local disk access, causing severe latency on deep recursive directory scans. | MTP protocol limits | Informs `FR-4`, `FR-8` |
| **FCT-11** | MTP Protocol | MTP does not reliably expose standard POSIX metadata (symlinks, permissions, ownership). | MTP protocol limits | Informs `FR-4`, `FR-8` |
| **FCT-12** | Physical Reality | Garmin watches process new courses by reading compatible files (e.g., `.fit`, `.gpx`) placed into the `GARMIN/NewFiles/` directory on the internal storage. | Hardware documentation / testing | Informs `FR-6` |
| **FCT-13** | OS (Linux) | GVFS FUSE mounts for MTP devices do not support standard POSIX file creation (`open(O_CREAT)` returns `EOPNOTSUPP`), requiring file transfers over GVFS to use GVFS D-Bus Push operations. | Empirical verification on GVFS MTP mount | Informs `FR-6` |

### 2.2 Assumptions
Assumptions are beliefs about user behavior, workflows, or integration needs that justify architectural decisions.

| ID | Source / Origin | Assumption | Verification Method | Impact / Traces |
|---|---|---|---|---|
| **ASM-1** | Product Decision | Users and external systems invoke the tool on-demand to query state, rather than connecting to a persistent background daemon. | User research / workflow analysis | Informs `FR-3`, `FR-4`, `FR-5`, `FR-8` |
| **ASM-2** | Stakeholder Request | External scripts/tools require machine-readable structured output to consume device status headlessly. | Integration requirements | Informs `FR-3`, `FR-4`, `FR-5` |
| **ASM-3** | User Research | Users typically connect only one Garmin watch via USB at any given time; surfacing the first detected device is sufficient. | User research | Scopes `FR-1`, `FR-8` |
| **ASM-4** | Product Decision | Knowing a device is connected is more valuable than strict metadata accuracy; graceful degradation is preferred over a hard failure. | Product decision | Scopes `FR-2`, `FR-5` |
| **ASM-5** | Product Decision | For file inspection, basic filesystem structure and metadata (name, size, modification time) are sufficient; complete POSIX file semantics are unnecessary. | Product decision | Scopes `FR-4`, `FR-8` |
| **ASM-6** | UX Principle | Deep recursive directory traversal is only useful if it returns quickly; imposing limits prevents the CLI from hanging indefinitely on MTP endpoints. | User experience | Scopes `FR-4`, `FR-8` |
| **ASM-7** | Product Decision | The user is responsible for providing well-formed course files; restricting uploads by file extension (`.fit`, `.gpx`) is sufficient, and deep file schema validation is unnecessary. | Product decision | Scopes `FR-6` |
| **ASM-8** | User Preference | Users seeking a graphical interface prefer launching an on-demand local web server bound to localhost accessible via a standard web browser, without background daemon requirements. | User request | Informs `FR-7`, `FR-8` |

## 3. Requirements

### 3.1 Functional Requirements
- **FR-1: Linux Device Discovery**: Automatically detect connected Garmin watches across Linux mount points and GVFS/MTP paths (e.g., `/run/user/<uid>/gvfs`, `/media`, `/mnt`) without manual mount path configuration.
- **FR-2: Device Metadata Extraction**: Read and parse `GarminDevice.xml` (case-insensitive, XML namespaces stripped) to extract identifying metadata with graceful fallbacks on missing or malformed XML.
- **FR-3: CLI Status Inspection**: Provide a CLI command (`garmin-connector status`) to inspect and report device connection status and metadata to stdout in human-readable text or a machine-readable structured data format.
- **FR-4: Read-Only Filesystem Inspection**: Provide CLI commands (`ls`, `tree`) to explore the watch's internal filesystem structure and basic metadata without modifying contents.
- **FR-5: Detailed Diagnostics and Storage Inspection**: Provide a CLI command (`garmin-connector info`) to report real-time filesystem capacity metrics, installed Connect IQ applications, and sub-component firmware versions in human-readable text or a machine-readable structured data format.
- **FR-6: Course Upload**: Provide a CLI command (`garmin-connector upload <file>`) to transfer a route/course file to the watch's incoming directory (e.g., `GARMIN/NewFiles/`), allowing the device to process it upon disconnection.
- **FR-7: Web-Based GUI Dashboard**: Provide an on-demand local web server (e.g., `garmin-connector web`) that serves an interactive, responsive browser dashboard displaying real-time watch connection status, storage capacity metrics, and device diagnostics, backed by local JSON API endpoints.
- **FR-8: Web GUI Column View File Browser**: Provide an interactive Column View (macOS Finder-style Miller columns) file browser within the web GUI to navigate watch directories lazily, inspect file metadata and details in a preview pane, and download files from the watch.

### 3.2 Non-Functional Requirements
- **NFR-1: Fault Tolerance**: Absence of a connected watch is a valid state (exits `0`), never an exception. Unexpected disconnects or missing metadata must not cause unhandled crashes.
- **NFR-2: Standalone Execution**: Low CPU and memory overhead. The tool must be executable by the end-user without requiring them to pre-install language runtimes, package managers, or third-party libraries.
- **NFR-3: Exclusive Dependencies**: All dependencies must be strictly exclusive to this repository and its chosen implementation.

## 4. Architecture

```mermaid
flowchart LR
    CLI["CLI (status, info, ls, tree, upload)"] --> Detector["Device Detection (MTP / OS Mounts)"]
    Web["Web GUI Server (Dashboard & File Browser)"] --> Detector
    Detector --> Watch["Garmin Watch (GarminDevice.xml & Filesystem)"]
```

## 5. Out of Scope
- Native desktop GUI frameworks (e.g., GTK, Qt, Electron) — GUI is provided strictly via local browser interface.
- Non-Linux operating systems (macOS, Windows).
- Multiple simultaneously connected watches.
