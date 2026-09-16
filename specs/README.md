# Spec-Driven Development — Working Agreement

This directory is the **single source of truth** for `garmin-connector`. From now on:

1. **Changes start here, not in the codebase (e.g. `cmd/`, `internal/`).** A fix, feature, or behavior change is first written as an edit to the relevant file under `specs/`. Code is a generated/derived artifact of the spec, not the other way around.
2. **`constitution.md`** is the sum of the core capabilities plus scope and architecture. It changes rarely and deliberately — see [constitution.md](constitution.md).
3. **Every spec file** starts from [`templates/spec-template.md`](templates/spec-template.md) and carries frontmatter (`id`, `title`, `namespace`, `status`, `depends_on`, `implements_requirements`, `relies_on_facts`, `relies_on_assumptions`, ...). Specs live in folders matching their namespace (e.g., `specs/gui/login/`, `specs/core/`).
4. **Change proposals**: when asked for a change, an agent edits the relevant spec file(s) and stops — it presents a diff of the *spec*, not the application, for review/approval.
5. **Single-shot implementation**: once a spec file (or set of files) has accumulated a sufficient, coherent corpus of change, an agent implements it against the codebase in one pass, then runs the test suite to confirm behavior matches the spec. A *full* regeneration follows [regeneration.md](workflows/regeneration.md) — inputs, outputs, order, gap rule, gate, and the prompt for a fresh agent.
6. **Rebuild test**: a spec is "good enough" if a clean agent, given only `specs/`, could regenerate a working equivalent of that slice. Gaps found during implementation should be patched back into the spec, not silently resolved only in code.
7. **Drift**: `specs/` and the codebase should never silently diverge. If code is changed directly (hotfix, exploratory patch), the corresponding spec file(s) must be updated in the same change before it's considered done.
8. **Diagrams are always Mermaid.** No ASCII art, no external image tools, no screenshots of diagrams — every diagram in `specs/` must be a fenced ` ```mermaid ` block so it renders natively wherever the spec is viewed.

## Namespaces

Specs are grouped into **namespaces** rather than rigid tiers (like features or epics). A namespace allows users to logically bundle specs as they see fit (e.g., `gui/login`, `cli/commands`, `core`). Files are stored under a matching directory path (e.g., `specs/gui/login/`).

## Layout

```
specs/
├── README.md                      # this file
├── constitution.md                # core specification (purpose, statements, requirements, architecture)
├── tech-stack.md                  # current technology implementation details
├── adrs/                          # architecture decision records
│   ├── 0001-use-go-for-core-cli.md
│   └── ...
├── workflows/                     # SOPs and lifecycle runbooks
│   ├── regeneration.md            # single-shot rewrite runbook + fresh-agent prompt
│   ├── create-feature-spec.md
│   └── ...
├── core/                          # core specs namespace
│   └── device-discovery.md
├── cli/                           # cli specs namespace
│   ├── cli-entrypoint.md
│   ├── course-upload.md
│   ├── device-info.md
│   └── file-browser.md
└── templates/
    └── spec-template.md           # starting point for every new spec
```

## Status

This corpus was seeded on 2026-09-14 by reverse-engineering the existing implementation (commit `4520796`), then restructured the same day into namespaced specs with a shared template. It describes the system **as it currently behaves**, not aspirationally — it is the working baseline for this workflow, not a wishlist. Treat gaps/ambiguities you find while implementing future changes as bugs in the spec to be fixed, not license to guess.
