# Gateway Contract

## Role

The gateway is the narrow orchestration layer between Matrix, local model invocation, workspace manifests, deterministic tools, and PEM.

## Responsibilities

1. Accept bounded incoming requests from the communication layer
2. Resolve or establish the explicit state surface for the request
3. Load the relevant workspace manifest or fail clearly if none applies
4. Invoke only allowed deterministic tools
5. Invoke local models only through the defined model boundary
6. Coordinate PEM continuity/governance hooks
7. Return responses with explicit completion semantics

## Non-responsibilities

- Not a hidden memory system
- Not a broad shell proxy
- Not a workflow automation engine
- Not a general planner with background autonomy

## Required properties

### Inspectable inputs

The gateway must be able to show what message arrived, what manifest was used, what documents were read, what tools were invoked, and what outputs were observed.

### Bounded authority

The gateway can only act through named allowed tools and declared workspace scope. Ambient repository authority is not acceptable.

### Explicit failure modes

If a manifest is missing, a tool is disallowed, a model call fails, or verification is incomplete, the gateway must surface that state explicitly.

## Completion semantics

Every gateway response should carry one of these statuses conceptually:

- `verified_complete`
- `partially_complete`
- `blocked`
- `deferred`
- `unverifiable`

Phase 1 documents the semantic contract; implementation is deferred.
