# Workflow: Deprecate a Feature

**Trigger:** A business requirement is dropped or a feature is no longer needed.

## Step 1: Mark as Deprecated
- Update the `status` field in the spec's frontmatter to `deprecated`.
- Do NOT immediately delete the markdown file (it provides historical context).

## Step 2: Orphan Check (Pruning the Graph)
- Look at the `relies_on_assumptions` and `relies_on_facts` in the deprecated spec.
- Check if those Assumptions/Facts are used by *any other* specs (via global search).
- If an Assumption or Fact is now orphaned (used nowhere else), consider removing it from `constitution.md` to keep the domain model clean.

## Step 3: Code Cleanup
- Run `specs/workflows/regeneration.md`. The agent will read the specs, notice the feature is marked `deprecated`, and safely remove the corresponding application code and tests.
