---
id: regeneration
title: Regeneration Protocol (single-shot rewrite runbook)
last_updated: 2026-09-14
---

# Regeneration Protocol

How a single-shot (re)generation of `src/` from `spec/` is run, what is fixed input vs. regenerated output, and the gate it must pass. This is the operational counterpart of the "rebuild test" in [README.md](README.md) and the testing requirement in [constitution.md §7](constitution.md).

## Who runs it

A **fresh agent** — one that has never read the current `src/` — in a new session. An agent that has seen the old code will reproduce it from memory and hide spec gaps instead of surfacing them, which defeats the point. The copy-paste prompt is at the bottom of this file.

## Inputs (read-only for the regenerating agent)

```
spec/**                                       # the only source of truth for behavior
tests/**                                      # regression oracle — existing assertions MUST NOT be weakened or deleted
examples/**                                   # fixtures the tests use
src/garmin_connector/gui/static/cybercore.min.css   # vendored third-party asset, copied verbatim
.gitignore
```

## Outputs (deleted first, then regenerated from spec)

```
src/garmin_connector/**   (everything except gui/static/cybercore.min.css)
pyproject.toml            # from constitution §1 (version 1.0.0) and §4 (deps: fitparse; dev: pytest)
README.md                 # short, from constitution §1 + install/usage; drop stale content (e.g. the Nerd Font note)
uv.lock                   # re-locked with `uv lock` if uv is available; otherwise left as-is and noted in the PR
tests/test_skeleton.py    # NEW — the walking-skeleton end-to-end test required by constitution §7
```

Regenerated files MUST NOT carry `// GENERATED` banners or references to this protocol — they are ordinary source files; the spec is the provenance.

## Order

1. Branch `rewrite/v1` from `main`. First commit: delete the outputs listed above (`git rm`), so nothing old is left in the working tree to be read. Do **not** read the deleted files from git history (`git show`, `git log -p`, etc.) — that is the one hard rule of this protocol.
2. Regenerate the **walking skeleton** in the order given in [constitution.md §2](constitution.md): `cli-entrypoint` → `gui-bootstrap` → `device-detection` → `connection-status-shell` (the latter as the minimal `index.html` + `app.js` needed for the header and polling). Write `tests/test_skeleton.py` (server starts on a free port, `GET /api/device` returns well-formed JSON without a watch, `GET /` returns the index page containing `Garmin Course Uploader`). Run it. It MUST pass before any feature is started.
3. Regenerate **features** in dependency order: `gpx-fit-conversion` → `device-manager` → `course-management-api` → `gui-course-frontend` → `ui-design` (the last produces `styles.css` and finalizes `index.html` per its markup contract).
4. Regenerate `pyproject.toml`, `README.md`; re-lock if possible.
5. Run the full gate (below). Fix until green.
6. Open a **draft PR** from `rewrite/v1`. The description MUST list every spec patch made under the gap rule below.

## Gap rule

The spec is expected to be sufficient. When it isn't:
- **Trivial, unambiguous gap** (a missing default, an obvious type, a name the tests already pin): choose the obvious answer **and patch the relevant spec file in the same branch** so the spec stays the source of truth. List it in the PR.
- **Real ambiguity or contradiction** (spec vs. test, two specs disagree, a behavior with no reasonable default): do not guess. Add it under an `## Open Questions` heading in the relevant spec, stop, and report. A regeneration that silently resolves a real ambiguity has failed even if the tests pass.

## Gate (all must hold before the PR is marked ready)

- `pytest` passes in full, including `tests/test_skeleton.py` and every pre-existing test unchanged.
- No module under `src/` is unreachable from the CLI or HTTP API (constitution §5 "no dead code").
- Manual smoke: `garmin-connector gui --no-browser` starts, prints the URL, `curl` of `/api/device` returns `{"connected": false, "mounting": false, "model_name": null}` with no watch attached, and `/static/styles.css` is served.
- `garmin_connector.__version__ == "1.0.0"` and `pyproject.toml` agrees.

## Prompt for the fresh agent

Copy verbatim into a new session started in the repo root on a clean `main`:

```
You are performing a single-shot regeneration of this repository from its specification.

Read spec/README.md, then spec/regeneration.md, then spec/constitution.md, then every other file under spec/ — in that order — before writing any code. Follow spec/regeneration.md exactly: it defines the inputs you may read, the outputs you must delete and regenerate, the order, the gap rule, and the gate.

Hard rule: do not read the deleted source files from git history (no git show / git log -p / git diff against old commits of src/). The spec is your only source for behavior. tests/ and examples/ are fixed inputs you must satisfy without modifying existing assertions.

Work on branch rewrite/v1. Use conventional commits. When the gate in spec/regeneration.md passes, open a draft PR and list every spec patch you made under the gap rule. If you hit a real ambiguity, record it as an Open Question in the relevant spec and stop rather than guess.
```
