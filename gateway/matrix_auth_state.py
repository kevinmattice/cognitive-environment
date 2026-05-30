from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class AuthStateLoadResult:
    status: str
    refresh_token: str | None
    device_id: str | None
    user_id: str | None
    expires_in_ms: int | None
    updated_at: str | None
    error: str | None = None


@dataclass(frozen=True)
class AuthStateSaveResult:
    status: str
    error: str | None = None


def load_auth_state(state_path: Path) -> AuthStateLoadResult:
    if not state_path.exists():
        return AuthStateLoadResult(
            status="absent",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
        )

    try:
        raw = state_path.read_text(encoding="utf-8")
    except OSError as exc:
        return AuthStateLoadResult(
            status="unavailable/error",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error=str(exc),
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return AuthStateLoadResult(
            status="invalid",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error=f"invalid JSON: {exc}",
        )

    if not isinstance(parsed, dict):
        return AuthStateLoadResult(
            status="invalid",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error="state JSON was not an object",
        )

    refresh_token = parsed.get("refresh_token")
    if refresh_token is not None and (not isinstance(refresh_token, str) or not refresh_token):
        return AuthStateLoadResult(
            status="invalid",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error="invalid refresh_token",
        )

    device_id = parsed.get("device_id")
    if device_id is not None and (not isinstance(device_id, str) or not device_id.strip()):
        return AuthStateLoadResult(
            status="invalid",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error="invalid device_id",
        )

    user_id = parsed.get("user_id")
    if user_id is not None and (not isinstance(user_id, str) or not user_id.strip()):
        return AuthStateLoadResult(
            status="invalid",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error="invalid user_id",
        )

    expires_in_ms = parsed.get("expires_in_ms")
    if expires_in_ms is not None and (not isinstance(expires_in_ms, int) or expires_in_ms <= 0):
        return AuthStateLoadResult(
            status="invalid",
            refresh_token=None,
            device_id=None,
            user_id=None,
            expires_in_ms=None,
            updated_at=None,
            error="invalid expires_in_ms",
        )

    updated_at = parsed.get("updated_at")
    if updated_at is not None and (not isinstance(updated_at, str) or not updated_at.strip()):
        updated_at = None

    return AuthStateLoadResult(
        status="loaded",
        refresh_token=refresh_token,
        device_id=device_id.strip() if isinstance(device_id, str) else None,
        user_id=user_id.strip() if isinstance(user_id, str) else None,
        expires_in_ms=expires_in_ms,
        updated_at=updated_at,
    )


def save_auth_state(
    state_path: Path,
    *,
    refresh_token: str | None,
    user_id: str | None,
    device_id: str | None,
    expires_in_ms: int | None,
) -> AuthStateSaveResult:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return AuthStateSaveResult(status="unavailable/error", error=str(exc))

    payload: dict[str, object] = {
        "updated_at": utc_now(),
    }
    if user_id:
        payload["user_id"] = user_id
    if device_id:
        payload["device_id"] = device_id
    if expires_in_ms:
        payload["expires_in_ms"] = expires_in_ms
    if refresh_token:
        payload["refresh_token"] = refresh_token

    try:
        state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return AuthStateSaveResult(status="unavailable/error", error=str(exc))

    return AuthStateSaveResult(status="updated")
