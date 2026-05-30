# Front-End Adapter Boundary

## Purpose

Define a strict boundary for CCE front ends so:

- front ends remain replaceable
- interfaces cannot capture or redefine CCE architecture
- operational semantics remain authoritative in the substrate

This document defines contract-level expectations for any front-end adapter (including future experiments such as Reins).

## Definition: what a CCE front-end adapter is

A CCE front-end adapter is a **transport/display boundary** that:

- accepts user input (usually text)
- carries that input into the CCE substrate (gateway/core)
- returns CCE responses back to the user

A front end **does not own CCE semantics**. It must not become the authority for workspace truth, grounding rules, PEM continuity, or completion semantics.

## Authority rule (non-negotiable)

**CCE is the substrate; front ends are replaceable; operational semantics are authoritative; interfaces are not.**

See `docs/architectural-invariants.md`.

## What front ends MAY own

Front ends may own adapter-local concerns only:

- transport mechanics (protocol details, message polling/push, retries)
- connection/session details (log-in flows, token storage policy inside the adapter, reconnection strategy)
- UI display choices (rendering, layout, affordances)
- local notification behavior
- transport-local cursor/session state (e.g., a sync cursor) needed for reliable delivery
- input affordances (slash commands, buttons, quick replies) as UI conveniences

Rule of thumb: if it can be discarded with no change to substrate truth, it can be adapter-owned.

## What front ends MUST NOT own

Front ends must not own or redefine:

- workspace truth (what workspace is open, what is in scope)
- manifest rules (what is a valid workspace, what files/sources exist)
- grounding eligibility (what content is permitted as context)
- model context construction (what sources are included, ordering, byte budgets)
- PEM continuity (case continuity, provenance, epistemic governance)
- verified completion semantics (what “complete” means)
- durable project state (any substrate state of record)
- source provenance rules (what counts as evidence, what must be cited)
- command authorization semantics (what commands exist, what they do, what is allowed)

Rule of thumb: if it changes the meaning of “what happened” or “what is true”, it must be substrate-owned.

## Minimal adapter contract (transport-agnostic)

The adapter must:

1. **Accept user text input**
2. **Normalize** input into a message text form suitable for the gateway/core
   - normalization must be minimal and documented (e.g., whitespace trimming)
   - must not rewrite intent
3. **Preserve identity** enough for audit
   - sender identity (stable user id)
   - session/room/channel identity (where the message came from)
4. **Send message to CCE gateway/core** as the single semantic entrypoint
5. **Return plain response text** from CCE to the user
6. **Preserve error fidelity**
   - surface auth failures, transport failures, and substrate failures distinctly
7. **Avoid false success**
   - do not pretend failed operations succeeded
8. **Avoid hidden rewriting**
   - no silent paraphrasing, command reinterpretation, or intent smoothing

Non-requirements (explicitly *not* in the adapter contract):

- no adapter-owned grounding logic
- no adapter-owned completion detection
- no adapter-owned retrieval/indexing

## Operational requirements

A front-end adapter must support lived operational prototyping, especially mobile reliability:

- low-friction mobile use (fast to access; minimal babysitting)
- clear failure modes (auth, network, permission, substrate)
- reconnect behavior visible enough to diagnose (no invisible “half-connected” state)
- no silent message loss where avoidable (duplicates are preferable to loss when clearly signaled)
- no hidden durable memory (adapter restarts must not imply “memory” beyond transport continuity)
- no broad filesystem/tool authority
- no bypassing CCE workspace/model/PEM rules

## Candidate front-end evaluation criteria (e.g., Reins)

Any candidate front end is evaluated as a reliability/friction-reduction experiment only:

- reliability (delivery guarantees and failure handling)
- mobile usability (time-to-interact, ergonomics)
- reconnect behavior (continuity under interruption)
- latency (perceived and measured)
- ability to preserve source-grounded response shape (including citations/refs)
- ability to surface failures clearly (no smoothing that hides diagnosability)
- degree of architectural intrusion (pressure to relocate authority into the UI)
- whether it reduces or increases operational babysitting

## Current verified adapter path

Element/Matrix remains the **currently verified** adapter path until another front end is verified against this boundary.

Shorthand:

`Element/Matrix -> CCE gateway -> workspace runtime -> local model`

## Explicit non-goals

This document does not implement any adapter, including Reins, and does not change runtime behavior.

