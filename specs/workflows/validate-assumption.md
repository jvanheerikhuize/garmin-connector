# Workflow: Validate an Assumption

**Trigger:** An assumption (`ASM-X`) has been proven true via testing, prototyping, user research, or empirical observation.

## Step 1: Promote to Fact
- Remove the `ASM-X` row from the Assumptions table in `constitution.md`.
- Create a new Fact (`FCT-Y`) in the External Facts table.
- Document the *Verification Method* (how we proved it) in the table.
- Ensure the `Source / Origin` carries over from the original assumption, or is updated to reflect the test.

## Step 2: Traceability Update (Refactoring the Graph)
- Perform a global Find & Replace across the entire `specs/` directory to update dependent specifications.
- In all spec frontmatter (`relies_on_assumptions`), remove `ASM-X`.
- In all spec frontmatter (`relies_on_facts`), insert `FCT-Y`.
- In any Architecture Decision Records (`specs/adrs/`) or `specs/tech-stack.md` that relied on `ASM-X`, update the justification to reference `FCT-Y`.

## Step 3: Execute the Fact Change Cascade
- Because validating an assumption introduces a verified fact (`FCT-Y`), trigger the [Fact Change Cascade](fact-change-cascade.md):
  1. Re-evaluate requirements in `constitution.md` (does the confirmed fact expand or alter capabilities?).
  2. Evaluate architecture and tech stack suitability in `specs/tech-stack.md`.
  3. Propagate changes into Feature Specs.
  4. Trigger `specs/workflows/regeneration.md` to rebuild the implementation from the new specs.
