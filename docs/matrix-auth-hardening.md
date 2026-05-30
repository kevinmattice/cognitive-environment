# Matrix Auth Hardening (Phase 4.2)

## Purpose

Phase 4.2 makes Matrix authentication failures explicit, diagnosable, and safe.

This phase does not implement encryption support, password managers, secret manager integration, or any non-Matrix credential scope expansion.

## Auth Modes

CCE supports two Matrix auth modes (configured in `config/cce.json`):

- `static_token` (legacy): a manually copied `access_token` stored in config.
- `password_login` (preferred for reliability): CCE performs an explicit `/login` at startup and holds the resulting `access_token` in memory.

If `password_login` is used and the homeserver provides refresh fields, CCE can refresh an expired token via `/refresh`.

## Key Failure Modes

CCE distinguishes:

- `401 M_UNKNOWN_TOKEN`: token rejected / not active
- `403`: forbidden (room access, policy, or account permissions)
- network/connectivity failures (DNS, socket, TLS, etc.)
- homeserver/API errors
- malformed/invalid config
- `user_id` mismatch between config and `whoami` (can cause own-message loop)

## Safe Diagnostics

Run:

```bash
.venv/bin/python -m gateway.runtime --config config/cce.json --check-connection
```

Expected signals:

- homeserver reachable: yes/no
- auth mode
- login accepted: yes/no (password_login only)
- device_id (if available)
- refresh support yes/no
- whoami user_id
- config user_id match enforced (fails if mismatch)
- room access (joined_rooms): yes/no
- sync ok: yes/no

No secrets are printed.

## Runtime Auth Failure Handling

If auth fails during the sync loop:

- the runtime logs a clear error
- the runtime halts (exits non-zero)
- it does not spin aggressively
- it does not send false success replies

## Token Provenance (recommended)

Even in `password_login` mode, keep non-secret provenance metadata locally so a human can audit how auth was established:

- `token_source_note` (how it was obtained; which client)
- `token_obtained_at` (ISO timestamp)
- `device_id` (if known)

Never commit real credentials.

## Token Refresh Runbook (static_token mode)

1. Obtain a new access token for the bot account from Element.
2. Update `config/cce.json:access_token` locally using a text editor (do not paste into chat).
3. Ensure `config/cce.json:user_id` matches `whoami` for that token.
4. Re-run `--check-connection`.
5. Restart the gateway runtime.

## What Not To Paste Into Chat

- access tokens
- passwords
- refresh tokens
- recovery keys / secure backup keys
- any exported E2EE keys
