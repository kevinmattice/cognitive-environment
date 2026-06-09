# Conversational Mode

CCE can answer ordinary conversational questions through the local model while still using grounded workspace QA when workspace sources are clearly relevant.

## Routing

- Known commands still run as commands.
- Explicit ask requests preserve grounded QA behavior.
- Ordinary questions route to the model.
- If workspace sources match, CCE uses grounded QA.
- If no relevant workspace source is selected, CCE falls back to a general local-model answer.
- If no workspace is active, ordinary questions still get a general local-model answer.

## Grounded vs general answers

Grounded answers:

- use declared workspace sources
- keep provenance labels visible
- may include a short source-selection footer while tuning

General answers:

- do not claim source grounding
- do not include a fake Sources section
- stay concise and conversational

## Configuration

The runtime supports conversational_fallback_enabled in config/cce.json.

- true (default): natural questions can fall back to general conversation when no relevant workspace source is selected.
- false: preserves the older document-first behavior.
