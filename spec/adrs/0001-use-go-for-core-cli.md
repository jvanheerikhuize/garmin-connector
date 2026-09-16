# ADR 0001: Use Go for Core CLI

## Status
Accepted

## Context
We need to select a programming language to implement the `garmin-connector` CLI tool.
According to the Constitution, the tool must have low overhead and run as a standalone execution unit without requiring users to pre-install runtimes or packages (NFR-2). It must also easily interface with the Linux filesystem (FR-1).

## Decision
We will use **Go (Golang)** as the primary programming language for this project.

## Consequences
- **Positive:** Go compiles to a static binary by default, completely fulfilling NFR-2. It has an excellent standard library for CLI tools and filesystem operations.
- **Positive:** High performance and fast startup times, matching the on-demand invocation expectation (ASM-1).
- **Negative:** We must manage cross-compilation if we ever expand beyond Linux, though Go makes this relatively straightforward.
