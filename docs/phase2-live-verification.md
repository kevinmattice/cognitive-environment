# Phase 2.1 Live Matrix Verification Checklist

This checklist verifies one thing only: a minimal Element -> CCE -> Element Matrix round-trip with explicit operational state.

It does not verify model calls, PEM integration, workspace runtime, document tools, shell execution, or any autonomous behavior.

## Prerequisites

- A Matrix homeserver URL (e.g. `https://matrix.example.com`)
- A Matrix user id for the bot (e.g. `@cce-bot:example.com`)
- A Matrix room id to listen in (e.g. `!abcdef:example.com`)
- An access token for that user

## 1) Create config

1. Copy `config/cce.example.json` to `config/cce.json`
2. Fill in:
   - `homeserver_url`
   - `access_token`
   - `user_id`
   - `room_id`

Notes:
- `config/cce.json` is gitignored.
- Do not commit secrets.

## 2) Verify config parsing (no network)

```bash
python3 -m gateway.runtime --config config/cce.json --check-config
```

Evidence of success:
- Logs show `config load ok`
- Logs show `config ok: homeserver_url, access_token, user_id, room_id present`

## 3) Verify Matrix connectivity (network)

```bash
python3 -m gateway.runtime --config config/cce.json --check-connection
```

Evidence of success:
- Logs show `Matrix sync verified`
- Room state is reported as either `joined in sync response` or `room not present in sync response`

Note:
- If the room is not present, the token/user may not be joined to that room.

## 4) Start the runtime

```bash
python3 -m gateway.runtime --config config/cce.json
```

Evidence of startup behavior:
- If `runtime/matrix-sync-state.json` does not exist:
  - Logs show `sync cursor state absent`
  - Logs show `sync cursor initialized and saved`
- If `runtime/matrix-sync-state.json` exists and is valid:
  - Logs show `sync cursor loaded from state file`
  - Logs show `sync cursor updated after warm sync`

## 5) Send a message from Element

Send:

```
status
```

Expected response (contents vary, shape should match):

- Starts with `CCE status`
- Includes:
  - `gateway state: running (status command active)`
  - `Matrix connection state: connected (...)`
  - `Matrix cursor state: ...` (e.g. `updated`)
  - `active workspace state: not configured`
  - `model state: disabled`
  - `PEM state: disabled`
  - `tools state: disabled`

For an unknown command (e.g. `hello`), expected response:

```
Unknown command. Supported commands: status
```

## 6) Inspect the runtime state file

Check:

- `runtime/matrix-sync-state.json` exists
- It is human-inspectable JSON
- It contains at least:
  - `next_batch`
  - `updated_at`

Example:

```json
{
  "next_batch": "...",
  "updated_at": "..."
}
```

## 7) Restart and verify startup does not replay confusing backlog by default

1. Stop the runtime (`Ctrl+C`)
2. Start it again

Evidence:
- Logs show cursor is loaded from `runtime/matrix-sync-state.json`
- A startup warm sync occurs and cursor is updated
- The runtime does not emit replies unless a new message is received after restart

## What counts as successful Phase 2 verification

- You sent `status` from Element
- CCE replied in the same room with a `CCE status` response
- Logs show:
  - message received
  - reply sent
  - cursor load/save behavior
- `runtime/matrix-sync-state.json` exists and updates over time
