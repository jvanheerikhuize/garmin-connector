# garmin-connector

A tool to connect a modern Garmin watch to a Linux laptop to exchange files over a USB connection.

This tool automatically detects Garmin MTP mounts and parses `GarminDevice.xml` without requiring any manual mount path configuration.

## Installation

```bash
go install github.com/jvanheerikhuize/garmin-connector/cmd/garmin-connector@latest
```

## Usage

Check if your watch is connected:

```bash
garmin-connector status
```

For external scripts, use the JSON output:

```bash
garmin-connector status --json
```

## Architecture & Specifications

This repository strictly adheres to Spec-Driven Development. All behavior is defined in the `spec/` folder. Do not edit source code directly; edit the specifications and regenerate the codebase.

See [spec/constitution.md](spec/constitution.md) for the grounding rules and architectural boundaries.
