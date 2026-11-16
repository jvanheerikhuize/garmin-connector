---
name: garmin-connector-specs
description: >-
  Use this skill before changing anything in garmin-connector: it explains that specs/ is the single source of
  truth, which files to read first, how changes cascade from facts to requirements to code, and which
  audit and test commands must pass. Activate for features, fixes, regeneration and spec reviews.
---

# garmin-connector: specs first

`specs/` is the authoritative blueprint of this repository; code is derived from it.
Read [`specs/README.md`](../../../specs/README.md) in full before editing anything, it defines the working
agreement, the layout and the reading order. The workspace-wide version of these rules is the shared
`specs-first-development` skill; this file carries only what is specific to garmin-connector.

## Steps

1. Read `specs/README.md`, then `specs/tech-stack.md`, `specs/workflows/regeneration.md` and
   `specs/constitution.md`, then the namespace or catalog you are changing.
2. Make the change in `specs/` first. Keep specs tech-stack agnostic; language and library choices only in
   `tech-stack.md` and `adrs/`.
3. Only then change code, in one pass, and run:
   ```bash
   go test ./...
   ```
4. Diagrams are Mermaid; validate with `~/.agents/bin/mermaid-check <file.md>` when available.
5. List the spec files before the code files in the PR and cite the IDs touched.
