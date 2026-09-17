# ADR 0003: Embedded Web GUI Using Standard Library

## Status
Accepted

## Context
With the introduction of FR-7 (Web-Based GUI Dashboard), the system requires a graphical interface accessible to the user without compromising the project's core non-functional requirements:
1. **NFR-2 (Standalone Execution)**: Zero external runtime requirements (no Node.js, Python, or external web servers required on the host system).
2. **NFR-3 (Exclusive Dependencies)**: No unnecessary third-party package dependencies.
3. **ASM-8**: The interface is launched on-demand by the user on localhost.

## Decision
We will implement the web GUI backend and file server using Go's standard library `net/http` and bundle all frontend assets (HTML, CSS, JavaScript) directly into the compiled binary using Go's `embed` package (`embed.FS`).

## Consequences
- **Positive:** The application remains a single, static binary executable with zero external runtime or browser framework dependencies, preserving NFR-2 and NFR-3.
- **Positive:** No external assets need to be distributed or placed in specific filesystem paths; the GUI is self-contained.
- **Positive:** Standard Go HTTP handlers can directly query the existing `internal/device` packages and emit JSON responses, reusing all discovery and diagnostic logic.
- **Negative:** Embedded frontend code is compiled into the binary, meaning frontend changes require recompiling the Go binary.
