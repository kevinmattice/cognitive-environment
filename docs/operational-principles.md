# Operational Principles

## Core principle

CCE exists to reduce cognitive friction, not create operational babysitting.

## Principles

1. Prefer boring, inspectable, deterministic mechanisms.
2. Do not assume hidden state.
3. Do not claim completion without observable evidence.
4. Keep interfaces narrow and named.
5. Keep authority surfaces bounded and explicit.
6. Prefer source-grounded reading over inferred knowledge.
7. Keep operational recovery simple enough to inspect manually.
8. Use PEM to govern continuity, not to obscure it.

## Constraints carried into design

- No broad filesystem access
- No uncontrolled shell access
- No Docker expansion
- No embeddings or vector database
- No autonomous workflows
- No unverifiable completion claims

## Phase 1 interpretation

In Phase 1, architecture quality is measured less by flexibility and more by clarity, boundedness, and inspectability.
