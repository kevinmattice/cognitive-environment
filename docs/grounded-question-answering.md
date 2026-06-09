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

## Deterministic Librarian Narrowing

- Explicit source IDs and declared paths remain an escape hatch.
- Otherwise, the gateway may use workspace-authored `category`, `keywords`, and `aliases` metadata to narrow the selected source set before the model runs.
- The model does not choose sources.
- The gateway may select up to 3 sources when they are plausible and strongly relevant.
- If a question is clearly single-fact and multiple sources tie for the top score, the gateway may ask for clarification instead of guessing.
- The response includes a short provenance bullet list during tuning, using workspace-authored `display_name` labels when available.

## Conversational Fallback

When no relevant workspace source is selected, the gateway may answer with the general local model instead of refusing. This is controlled by conversational_fallback_enabled in the runtime config.

General answers:

- do not include a fake Sources section
- do not claim document grounding
- remain concise and helpful

## Output Requirements

Responses should be concise and include visible source references.
For answers with multiple items or times, a short bullet list is preferred.

This phase does not claim summarization, memory, retrieval, or autonomous reasoning.
