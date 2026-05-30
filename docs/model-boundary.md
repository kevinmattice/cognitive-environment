# Model Boundary (Phase 4)

## Purpose

Phase 4 introduces a minimal local-model boundary for bounded question answering over an active workspace.

The model is treated as a stateless reasoning component:

- explicit input prompt/context in
- plain text output out
- no hidden session or memory behavior

## Invocation Strategy

Default provider: `ollama`

Invocation is performed via a direct subprocess call:

- `ollama run <model_name>`
- prompt is provided on stdin
- timeout is enforced

No shell interpolation is used.

## Configuration

Configured via `config/cce.json`:

- `model_provider` (default `ollama`)
- `model_name` (default `llama3.1`)
- `model_max_context_bytes` (default `24000`)
- `model_timeout_s` (default `30`)

## Non-Goals

This phase does not add:

- embeddings / vector DBs
- semantic retrieval / indexing
- web access
- PEM runtime integration
- autonomous planning
- background agents
