---
id: file-browser
title: File Browser (ls / tree)
tier: feature
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

Depends on: [CLI Entrypoint](../skeleton/cli-entrypoint.md), [Device Discovery](../skeleton/device-discovery.md)

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

### Sub-behavior A: Directory Listing (`ls` command)
- MUST provide an `ls [path]` command to list the contents of a specific directory on the watch.
- If `[path]` is omitted, it MUST default to the root of the watch's internal storage (the parent of the `GARMIN` folder).
- MUST output the name, size (human-readable or raw bytes), and modification time of each file/directory.
- MUST handle case-insensitive path resolution, as MTP implementations often abstract or alter character casing (FCT-8).
- MUST hide files and directories starting with `.` by default to reduce OS-level mount clutter (e.g., GVFS metadata).
- MUST support an `-a` or `--all` flag to show hidden files.
- MUST support the `--json` flag to output the directory listing as a structured JSON array.

### Sub-behavior B: Recursive Tree View (`tree` command)
- MUST provide a `tree [path]` command to recursively list directories and files.
- If `[path]` is omitted, it MUST default to the root of the watch's internal storage.
- SHOULD limit recursion depth by default (e.g., 3 levels) to prevent excessive MTP traversal delays, with a flag (e.g., `--depth`) to override.
- MUST format the standard output visually similarly to the traditional Linux `tree` command.
- MUST hide files and directories starting with `.` by default.
- MUST support an `-a` or `--all` flag to show hidden files.
- MUST support the `--json` flag to output the tree as a nested JSON object.

## Data Shapes / Interfaces

```go
package device

type FileNode struct {
	Name         string      `json:"name"`
	IsDir        bool        `json:"is_dir"`
	Size         int64       `json:"size_bytes"`
	ModifiedTime string      `json:"modified_time"`
	Children     []*FileNode `json:"children,omitempty"` // Populated only for 'tree'
}

// ListDir returns a flat slice of files/directories within the specified path relative to the watch root.
func ListDir(info *Info, relPath string, showHidden bool) ([]FileNode, error)

// Tree returns a hierarchical representation of the filesystem starting at the specified path.
func Tree(info *Info, relPath string, maxDepth int, showHidden bool) (*FileNode, error)
```

## Non-Goals

- Complete POSIX file system compliance (e.g., symlinks, permissions, owners), as MTP does not reliably support or expose these.
