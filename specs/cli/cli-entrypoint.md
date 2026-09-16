---
id: cli-entrypoint
title: CLI Entrypoint and Status Command
namespace: cli
status: implemented
owners: [jerry]
depends_on: [device-discovery]
implements_requirements: [FR-3, NFR-1]
relies_on_facts: []
relies_on_assumptions: [ASM-1, ASM-2]
last_updated: 2026-09-16
---

# CLI Entrypoint and Status Command

`cmd/garmin-connector/main.go`
`internal/cli/root.go` (dispatch, usage, flag parsing shared by all subcommands)
`internal/cli/format.go` (JSON envelope and human-readable size formatting shared by all subcommands)
`internal/cli/status.go`

Depends on: [device-discovery](../core/device-discovery.md)

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
- MUST register the subcommands `status`, `info` ([device-info](device-info.md)), `ls`, `tree` ([file-browser](file-browser.md)), and `upload` ([course-upload](course-upload.md)).
- MUST accept a `--version` flag on the root command that outputs `1.0.0` (followed by a newline) to stdout and exits `0`.
- MUST print help text and exit `0` when invoked with no arguments, or with `--help`, `-h` or `help`. The help text MUST name every registered subcommand.
- MUST exit with code `2` and print an error naming the unknown command plus the usage text to stderr (nothing to stdout) when invoked with an unrecognized subcommand.
- Every subcommand MUST accept `--help`/`-h` (prints its own usage to stderr, exit `0`) and MUST exit `2` with a message on stderr on an unknown flag or invalid flag value.
- Flags MAY appear before or after positional arguments (e.g. `ls GARMIN --json` and `ls --json GARMIN` are equivalent).

### Status Command Execution
- MUST accept a `--json` boolean flag on the `status` command.
- MUST invoke the device discovery module to find connected Garmin watches.
- MUST cleanly exit with code `0` if no watch is found (fault tolerance).
- MUST NOT panic or crash if unexpected device states are encountered.

### Output Formatting
- If `--json` is `true`:
  - MUST output a JSON representation of the device state to `stdout`, pretty-printed with two-space indentation and a trailing newline (all `--json` output of every subcommand uses this formatting).
  - MUST format disconnected states as `{"connected": false, "device": null}`.
  - MUST format connected states as `{"connected": true, "device": { ... }}` matching the shape returned by discovery (exactly the five keys `model`, `id`, `software_version`, `part_number`, `mount_path`).
- If `--json` is `false` (default):
  - MUST output a human-readable text summary to `stdout` consisting of a headline `Device found: <model> (ID: <id>)` followed by indented lines for `Software version`, `Part number` and `Mount path`. Empty metadata values are rendered as `-`.
  - MUST output "No Garmin device detected." if no device is found.

### Exit Codes (all subcommands)
| Code | Meaning |
|---|---|
| `0` | Success — including "no device connected" (NFR-1) |
| `1` | Runtime failure while a device is connected (e.g. a path given to `ls`/`tree` does not exist) |
| `2` | Usage error: unknown subcommand, unknown flag, invalid flag value, too many arguments |

## Data Shapes / Interfaces

```json
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
