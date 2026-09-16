# ADR 0002: Use JSON for Structured Output

## Status
Accepted

## Context
External scripts and tools require machine-readable structured output to consume the device status headlessly (ASM-2). We need to decide on the format that best balances human readability, ecosystem support, and machine parsability.

## Decision
We will use **JSON** as the standard format for all machine-readable output across CLI commands.

## Consequences
- **Positive:** JSON is universally supported by almost all programming languages and integration tools (like `jq`).
- **Positive:** The Go standard library has robust, built-in JSON marshaling support.
- **Negative:** JSON does not support comments natively, but this is acceptable for machine-to-machine output.
