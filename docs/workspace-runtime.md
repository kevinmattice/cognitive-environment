# Workspace Runtime (Phase 3)

## Purpose

Phase 3 establishes a deterministic, inspectable workspace runtime centered around explicit workspace manifests and explicit source boundaries.

The workspace runtime exists to answer these questions without guessing:

- What workspace is open?
- What sources are declared?
- Which declared sources exist or are missing?
- What content is readable, and under what constraints?

This phase does not add model cognition, summarization, PEM runtime integration, or any autonomous behavior.

## Workspace Discovery

Discovery is intentionally narrow:

- Only the configured workspaces directory is inspected (default: `workspaces/`).
- Only direct child directories are considered workspaces.
- A directory is recognized as a workspace only if it contains an explicit manifest file (`workspace.toml`).

No recursive indexing is performed.

## Active Workspace Persistence (Phase 3.1)

The active workspace selection is persisted across manual gateway restarts in:

- `runtime/workspace-state.json`

This file is gitignored and human-inspectable JSON with the minimal shape:

```json
{
  "active_workspace_id": "example-workspace",
  "updated_at": "..."
}
```

Invalid/missing state files are treated as non-fatal and result in "no active workspace".

## Manifest Format

The manifest format is TOML (`workspace.toml`).

Rationale:

- The Python standard library can parse TOML via `tomllib` (no added dependency).
- The schema is kept small and human-readable.

If YAML is desired later, it should be a deliberate decision with an explicit parser dependency and explicit security posture.

## Manifest Schema v1

Required fields:

- `workspace_id` (string)
- `title` (string)

Optional fields:

- `description` (string)
- `notes` (string)

Sources:

- `sources` is a list of declared sources.
- Each source entry includes:
  - `source_id` (string, unique within the workspace)
  - `path` (string, workspace-relative path)
  - `kind` (string, optional)
  - `category` (string, optional)
  - `keywords` (list of strings, optional)
  - `aliases` (list of strings, optional)

Optional source metadata is workspace-authored and deterministic. It does not enable automatic ingestion or semantic retrieval; it only helps the gateway choose a smaller declared-source subset before model invocation.

Optional source presentation metadata:

- `display_name` (string, optional)

`display_name` is a human-readable label for the source. When present, the gateway can show it in answer provenance bullets instead of the raw file name.

Policies:

- `policies.max_read_bytes` (int, default 8192)

## Source Reading Rules

- Only declared sources may be enumerated or read.
- Declared source paths must resolve inside the workspace directory.
- Readable source types are explicit and limited: `.md`, `.txt`, and `.pdf` (PDF text extraction only).
- Unsupported file types are rejected explicitly.
- Missing files are reported explicitly.
- PDF notes:
  - Text extraction only (no OCR, rendering, image extraction, or table extraction).
  - If extraction yields no text, the runtime returns: `PDF text extraction produced no text; OCR is not supported.`
  - Encrypted/unreadable PDFs fail explicitly and safely.

## Deterministic Librarian Narrowing

When the gateway builds grounded QA context, it may use optional source metadata from `workspace.toml` to select a small deterministic subset of declared sources before model invocation.

Rules:

- Explicit source IDs or declared paths in the question remain an escape hatch.
- Otherwise, source selection uses only workspace-authored metadata (`category`, `keywords`, `aliases`).
- The model does not participate in source selection.
- Selection is deterministic and visible in the answer provenance bullets while tuning.
- If the question is clearly single-fact and multiple sources tie for the best score, the gateway may ask a clarification question instead of guessing.
- Existing workspaces without metadata continue to work unchanged.

## Gateway Commands

Workspace commands are exposed through the gateway:

- `workspace list`
- `workspace open <id>`
- `workspace status`
- `sources`
- `read <source>`

Responses are concise and operational.
