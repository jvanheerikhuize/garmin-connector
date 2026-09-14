# Spec-Driven Development — Working Agreement

This directory is the **single source of truth** for `garmin-venu-x1`. From now on:

1. **Changes start here, not in `src/`.** A fix, feature, or behavior change is first written as an edit to the relevant file under `spec/`. Code is a generated/derived artifact of the spec, not the other way around.
2. **`constitution.md`** describes the walking skeleton: the architecture, boundaries, and non-negotiables that rarely change. Edits here are rare and deliberate.
3. **`features/*.md`** describes vertical slices layered on the skeleton. Each file is independently editable and (eventually) independently regenerable.
4. **Change proposals**: when asked for a change, an agent edits the relevant spec file(s) and stops — it presents a diff of the *spec*, not the application, for review/approval.
5. **Single-shot implementation**: once a spec file (or set of files) has accumulated a sufficient, coherent corpus of change, an agent implements it against `src/` in one pass, then runs the test suite to confirm behavior matches the spec.
6. **Rebuild test**: a spec is "good enough" if a clean agent, given only `spec/`, could regenerate a working equivalent of that slice. Gaps found during implementation should be patched back into the spec, not silently resolved only in code.
7. **Drift**: `spec/` and `src/` should never silently diverge. If code is changed directly (hotfix, exploratory patch), the corresponding spec file(s) must be updated in the same change before it's considered done.

## Layout

```
spec/
  constitution.md         # walking skeleton: architecture, boundaries, invariants
  features/
    device-detection.md
    device-manager.md
    gpx-fit-conversion.md
    direct-mtp-client.md
    gui-http-api.md
    gui-frontend.md
```

## Status

This corpus was seeded on 2026-09-14 by reverse-engineering the existing implementation (commit `4520796`). It describes the system **as it currently behaves**, not aspirationally — it is the starting baseline for the new workflow, not a wishlist. Treat gaps/ambiguities you find while implementing future changes as bugs in the spec to be fixed, not license to guess.
