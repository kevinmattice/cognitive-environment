# Runtime

This directory holds local operational state for running CCE.

- `runtime/matrix-sync-state.json`: last known Matrix `next_batch` sync cursor used for restart continuity

This is operational state only. It is not PEM continuity and it is not a hidden memory system.
