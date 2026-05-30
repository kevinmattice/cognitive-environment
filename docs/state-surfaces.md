# State Surfaces

## Purpose

CCE should expose its important state surfaces explicitly so operators and reviewers can see where continuity, temporary work, and initialization state actually live.

## Phase 1 state surfaces

### `workspaces/`

Durable bounded truth containers for task or thread scope. This is the authoritative home for future manifest-backed workspace definitions.

### `cases/`

PEM-backed continuity and forensic case records. These artifacts may capture bounded discussion context, breadcrumbs, evidence posture, and decision continuity for reviewable work.

### `scratch/`

Ephemeral, non-authoritative workspace for temporary artifacts. Nothing in `scratch/` should be treated as durable truth unless it is intentionally promoted into a documented workspace or document surface.

### `pem.initialized`

Repository-level marker showing that PEM project initialization has occurred. This is state, but narrow state: it indicates initialization, not correctness, completeness, or approval.

## Design stance

- State surfaces should be visible in the repository
- State surfaces should have clear authority semantics
- Temporary state should not masquerade as durable truth
- Continuity artifacts should be inspectable rather than hidden

## Authority and interpretation

- `workspaces/` is authoritative for bounded work scope once manifests exist
- `cases/` is authoritative for continuity/provenance records within PEM's role
- `scratch/` is explicitly non-authoritative
- `pem.initialized` is authoritative only for initialization state

## Phase 1 implication

Phase 1 does not yet implement the full runtime behavior around these surfaces, but it does recognize them as part of the project foundation and operational contract.
