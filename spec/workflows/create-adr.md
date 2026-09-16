# Workflow: Architecture Decision (Create / Change Tech Stack)

**Trigger:** A new technical tool, language, or framework must be chosen, OR an existing tech stack component is being replaced.

## Step 1: Draft the Architecture Decision Record (ADR)
- Create a new markdown file in `spec/adrs/` following the sequential naming convention (e.g., `0003-use-sqlite.md`).
- Define the **Context** (why the decision is needed).
- Define the **Decision** (what is being chosen).
- Map the decision to specific Constitution IDs (e.g., "This satisfies NFR-2").

## Step 2: Supersede Old Decisions (If Changing Stack)
- If this decision replaces an older one, edit the old ADR and change its Status to `Superseded by ADR-XXXX`.

## Step 3: Update the Tech Stack Manifest
- Open `spec/tech-stack.md`.
- Update the table to reflect the newly chosen technology, linking to the new ADR.

## Step 4: Application Code Regeneration
- If this decision changes existing implementation details (e.g., switching databases or programming languages), trigger `spec/workflows/regeneration.md` to align the codebase with the newly chosen architecture.
