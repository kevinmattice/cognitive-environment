# Matrix Token Root Cause (M_UNKNOWN_TOKEN)

## Scope

This document covers recurring `401 M_UNKNOWN_TOKEN` failures in the CCE gateway Matrix runtime.

## Problem statement

CCE historically relied on a manually copied `access_token` in `config/cce.json`.

That token repeatedly becomes inactive, causing `401 M_UNKNOWN_TOKEN` and halting the gateway.

## What `M_UNKNOWN_TOKEN` means in practice

- The homeserver is reachable.
- The configured token is **not active** (revoked, expired, rotated, or otherwise invalid).
- CCE has no way to recover unless it owns an auth lifecycle.

## Likely causes

Ordered by likelihood for an Element-sourced token:

1. Token is tied to a specific interactive session/device and is revoked when that session/device is logged out or reset.
2. Token was copied from a different account/device/session than intended.
3. Homeserver policy rotates/invalidates access tokens.

## Smallest reliable fix

Make CCE own its bot session lifecycle:

- Prefer `password_login` auth mode.
- On startup, CCE performs `/login` and stores `access_token` in memory.
- If the homeserver provides `refresh_token` + `expires_in_ms`, CCE can refresh via `/refresh`.

`static_token` remains supported as a fallback, but it is inherently less reliable unless the server guarantees long-lived tokens.

## Non-goals

- No secret manager integration
- No encryption support
- No OCR or unrelated features
