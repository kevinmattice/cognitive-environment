from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class CursorLoadResult:
    status: str
    cursor: str | None
    error: str | None = None


@dataclass(frozen=True)
class CursorSaveResult:
    status: str
    error: str | None = None


def load_cursor(state_path: Path) -> CursorLoadResult:
    if not state_path.exists():
        return CursorLoadResult(status="absent", cursor=None)

    try:
        raw = state_path.read_text(encoding="utf-8")
    except OSError as exc:
        return CursorLoadResult(status="unavailable/error", cursor=None, error=str(exc))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return CursorLoadResult(status="unavailable/error", cursor=None, error=f"invalid JSON: {exc}")

    if not isinstance(parsed, dict):
        return CursorLoadResult(status="unavailable/error", cursor=None, error="state JSON was not an object")

    cursor = parsed.get("next_batch")
    if cursor is None:
        return CursorLoadResult(status="unavailable/error", cursor=None, error="missing next_batch")
    if not isinstance(cursor, str) or not cursor:
        return CursorLoadResult(status="unavailable/error", cursor=None, error="invalid next_batch")

    return CursorLoadResult(status="loaded", cursor=cursor)


def save_cursor(state_path: Path, cursor: str) -> CursorSaveResult:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return CursorSaveResult(status="unavailable/error", error=str(exc))

    payload = {
        "next_batch": cursor,
        "updated_at": utc_now(),
    }
    try:
        state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return CursorSaveResult(status="unavailable/error", error=str(exc))

    return CursorSaveResult(status="updated")
