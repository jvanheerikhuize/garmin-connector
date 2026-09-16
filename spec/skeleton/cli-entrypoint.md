---
id: cli-entrypoint
title: CLI Entrypoint and Status Command
tier: skeleton
status: implemented
owners: [jerry]
depends_on: [device-discovery]
implements_requirements: [FR-3, NFR-1]
relies_on_facts: []
relies_on_assumptions: [ASM-1, ASM-2]
last_updated: 2026-09-15
---

# CLI Entrypoint and Status Command

`cmd/garmin-connector/main.go`
`internal/cli/status.go`

Depends on: [device-discovery](device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-3` (CLI Status Inspection), `NFR-1` (Fault Tolerance - clean exit on no device)
- **Relies on Assumptions:** `ASM-1` (On-demand execution assumption), `ASM-2` (Structured output assumption)

## Purpose

The single process entrypoint (`garmin-connector`) that a user invokes. It handles argument parsing, subcommand dispatch, and formatting the output of the device discovery process (either as human-readable text or structured JSON).

## Scope

**In scope:**
- Top-level `garmin-connector` CLI setup (using standard library or a lightweight CLI framework like Cobra).
- The `status` subcommand and its `--json` flag.
- Output formatting (stdout/stderr).
- Exit code management.

**Out of scope:**
- The actual filesystem traversal to find the device (handled by `device-discovery`).

## Requirements

### Subcommand Dispatch
- MUST expose a root command (`garmin-connector`).
- MUST register a `status` subcommand.
- MUST accept a `--version` flag on the root command that outputs `1.0.0`.
- MUST print help text and exit `0` when invoked with no arguments.
- MUST exit with a non-zero code and print usage to stderr when invoked with an unrecognized subcommand.

### Status Command Execution
- MUST accept a `--json` boolean flag on the `status` command.
- MUST invoke the device discovery module to find connected Garmin watches.
- MUST cleanly exit with code `0` if no watch is found (fault tolerance).
- MUST NOT panic or crash if unexpected device states are encountered.

### Output Formatting
- If `--json` is `true`:
  - MUST output a JSON representation of the device state to `stdout`.
  - MUST format disconnected states as `{"connected": false, "device": null}`.
  - MUST format connected states as `{"connected": true, "device": { ... }}` matching the shape returned by discovery.
- If `--json` is `false` (default):
  - MUST output a human-readable text summary to `stdout` (e.g., "Device found: Garmin Venu X1 (ID: 12345)").
  - MUST output "No Garmin device detected." if no device is found.

## Data Shapes / Interfaces

```go
// Output of garmin-connector status --json
{
  "connected": true,
  "device": {
    "model": "Garmin Venu X1",
    "id": "3123456789",
    "software_version": "14.20",
    "part_number": "010-02430-01",
    "mount_path": "/run/user/1000/gvfs/mtp:host=Garmin_Venu_X1"
  }
}
```

## Non-Goals

- Interactive prompts or TUI components.
- Persistent background daemons (runs once and exits).
