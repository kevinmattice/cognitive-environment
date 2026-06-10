from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PemStatusSnapshot:
    state: str  # active | inactive | unavailable | ambiguous
    reachable: bool
    active: bool
    message: str
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class PemClientConfig:
    enabled: bool
    launcher_path: str | None
    project_root: str | None
    config_path: str | None
    timeout_s: int


class PemProbeError(RuntimeError):
    pass


def pem_client_config_from_runtime(config: dict | None) -> PemClientConfig:
    data = config or {}
    timeout_value = data.get("pem_timeout_s", 10)
    try:
        timeout_s = int(timeout_value)
    except (TypeError, ValueError):
        timeout_s = 10
    if timeout_s <= 0:
        timeout_s = 10
    return PemClientConfig(
        enabled=bool(data.get("pem_enabled", False)),
        launcher_path=_normalized_optional_str(data.get("pem_launcher_path")),
        project_root=_normalized_optional_str(data.get("pem_project_root")),
        config_path=_normalized_optional_str(data.get("pem_config_path")),
        timeout_s=timeout_s,
    )


def get_pem_status(config: dict | None = None) -> PemStatusSnapshot:
    client_cfg = pem_client_config_from_runtime(config)
    if not client_cfg.enabled:
        return PemStatusSnapshot(
            state="unavailable",
            reachable=False,
            active=False,
            message="PEM status is disabled in CCE config.",
            diagnostics={"reason": "pem_disabled"},
        )

    config_error = _validate_client_config(client_cfg)
    if config_error is not None:
        return PemStatusSnapshot(
            state="unavailable",
            reachable=False,
            active=False,
            message=config_error,
            diagnostics={"reason": "invalid_client_config"},
        )

    try:
        activation_payload, meta_payload = _query_pem_status(client_cfg)
    except PemProbeError as exc:
        return PemStatusSnapshot(
            state="unavailable",
            reachable=False,
            active=False,
            message=str(exc),
            diagnostics={"reason": "probe_failed"},
        )

    return _map_pem_status_payloads(activation_payload, meta_payload)


def _normalized_optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _validate_client_config(cfg: PemClientConfig) -> str | None:
    if not cfg.launcher_path:
        return "PEM launcher path is not configured."
    if not cfg.project_root:
        return "PEM project root is not configured."

    launcher = Path(cfg.launcher_path)
    if not launcher.is_file():
        return f"PEM launcher path not found: {launcher}"
    if not os.access(launcher, os.X_OK):
        return f"PEM launcher path is not executable: {launcher}"
    helper_python = launcher.parent / ".venv" / "bin" / "python"
    if not helper_python.is_file():
        return f"PEM helper python not found: {helper_python}"
    if not os.access(helper_python, os.X_OK):
        return f"PEM helper python is not executable: {helper_python}"

    project_root = Path(cfg.project_root)
    if not project_root.is_dir():
        return f"PEM project root not found: {project_root}"

    if cfg.config_path:
        config_path = Path(cfg.config_path)
        if not config_path.is_file():
            return f"PEM config path not found: {config_path}"

    return None


def _query_pem_status(cfg: PemClientConfig) -> tuple[dict[str, Any], dict[str, Any] | None]:
    env = os.environ.copy()
    env["PEM_PROJECT_ROOT"] = str(Path(cfg.project_root or "").resolve())
    if cfg.config_path:
        env["PEM_CONFIG_PATH"] = str(Path(cfg.config_path).resolve())
    launcher_path = Path(cfg.launcher_path or "").resolve()
    helper_python = launcher_path.parent / ".venv" / "bin" / "python"
    project_root = str(Path(cfg.project_root or "").resolve())
    try:
        result = subprocess.run(
            [
                str(helper_python),
                "-c",
                _PEM_MCP_HELPER_SCRIPT,
                str(launcher_path),
                project_root,
                str(cfg.timeout_s),
            ],
            text=True,
            capture_output=True,
            env=env,
            timeout=cfg.timeout_s + 5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PemProbeError("Timed out waiting for PEM status response.") from exc
    except OSError as exc:
        raise PemProbeError(f"Failed to launch PEM status helper: {exc}") from exc

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise PemProbeError(err or "PEM status helper failed.")

    stdout = (result.stdout or "").strip()
    if not stdout:
        raise PemProbeError("PEM status helper returned no output.")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PemProbeError(f"PEM status helper returned malformed JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PemProbeError("PEM status helper returned non-object JSON.")
    activation = payload.get("activation")
    meta = payload.get("meta")
    if not isinstance(activation, dict):
        raise PemProbeError("PEM status helper returned no activation payload.")
    return activation, meta if isinstance(meta, dict) else None


def _map_pem_status_payloads(
    activation_payload: dict[str, Any],
    meta_payload: dict[str, Any] | None,
) -> PemStatusSnapshot:
    activation_result = activation_payload.get("result")
    if not isinstance(activation_result, dict):
        return PemStatusSnapshot(
            state="ambiguous",
            reachable=True,
            active=False,
            message="PEM activation status response was missing result.",
            diagnostics={"activation_payload": activation_payload, "meta_payload": meta_payload},
        )

    activation = activation_result.get("activation")
    if not isinstance(activation, dict):
        return PemStatusSnapshot(
            state="ambiguous",
            reachable=True,
            active=False,
            message="PEM activation status response was missing activation fields.",
            diagnostics={"activation_payload": activation_payload, "meta_payload": meta_payload},
        )

    active = activation.get("active")
    activation_state = activation.get("activation_state")
    if not isinstance(active, bool) or activation_state not in {"active", "inactive"}:
        return PemStatusSnapshot(
            state="ambiguous",
            reachable=True,
            active=False,
            message="PEM activation status response was malformed.",
            diagnostics={"activation_payload": activation_payload, "meta_payload": meta_payload},
        )

    if active and activation_state != "active":
        return PemStatusSnapshot(
            state="ambiguous",
            reachable=True,
            active=False,
            message="PEM activation status response was contradictory.",
            diagnostics={"activation_payload": activation_payload, "meta_payload": meta_payload},
        )

    diagnostics = {
        "activation": activation,
        "meta": meta_payload.get("result") if isinstance(meta_payload, dict) else None,
    }
    if active:
        return PemStatusSnapshot(
            state="active",
            reachable=True,
            active=True,
            message="PEM is reachable and active.",
            diagnostics=diagnostics,
        )

    inactive_reason = activation.get("inactive_reason")
    failure_reason = activation.get("failure_reason")
    if failure_reason in {"runtime_config_error", "restart_required", "bootstrap_unverified"}:
        return PemStatusSnapshot(
            state="unavailable",
            reachable=True,
            active=False,
            message=f"PEM is reachable but not activation-ready ({failure_reason}).",
            diagnostics=diagnostics,
        )

    reason = inactive_reason if isinstance(inactive_reason, str) and inactive_reason else "inactive"
    return PemStatusSnapshot(
        state="inactive",
        reachable=True,
        active=False,
        message=f"PEM is reachable but inactive ({reason}).",
        diagnostics=diagnostics,
    )


_PEM_MCP_HELPER_SCRIPT = r"""
import asyncio
import json
import os
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def _main() -> None:
    launcher_path = sys.argv[1]
    project_root = sys.argv[2]
    timeout_s = int(sys.argv[3])
    env = os.environ.copy()
    params = StdioServerParameters(
        command=launcher_path,
        args=[],
        env=env,
        cwd=project_root,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout_s)
            activation = await asyncio.wait_for(session.call_tool("pem_activation_status", {}), timeout=timeout_s)
            try:
                meta = await asyncio.wait_for(session.call_tool("pem_meta_status", {}), timeout=timeout_s)
                meta_payload = meta.structuredContent
            except Exception:
                meta_payload = None
    print(
        json.dumps(
            {
                "activation": activation.structuredContent,
                "meta": meta_payload,
            },
            ensure_ascii=True,
        )
    )


asyncio.run(_main())
"""
