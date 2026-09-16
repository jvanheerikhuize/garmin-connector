---
id: tech-stack
title: Current Tech Stack
last_updated: 2026-09-16
---

# Current Tech Stack

This document outlines the current technologies chosen to implement the system described in the [Constitution](./constitution.md). 
These can be swapped out over time; history of these choices is tracked in the Architecture Decision Records (ADRs).

| Component / Capability | Chosen Technology | Decision Record |
|---|---|---|
| **Core Language** | Go (Golang) | [ADR-0001](./adrs/0001-use-go-for-core-cli.md) |
| **Structured Output** | JSON | [ADR-0002](./adrs/0002-use-json-for-structured-output.md) |

## Rationale Overview
- **Go** was selected to easily build standalone, dependency-free binaries for Linux users (satisfying NFR-2).
- **JSON** was selected as it is the most ubiquitous format for external tools/scripts to consume (satisfying ASM-2).

## Build Configuration

| Setting | Value |
|---|---|
| Module path | `github.com/jvanheerikhuize/garmin-connector` |
| Minimum Go version | `1.22` (`go` directive in `go.mod`) |
| Third-party dependencies | **None.** The CLI uses only the Go standard library (`flag`, `encoding/xml`, `encoding/json`, `syscall`), so no `go.sum` exists. Adding a dependency requires an ADR (NFR-3). |
| Binary name | `garmin-connector`, built from `cmd/garmin-connector` |
| Layout | `cmd/garmin-connector/main.go` (entrypoint), `internal/cli/` (commands, output), `internal/device/` (discovery, XML, storage, filesystem) |

## Standard Commands

| Purpose | Command |
|---|---|
| Build | `go build -o garmin-connector ./cmd/garmin-connector` |
| Test (the gate in [regeneration.md](workflows/regeneration.md)) | `go test ./...` |
| Static checks | `go vet ./...` and `gofmt -l .` (must print nothing) |
| Install for the current user | `go install ./cmd/garmin-connector` |
