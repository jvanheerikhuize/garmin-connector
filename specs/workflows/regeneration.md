---
id: regeneration
title: Regeneration Protocol (single-shot rewrite runbook)
last_updated: 2026-09-16
---

# Regeneration Protocol

How a single-shot (re)generation of the application from `specs/` is run, what is fixed input vs. regenerated output, and the gate it must pass. This is the operational counterpart of the "rebuild test" in [README.md](../README.md).

## Who runs it

A **fresh agent** — one that has never read the current codebase — in a new session. An agent that has seen the old code will reproduce it from memory and hide spec gaps instead of surfacing them, which defeats the point. The copy-paste prompt is at the bottom of this file.

## Inputs (read-only for the regenerating agent)

```
specs/**                                       # the only source of truth for behavior
.gitignore
```

## Outputs (deleted first, then regenerated from spec)

```
cmd/** / internal/**          # Application source code
go.mod, go.sum                # Or equivalent build config (see tech-stack.md)
README.md                     # Application README generated from specs
```

Regenerated files MUST NOT carry `// GENERATED` banners or references to this protocol — they are ordinary source files; the spec is the provenance.

## Order

1. Branch `rewrite/v1` from `main`. First commit: clear the outputs listed above from the working tree (`rm -rf cmd/ internal/ go.mod go.sum; git rm README.md`), so nothing old is left in the working tree to be read. Do **not** read the deleted files from git history (`git show`, `git log -p`, etc.) — that is the one hard rule of this protocol.
2. Implement the walking skeleton according to the specs in `specs/core/` and the requirements in `constitution.md`. Write automated unit tests as required.
3. Implement layered feature specs in `specs/cli/` (`file-browser.md`, `device-info.md`, `course-upload.md`) and `specs/gui/` (`dashboard.md`, `file-browser.md`, `course-upload.md`, `course-preview.md`) and their corresponding unit tests.
4. Regenerate application build configuration based on `tech-stack.md` and generate `README.md`.
5. Run the full gate (below). Fix until green.
6. Perform the **constitution review** (below) and, where a workflow is triggered, run it.
7. Open a **draft PR** from `rewrite/v1`. The description MUST list every spec patch made under the gap rule below and MUST contain the constitution review table.

## Gap rule

The spec is expected to be sufficient. When it isn't:
- **Trivial, unambiguous gap** (a missing default, an obvious type, a name the tests already pin): choose the obvious answer **and patch the relevant spec file in the same branch** so the spec stays the source of truth. List it in the PR.
- **Real ambiguity or contradiction** (spec vs. test, two specs disagree, a behavior with no reasonable default): do not guess. Add it under an `## Open Questions` heading in the relevant spec, stop, and report. A regeneration that silently resolves a real ambiguity has failed even if the tests pass.

## Gate (all must hold before the PR is marked ready)

- Automated tests pass in full (using the test command standard for the chosen `tech-stack.md`).
- `garmin-connector --help` cleanly displays usage and available commands (`status`, `info`, `ls`, `tree`, `upload`, `web`).
- `garmin-connector status` and `garmin-connector status --json` execute without errors.
- `garmin-connector info` and `garmin-connector info --json` execute without errors.
- `garmin-connector ls` and `garmin-connector tree` execute without errors.
- `garmin-connector upload --help` and `garmin-connector web --help` execute without errors.
- `garmin-connector --version` returns `1.0.0`.
- The constitution review below has been performed and its table is in the PR description.

## Constitution review (part of the gate)

A regeneration run is also an experiment: the gate commands run against a real machine and — whenever one is plugged in — a real watch. That evidence must flow back into `constitution.md`, otherwise its facts and assumptions silently age. Before the PR is marked ready the agent MUST:

1. **Classify every row** of `constitution.md` §2.1 (Facts) and §2.2 (Assumptions), and every requirement in §3, against what the run actually observed. Exactly one verdict per row:
   - **confirmed** — the run observed the statement to hold (name the command/file/value that shows it);
   - **contradicted** — the run observed it to fail;
   - **refined** — it holds, but the run learned a more precise or narrower statement;
   - **weakened** — not contradicted, but the run's evidence does not support the strength of the claim (e.g. a "severe" effect that did not reproduce);
   - **not exercised** — the run produced no evidence either way (product decisions, user-behaviour claims, environments not available on this machine).
2. **Trigger the lifecycle workflows** where their conditions are met, in the same branch:
   - a **contradicted** fact → [invalidate-fact.md](invalidate-fact.md);
   - an assumption **proven true by empirical observation** (not merely "consistent with one run") → [validate-assumption.md](validate-assumption.md);
   - a **refined** or **weakened** row → propose the new wording as a diff in the PR description. `constitution.md` changes deliberately: do **not** apply the wording change silently — the reviewer applies or rejects it.
3. **Record the table** in the PR description under a `## Constitution review` heading, with the evidence column filled for every row that is not "not exercised" (device model and software version, command run, observed value, timing where relevant). State explicitly which workflows were triggered, or that none were.

A run whose PR carries no constitution review has not passed the gate, even if every command above is green. Gathering evidence MAY require extra commands beyond the gate list (e.g. timing `tree --depth N`, `ls -ld /run/user/*`, inspecting the raw `GarminDevice.xml`); those are read-only and permitted.

## Prompt for the fresh agent

Copy verbatim into a new session started in the repo root on a clean `main`:

```
You are performing a single-shot regeneration of this repository from its specification.

Read specs/README.md, then specs/tech-stack.md, then specs/workflows/regeneration.md, then specs/constitution.md, then every other file under specs/ — in that order — before writing any code. Follow specs/workflows/regeneration.md exactly: it defines the inputs you may read, the outputs you must delete and regenerate, the order, the gap rule, and the gate.

Hard rule: do not read the deleted source files from git history (no git show / git log -p / git diff against old commits). The spec is your only source for behavior.

Work on branch rewrite/v1. Use conventional commits. When the gate in specs/workflows/regeneration.md passes, perform the constitution review it defines, then open a draft PR that lists every spec patch you made under the gap rule and contains the constitution review table. If you hit a real ambiguity, record it as an Open Question in the relevant spec and stop rather than guess.
```
