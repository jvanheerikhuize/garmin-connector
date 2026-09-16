# Workflow: Create a Requirement

**Trigger:** A stakeholder requests a new capability or a new constraint is discovered.

## Step 1: Draft the Requirement
- Assign the next available `REQ-X` ID (e.g. `FR-X` for functional, `NFR-X` for non-functional).
- Define the requirement using RFC 2119 language (MUST, SHOULD, MAY).
- Ensure the requirement is completely decoupled from the tech stack (describes the *what*, not the *how*).

## Step 2: Inheritance & Causality Check
Ask the following questions. If the answer is yes, draft them and link their `Source / Origin` column to this new `REQ-X`.
- **Does this require new Tech Stack changes?** (If yes, draft an ADR in `spec/adrs/` linking back to the requirement).
- **Does this rely on unknown variables or user behaviors?** (If yes, draft new `ASM-X` Assumptions).
- **Does this rely on external truths (APIs, hardware, OS)?** (If yes, draft new `FCT-X` Facts).

## Step 3: Update Constitution
- Insert the Requirement into the `3. Requirements` section in `constitution.md`.
- Insert any new Assumptions or Facts generated from Step 2 into their respective tables in `constitution.md`, using the new `REQ-X` ID in the `Source / Origin` column.

## Step 4: Downstream Specs
- If this requirement requires a new feature, duplicate `spec/templates/spec-template.md` into `spec/feature/<feature-name>.md`.
- If this modifies an existing feature, update its spec file.
- Update the frontmatter of the affected specs:
  - Add the new `REQ-X` to `implements_requirements`.
  - Add any new `ASM-X` to `relies_on_assumptions`.
  - Add any new `FCT-X` to `relies_on_facts`.
