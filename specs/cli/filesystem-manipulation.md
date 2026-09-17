---
id: filesystem-manipulation
title: Filesystem Manipulation (mkdir, rm, touch, put)
namespace: cli
status: draft
owners: [jerry]
depends_on: [cli-entrypoint, device-discovery]
implements_requirements: [FR-11]
relies_on_facts: [FCT-3, FCT-4, FCT-8, FCT-11, FCT-13, FCT-15, FCT-19]
relies_on_assumptions: [ASM-1, ASM-2, ASM-3, ASM-12]
last_updated: 2026-09-17
---

# Filesystem Manipulation (`mkdir`, `rm`, `touch`, `put`)

`internal/cli/mkdir.go`
`internal/cli/rm.go`
`internal/cli/touch.go`
`internal/cli/put.go`
`internal/device/fs_mutation.go`

Depends on: [CLI Entrypoint](cli-entrypoint.md), [Device Discovery](../core/device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-11` (Watch Filesystem Manipulation)
- **Relies on Facts:** `FCT-3` (GARMIN directory structure), `FCT-4` (GVFS paths), `FCT-8` (MTP Casing), `FCT-11` (MTP Metadata limits), `FCT-13` (GVFS direct write limits), `FCT-15` (GVFS client tooling/D-Bus transfers), `FCT-19` (GVFS FUSE mutation limitations)
- **Relies on Assumptions:** `ASM-1` (On-demand execution), `ASM-2` (Structured output), `ASM-3` (Single connected watch), `ASM-12` (Immediate mutation without recycle bin)

## Purpose

Provides CLI commands to manipulate files and directories on a connected Garmin watch. While `upload` is specialized for syncing courses to `GARMIN/NewFiles/` and `ls`/`tree` provide read-only inspection, `mkdir`, `rm`, `touch`, and `put` provide general-purpose filesystem operations (creating folders, creating empty files, uploading arbitrary local files, and removing files/directories) directly on the watch from the terminal.

## Scope

**In scope:**
- `mkdir`: create directories on the watch, with optional recursive parent creation (`-p`, `--parents`).
- `rm`: delete files or directories on the watch, with optional recursive removal (`-r`, `--recursive`) and force flag (`-f`, `--force`).
- `touch`: create empty files on the watch or touch existing files.
- `put`: copy arbitrary local files to any destination path or directory on the watch.
- Path resolution relative to internal storage root, case-insensitive per segment (matching `ls` and `tree`), clamping `..` segments at the storage root.
- Safeguards preventing accidental deletion or overwriting of the storage root itself (`/`, `.`, or `""`).
- Dual-mode execution attempting direct POSIX system calls with fallback to GVFS client tooling (e.g. `gio mkdir`, `gio remove`, `gio copy`) when running over MTP FUSE mounts (`FCT-13`, `FCT-19`).
- Structured JSON output support via `--json` flag on all mutating commands.

**Out of scope:**
- Moving or renaming files on the watch (`mv`).
- Interactive deletion prompts or recycle bin/trash staging.
- POSIX permissions or file mode modification (`chmod`, `chown`).
- In-place editing or file appending.

## Requirements

### Shared Behavior & Path Resolution

- **Device Connection**: When no Garmin device is detected, mutating commands (`mkdir`, `rm`, `touch`, `put`) MUST print an error message `garmin-connector <cmd>: no Garmin device detected` to `stderr` and exit with code `1`.
- **Target Path Resolution**: All watch paths are interpreted relative to the internal storage root (the parent directory of `GARMIN`). A leading `/` is stripped and treated as relative to the storage root. `..` segments MUST NOT climb above the storage root (they are clamped at root level).
- **Case-Insensitive Resolution**: Path resolution MUST match existing path segments case-insensitively (`FCT-8`). When creating new items, the requested casing MUST be used for new segments.
- **Safety Protection**: Commands MUST NOT allow deleting, removing, or overwriting the storage root itself (`/`, `.`, or empty path `""`). An attempt to do so MUST output an error to `stderr` and exit `1`.
- **GVFS / MTP Fallback**: File and directory mutations MUST attempt direct filesystem operations first. If the underlying mount returns `EOPNOTSUPP` or an unsupported operation error (`FCT-13`, `FCT-19`), the command MUST attempt execution via GVFS client tooling (such as `gio mkdir`, `gio remove`, `gio copy`). If the operation cannot be completed, the error MUST be written to `stderr` and exit `1`.
- **Argument Validation**: Omission of required positional arguments or unrecognized flags MUST exit with code `2` (usage error) and print usage instructions to `stderr`.

### Sub-behavior A: Directory Creation (`mkdir` command)

- MUST provide a `mkdir` subcommand: `garmin-connector mkdir [flags] <watch-path>`.
- MUST accept `-p` or `--parents` to create intermediate parent directories as needed without failing if target or parents already exist.
- Without `-p`/`--parents`:
  - MUST fail with exit `1` if the parent directory does not exist.
  - MUST fail with exit `1` if the target directory already exists.
- MUST accept an optional `--json` flag to return structured output to `stdout`.
- Default text output MUST confirm creation to `stdout` (e.g., `Created directory 'GARMIN/Workouts'`).

### Sub-behavior B: File & Directory Removal (`rm` command)

- MUST provide an `rm` subcommand: `garmin-connector rm [flags] <watch-path>`.
- MUST accept `-r` or `--recursive` to remove directories and their contents recursively.
- MUST accept `-f` or `--force` to ignore non-existent files without reporting an error.
- Without `-r`/`--recursive`:
  - If `<watch-path>` resolves to a directory, MUST NOT remove it, MUST print `garmin-connector rm: cannot remove '<path>': Is a directory` to `stderr`, and MUST exit `1`.
- Without `-f`/`--force`:
  - If `<watch-path>` does not exist, MUST print `garmin-connector rm: cannot remove '<path>': No such file or directory` to `stderr`, and MUST exit `1`.
- With `-f`/`--force`:
  - If `<watch-path>` does not exist, MUST exit `0`.
- MUST accept an optional `--json` flag to return structured output to `stdout`.
- Default text output MUST confirm deletion to `stdout` (e.g., `Removed 'GARMIN/NewFiles/old_route.gpx'`).

### Sub-behavior C: File Touch (`touch` command)

- MUST provide a `touch` subcommand: `garmin-connector touch [flags] <watch-path>`.
- If `<watch-path>` does not exist:
  - MUST create an empty file at `<watch-path>`.
  - MUST fail with exit `1` if the parent directory does not exist.
- If `<watch-path>` already exists:
  - MUST succeed and update modification timestamp if supported by the mount.
- MUST accept an optional `--json` flag to return structured output to `stdout`.
- Default text output MUST confirm the operation to `stdout` (e.g., `Created file 'GARMIN/marker.txt'`).

### Sub-behavior D: File Copy / Transfer (`put` command)

- MUST provide a `put` subcommand: `garmin-connector put [flags] <local-file-path> [watch-path]`.
- MUST verify that `<local-file-path>` exists, is a regular file, and is readable; otherwise MUST fail with exit `1`.
- If `[watch-path]` is omitted:
  - MUST copy `<local-file-path>` to the root of the watch's internal storage, retaining the local file's basename.
- If `[watch-path]` resolves to an existing directory:
  - MUST copy `<local-file-path>` into that directory, retaining the local file's basename.
- If `[watch-path]` resolves to a non-existent path whose parent directory exists:
  - MUST copy `<local-file-path>` to that path with the specified filename.
- If `[watch-path]`'s parent directory does not exist:
  - MUST fail with exit `1` (`garmin-connector put: cannot copy to '<path>': No such file or directory`).
- MUST overwrite any existing file at the destination path.
- MUST accept an optional `--json` flag to return structured output to `stdout`.
- Default text output MUST confirm transfer to `stdout` with bytes copied (e.g., `Transferred 'workout.fit' to 'GARMIN/Workouts/workout.fit' (14280 bytes)`).

## Data Shapes / Interfaces

### CLI Usage

```
garmin-connector mkdir [-p|--parents] [--json] <watch-path>
garmin-connector rm [-r|--recursive] [-f|--force] [--json] <watch-path>
garmin-connector touch [--json] <watch-path>
garmin-connector put [--json] <local-file-path> [watch-path]
```

### JSON Response Schema (`--json`)

```yaml
FsMutationResponse:
  success: boolean        # True if operation completed successfully
  operation: string      # "mkdir" | "rm" | "touch" | "put"
  target_path: string    # Canonical relative path on watch (e.g. "GARMIN/Workouts")
  bytes_transferred: integer # Optional, present for "put" operations
  message: string        # Human-readable summary description
```

Example JSON outputs:

```json
// garmin-connector mkdir -p GARMIN/Custom --json
{
  "success": true,
  "operation": "mkdir",
  "target_path": "GARMIN/Custom",
  "message": "Created directory 'GARMIN/Custom'"
}
```

```json
// garmin-connector put local.fit GARMIN/Workouts --json
{
  "success": true,
  "operation": "put",
  "target_path": "GARMIN/Workouts/local.fit",
  "bytes_transferred": 8192,
  "message": "Transferred 'local.fit' to 'GARMIN/Workouts/local.fit' (8192 bytes)"
}
```

## Non-Goals

- Interactive confirmation prompts (the CLI is non-interactive to preserve scriptability per `ASM-1` and `ASM-2`).
- Directory synchronisation or two-way sync (rsync semantics).
- In-place modification of existing watch file contents.
- Changing permissions or Unix ownership modes (unsupported by MTP per `FCT-11`).
