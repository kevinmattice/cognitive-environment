# Colossus Cognitive Environment (CCE)

CCE is a private, low-friction, inspectable operating channel between a human-facing interface (today: Matrix/Element) and a local runtime on Colossus.

## Architectural stance (read first)

- **CCE is the substrate; front ends are replaceable; operational semantics are authoritative; interfaces are not.**
- Near-term map (through June 18, 2026): `docs/near-term-architecture.md`
- Architectural invariants: `docs/architectural-invariants.md`
- Front-end adapter boundary: `docs/frontend-adapter-boundary.md`

## Core docs

- Reins evaluation framing: `docs/reins-evaluation.md`
- Architecture overview: `docs/architecture.md`
- June 18 milestone framing: `docs/june18-target.md`
- Operational principles: `docs/operational-principles.md`
- Decisions: `docs/decision-log.md`

## Operational boundaries

- Workspace runtime: `docs/workspace-runtime.md`
- Grounded QA: `docs/grounded-question-answering.md`
- Conversational mode: docs/conversational-mode.md
- Model boundary: `docs/model-boundary.md`
- Matrix auth hardening: `docs/matrix-auth-hardening.md`
- Private Matrix homeserver plan (Synapse, tailnet-only): `docs/private-matrix-homeserver.md`

## Dependencies

- PDF declared-source support (text extraction only) requires `pypdf` (see `requirements.txt`).
