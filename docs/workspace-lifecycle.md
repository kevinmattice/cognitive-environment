# Workspace Lifecycle (Phase 3)

## Lifecycle States

Phase 3 defines a minimal lifecycle:

1. **Discovered**
   - A directory exists under the workspaces directory and contains `workspace.toml`.
2. **Open**
   - The gateway runtime has selected a workspace by `workspace_id`.
3. **Source-Enumerated**
   - Declared sources have been listed, including missing/unsupported flags.
4. **Source-Read**
   - A declared `.md` or `.txt` source has been read successfully under policy constraints.

## Explicit Boundaries

- Workspaces are bounded by their directory + manifest.
- Sources are bounded by explicit declaration; nothing is loaded implicitly.
- The gateway must not silently discover or ingest undeclared files.

## Persistence

Phase 3.1 persists the active workspace selection across manual gateway restarts via explicit operational state.

The active workspace id is stored in `runtime/workspace-state.json` as human-inspectable JSON. This is operational state only, not PEM continuity and not hidden memory.
