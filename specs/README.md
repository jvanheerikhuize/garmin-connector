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
9. **Tech-stack agnosticism**: `specs/` (Constitution, Requirements, Facts, Assumptions, and Feature Specs) MUST remain strictly agnostic to the implementation language. They define *what* the system does and external environment contracts, never *how* in a specific language (e.g., Go, Rust, Python). Concrete language choices, standard libraries, and build toolchains belong exclusively in `specs/tech-stack.md` and `specs/adrs/`. Future agents and contributors must never introduce language-specific types, function names, package paths, or language imports into `specs/`.
10. **The Causal Cascade Law**: Every shift in real-world facts (`FCT-X` added, invalidated, or verified from an `ASM-Y`) MUST trigger the [Fact Change Cascade](workflows/fact-change-cascade.md). Changes flow strictly top-down: Facts → Requirements (`FR`/`NFR`) → Architecture & Tech Stack Evaluation (`tech-stack.md`/`adrs/`) → Feature Specs → Implementation Regeneration. Code changes must NEVER precede or bypass upstream specification layers.

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
│   ├── fact-change-cascade.md     # facts -> requirements -> tech stack -> rewrite cascade runbook
│   ├── regeneration.md            # single-shot rewrite runbook + fresh-agent prompt
│   ├── create-feature-spec.md
│   └── ...
├── core/                          # core specs namespace
│   └── device-discovery.md
├── cli/                           # cli specs namespace
│   ├── cli-entrypoint.md
│   ├── course-upload.md
│   ├── device-info.md
│   ├── file-browser.md
│   └── filesystem-manipulation.md
├── gui/                           # web gui specs namespace
│   ├── course-preview.md
│   ├── course-upload.md
│   ├── dashboard.md               # owns the HTTP server and the request-origin gate (NFR-4)
│   ├── file-browser.md
│   └── filesystem-manipulation.md
└── templates/
    └── spec-template.md           # starting point for every new spec
```

## Status

This corpus was seeded on 2026-09-14 by reverse-engineering the then-existing implementation (its history has since been squashed into the initial-release commit `ac1b7e5`), then restructured the same day into namespaced specs with a shared template. It describes the system **as it currently behaves**, not aspirationally — it is the working baseline for this workflow, not a wishlist. Treat gaps/ambiguities you find while implementing future changes as bugs in the spec to be fixed, not license to guess.

**Pending implementation (2026-09-18):** a security/consistency audit was folded into the corpus ahead of the code. The following are specified but not yet regenerated, and `main`'s generated code does not satisfy them until the next single-shot implementation runs: `NFR-4` request-origin gate ([gui/dashboard.md](gui/dashboard.md)), `FCT-23` percent-encoding of GVFS URIs, the `GARMIN`-root delete guard on the CLI, RFC 6266 encoding of the download filename, symlink containment at the storage root, the `--` end-of-flags token, and JSON body limits. One open question was left in [core/device-discovery.md](core/device-discovery.md).
