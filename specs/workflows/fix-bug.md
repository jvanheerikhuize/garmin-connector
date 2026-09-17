# Workflow: Fix a Bug (Spec-Drift Prevention)

**Trigger:** The software behaves incorrectly, crashes, or fails an edge case not currently handled.

## Step 1: DO NOT PATCH THE CODE FIRST
- Resist the urge to dive into the application source code to write a quick `if/else` statement. Code is a byproduct of the spec; changing code directly introduces "spec drift".

## Step 2: Identify the Spec Gap
- Locate the specific file in `specs/skeleton/` or `specs/feature/` that governs this behavior.
- Determine why the bug happened:
  - Was a Data Shape missing a nullable field?
  - Was an explicit `MUST` requirement missing for the edge case?
  - Was an Assumption proven false? (If so, run `invalidate-fact.md` or `validate-assumption.md` instead).

## Step 3: Patch the Spec
- Update the Markdown spec to explicitly dictate how the software MUST handle this edge case.

## Step 4: Patch the Code
- Now that the spec is updated, instruct the agent/developer to implement the spec diff.
- Write a failing unit test based on the newly updated spec.
- Modify the application code to pass the test.
