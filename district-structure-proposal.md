---
type: Note
status: Proposal
related_to:
  - "[[CCE]]"
  - "[[Atlas]]"
  - "[[PEM]]"
  - "[[Matrix]]"
  - "[[Tolaria]]"
  - "[[Codex]]"
---
# District Structure Proposal

This note proposes a minimal three-district layer under [[CCE]] to reduce graph flatness without changing any existing entity types or moving any notes.

## Proposed districts

### Atlas Layer

Entities:

- [[Atlas]]
- [[Cognitive Registry]]
- [[Corpus]]
- [[Provenance]]
- [[Memory]]

Why this district exists:\
It groups the knowledge-bearing artifacts and capabilities that define, store, trace, and recall atlas content.

### Interaction Layer

Entities:

- [[Tolaria]]
- [[Codex]]
- [[ChatGPT]]
- [[GitHub]]

Why this district exists:\
It groups the interfaces through which people and agents inspect, edit, discuss, or distribute the atlas and related environment content.

### Runtime Layer

Entities:

- [[PEM]]
- [[Matrix]]
- [[Colossus]]
- [[Element]]
- [[Browser Agents]]

Why this district exists:\
It groups the systems, substrate, and runtime-oriented capability that make the broader environment operate beyond the atlas as a knowledge object.

## Cross-district fits

- [[Memory]] could also fit in the runtime-oriented cluster if it is primarily implemented as an operational system capability rather than a knowledge-layer function.
- [[Provenance]] could also fit closer to the interaction layer if attribution is mainly surfaced through tools rather than maintained in the knowledge layer.
- [[GitHub]] could also fit closer to runtime support if its main role is repository substrate rather than user-facing interaction.
- [[Browser Agents]] could also fit in the interaction layer if its main role is acting through interfaces rather than enabling runtime behavior.
- [[Element]] remains the most ambiguous member because its distinction from [[Matrix]] and [[Colossus]] is not yet sharp.

## Special case

[[Kevin]] is best kept directly under [[CCE]] in this proposal because the note reads more clearly as steward of the whole environment than as a member of one district.

## Rationale

This is the smallest proposed intermediate structure because it introduces only three districts while giving the atlas a clear split between knowledge, interfaces, and runtime.
