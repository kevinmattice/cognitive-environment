# Grounded Question Answering (Phase 4)

## Command

`ask <question>`

## Status

Phase 4 defines the boundary and wiring. Reliability must be verified via live Matrix testing.

## Phase 4.1 Natural Question Routing

When an active workspace is open, ordinary non-command text is routed through the same grounded QA path as `ask <question>`.

Command-like operational inputs (e.g. `shell ...`, `delete ...`, `workspace ...`) do not route to the model.

## Preconditions

- An active workspace must be open.
- At least one declared readable source must exist (`.md` / `.txt` / `.pdf`).

## Context Assembly Rules

- Only declared sources from the active workspace are used.
- Only existing, readable sources are included.
- Sources are included deterministically (stable ordering).
- A maximum context byte budget is enforced (`model_max_context_bytes`).
- If the budget is exceeded, context is truncated and the reply includes `[truncation: context limited]`.

## Output Requirements

Responses should be concise and include visible source references.

This phase does not claim summarization, memory, retrieval, or autonomous reasoning.
