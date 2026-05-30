# Config

Create a local runtime config at `config/cce.json` by copying `config/cce.example.json` and filling in real values.

Do not commit real credentials.

CCE supports two Matrix auth modes:

- `static_token`: provide `access_token` manually.
- `password_login`: provide `password` (and optionally `device_id`) so CCE can `/login` at startup.

If Matrix auth begins failing with `401 M_UNKNOWN_TOKEN`, see:

- `docs/matrix-auth-hardening.md`
- `docs/matrix-token-root-cause.md`
