# Architecture

## Purpose

CCE exists to provide a private, low-friction, inspectable operating channel between Matrix/Element and Colossus. The system should stay narrow, deterministic where possible, and explicit about what it knows, what it can touch, and what it has verified.

## Architectural layers

### 1. Communication layer: Matrix/Element

Matrix/Element provides the human-facing transport. In Phase 1, this layer is only concerned with reliable message ingress, bounded message handling, and reliable message egress. It is not a place for hidden workflow logic.

### 2. Reasoning layer: local models on Colossus

Local models provide bounded reasoning. The model boundary should be explicit: request in, response out, with known inputs and captured outputs. The model is not treated as a hidden state store.

### 3. Operational layer: deterministic bounded tools

Operational capability is exposed through narrow tools with explicit arguments, explicit outputs, and inspectable failure modes. Tools should be boring, constrained, and auditable.

### 4. Epistemic governance layer: PEM

PEM provides continuity, source-grounding expectations, decision traceability, and governance over what can be treated as known, verified, deferred, or unknown.

### 5. Durable truth containers: workspaces and manifests

Workspace manifests define the bounded truth surface for a task or thread. They declare what documents, files, and state are in scope rather than assuming ambient filesystem knowledge.

### 6. Narrow orchestration layer: gateway/kernel

The gateway coordinates message handling, manifest resolution, tool dispatch, model invocation, and PEM interactions. It must remain narrow and avoid becoming a hidden autonomous control plane.

## Explicit state surfaces

Phase 1 treats the following repository surfaces as first-class and inspectable:

- `workspaces/`: durable bounded truth containers and future manifest-backed workspace definitions
- `cases/`: PEM-backed continuity and forensic case records tied to bounded work
- `scratch/`: ephemeral, non-authoritative working space for temporary artifacts
- `pem.initialized`: explicit marker that PEM project initialization has occurred

These surfaces are not hidden implementation residue. They are part of the repository's visible operational model and should remain documented as such.

## Phase 1 architectural stance

- Prefer explicit files over inferred memory
- Prefer manifests over ambient filesystem traversal
- Prefer bounded tools over shell access
- Prefer documented contracts over clever coupling
- Prefer verified completion signals over optimistic claims

## High-level data flow

1. Matrix message arrives
2. Gateway creates or resolves an explicit state surface
3. Relevant workspace manifest is loaded
4. Source documents and bounded tools are made available according to manifest and policy
5. Local model is invoked through an explicit boundary
6. PEM records governing context, continuity, and verification state, including case-level artifacts where applicable
7. Gateway returns a response with explicit completion semantics

## Out of scope for this phase

Phase 1 does not include autonomous planning loops, hidden memory, multi-agent delegation, broad shell or filesystem powers, or embeddings-backed retrieval.
