# Source Grounding Principles (Phase 3)

## Principle: Declared Sources Only

CCE must never silently discover, index, or ingest files. If a file is not declared as a source in the active workspace manifest, it is out of scope.

## Principle: Visible Provenance

Every loaded source must be tied to:

- a workspace id
- a declared source id
- a declared path in the manifest

## Principle: Explicit Missingness

Missing sources are part of reality and must be reported explicitly (not guessed around).

## Principle: Deterministic Reading

Reading is bounded and deterministic:

- file type restrictions are explicit
- maximum read size is explicit
- path traversal is rejected explicitly
- when PDFs are supported, they are treated as text-only sources via deterministic extraction (no OCR)

## Principle: Workspace-Authored Librarian Hints

Optional source metadata in a workspace manifest (`display_name`, `category`, `keywords`, `aliases`) may be used to deterministically narrow the declared-source set before model invocation and present human-readable provenance labels.

- The metadata is authored in the workspace manifest, not inferred or learned.
- The model does not participate in source selection.
- Existing workspaces without metadata continue to behave as they did before.
- Selection remains inspectable and bounded to declared sources only.

## Non-Goals

This phase does not include:

- semantic search
- embeddings or vector databases
- automatic ingestion
- summarization
- hidden memory
