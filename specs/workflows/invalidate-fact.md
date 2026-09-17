# Workflow: Invalidate a Fact

**Trigger:** The external environment changes, rendering an existing `FCT-X` false (e.g., a third-party API shuts down, OS removes a feature, or hardware behavior changes).

## Step 1: Mark the Fact as Invalidated
- Do NOT delete the fact from `constitution.md` completely without leaving a trace. 
- You may move it to an "Invalidated / Historical Facts" table at the bottom of the section.
- Document the reason and date of invalidation.

## Step 2: Traceability Impact Assessment
- Perform a global search (`grep`) across the `specs/` directory for `FCT-X`.
- Identify all Feature Specs, Skeleton Specs, and ADRs that list `FCT-X` in their `relies_on_facts` frontmatter.

## Step 3: Triage and Adapt
- For each affected Spec or ADR:
  - Determine if the core requirement can still be met without this fact.
  - Draft new Assumptions (`ASM-Y`) or Facts (`FCT-Y`) needed to bridge the gap.
  - Run the `create-requirement` or `validate-assumption` workflow if necessary.

## Step 4: Execute the Fact Change Cascade
- Invalidation of a fact triggers the full downstream cascade defined in [`specs/workflows/fact-change-cascade.md`](fact-change-cascade.md):
  1. Audit and update Functional and Non-Functional Requirements in `specs/constitution.md`.
  2. Re-evaluate the architecture and tech stack against `specs/tech-stack.md` (authoring new ADRs if needed).
  3. Rewrite the affected feature specs to accommodate the new reality.
  4. Trigger `specs/workflows/regeneration.md` to rebuild the implementation from the updated specifications.
