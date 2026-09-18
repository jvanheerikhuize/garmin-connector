---
id: course-upload
title: Course Upload (upload command)
namespace: cli
status: implemented
owners: [jerry]
depends_on: [cli-entrypoint, device-discovery]
implements_requirements: [FR-6]
relies_on_facts: [FCT-8, FCT-12, FCT-13, FCT-15, FCT-17, FCT-23]
relies_on_assumptions: [ASM-7]
last_updated: 2026-09-18
---

# Course Upload (`upload`)

`internal/cli/upload.go`
`internal/device/upload.go`

Depends on: [CLI Entrypoint](cli-entrypoint.md), [Device Discovery](../core/device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-6`
- **Relies on Facts:** `FCT-8`, `FCT-12`, `FCT-13`, `FCT-15` (D-Bus Push has no in-process equivalent), `FCT-17` (`NewFiles` pre-exists on-device), `FCT-23` (URI reserved characters)
- **Relies on Assumptions:** `ASM-7`

## Purpose

The course upload capability allows users to transfer route and course files (such as `.fit` or `.gpx` files) from their local machine to a connected Garmin watch. This enables external routing tools to seamlessly sync new courses to the device without requiring graphical software.

## Scope

**In scope:**
- Transferring a local file to the Garmin device's `GARMIN/NewFiles` directory.
- Verifying the existence and read permissions of the local file before transfer.
- Validating the destination `NewFiles` directory exists on the connected device.
- Handling capitalization variations of `GARMIN/NewFiles` on the device (per `FCT-8`).

**Out of scope:**
- Validating the contents of the `.fit` or `.gpx` files.
- File format conversion (e.g., converting KML to GPX).
- Deleting or managing existing courses on the device.

## Requirements

### CLI Command Execution
- MUST provide an `upload` subcommand: `garmin-connector upload <local-file-path>`.
- MUST return a non-zero exit code if no file path is provided.
- MUST return a non-zero exit code if the specified local file does not exist or is not readable.
- MUST return a non-zero exit code if the specified local file does not end in `.fit` or `.gpx` (case-insensitive).

### Device Interaction
- MUST rely on `device-discovery` to locate the connected watch.
- MUST fail with a non-zero exit code if no watch is connected.
- MUST locate the `NewFiles` directory within the `GARMIN` directory, ignoring case sensitivity for both `GARMIN` and `NewFiles`.
- MUST copy the local file into the `NewFiles` directory.
- SHOULD preserve the original filename of the uploaded file.
- MUST overwrite any existing file in the `NewFiles` directory that has the exact same name.
- When the copy falls back to GVFS client tooling (`FCT-13`, `FCT-15`), the destination MUST be handed over as the plain local GVFS mount path or as a fully percent-encoded `mtp://` URI (`FCT-23`), so that a local filename containing `#`, `%`, `?` or a space (e.g. `ride #2.gpx`) arrives on the watch under exactly that name rather than being truncated or rejected.

### Feedback
- MUST output a success message to `stdout` upon completion.
- MUST output any failure reasons (e.g., "Device not found", "Local file unreadable", "NewFiles directory not found") to `stderr`.

## Data Shapes / Interfaces

### CLI Arguments
```
garmin-connector upload <file_path>

Arguments:
  file_path: string    # Absolute or relative path to the local course file (.gpx, .fit)
```

## Non-Goals
- We will not validate the internal schema or XML/binary validity of the uploaded files. File extension validation is deemed sufficient (as per `ASM-7`), and the Garmin watch's internal OS will handle (or reject) malformed contents silently upon disconnection.
