from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gateway.pem_status import PemProbeError, call_pem_tool, pem_client_config_from_runtime


@dataclass(frozen=True)
class PemHandoffResult:
    ok: bool
    reply: str | None
    error: str | None = None


def handoff_to_pem(config: dict | None, *, question: str) -> PemHandoffResult:
    client_cfg = pem_client_config_from_runtime(config)
    try:
        payload = call_pem_tool(
            client_cfg,
            tool_name="pem_ask",
            arguments={
                "question": question,
                "new_case": False,
                "include_full_history": False,
            },
        )
    except PemProbeError as exc:
        return PemHandoffResult(ok=False, reply=None, error=str(exc))

    return _map_pem_ask_payload(payload)


def _map_pem_ask_payload(payload: dict[str, Any]) -> PemHandoffResult:
    if payload.get("ok") is False:
        return PemHandoffResult(ok=False, reply=None, error=_error_message_from_payload(payload))

    result = payload.get("result")
    if not isinstance(result, dict):
        return PemHandoffResult(ok=False, reply=None, error="PEM handoff returned malformed result.")

    answer = result.get("answer")
    breadcrumb = result.get("breadcrumb")
    if not isinstance(answer, str) or not answer.strip():
        return PemHandoffResult(ok=False, reply=None, error="PEM handoff returned no answer text.")
    if not isinstance(breadcrumb, dict):
        return PemHandoffResult(ok=False, reply=None, error="PEM handoff returned no breadcrumb metadata.")

    case_id = breadcrumb.get("case_id")
    projection_hash = breadcrumb.get("projection_hash")
    reused_active_case = breadcrumb.get("reused_active_case")
    if not isinstance(case_id, str) or not case_id.strip():
        return PemHandoffResult(ok=False, reply=None, error="PEM handoff returned no case id.")
    if not isinstance(projection_hash, str) or not projection_hash.strip():
        return PemHandoffResult(ok=False, reply=None, error="PEM handoff returned no projection hash.")
    if not isinstance(reused_active_case, bool):
        return PemHandoffResult(ok=False, reply=None, error="PEM handoff returned no reused-case flag.")

    lines = [
        answer.strip(),
        "",
        f"PEM case: {case_id}",
        f"Projection: {projection_hash}",
        f"Reused case: {'yes' if reused_active_case else 'no'}",
    ]
    return PemHandoffResult(ok=True, reply="\n".join(lines))


def _error_message_from_payload(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        code = error.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    return "PEM returned an error."
