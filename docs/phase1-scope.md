# Phase 1 Scope

## Objective

Phase 1 establishes the minimum reliable operational foundation for a private Matrix/Element-to-Colossus channel. It is a planning and foundation phase only.

## In scope

### Reliable Matrix round-trip foundation

Define the expected ingress/egress path, message handling assumptions, failure surfaces, and the criteria for saying the communication path is reliable enough to build on.

### Local model invocation boundary

Define a narrow contract for model invocation: inputs, allowed context surfaces, output capture, timeout/failure handling, and what may be claimed from the result.

### Workspace manifest concept

Define a versioned manifest concept that declares the files, documents, and bounded state surfaces in scope for work.

### Source-grounded document reading concept

Define how documents are read and cited from explicit sources in a workspace rather than from hidden or inferred context.

### Deterministic tool boundary

Define the tool model as inspectable, named operations with constrained inputs/outputs and no uncontrolled side effects.

### Verified completion semantics

Define what counts as complete, partially complete, blocked, unverifiable, or deferred. Completion claims must be tied to observable evidence.

### PEM-backed continuity and governance role

Define PEM's role in continuity, evidence discipline, decision traceability, and explicit unknowns.

### Explicit state surfaces

Define which state surfaces exist at all in Phase 1, ensure they are visible and bounded, and treat `cases/`, `scratch/`, and `pem.initialized` as intentional repository surfaces rather than residue.

## Deliverables for this phase

- Architecture and contracts documentation
- Repository directory structure aligned with those contracts
- Explicit documentation of first-class state surfaces
- Decision log
- Minimal README describing scope, non-goals, and target date

## Exit criteria

Phase 1 is successful if a reviewer can inspect the repository and understand:

1. What the system is for
2. What the first implementation phase should and should not build
3. What boundaries exist between Matrix, gateway, models, tools, workspaces, and PEM
4. What counts as verified completion
5. Which areas are intentionally deferred
