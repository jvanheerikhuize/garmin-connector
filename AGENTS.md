# AGENTS.md: garmin-connector

Workspace-wide rules: [`~/AGENTS.md`](file:///home/jerry/AGENTS.md) (git, PRs, shared-checkout etiquette, telemetry).

This repository is spec-driven: `specs/` is the single source of truth and code is derived from it.
Start with [`specs/README.md`](specs/README.md). The repo skill `.agents/skills/garmin-connector-specs` summarises the
reading order and the commands that must pass:

```bash
go test ./...
```
