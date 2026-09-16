---
id: kebab-case-id                  # stable, matches filename without extension; never renamed once referenced by depends_on elsewhere
title: Human-Readable Title
tier: skeleton                     # skeleton = load-bearing for the walking skeleton/MVP | feature = layered on top, can be removed without breaking the skeleton
status: draft                      # draft (proposed, not yet implemented) | implemented (matches codebase) | deprecated (superseded, kept for history)
owners: [jerry]
depends_on: []                     # ids of other specs this one builds on or assumes are present
implements_requirements: []        # ids of requirements from constitution.md this spec fulfills (e.g., [FR-1, NFR-2])
relies_on_facts: []                # ids of external facts from constitution.md this spec relies upon (e.g., [FCT-1])
relies_on_assumptions: []          # ids of assumptions from constitution.md this spec relies upon (e.g., [ASM-1])
last_updated: YYYY-MM-DD
---

# <Title>

`path/to/implementing/module` (or files, if more than one)

Depends on: [other-spec-title](../relative/path.md) <!-- omit this line if depends_on is empty -->

## Constitution Alignment

- **Implements Requirements:** `FR-X` ... <!-- omit this section if none -->
- **Relies on Facts:** `FCT-X` ... <!-- omit this section if none -->
- **Relies on Assumptions:** `ASM-X` ... <!-- omit this section if none -->

## Purpose

One paragraph: what this exists to do and why, in plain language. Not a restatement of the requirements below.

## Scope

**In scope:**
- Bullet list of what this spec covers.

**Out of scope:**
- Bullet list of adjacent behavior this spec deliberately does NOT cover (link to the spec that does, if one exists).

## Requirements

Numbered or bulleted, grouped by sub-behavior. Use RFC 2119 language (MUST/MUST NOT/SHOULD/MAY) so requirements are testable, not descriptive prose. Each requirement should be precise enough that two different implementers (human or agent) would produce interoperable results.

### <Sub-behavior A>
- MUST ...
- MUST NOT ...
- SHOULD ... (justify why it's a should, not a must)

### <Sub-behavior B>
- ...

## Data Shapes / Interfaces

Concrete schemas: function signatures, request/response JSON shapes, dataclass fields, message formats. This is what makes the spec regenerable — an implementer should not have to guess a field name or type.

```
ExampleShape:
  field: type              # notes on units, encoding, limits
```

## Non-Goals

Explicit exclusions — things a reasonable implementer might assume are in scope but aren't. This is what prevents scope creep during single-shot (re)generation.

## Open Questions

Unresolved decisions blocking full confidence in the "rebuild test" (see [spec/README.md](../README.md)). Delete this section if there are none — don't leave it as a placeholder.
