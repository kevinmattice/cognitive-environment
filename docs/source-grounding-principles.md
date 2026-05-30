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

## Non-Goals

This phase does not include:

- semantic search
- embeddings or vector databases
- automatic ingestion
- summarization
- hidden memory
