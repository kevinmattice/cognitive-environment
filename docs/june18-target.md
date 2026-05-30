# June 18, 2026 Target

## Target statement

By Thursday, June 18, 2026, CCE should be ready to enter a narrow implementation phase for a private Matrix/Element-to-Colossus channel without requiring architectural reinterpretation.

## What "ready" means

Ready does not mean feature-rich. It means the repository has explicit contracts and a structure that supports a small, reliable implementation pass.

## Minimum readiness criteria

1. Phase 1 scope is written and narrow
2. Non-goals are explicit
3. Gateway, manifest, and PEM roles are documented
4. Completion semantics are defined in a verifiable way
5. State surfaces are explicit rather than ambient
6. The repository structure matches the written architecture

## Evaluation questions

- Can a reviewer identify the intended message path without guessing?
- Can a reviewer tell what the model is allowed to see and do?
- Can a reviewer tell how workspace truth is bounded?
- Can a reviewer tell what is recorded by PEM?
- Can a reviewer tell why a response is considered complete or incomplete?
- Can a reviewer tell which tempting capabilities are intentionally excluded?

## Risks to the target

- Scope drift into autonomous behavior
- Coupling implementation details before contracts are stable
- Introducing broad access surfaces for convenience
- Treating prototype lessons from Hermes as reusable foundation without re-justification

## Recommendation

Treat the June 18 target as a readiness checkpoint, not as pressure to ship extra behavior.
