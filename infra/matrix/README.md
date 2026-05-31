# Private Matrix (Synapse + Postgres) for CCE

This directory contains **templates and operator runbooks** for a minimal private Synapse homeserver used only as CCE transport.

Do not start containers as part of the docs/scaffolding phase.

## Principles

- Tailnet-only access (Tailscale)
- No federation (disabled)
- No bridges, Element Web, TURN, SSO, MAS
- Registration off after bootstrap
- Only 2 users + 1 private room
- No secrets committed

## Choose/Verify Hostname First

Pick and verify the actual client-reachable HTTPS hostname (Tailscale Serve):

- `<TAILNET_HS_HOST>`: the hostname clients will use (Element + CCE)

Pick a Matrix `server_name`:

- `<SERVER_NAME>`: used in MXIDs and room IDs

Often you set `<SERVER_NAME>` = `<TAILNET_HS_HOST>`, but only after confirming that hostname is the stable one you want.

## Files

- `compose.yaml.template`: Synapse + Postgres compose template (copy to `compose.yaml` locally)
- `env/.env.example`: environment placeholders (copy to `env/.env` locally; gitignored)
- `state/`: runtime state (created by operator later; gitignored)

## Operator Steps (Later)

1. Copy templates
   - Copy `env/.env.example` -> `env/.env` and fill credentials locally
   - Copy `compose.yaml.template` -> `compose.yaml` and set placeholder values

2. Create state directories
   - `state/synapse/`
   - `state/postgres/`

3. Generate Synapse config into `state/synapse/`
   - Use Synapse’s built-in config generation with `<SERVER_NAME>`
   - Set `public_baseurl: https://<TAILNET_HS_HOST>/`
   - Configure Postgres in `homeserver.yaml`
   - Disable federation

4. Bring up containers (Synapse + Postgres)

5. Create accounts
   - Kevin user
   - CCE bot user
   - Disable registration afterward

6. Create private room in Element and invite bot

7. Enable tailnet HTTPS with Tailscale Serve
   - Serve `http://127.0.0.1:8008` as `https://<TAILNET_HS_HOST>`

8. Point CCE at the new homeserver and verify
   - `.venv/bin/python -m gateway.runtime --config config/cce.json --check-connection`
   - Start the gateway and test `status` from Element

See `docs/private-matrix-homeserver.md` for the full runbook and checklist.
