# Garmin Connector (`garmin-connector`)

A lightweight, zero-runtime-dependency CLI tool to connect modern Garmin watches to a Linux machine over USB, inspect device connection status, and read device metadata.

## Features

- **Automatic Device Discovery**: Scans standard Linux MTP and mount paths (`/run/user/<uid>/gvfs`, `/media`, `/mnt`) without manual configuration.
- **Metadata Extraction**: Reads and parses `GarminDevice.xml`, extracting model description, unique unit ID, software version, and part number.
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

### Machine-Readable JSON Output

Structured JSON output for scripts and integrations:

```bash
./garmin-connector status --json
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
- [Regeneration Protocol](spec/regeneration.md): Runbook for spec-driven regeneration and quality gates.

## License

MIT License. See [LICENSE](LICENSE) for details.
