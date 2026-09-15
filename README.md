# Garmin Connector (`garmin-venu-x1`) — Specification Corpus

This repository serves exclusively as the **specification corpus and architectural blueprint** for `garmin-connector`, a single-binary, cross-platform (Linux, Windows, macOS) CLI tool with an embedded React web GUI for Garmin watches.

In this repository, **specs are the single source of truth**. Code is treated as a transient, generated artifact derived directly from these specifications through single-shot autonomous agent generation.

---

## Repository Map & Entry Points

- **[Architecture & Constitution](spec/constitution.md)**: Defines the overarching Purpose & Goal (Go + React Architecture), the Walking Skeleton composition, system architecture diagrams, tech stack constraints, and non-negotiable architectural boundaries.
- **[Spec-Driven Working Agreement](spec/README.md)**: Rules of engagement, spec tiers, drift policies, and the rebuild-test philosophy.
- **[Regeneration Protocol & Runbook](spec/regeneration.md)**: Operational guide for initiating a single-shot generation run from scratch with an autonomous agent, including fixed inputs, gates, and the agent prompt.
- **[Spec Templates](spec/templates/)**: 
  - [`spec-template.md`](spec/templates/spec-template.md): Template for authoring new specifications.
  - [`APP_README.md`](spec/templates/APP_README.md): Template for the user-facing README scaffolded during application code generation.

---

## Spec Tiers

The specifications are structured in two tiers:

### 1. The Walking Skeleton (`tier: skeleton`)
These specs define the minimal, end-to-end chain required to prove the application runs and truthfully communicates with the environment:
1. **[`spec/cli-entrypoint.md`](spec/cli-entrypoint.md)**: Process initialization via Cobra CLI and argument parsing.
2. **[`spec/gui-bootstrap.md`](spec/gui-bootstrap.md)**: Go HTTP server startup, WebSocket routing, and embedded Vite/React asset serving.
3. **[`spec/device-detection.md`](spec/device-detection.md)**: Read-only detection of connected watches across OS mount roots, triggering OS event hooks.
4. **[`spec/connection-status-shell.md`](spec/connection-status-shell.md)**: React frontend shell establishing a WebSocket to reflect real-time connection state.

### 2. Feature Specs (`tier: feature`)
Modular capabilities layered atop the skeleton that degrade gracefully if unavailable:
- **[`spec/features/device-manager.md`](spec/features/device-manager.md)**: Go `os` file operations (sideloading, listing, deleting courses on watch storage).
- **[`spec/features/gpx-fit-conversion.md`](spec/features/gpx-fit-conversion.md)**: In-memory GPX XML parsing and Go binary FIT encoding.
- **[`spec/features/course-management-api.md`](spec/features/course-management-api.md)**: JSON REST endpoints for file upload, deletion, and preview extraction.
- **[`spec/features/gui-course-frontend.md`](spec/features/gui-course-frontend.md)**: React course manager UI interactions, course list rendering, and Leaflet preview.
- **[`spec/features/ui-design.md`](spec/features/ui-design.md)**: Tailwind CSS configuration, Cyberpunk aesthetic tokens, HUD layout, and markup contracts.

---

## Generating the Application

To scaffold or regenerate the implementation code from this spec corpus, refer to the prompt and step-by-step instructions in [`spec/regeneration.md`](spec/regeneration.md).
