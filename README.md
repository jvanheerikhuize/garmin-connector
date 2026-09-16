# Garmin Connector (`garmin-connector`)

A lightweight, zero-runtime-dependency CLI tool to connect modern Garmin watches to a Linux machine over USB, inspect device connection status, and read device metadata.

## Features

- **Automatic Device Discovery**: Scans standard Linux MTP and mount paths (`/run/user/<uid>/gvfs`, `/media`, `/mnt`) without manual configuration.
- **Metadata Extraction**: Reads and parses `GarminDevice.xml`, extracting model description, unique unit ID, software version, and part number.
- **File Browser**: Inspect watch directories and files directly from the CLI using `ls` and `tree`, with case-insensitive path resolution and dotfile filtering.
- **CLI & Machine-Readable Output**: Inspect status interactively or output structured JSON (`--json`) for automated scripting.
- **Fault-Tolerant**: Cleanly exits with code `0` when no device is connected, with graceful fallbacks on missing or unreadable metadata.

## Prerequisites

- Linux operating system
- [Go](https://go.dev/) 1.22 or newer (for building from source)
- GVFS / MTP support (standard on modern Linux desktop environments)

## Building

Clone the repository and build the binary:

```bash
go build -o garmin-connector ./cmd/garmin-connector
```

To run automated tests:

```bash
go test -v ./...
```

## Usage

### Display Help and Available Commands

```bash
./garmin-connector --help
```

### Check Version

```bash
./garmin-connector --version
# Output: 1.0.0
```

### Inspect Connection Status

Human-readable text output:

```bash
./garmin-connector status
```

Example output when a device is connected:
```text
Device found: Venu X1 (ID: 3617019779)
```

Example output when no device is detected:
```text
No Garmin device detected.
```

### File Browser (`ls` / `tree`)

You can inspect the filesystem of your connected watch without opening a graphical file manager. Paths are resolved relative to the root of the watch's internal storage (the parent of the `GARMIN` folder).

List contents of a directory (defaults to root):
```bash
./garmin-connector ls
./garmin-connector ls GARMIN/Activity
```

View contents as a recursive tree (defaults to depth 3):
```bash
./garmin-connector tree
./garmin-connector tree GARMIN/Metrics --depth 2
```

*(Note: Files and directories starting with `.` are hidden by default to reduce GVFS metadata clutter. Use the `-a` or `--all` flag to show them.)*

### Machine-Readable JSON Output

Structured JSON output for scripts and integrations:

```bash
./garmin-connector status --json
./garmin-connector ls --json
./garmin-connector tree --json
```

Example output when connected:
```json
{
  "connected": true,
  "device": {
    "model": "Venu X1",
    "id": "3617019779",
    "software_version": "1829",
    "part_number": "006-B4603-00",
    "mount_path": "/run/user/1000/gvfs/mtp:host=091e_51fb_0000d7975783"
  }
}
```

Example output when disconnected:
```json
{
  "connected": false,
  "device": null
}
```

## Architecture & Specifications

This repository is governed by formal specifications located in the `spec/` directory:

- [Constitution](spec/constitution.md): Core requirements, grounding reality, facts, and assumptions.
- [CLI Entrypoint Spec](spec/skeleton/cli-entrypoint.md): Command dispatch and output contract.
- [Device Discovery Spec](spec/skeleton/device-discovery.md): Filesystem traversal and XML parsing rules.
- [File Browser Spec](spec/feature/file-browser.md): Read-only filesystem inspection (`ls`, `tree`).
- [Regeneration Protocol](spec/regeneration.md): Runbook for spec-driven regeneration and quality gates.

## License

MIT License. See [LICENSE](LICENSE) for details.
