from __future__ import annotations

from dataclasses import dataclass

from models.interface import LocalModel, ModelRequest
from workspace_runtime.errors import WorkspaceError
from workspace_runtime.runtime import SourceInfo, WorkspaceRuntime


@dataclass(frozen=True)
class AskConfig:
    provider: str
    model_name: str
    max_context_bytes: int
    timeout_s: int


@dataclass(frozen=True)
class ContextBuildResult:
    ok: bool
    context_text: str
    sources_used: tuple[str, ...]
    truncated: bool
    error: str | None = None


def _readable_existing_sources(workspace: WorkspaceRuntime) -> list[SourceInfo]:
    sources = workspace.sources()
    readable = [s for s in sources if s.exists and s.supported_type]
    # Deterministic ordering.
    return sorted(readable, key=lambda s: s.source_id)


def build_context(workspace: WorkspaceRuntime, max_context_bytes: int) -> ContextBuildResult:
    if workspace.active_workspace_id is None:
        return ContextBuildResult(
            ok=False,
            context_text="",
            sources_used=tuple(),
            truncated=False,
            error="no active workspace; use: workspace open <id>",
        )

    try:
        readable = _readable_existing_sources(workspace)
    except WorkspaceError as exc:
        return ContextBuildResult(ok=False, context_text="", sources_used=tuple(), truncated=False, error=str(exc))

    if not readable:
        return ContextBuildResult(
            ok=False,
            context_text="",
            sources_used=tuple(),
            truncated=False,
            error="no declared readable sources available (.md/.txt)",
        )

    if not isinstance(max_context_bytes, int) or max_context_bytes <= 0:
        return ContextBuildResult(ok=False, context_text="", sources_used=tuple(), truncated=False, error="invalid max_context_bytes")

    parts: list[str] = []
    used: list[str] = []
    remaining = max_context_bytes
    truncated = False

    for src in readable:
        header = f"=== source: {src.rel_path} (id: {src.source_id}) ===\n"
        header_b = header.encode("utf-8")
        if len(header_b) > remaining:
            truncated = True
            break
        remaining -= len(header_b)

        try:
            text = workspace.read_source(src.source_id)
        except WorkspaceError:
            # Should not happen because exists/supported_type was checked, but keep it safe/deterministic.
            truncated = True
            break

        data_b = text.encode("utf-8")
        if len(data_b) > remaining:
            # Visible truncation: include the header and a partial body.
            partial = data_b[:remaining].decode("utf-8", errors="replace")
            parts.append(header)
            parts.append(partial)
            used.append(src.rel_path)
            truncated = True
            remaining = 0
            break

        parts.append(header)
        parts.append(text)
        used.append(src.rel_path)
        remaining -= len(data_b)

    context = "\n\n".join(parts).strip() + "\n"
    return ContextBuildResult(ok=True, context_text=context, sources_used=tuple(used), truncated=truncated)


def answer_question(
    *,
    question: str,
    workspace: WorkspaceRuntime,
    model: LocalModel,
    cfg: AskConfig,
) -> str:
    question = (question or "").strip()
    if not question:
        return "Usage: ask <question>"

    ctx = build_context(workspace, cfg.max_context_bytes)
    if not ctx.ok:
        return f"Ask error: {ctx.error}"

    system_prompt = (
        "You are a bounded reasoning component for CCE.\n"
        "Answer ONLY using the provided sources. If the answer is not present, say you cannot find it.\n"
        "Do not use external knowledge. Do not browse. Be concise.\n"
        "Always include a Sources section listing the source paths you used."
    )

    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Sources:\n{ctx.context_text}\n"
        "Return format:\n"
        "Answer:\n"
        "<text>\n\n"
        "Sources:\n"
        "- <path>\n"
    )

    resp = model.generate(ModelRequest(system_prompt=system_prompt, user_prompt=user_prompt, timeout_s=cfg.timeout_s))
    if not resp.ok:
        return f"Ask error: model failed: {resp.error}"

    # If we had to truncate context, surface it as operational metadata.
    if ctx.truncated:
        return resp.text.strip() + "\n\n[truncation: context limited]\n"
    return resp.text.strip()

