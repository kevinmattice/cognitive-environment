from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class WorkspaceStateLoadResult:
    status: str
    active_workspace_id: str | None
    error: str | None = None


@dataclass(frozen=True)
class WorkspaceStateSaveResult:
    status: str
    error: str | None = None


def load_workspace_state(state_path: Path) -> WorkspaceStateLoadResult:
    if not state_path.exists():
        return WorkspaceStateLoadResult(status="absent", active_workspace_id=None)

    try:
        raw = state_path.read_text(encoding="utf-8")
    except OSError as exc:
        return WorkspaceStateLoadResult(status="unavailable/error", active_workspace_id=None, error=str(exc))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return WorkspaceStateLoadResult(status="invalid", active_workspace_id=None, error=f"invalid JSON: {exc}")

    if not isinstance(parsed, dict):
        return WorkspaceStateLoadResult(status="invalid", active_workspace_id=None, error="state JSON was not an object")

    wid = parsed.get("active_workspace_id")
    if wid is None:
        return WorkspaceStateLoadResult(status="invalid", active_workspace_id=None, error="missing active_workspace_id")
    if not isinstance(wid, str) or not wid.strip():
        return WorkspaceStateLoadResult(status="invalid", active_workspace_id=None, error="invalid active_workspace_id")

    return WorkspaceStateLoadResult(status="loaded", active_workspace_id=wid.strip())


def save_workspace_state(state_path: Path, active_workspace_id: str) -> WorkspaceStateSaveResult:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return WorkspaceStateSaveResult(status="unavailable/error", error=str(exc))

    payload = {
        "active_workspace_id": active_workspace_id,
        "updated_at": utc_now(),
    }
    try:
        state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return WorkspaceStateSaveResult(status="unavailable/error", error=str(exc))

    return WorkspaceStateSaveResult(status="updated")

