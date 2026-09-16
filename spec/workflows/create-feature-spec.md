# Workflow: Create a Feature Spec

**Trigger:** A Requirement (`REQ-X`) from the Constitution is ready to be detailed into actionable, testable software behavior.

## Step 1: Scaffold the Spec
- Duplicate `spec/templates/spec-template.md` into either `spec/skeleton/` (if core/MVP) or `spec/feature/` (if layered/optional).
- Rename the file to describe the feature (e.g., `export-csv.md`).

## Step 2: Frontmatter & Traceability
- Set the `id` to match the filename.
- Fill out `implements_requirements` with the `REQ-X` IDs this spec fulfills.
- Fill out `relies_on_facts` and `relies_on_assumptions` with the specific truths this feature depends on.

## Step 3: Define Tech-Agnostic Behavior
- Write the requirements in RFC 2119 language (MUST, SHOULD).
- Define the **Data Shapes / Interfaces** using generic syntax (e.g., YAML, JSON schema, or TypeScript interfaces). **Do not use language-specific (e.g., Go/Rust) struct definitions in the spec.**

## Step 4: Implementation
- Review the spec for gaps or ambiguities.
- Once approved, run `spec/workflows/regeneration.md` to instruct the agent/developer to implement the spec in code.
