# Architectural Invariants

## Purpose

This document records the architectural truths that must carry forward across interface experiments (including Reins) so the lived operational substrate of CCE cannot be accidentally redefined.

These invariants are **authoritative constraints** on near-term work.

## Core authority invariant (non-negotiable)

**CCE is the substrate; front ends are replaceable; operational semantics are authoritative; interfaces are not.**

Implications:

- A front end must never become the authority for workspace state, grounding rules, PEM continuity, or completion semantics.
- A front end may be swapped without redefining what CCE *is*.

## Invariants by boundary

### 1) Substrate vs. interface

- **CCE (gateway + workspace runtime + model boundary + explicit state surfaces) is the substrate.**
- **Front ends are adapters.** They translate user interaction into substrate inputs and substrate outputs back into a UI/transport.
- **Operational semantics live in the substrate** (what is considered “open workspace”, what sources are readable, what “complete” means, what gets recorded, how failure is surfaced).

### 2) Explicit authority surfaces

- Repository state surfaces remain explicit and inspectable (see `docs/state-surfaces.md`).
- Operational continuity state is explicit and minimal:
  - Transport cursor persistence is transport continuity only (Matrix `next_batch` / equivalent).
  - Active workspace persistence is workspace-boundary convenience only.
  - Neither is a “memory system”.

### 3) Workspace truth is bounded

- A workspace is a **bounded truth container** defined by an explicit manifest (`workspace.toml`).
- Only declared sources are readable; undeclared files are not implicitly in scope.
- Source reading remains deterministic, byte-budgeted, and failure-explicit.

### 4) Grounding rules are substrate-owned

- Grounded QA uses declared sources from the active workspace only (see `docs/grounded-question-answering.md`).
- A front end may display citations, previews, or affordances, but it does not decide what sources exist or what content is eligible.

### 5) Model boundary is explicit and narrow

- The model is treated as a stateless reasoning component: explicit input in, plain text out (see `docs/model-boundary.md`).
- No interface is allowed to smuggle hidden state, memory, or retrieval into the model boundary implicitly.
- “Answer quality” improvements must not widen access surfaces without an explicit decision.

### 6) Completion semantics are operational

- “Complete” is not a UI feeling; it is a substrate claim tied to observable evidence (see `docs/decision-log.md` and `docs/operational-principles.md`).
- A front end must preserve completion markers and failure modes; it may not reinterpret them to look smoother.

### 7) Recovery and reliability remain first-class

- Operational recovery must remain inspectable and manual-debuggable.
- Reliability failures observed in one interface (e.g., Element mobile fragility) are **operational facts** to be addressed by substrate discipline and/or interface swap — not a reason to move authority into the UI.

## Near-term (June 18, 2026) invariant scope

June 18, 2026 is **not** a target for realizing “full CCE”. It is a **reliability milestone** for:

- dependable mobile interaction
- continuity across interruption/reconnection
- low-friction access
- operational trust

Any work framed as “before June 18” must preserve all invariants above and must not expand scope into:

- new substrate semantics
- autonomous behavior
- embeddings / vector DB retrieval
- PEM runtime integration
- broad shell / filesystem access

## Front-end adapter boundary

The front-end adapter boundary is defined in `docs/frontend-adapter-boundary.md`. It is mandatory for any interface experiment.

## What front-end adapter work must preserve

When experimenting with a new front end (e.g., Reins), the adapter layer must:

- treat the substrate as the system of record
- pass through substrate errors without smoothing away diagnosability
- avoid new state ownership (no UI-owned workspace truth, grounding eligibility, PEM continuity, or completion rules)
- keep transport continuity strictly transport-scoped

