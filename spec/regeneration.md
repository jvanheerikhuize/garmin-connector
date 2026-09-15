---
id: regeneration
title: Regeneration Protocol (single-shot rewrite runbook)
last_updated: 2026-09-15
---

# Regeneration Protocol

How a single-shot (re)generation of the application from `spec/` is run, what is fixed input vs. regenerated output, and the gate it must pass. This is the operational counterpart of the "rebuild test" in [README.md](README.md) and the testing requirement in [constitution.md §7](constitution.md).

## Who runs it

A **fresh agent** — one that has never read the current codebase — in a new session. An agent that has seen the old code will reproduce it from memory and hide spec gaps instead of surfacing them, which defeats the point. The copy-paste prompt is at the bottom of this file.

## Inputs (read-only for the regenerating agent)

```
spec/**                                       # the only source of truth for behavior
examples/**                                   # fixtures the tests use
.gitignore
```

## Outputs (deleted first, then regenerated from spec)

```
src/** / cmd/** / internal/** # Application source code
README.md                     # Application README generated from specs
```

Regenerated files MUST NOT carry `// GENERATED` banners or references to this protocol — they are ordinary source files; the spec is the provenance.

## Order

1. Branch `rewrite/v1` from `main`. First commit: delete the outputs listed above (`git rm`), so nothing old is left in the working tree to be read. Do **not** read the deleted files from git history (`git show`, `git log -p`, etc.) — that is the one hard rule of this protocol.
2. Implement the walking skeleton according to [constitution.md](constitution.md). Write automated unit tests as required.
3. Regenerate application build configuration and `README.md`.
4. Run the full gate (below). Fix until green.
5. Open a **draft PR** from `rewrite/v1`. The description MUST list every spec patch made under the gap rule below.

## Gap rule

The spec is expected to be sufficient. When it isn't:
- **Trivial, unambiguous gap** (a missing default, an obvious type, a name the tests already pin): choose the obvious answer **and patch the relevant spec file in the same branch** so the spec stays the source of truth. List it in the PR.
- **Real ambiguity or contradiction** (spec vs. test, two specs disagree, a behavior with no reasonable default): do not guess. Add it under an `## Open Questions` heading in the relevant spec, stop, and report. A regeneration that silently resolves a real ambiguity has failed even if the tests pass.

## Gate (all must hold before the PR is marked ready)

- Automated tests pass in full.
- `garmin-connector --help` cleanly displays usage and available commands.
- `garmin-connector status` and `garmin-connector status --json` execute without errors.
- `garmin-connector --version` returns `1.0.0`.

## Prompt for the fresh agent

Copy verbatim into a new session started in the repo root on a clean `main`:

```
You are performing a single-shot regeneration of this repository from its specification.

Read spec/README.md, then spec/regeneration.md, then spec/constitution.md, then every other file under spec/ — in that order — before writing any code. Follow spec/regeneration.md exactly: it defines the inputs you may read, the outputs you must delete and regenerate, the order, the gap rule, and the gate.

Hard rule: do not read the deleted source files from git history (no git show / git log -p / git diff against old commits). The spec is your only source for behavior. tests/ and examples/ are fixed inputs you must satisfy without modifying existing assertions.

Work on branch rewrite/v1. Use conventional commits. When the gate in spec/regeneration.md passes, open a draft PR and list every spec patch you made under the gap rule. If you hit a real ambiguity, record it as an Open Question in the relevant spec and stop rather than guess.
```
