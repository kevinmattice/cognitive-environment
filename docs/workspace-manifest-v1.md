# Workspace Manifest v1

## Purpose

The workspace manifest is the durable, bounded declaration of what is in scope for a unit of work. It exists so the system does not rely on ambient filesystem knowledge or hidden state.

## Goals

- Bound truth to explicit files and documents
- Make access surfaces inspectable
- Support reproducible context assembly
- Provide a versioned contract for future implementation

## Conceptual fields

### Identity

- `manifest_version`
- `workspace_id`
- `title`
- `created_at`
- `updated_at`

### Scope

- `allowed_paths`: explicit repository or document paths in scope
- `documents`: named source documents available for reading
- `artifacts`: outputs that may be created or updated

### Operational policy

- `allowed_tools`: named deterministic tools available in this workspace
- `model_profile`: local model boundary/profile allowed for this workspace
- `shell_access`: expected to be `none` in Phase 1 unless explicitly justified later

### Governance

- `pem_context_id`
- `verification_requirements`
- `completion_rules`

## Phase 1 stance

This document defines the concept and contract only. Phase 1 does not require a manifest parser or runtime implementation.

## Example shape

```yaml
manifest_version: 1
workspace_id: matrix-private-channel
title: Private Matrix channel foundation
allowed_paths:
  - docs/
documents:
  - docs/architecture.md
  - docs/gateway-contract.md
allowed_tools:
  - read_document
  - write_document
model_profile: local-text-reasoning
shell_access: none
verification_requirements:
  - file_written
  - file_re_read
completion_rules:
  - no_unverified_claims
```

## Open implementation question

Whether manifests should eventually be stored as YAML, TOML, or JSON is intentionally deferred. The important Phase 1 requirement is the explicit bounded contract.
