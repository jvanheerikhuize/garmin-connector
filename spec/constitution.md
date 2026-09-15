---
id: constitution
title: Constitution
last_updated: 2026-09-15
---

# Constitution

## 1. Purpose

A tool to connect a modern garmin watch to a laptop to exchange files over a USB connection.

## 2. Grounding Reality

### 2.1 External Facts
Facts are objective, verifiable truths about the external environment (hardware, third-party APIs, operating systems) that exist independently of this software.

| ID | Fact | Verification Method | Impact / Traces |
|---|---|---|---|
| **FCT-1** | The Garmin Venu X1 only supports the MTP protocol (no USB Mass Storage support). | USB device descriptor inspection (`lsusb` / OS device query) | Informs `FR-1` |
| **FCT-2** | `GarminDevice.xml` is the file that holds the device's metadata. | File inspection within `GARMIN/` filesystem root | Informs `FR-2` |
| **FCT-3** | Garmin devices expose a `GARMIN` directory at or near the root of the MTP mount, which contains the `GarminDevice.xml` file. | Mount structure inspection | Informs `FR-1`, `FR-2` |
| **FCT-4** | Linux dynamically mounts MTP devices via GVFS under `/run/user/<uid>/gvfs` using an `mtp:` prefix. | Linux GVFS documentation/testing | Informs `FR-1` |
| **FCT-5** | `GarminDevice.xml` contains specific metadata fields such as `Model/Description`, `Id`, `SoftwareVersion`, and `PartNumber`. | XML file inspection | Informs `FR-2` |
| **FCT-6** | `GarminDevice.xml` utilizes XML namespaces, which complicates standard parsing if not stripped. | XML file inspection | Informs `FR-2` |

### 2.2 Assumptions
Assumptions are beliefs about user behavior, workflows, or integration needs that justify architectural decisions.

| ID | Assumption | Verification Method | Impact / Traces |
|---|---|---|---|
| **ASM-1** | Users and external systems invoke the tool on-demand to query state, rather than connecting to a persistent background daemon. | User research / workflow analysis | Informs `FR-3` |
| **ASM-2** | External scripts/tools require machine-readable structured output to consume device status headlessly. | Integration requirements | Informs `FR-3` |

## 3. Requirements

### 3.1 Functional Requirements
- **FR-1: Linux Device Discovery**: Automatically detect connected Garmin watches across Linux mount points and GVFS/MTP paths (e.g., `/run/user/<uid>/gvfs`, `/media`, `/mnt`) without manual mount path configuration.
- **FR-2: Device Metadata Extraction**: Read and parse `GarminDevice.xml` (case-insensitive, XML namespaces stripped) to extract identifying metadata with graceful fallbacks on missing or malformed XML.
- **FR-3: CLI Status Inspection**: Provide a CLI command (`garmin-connector status`) to inspect and report device connection status and metadata to stdout in human-readable text or structured JSON (`--json`).

### 3.2 Non-Functional Requirements
- **NFR-1: Fault Tolerance**: Absence of a connected watch is a valid state (exits `0`), never an exception. Unexpected disconnects or missing metadata must not cause unhandled crashes.
- **NFR-2: Minimal Footprint**: Low CPU and memory overhead with zero external runtime dependencies.
- **NFR-3: Exclusive Dependencies**: All dependencies must be strictly exclusive to this repository and its chosen tech stack.

## 4. Architecture

```mermaid
flowchart LR
    CLI["CLI (status)"] --> Detector["Device Detection (MTP / OS Mounts)"] --> Watch["Garmin Watch (GarminDevice.xml)"]
```

## 5. Tech Stack

- **Language:** Go (Golang) — Chosen to satisfy NFR-2 (zero external runtime dependencies, compiled static binary) and NFR-3.

## 6. Out of Scope
- Graphical User Interface (GUI).
- Non-Linux operating systems (macOS, Windows).
- Course and activity file management, conversion, or sideloading.
- Multiple simultaneously connected watches.
