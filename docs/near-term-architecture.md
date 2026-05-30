# Near-Term Architecture Map (through June 18, 2026)

## Purpose

This is the near-term map of what CCE *is today*, what is verified, and what must remain invariant while interface experiments (including Reins) are evaluated.

This document is intentionally scoped to the June 18, 2026 reliability milestone.

## One-line architectural identity

CCE is the substrate; front ends are replaceable; operational semantics are authoritative; interfaces are not.

See `docs/architectural-invariants.md`.

Front-end adapter boundary: `docs/frontend-adapter-boundary.md`.

## Current verified capabilities (operational substrate)

CCE has crossed from speculative architecture into lived operational prototyping. Verified capabilities include:

- Matrix communication works end-to-end (ingress/egress).
- Matrix sync cursor state persists across restart.
- Matrix auth failures are clearer and halt safely.
- Workspace manifests define bounded truth containers.
- Declared source access works (declared-only, deterministic, bounded reads).
- Active workspace persists across restart.
- Local grounded QA works when a workspace is active.
- Natural questions route to grounded QA when a workspace is active.
- A first real workspace exists and has been live-tested: `workspaces/montana-trip/`.

## Current active path (authoritative operational flow)

1. **Front end (today): Element/Matrix**
2. **CCE gateway/kernel** (message handling, command routing, state surfaces)
3. **Workspace runtime** (manifest resolution, declared sources, bounded reads)
4. **Model boundary** (local model invocation, explicit input/output)

Shorthand:

`Element/Matrix -> CCE gateway -> workspace runtime -> local model`

Notes:

- Transport continuity (Matrix cursor) is transport-scoped operational state.
- Workspace continuity (active workspace id) is workspace-boundary operational state.
- Neither is PEM continuity and neither is “memory”.

## Front-end adapter boundary

Any front end beyond the currently verified Element/Matrix path must be evaluated and implemented (later) against the adapter boundary in `docs/frontend-adapter-boundary.md`.

## Interface experiments: Reins framing

Reins is a **candidate interface/transport experiment**.

Controlled evaluation notes: see `docs/reins-evaluation.md`.

Reins may be evaluated in a parallel topology as a direct Ollama mobile client without changing the verified CCE path; this does not make it a CCE adapter.

- Reins is not a substrate replacement.
- Reins evaluation must not redefine workspace authority, grounding rules, PEM continuity, or completion semantics.
- Any Reins adapter must preserve substrate semantics and failure diagnosability.

## June 18, 2026 target scope

June 18 is a **reliability milestone**, not a “full CCE” milestone.

The purpose is dependable mobile interaction with:

- continuity across interruption/reconnection
- low-friction access
- operational trust (errors are explicit; recovery is possible)

See `docs/june18-target.md`.

## Explicit non-goals before June 18

Before June 18, do not add or expand:

- Reins integration (no adapter implementation yet)
- new runtime behavior
- new model behavior
- PEM runtime integration
- workspace feature expansion beyond documented, bounded semantics
- Matrix feature expansion beyond reliability/diagnosability
- service orchestration
- embeddings/vector DB
- autonomous behavior
- shell tools / broad filesystem access
- external web access

See also `docs/non-goals.md`.

## Known caveats (current lived constraints)

- **Mobile reliability is fragile in Element**; interface reliability is an operational risk surface.
- Front-end reliability failures must be treated as first-class signals (friction, interruption, reconnection, habit formation, trust failures).
- “Works on desktop” is not a proxy for dependable mobile continuity.

## What must remain invariant across front ends

Across Element, Reins, or any future interface, the following must not change:

- **Workspace truth is manifest-bounded** (`workspace.toml` is the authority).
- **Declared sources only** (no implicit repo browsing, no ambient filesystem knowledge).
- **Grounding eligibility is substrate-owned** (front end may display; substrate decides).
- **Completion semantics are operational** (front end must not redefine “done”).
- **Failure modes stay explicit** (front end must not smooth away diagnosability).
- **State ownership remains in the substrate** (no UI-owned workspace state, grounding rules, PEM continuity, or completion semantics).

## What future front-end adapter work should preserve

When an adapter is built (later), it should preserve:

- message integrity (no silent transformations that change meaning)
- error fidelity (surface auth failures, transport failures, and substrate failures distinctly)
- idempotent handling where applicable (avoid duplicate sends/loops)
- transport continuity only (cursor persistence belongs to transport boundary)
- substrate authority for all semantics (workspaces, grounding, completion)

## References

- `docs/architectural-invariants.md`
- `docs/architecture.md`
- `docs/operational-principles.md`
- `docs/decision-log.md`
- `docs/workspace-runtime.md`
- `docs/grounded-question-answering.md`
- `docs/model-boundary.md`
- `docs/matrix-auth-hardening.md`
- `docs/june18-target.md`

