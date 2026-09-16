---
id: file-browser
title: File Browser (ls / tree)
namespace: cli
status: implemented
owners: [jerry]
depends_on: [cli-entrypoint, device-discovery]
implements_requirements: [FR-4]
relies_on_facts: [FCT-3, FCT-4, FCT-8, FCT-10, FCT-11]
relies_on_assumptions: [ASM-3, ASM-5, ASM-6]
last_updated: 2026-09-16
---

# File Browser (ls / tree)

`internal/cli/ls.go`
`internal/cli/tree.go`
`internal/device/fs.go`

Depends on: [CLI Entrypoint](cli-entrypoint.md), [Device Discovery](../core/device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-4` (Read-Only Filesystem Inspection)
- **Relies on Facts:** `FCT-3` (GARMIN structure), `FCT-4` (GVFS paths), `FCT-8` (MTP Casing), `FCT-10` (MTP Traversal latency), `FCT-11` (MTP Metadata limits)
- **Relies on Assumptions:** `ASM-3` (Single device workflow), `ASM-5` (Basic metadata sufficiency), `ASM-6` (Depth-limited traversal)

*Note: This feature extends the CLI but adheres to the read-only, discovery-first nature of the tool. It does not violate the "Out of Scope" rule regarding file management/sideloading, as it only inspects the existing filesystem structure.*

## Purpose

Provides a way to inspect the file and directory structure of a connected Garmin watch directly from the CLI. This allows users to see available storage, check for the presence of specific FIT files (like activities or workouts), and understand the internal layout without needing a graphical file manager or complex GVFS path navigation.

## Scope

**In scope:**
- Listing directories and files within the watch's mount path.
- Supporting a flat list (`ls`) and a recursive tree view (`tree`).
- Displaying basic file metadata (size, last modified time).
- JSON output support for automated processing.

**Out of scope:**
- Reading the contents of files (e.g., parsing FIT files).
- Writing, deleting, or modifying files on the watch.
- Watching for filesystem changes in real-time.

## Requirements

### Shared behavior (`ls` and `tree`)
- When no device is connected both commands MUST behave exactly like `status` (see [cli-entrypoint](cli-entrypoint.md)): print `No Garmin device detected.` (text) or `{"connected": false, "device": null}` (`--json`) to stdout and exit `0` (NFR-1).
- `[path]` is interpreted relative to the storage root (the parent of the `GARMIN` folder). A leading `/` is also relative to the storage root, and `..` segments MUST NOT climb above it (they are clamped at the root, so `../../GARMIN` resolves to `GARMIN`).
- Path resolution MUST be case-insensitive per segment (`garmin/activity` resolves to `GARMIN/Activity`), as MTP implementations often abstract or alter character casing (FCT-8). An exact-case match wins over a folded one when both exist.
- If `[path]` cannot be resolved or read, the command MUST print `garmin-connector <cmd>: cannot access <path>: <reason>` to stderr and exit `1` (nothing on stdout).
- More than one positional argument is a usage error (exit `2`).
- Entries MUST be sorted by name, case-insensitively (ties broken by byte order), directories and files interleaved — as `tree` does.
- Hidden entries are those whose name starts with `.`; they are hidden by default and shown with `-a`/`--all`.
- `modified_time` is RFC 3339 with the local UTC offset (e.g. `2026-09-13T11:06:56+02:00`); `size_bytes` is whatever the mount reports (MTP reports `0` for directories).

### Sub-behavior A: Directory Listing (`ls` command)
- MUST provide an `ls [path]` command to list the contents of a specific directory on the watch.
- If `[path]` is omitted, it MUST default to the root of the watch's internal storage (the parent of the `GARMIN` folder).
- MUST output the name, size (human-readable or raw bytes), and modification time of each file/directory. Text format: one entry per line — size right-aligned in human-friendly units (same formatting as [device-info](device-info.md)), modification time as `YYYY-MM-DD HH:MM` (local time), then the name with a trailing `/` for directories.
- MUST handle case-insensitive path resolution (see shared behavior).
- MUST hide files and directories starting with `.` by default to reduce OS-level mount clutter (e.g., GVFS metadata).
- MUST support an `-a` or `--all` flag to show hidden files.
- MUST support the `--json` flag to output the directory listing as a structured JSON array of `FileNode` objects **without** a `children` key.

### Sub-behavior B: Recursive Tree View (`tree` command)
- MUST provide a `tree [path]` command to recursively list directories and files.
- If `[path]` is omitted, it MUST default to the root of the watch's internal storage.
- SHOULD limit recursion depth by default (e.g., 3 levels) to prevent excessive MTP traversal delays, with a flag (e.g., `--depth`) to override. Concretely: default `--depth 3`; `--depth N` shows entries up to `N` levels below the starting directory (same semantics as `tree -L N`); `N < 1` is a usage error (exit `2`).
- MUST format the standard output visually similarly to the traditional Linux `tree` command: first line is the starting path as resolved (`/` for the storage root, otherwise the canonical relative path such as `GARMIN/Activity`), branches drawn with `├── `, `└── `, `│   ` connectors, then a blank line and a summary `N directories, M files` (counting only what was printed).
- Directories that cannot be read during traversal are printed but their contents are skipped (no failure).
- MUST hide files and directories starting with `.` by default.
- MUST support an `-a` or `--all` flag to show hidden files.
- MUST support the `--json` flag to output the tree as a nested JSON object: the starting directory is the root `FileNode` (its `name` is the same label as the first text line).

## Data Shapes / Interfaces

```yaml
FileNode:
  name: string          # Name of the file/directory
  is_dir: boolean       # True if it's a directory
  size_bytes: integer   # Size in bytes
  modified_time: string # RFC 3339 modification time with local offset
  children: array       # Optional list of FileNode objects (only for 'tree')
```

`children` semantics in `tree --json`: present for every directory whose contents were traversed (an empty directory yields `"children": []`); absent for files, for directories at the depth limit, and for directories that could not be read. Consumers can therefore distinguish "empty" from "not traversed".

## Non-Goals

- Complete POSIX file system compliance (e.g., symlinks, permissions, owners), as MTP does not reliably support or expose these.
