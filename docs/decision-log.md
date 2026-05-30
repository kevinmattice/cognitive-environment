# Decision Log

## 2026-05-28

### D-020: CCE substrate authority (operational semantics)

CCE is the substrate. The substrate (gateway, workspace runtime, model boundary, and explicit state surfaces) is the system of record for operational semantics.

Interfaces and transports are adapters and must not redefine substrate semantics.

### D-021: Front ends are replaceable

CCE must be architected so a front end can be replaced without redefining workspace authority, grounding rules, PEM continuity, or completion semantics.

### D-022: Reins is an interface experiment, not a substrate replacement

Any evaluation of Reins is framed as a transport/interface experiment. It may improve reliability and usability, but it is not permitted to relocate authority into the UI layer or redefine substrate responsibilities.

### D-023: June 18, 2026 is a reliability milestone

June 18, 2026 is not a target for realizing full CCE. It is a milestone for dependable mobile interaction, continuity, low-friction access, and operational trust.

### D-024: Phase transition to lived operational prototyping

CCE has crossed from speculative architecture into lived operational prototyping. Near-term architectural discovery should come primarily from lived use (friction, interruption, reconnection, habit formation, trust failures, boredom, and real operational loops) rather than speculative interface design.

### D-025: Front-end adapter boundary defined before Reins evaluation

The front-end adapter boundary is defined in `docs/frontend-adapter-boundary.md` before any Reins evaluation or other interface experiments. This preserves substrate authority and prevents interfaces from capturing CCE semantics.

### D-026: Controlled Reins evaluation is parallel and non-migratory

Reins evaluation is a controlled usability/reliability experiment. It runs in parallel to the verified Element/Matrix adapter path and must not replace Matrix, redefine substrate semantics, or move workspace/grounding/PEM/completion authority into the interface.

## 2026-05-26

### D-001: Phase 1 is documentation-first and implementation-light

The repository begins with explicit architecture and contract documents before behavior implementation to avoid accidental scope expansion and hidden assumptions.

### D-002: Repository structure is boundary-oriented

Top-level directories are organized by operational boundary (`matrix/`, `models/`, `tools/`, `pem/`, `workspaces/`, `gateway/`, `docs/`) rather than by speculative framework layers.

### D-003: Workspace truth is manifest-bounded

CCE should rely on explicit workspace manifests rather than ambient repository access or hidden state.

### D-004: Completion semantics must be verifiable

The system should distinguish verified completion from partial, blocked, deferred, or unverifiable outcomes.

### D-005: Hermes is a lesson source, not a foundation

Prototype lessons may inform future work, but Phase 1 does not inherit Hermes architecture by default.

### D-006: PEM is governance, not hidden memory

PEM is positioned as an epistemic governance and continuity layer with explicit boundaries.

### D-007: `cases/`, `scratch/`, and `pem.initialized` are first-class state surfaces

Observed repository artifacts are adopted into the explicit Phase 1 model: `cases/` for PEM-backed continuity records, `scratch/` for non-authoritative temporary work, and `pem.initialized` as an initialization state marker.

## Phase 2

### D-008: Phase 2 uses direct Matrix Client-Server API calls via Python standard library

The smallest implementation approach is a plain Python runtime using `urllib` against Matrix Client-Server endpoints. This avoids dependency sprawl and keeps the communication loop inspectable.

### D-009: The gateway supports one explicit command

Phase 2 supports only `status`. Unknown commands receive a short safe response and are not interpreted.

### D-010: Status claims must be tied to observed runtime state

The status reply may report connected state only after a successful sync, and disabled or not-configured state where runtime features are intentionally absent.

### D-011: Matrix sync cursor persistence is explicit operational state, not hidden memory

Phase 2.1 persists the Matrix `next_batch` cursor in a gitignored, human-inspectable JSON file under `runtime/`. This is operational continuity for the transport layer only (restart behavior), not PEM continuity and not a hidden memory system.

## Phase 3

### D-012: Workspace truth containers precede model cognition

Phase 3 introduces a deterministic workspace runtime with explicit manifests and explicit source boundaries before any model/runtime cognition is added.

### D-013: Workspace manifest v1 uses TOML for stdlib parsing

Although YAML is preferred in principle, Phase 3 uses `workspace.toml` so the runtime can parse manifests with Python standard library support (`tomllib`) and avoid introducing parser dependencies.

### D-014: Declared sources only

The workspace runtime lists and reads declared sources only. Undeclared paths are rejected, path traversal is rejected, and unsupported file types are rejected explicitly.

### D-015: Active workspace selection persistence is explicit operational state

Phase 3.1 persists `active_workspace_id` in `runtime/workspace-state.json` (gitignored, human-inspectable JSON). This is restart convenience for the workspace boundary only; it is not PEM continuity and not a hidden memory system.

## Phase 4

### D-016: Grounded question answering uses full declared-source context (no retrieval)

Phase 4 assembles model context deterministically from existing declared readable sources in the active workspace. It does not use embeddings, indexing, chunk stores, or semantic retrieval.

### D-017: Local model invocation via a narrow provider boundary

Phase 4 introduces a minimal local model boundary with explicit configuration, byte limits, and timeouts. The provider is invoked via subprocess without shell interpolation.

### D-018: Natural question routing is gated by an active workspace

Phase 4.1 routes ordinary non-command text through the grounded QA path only when an active workspace is open. Command-like operational inputs remain non-model and return safe help.

### D-019: Matrix auth failures halt the runtime safely

Phase 4.2 makes Matrix auth failures explicit (e.g. `401 M_UNKNOWN_TOKEN`) and causes the gateway runtime to halt rather than continue in a degraded/pretend-healthy state.

## Phase 5

### D-027: Declared PDF sources are supported via text extraction only

Phase 5.1 expands declared readable source types to include .pdf while preserving manifest-bounded provenance and path restrictions. PDF support is limited to deterministic text extraction (no OCR, rendering, images, tables, indexing, or retrieval).

### D-028: Matrix access token provenance must be explicit (investigation)

Recurring 401 M_UNKNOWN_TOKEN failures indicate the configured token is not active. Phase 5.1 pauses live testing until token stability is improved. Root-cause notes and smallest-fix options are recorded in docs/matrix-token-root-cause.md.

### D-029: Add optional password_login Matrix auth mode

To improve Matrix auth reliability, CCE supports an optional password-based login mode that performs /login at startup and keeps access tokens in memory. Static access_token mode remains supported as fallback.
