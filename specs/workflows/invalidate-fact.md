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

## Step 4: Spec Update & Regeneration
- Rewrite the affected feature specs to accommodate the new reality.
- Trigger `specs/workflows/regeneration.md` to instruct the agent to update the implementation to match the new spec.
