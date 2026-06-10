from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from gateway.ask import AskConfig, answer_question
from gateway.pem_handoff import handoff_to_pem
from gateway.matrix_auth_state import save_auth_state
from gateway.matrix_sync_state import load_cursor, save_cursor
from gateway.pem_status import get_pem_status
from gateway.policy import (
    POLICY_PEM_REQUIRED,
    pem_activation_needed_message,
    pem_handoff_failed_message,
    pem_unavailable_message,
)
from gateway.routing import SAFE_COMMAND_HELP, decide_route
from gateway.status import build_status_snapshot, handle_command, handle_workspace_command
from gateway.workspace_state import load_workspace_state, save_workspace_state
from matrix.client import MatrixApiError, MatrixClient, MatrixClientError
from models.local_model import build_local_model
from workspace_runtime.errors import WorkspaceError
from workspace_runtime.runtime import WorkspaceRuntime


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log(level: str, message: str) -> None:
    print(f"{utc_now()} [{level}] {message}", flush=True)


@dataclass(frozen=True)
class MatrixAuthInfo:
    mode: str
    device_id: str | None
    refresh_supported: bool


@dataclass
class MatrixAuthSession:
    client: MatrixClient
    info: MatrixAuthInfo
    refresh_token: str | None = None
    expires_in_ms: int | None = None


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    mode = (config.get("matrix_auth_mode") or "static_token").strip()
    if mode not in ("static_token", "password_login"):
        raise ValueError("matrix_auth_mode must be one of: static_token, password_login")

    required_common = ["homeserver_url", "user_id", "room_id"]
    missing_common = [key for key in required_common if not config.get(key)]
    if missing_common:
        raise ValueError(f"missing required config keys: {', '.join(missing_common)}")

    if mode == "static_token":
        if not config.get("access_token"):
            raise ValueError("missing required config key: access_token")
    else:
        if not config.get("password"):
            raise ValueError("missing required config key: password")

    config.setdefault("matrix_auth_mode", mode)
    config.setdefault("sync_timeout_ms", 30000)
    config.setdefault("active_workspace", None)
    config.setdefault("workspaces_dir", "workspaces")
    config.setdefault("model_provider", "ollama")
    config.setdefault("model_name", "llama3.1")
    config.setdefault("model_max_context_bytes", 24000)
    config.setdefault("model_timeout_s", 30)
    config.setdefault("conversational_fallback_enabled", True)
    config.setdefault("pem_enabled", False)
    config.setdefault("pem_launcher_path", None)
    config.setdefault("pem_project_root", None)
    config.setdefault("pem_config_path", None)
    config.setdefault("pem_timeout_s", 10)
    return config


def configured_active_workspace_state(config: dict) -> str:
    workspace = config.get("active_workspace")
    if not workspace:
        return "not configured"
    return f"configured in config ({workspace}), runtime disabled"


def matrix_connection_state(last_sync_at: str | None) -> str:
    if not last_sync_at:
        return "not connected"
    return f"connected (last sync ok at {last_sync_at})"


def process_event(
    config: dict,
    *,
    last_sync_at: str,
    cursor_state: str,
    workspace: WorkspaceRuntime,
    workspace_persistence_state: str,
    on_workspace_opened: callable | None,
    ask_cfg: AskConfig,
    model,
    body: str,
) -> tuple[str | None, str]:
    normalized_body = body.strip().lower()
    pem_state = "disabled"
    if normalized_body == "status":
        pem_state = get_pem_status(config).state
    snapshot = build_status_snapshot(
        matrix_connection_state=matrix_connection_state(last_sync_at),
        matrix_cursor_state=cursor_state,
        active_workspace_state=workspace.status_line(),
        workspace_persistence_state=workspace_persistence_state,
        pem_state=pem_state,
    )
    ws_reply, new_state = handle_workspace_command(
        body.strip(),
        workspace=workspace,
        workspace_persistence_state=workspace_persistence_state,
        on_workspace_opened=on_workspace_opened,
    )
    if ws_reply is not None:
        return ws_reply, new_state

    decision = decide_route(body, has_active_workspace=workspace.active_workspace_id is not None)
    if decision.action == "ignore":
        return None, workspace_persistence_state
    if decision.action == "ask":
        if decision.policy and decision.policy.state == POLICY_PEM_REQUIRED:
            pem_status = get_pem_status(config)
            if pem_status.active:
                handoff = handoff_to_pem(config, question=decision.question or "")
                if handoff.ok:
                    return handoff.reply, workspace_persistence_state
                return pem_handoff_failed_message(), workspace_persistence_state
            if pem_status.state == "inactive":
                return pem_activation_needed_message(), workspace_persistence_state
            if pem_status.state in {"unavailable", "ambiguous"}:
                return pem_unavailable_message(), workspace_persistence_state
        return (
            answer_question(
                question=decision.question or "",
                workspace=workspace,
                model=model,
                cfg=ask_cfg,
                force_grounded=decision.force_grounded,
                conversational_fallback_enabled=bool(config.get("conversational_fallback_enabled", True)),
            ),
            workspace_persistence_state,
        )
    if decision.action == "help":
        if workspace.active_workspace_id is None:
            return f"No active workspace. Use: workspace list; workspace open <id>.\n{SAFE_COMMAND_HELP}", workspace_persistence_state
        return SAFE_COMMAND_HELP, workspace_persistence_state
    return handle_command(body, snapshot), workspace_persistence_state


def check_config(config: dict) -> None:
    log(
        "INFO",
        "config ok: homeserver_url, user_id, room_id present",
    )
    log("INFO", f"matrix_auth_mode: {config.get('matrix_auth_mode')}")
    if config.get("matrix_auth_mode") == "static_token":
        log("INFO", "access_token present: yes")
    else:
        log("INFO", "password present: yes")
    log("INFO", f"active workspace state: {configured_active_workspace_state(config)}")
    log("INFO", f"workspaces_dir: {config.get('workspaces_dir')}")


def check_connection(client: MatrixClient, room_id: str) -> None:
    client.versions()
    log("INFO", "homeserver reachable: yes")

    who = client.whoami()
    who_user = who.get("user_id")
    if not isinstance(who_user, str) or not who_user:
        raise MatrixClientError("whoami response missing user_id")
    log("INFO", f"token accepted: yes; whoami user_id: {who_user}")

    if who_user != client.user_id:
        raise MatrixClientError(f"config user_id mismatch (config={client.user_id}, whoami={who_user})")

    joined = client.joined_rooms()
    has_room = room_id in joined
    log("INFO", f"room access (joined_rooms): {'yes' if has_room else 'no'}")

    next_batch = client.initial_sync_cursor()
    if not next_batch:
        raise MatrixClientError("sync response did not contain next_batch")
    log("INFO", "sync ok: yes")


def restore_active_workspace(*, workspace: WorkspaceRuntime, workspace_state_path: Path, log_fn: callable) -> str:
    ws_loaded = load_workspace_state(workspace_state_path)
    state = ws_loaded.status
    if ws_loaded.status == "loaded" and ws_loaded.active_workspace_id:
        try:
            workspace.open(ws_loaded.active_workspace_id)
            log_fn("INFO", f"active workspace restored: {ws_loaded.active_workspace_id}")
            return "loaded"
        except WorkspaceError as exc:
            log_fn("WARN", f"active workspace restore failed: {exc}")
            return "missing_workspace"
    if ws_loaded.status in ("invalid", "unavailable/error"):
        log_fn("WARN", f"workspace state load issue: {ws_loaded.error}")
    return state


def establish_matrix_auth_session(config: dict, *, auth_state_path: Path) -> MatrixAuthSession:
    mode = config.get("matrix_auth_mode")
    if mode == "static_token":
        client = MatrixClient(
            homeserver_url=config["homeserver_url"],
            access_token=config["access_token"],
            user_id=config["user_id"],
            room_id=config["room_id"],
        )
        log("INFO", "matrix_auth_mode: static_token")
        return MatrixAuthSession(
            client=client,
            info=MatrixAuthInfo(mode="static_token", device_id=None, refresh_supported=False),
        )

    log("INFO", "matrix_auth_mode: password_login")
    requested_device_id = (config.get("device_id") or "").strip() or None
    initial_name = (config.get("initial_device_display_name") or "").strip() or None

    client = MatrixClient(
        homeserver_url=config["homeserver_url"],
        access_token=None,
        user_id=config["user_id"],
        room_id=config["room_id"],
    )

    def _mxid_localpart(mxid_or_user: str) -> str:
        value = mxid_or_user.strip()
        if value.startswith("@") and ":" in value:
            return value[1 : value.index(":")]
        return value

    login_identifier_user = _mxid_localpart(config["user_id"])
    login = client.login_password(
        user_id=login_identifier_user,
        password=config["password"],
        device_id=requested_device_id,
        initial_device_display_name=initial_name,
    )

    token = login.get("access_token")
    login_user = login.get("user_id")
    device_id = login.get("device_id")

    if not isinstance(token, str) or not token:
        raise MatrixClientError("login response missing access_token")
    if not isinstance(login_user, str) or not login_user:
        raise MatrixClientError("login response missing user_id")
    if not isinstance(device_id, str) or not device_id:
        raise MatrixClientError("login response missing device_id")

    if login_user != config["user_id"]:
        raise MatrixClientError(f"login user_id mismatch (config={config['user_id']}, login={login_user})")

    refresh_token = login.get("refresh_token") if isinstance(login.get("refresh_token"), str) else None
    expires_in_ms = login.get("expires_in_ms") if isinstance(login.get("expires_in_ms"), int) else None
    refresh_supported = bool(refresh_token and expires_in_ms)

    client.access_token = token

    log("INFO", "login accepted: yes")
    log("INFO", f"device_id: {device_id}")
    log("INFO", f"refresh support: {'yes' if refresh_supported else 'no'}")

    if refresh_supported:
        saved = save_auth_state(
            auth_state_path,
            refresh_token=refresh_token,
            user_id=login_user,
            device_id=device_id,
            expires_in_ms=expires_in_ms,
        )
        if saved.status == "updated":
            log("INFO", f"auth state persisted: {auth_state_path}")
        else:
            log("WARN", f"auth state persist failed: {saved.error}")

    return MatrixAuthSession(
        client=client,
        info=MatrixAuthInfo(mode="password_login", device_id=device_id, refresh_supported=refresh_supported),
        refresh_token=refresh_token if refresh_supported else None,
        expires_in_ms=expires_in_ms if refresh_supported else None,
    )


def try_refresh_on_unknown_token(session: MatrixAuthSession, *, auth_state_path: Path) -> bool:
    if session.info.mode != "password_login":
        return False
    if not session.info.refresh_supported or not session.refresh_token:
        return False

    log("WARN", "received M_UNKNOWN_TOKEN; attempting refresh")
    try:
        refreshed = session.client.refresh(refresh_token=session.refresh_token)
    except (MatrixClientError, MatrixApiError) as exc:
        log("ERROR", f"refresh failed: {exc}")
        return False

    new_access = refreshed.get("access_token")
    if not isinstance(new_access, str) or not new_access:
        log("ERROR", "refresh response missing access_token")
        return False

    new_refresh = refreshed.get("refresh_token") if isinstance(refreshed.get("refresh_token"), str) else session.refresh_token
    new_expires = refreshed.get("expires_in_ms") if isinstance(refreshed.get("expires_in_ms"), int) else session.expires_in_ms

    session.client.access_token = new_access
    session.refresh_token = new_refresh
    session.expires_in_ms = new_expires

    saved = save_auth_state(
        auth_state_path,
        refresh_token=new_refresh,
        user_id=session.client.user_id,
        device_id=session.info.device_id,
        expires_in_ms=new_expires,
    )
    if saved.status != "updated":
        log("WARN", f"auth state persist failed after refresh: {saved.error}")

    log("INFO", "refresh ok: yes")
    return True



def run_forever(
    config: dict,
    *,
    session: MatrixAuthSession,
    state_path: Path,
    workspace_state_path: Path,
    auth_state_path: Path,
) -> int:
    client = session.client

    workspace = WorkspaceRuntime(Path(config["workspaces_dir"]))
    model = build_local_model(config["model_provider"], config["model_name"])
    ask_cfg = AskConfig(
        provider=config["model_provider"],
        model_name=config["model_name"],
        max_context_bytes=int(config["model_max_context_bytes"]),
        timeout_s=int(config["model_timeout_s"]),
    )

    workspace_persistence_state = restore_active_workspace(
        workspace=workspace,
        workspace_state_path=workspace_state_path,
        log_fn=log,
    )

    def on_workspace_opened(workspace_id: str) -> str:
        saved = save_workspace_state(workspace_state_path, workspace_id)
        if saved.status == "updated":
            log("INFO", f"active workspace persisted: {workspace_state_path}")
            return "updated"
        log("WARN", f"active workspace persist failed: {saved.error}")
        return "unavailable/error"

    cursor_state = "absent"
    loaded = load_cursor(state_path)
    if loaded.status == "loaded" and loaded.cursor:
        cursor_state = "loaded"
        since = loaded.cursor
        log("INFO", f"sync cursor loaded from state file: {state_path}")
        warm = client.sync(since=since, timeout_ms=0)
        since = warm["next_batch"]
        last_sync_at = utc_now()
        saved = save_cursor(state_path, since)
        if saved.status == "updated":
            cursor_state = "updated"
            log("INFO", f"sync cursor updated after warm sync: {state_path}")
        else:
            cursor_state = "unavailable/error"
            log("ERROR", f"sync cursor save failed after warm sync: {saved.error}")
        log("INFO", "startup warm sync ok; entering listener loop")
    elif loaded.status == "absent":
        log("INFO", f"sync cursor state absent: {state_path}")
        since = client.initial_sync_cursor()
        last_sync_at = utc_now()
        cursor_state = "initialized"
        saved = save_cursor(state_path, since)
        if saved.status == "updated":
            log("INFO", f"sync cursor initialized and saved: {state_path}")
        else:
            cursor_state = "unavailable/error"
            log("ERROR", f"sync cursor init save failed: {saved.error}")
        log("INFO", "initial sync ok; entering listener loop")
    else:
        cursor_state = loaded.status
        log("ERROR", f"sync cursor load failed: {loaded.error}")
        since = client.initial_sync_cursor()
        last_sync_at = utc_now()
        cursor_state = "initialized"
        saved = save_cursor(state_path, since)
        if saved.status == "updated":
            log("INFO", f"sync cursor initialized and saved after load failure: {state_path}")
        else:
            cursor_state = "unavailable/error"
            log("ERROR", f"sync cursor init save failed after load failure: {saved.error}")
        log("INFO", "initial sync ok after load failure; entering listener loop")

    while True:
        try:
            sync_response = client.sync(since=since, timeout_ms=config["sync_timeout_ms"])
        except MatrixApiError as exc:
            if exc.http_status == 401 and exc.errcode == "M_UNKNOWN_TOKEN":
                if try_refresh_on_unknown_token(session, auth_state_path=auth_state_path):
                    try:
                        sync_response = client.sync(since=since, timeout_ms=config["sync_timeout_ms"])
                    except (MatrixApiError, MatrixClientError) as retry_exc:
                        log("ERROR", f"Matrix sync failed after refresh. Halting runtime. ({retry_exc})")
                        return 1
                else:
                    log("ERROR", "Matrix auth failed (M_UNKNOWN_TOKEN). Halting runtime.")
                    return 1
            elif exc.http_status == 403:
                log("ERROR", "Matrix forbidden (403). Halting runtime.")
                return 1
            else:
                log("ERROR", f"Matrix API error. Halting runtime. ({exc})")
                return 1
        except MatrixClientError as exc:
            log("ERROR", f"Matrix sync failed. Halting runtime. ({exc})")
            return 1

        since = sync_response["next_batch"]
        last_sync_at = utc_now()
        saved = save_cursor(state_path, since)
        if saved.status == "updated":
            cursor_state = "updated"
        else:
            cursor_state = "unavailable/error"
            log("ERROR", f"sync cursor save failed: {saved.error}")

        for event in client.text_events(sync_response):
            if event.get("sender") == config["user_id"]:
                log("INFO", f"ignored own message event {event.get('event_id', '<unknown>')}")
                continue

            body = event.get("content", {}).get("body", "")
            event_id = event.get("event_id", "<unknown>")
            log("INFO", f"received event {event_id}: {body!r}")

            reply_text, workspace_persistence_state = process_event(
                config,
                last_sync_at=last_sync_at,
                cursor_state=cursor_state,
                workspace=workspace,
                workspace_persistence_state=workspace_persistence_state,
                on_workspace_opened=on_workspace_opened,
                ask_cfg=ask_cfg,
                model=model,
                body=body,
            )
            if reply_text is None:
                log("INFO", f"ignored empty command from event {event_id}")
                continue

            if reply_text.startswith("Unknown command."):
                log("INFO", f"unknown command from event {event_id}")

            sent_event_id = client.send_text(reply_text)
            log("INFO", f"sent reply for {event_id} as {sent_event_id}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CCE Phase 2 Matrix runtime")
    parser.add_argument(
        "--config",
        default="config/cce.json",
        help="Path to runtime config JSON",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate config and exit without network calls",
    )
    parser.add_argument(
        "--check-connection",
        action="store_true",
        help="Verify Matrix connectivity with an initial sync and exit",
    )
    parser.add_argument(
        "--state-path",
        default="runtime/matrix-sync-state.json",
        help="Path to Matrix sync cursor operational state JSON",
    )
    parser.add_argument(
        "--workspace-state-path",
        default="runtime/workspace-state.json",
        help="Path to active workspace operational state JSON",
    )
    parser.add_argument(
        "--auth-state-path",
        default="runtime/matrix-auth-state.json",
        help="Path to Matrix auth operational state JSON (refresh token metadata)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        log("INFO", f"loading config: {args.config}")
        config = load_config(Path(args.config))
        log("INFO", "config load ok")
        if args.check_config:
            check_config(config)
            return 0

        try:
            session = establish_matrix_auth_session(config, auth_state_path=Path(args.auth_state_path))
        except MatrixApiError as exc:
            if exc.http_status == 429 and exc.errcode == "M_LIMIT_EXCEEDED":
                if isinstance(getattr(exc, "retry_after_ms", None), int) and exc.retry_after_ms is not None:
                    seconds = max(1, int((exc.retry_after_ms + 999) / 1000))
                    log("ERROR", f"rate limited by homeserver during login (M_LIMIT_EXCEEDED). wait ~{seconds}s then retry.")
                else:
                    log("ERROR", "rate limited by homeserver during login (M_LIMIT_EXCEEDED). wait then retry.")
                return 1
            raise


        if args.check_connection:
            log("INFO", f"matrix_auth_mode: {config.get('matrix_auth_mode')}")
            if session.info.mode == "password_login":
                log("INFO", f"device_id: {session.info.device_id}")
                log("INFO", f"refresh support: {'yes' if session.info.refresh_supported else 'no'}")

            try:
                check_connection(session.client, config["room_id"])
                return 0
            except MatrixApiError as exc:
                if exc.http_status == 401 and exc.errcode == "M_UNKNOWN_TOKEN":
                    log("ERROR", "token rejected: M_UNKNOWN_TOKEN (401)")
                    return 1
                if exc.http_status == 403:
                    log("ERROR", "forbidden: 403")
                    return 1
                log("ERROR", f"Matrix API error during check-connection: {exc}")
                return 1
            except MatrixClientError as exc:
                log("ERROR", f"check-connection failed: {exc}")
                return 1

        try:
            return run_forever(
                config,
                session=session,
                state_path=Path(args.state_path),
                workspace_state_path=Path(args.workspace_state_path),
                auth_state_path=Path(args.auth_state_path),
            )
        except MatrixApiError as exc:
            if exc.http_status == 429 and exc.errcode == "M_LIMIT_EXCEEDED":
                if isinstance(getattr(exc, "retry_after_ms", None), int) and exc.retry_after_ms is not None:
                    seconds = max(1, int((exc.retry_after_ms + 999) / 1000))
                    log("ERROR", f"rate limited by homeserver (M_LIMIT_EXCEEDED). wait ~{seconds}s then retry.")
                else:
                    log("ERROR", "rate limited by homeserver (M_LIMIT_EXCEEDED). wait then retry.")
                return 1
            raise
    except (FileNotFoundError, ValueError, json.JSONDecodeError, MatrixClientError) as exc:
        log("ERROR", str(exc))
        return 1
    except KeyboardInterrupt:
        log("INFO", "shutting down on interrupt")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
