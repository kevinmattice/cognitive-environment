# Private Matrix Homeserver (Synapse) for CCE Transport

## Purpose

Matrix.org auth (MAS/OIDC) has proven unsuitable for a boring, stable bot credential flow (`m.login.password`) needed for CCE gateway reliability.

This document defines a **minimal private Matrix homeserver** plan for CCE transport on Colossus.

CCE behavior does not change (workspace/model/PDF/PEM rules stay the same). This is transport infrastructure only.

## Scope (Hard Limits)

This homeserver exists only to support:

- 1 human user account (Kevin)
- 1 bot account (CCE gateway)
- 1 private room for CCE transport
- password login (`m.login.password`)

Explicit non-goals:

- federation (disabled)
- bridges
- Element Web hosting
- TURN
- SSO
- MAS
- public registration after initial account creation
- monitoring/HA/backups (deferred)

## “Choose Hostname First” Rule

Before generating Synapse config, decide and verify the client-reachable HTTPS hostname:

- Choose a tailnet HTTPS hostname served by Tailscale Serve, referenced here as `<TAILNET_HS_HOST>`.
- The Synapse config must then set `public_baseurl` consistently to `https://<TAILNET_HS_HOST>/`.

Separately, choose the Matrix `server_name`, referenced as `<SERVER_NAME>`. Often, for simplicity, set:

- `<SERVER_NAME>` = `<TAILNET_HS_HOST>`

but do not assume this without verifying it is the intended stable hostname.

Clients must consistently use:

- Element homeserver URL: `https://<TAILNET_HS_HOST>`
- CCE `homeserver_url`: `https://<TAILNET_HS_HOST>`

## State Locations (Local, Obvious, Gitignored)

Planned locations under `infra/matrix/`:

- Synapse config + keys + media store: `infra/matrix/state/synapse/`
- Postgres data: `infra/matrix/state/postgres/`
- Secrets env file: `infra/matrix/env/.env` (gitignored)

Backups are intentionally deferred in this phase.

## Operator Runbook (Do Not Execute During Docs/Scaffolding Phase)

This section is intentionally explicit. It is a runbook to execute later.

### 1) Prereqs

- Docker installed on Colossus (Docker Desktop or Docker Engine)
- Tailscale installed on Colossus
- Decide `<TAILNET_HS_HOST>` (actual reachable HTTPS hostname) and `<SERVER_NAME>`

### 2) Create local state/env files

- Create `infra/matrix/state/synapse/`
- Create `infra/matrix/state/postgres/`
- Copy `infra/matrix/env/.env.example` -> `infra/matrix/env/.env` and fill passwords locally

### 3) Generate Synapse config (one-time)

Use the Synapse image to generate initial config into `infra/matrix/state/synapse/`:

- Run Synapse config generation with `<SERVER_NAME>` and write output into the synapse state dir.
- Edit the generated `homeserver.yaml`:
  - set `public_baseurl: https://<TAILNET_HS_HOST>/`
  - configure Postgres (disable SQLite)
  - set `federation_enabled: false`
  - ensure only client API listener is needed (HTTP on `8008`)
  - allow registration only for initial bootstrap, then disable it

### 4) Start containers

- Use `infra/matrix/compose.yaml.template` to create a local `infra/matrix/compose.yaml`
- Start services with Docker Compose

### 5) Create accounts (Kevin + bot)

- Use Synapse admin registration tooling from inside the Synapse container.
- After both accounts exist, set `enable_registration: false` in `homeserver.yaml`.

### 6) Create private room + invite bot

- Log into Element as Kevin against `https://<TAILNET_HS_HOST>`.
- Create one private room.
- Invite the bot.
- Ensure the bot joins.

### 7) Expose HTTPS over tailnet (Tailscale Serve)

- Serve Synapse client API (container listens on Colossus localhost `127.0.0.1:8008`) as HTTPS at `https://<TAILNET_HS_HOST>`.
- Confirm the URL is reachable from laptop/phone over the tailnet.

### 8) Update CCE config locally and verify

Update `config/cce.json` (locally only; never commit credentials):

- `matrix_auth_mode: password_login`
- `homeserver_url: https://<TAILNET_HS_HOST>`
- `user_id: @<bot_localpart>:<SERVER_NAME>`
- `password: <bot_password>`
- `room_id: !<room_id>:<SERVER_NAME>`

Then verify:

- `.venv/bin/python -m gateway.runtime --config config/cce.json --check-connection`
- Start the gateway and verify `status` in Element (exactly one reply, no loops/flood)

## “Done” Checklist

- Synapse starts and stays healthy (Synapse + Postgres)
- Element can log in to `https://<TAILNET_HS_HOST>` as Kevin
- Bot can log in via `m.login.password`
- CCE `--check-connection` passes (login accepted, whoami ok, room joined yes, sync ok)
- CCE replies exactly once to `status`
- No matrix.org token is required

## Risks / Caveats

- TLS: Element generally expects HTTPS; plan relies on Tailscale Serve to provide HTTPS.
- Mobile reachability: phone/tablet must reach `https://<TAILNET_HS_HOST>` (typically via Tailscale).
- Backups: not implemented yet; state lives only in local volumes.
- Push notifications: may be limited/absent in the initial setup.
