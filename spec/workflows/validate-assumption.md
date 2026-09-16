# Workflow: Validate an Assumption

**Trigger:** An assumption (`ASM-X`) has been proven true via testing, prototyping, user research, or empirical observation.

## Step 1: Promote to Fact
- Remove the `ASM-X` row from the Assumptions table in `constitution.md`.
- Create a new Fact (`FCT-Y`) in the External Facts table.
- Document the *Verification Method* (how we proved it) in the table.
- Ensure the `Source / Origin` carries over from the original assumption, or is updated to reflect the test.

## Step 2: Traceability Update (Refactoring the Graph)
- Perform a global Find & Replace across the entire `spec/` directory to update dependent specifications.
- In all spec frontmatter (`relies_on_assumptions`), remove `ASM-X`.
- In all spec frontmatter (`relies_on_facts`), insert `FCT-Y`.
- In any Architecture Decision Records (`spec/adrs/`) or `spec/tech-stack.md` that relied on `ASM-X`, update the justification to reference `FCT-Y`.

## Step 3: Application Code Regeneration
- If validating this assumption resulted in uncovering edge cases or changing the data structures, ensure those updates are reflected in the Feature Specs first.
- If the spec changed, trigger the `spec/workflows/regeneration.md` protocol to allow the autonomous agent (or developer) to rebuild the implementation from the new facts.
