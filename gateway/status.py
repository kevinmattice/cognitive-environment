from __future__ import annotations

from dataclasses import dataclass

from workspace_runtime.errors import WorkspaceError
from workspace_runtime.runtime import WorkspaceRuntime


@dataclass(frozen=True)
class StatusSnapshot:
    gateway_state: str
    matrix_connection_state: str
    matrix_cursor_state: str
    active_workspace_state: str
    workspace_persistence_state: str
    model_state: str
    pem_state: str
    tools_state: str


def build_status_snapshot(
    *,
    matrix_connection_state: str,
    matrix_cursor_state: str,
    active_workspace_state: str,
    workspace_persistence_state: str,
    pem_state: str = "disabled",
) -> StatusSnapshot:
    return StatusSnapshot(
        gateway_state="running (status command active)",
        matrix_connection_state=matrix_connection_state,
        matrix_cursor_state=matrix_cursor_state,
        active_workspace_state=active_workspace_state,
        workspace_persistence_state=workspace_persistence_state,
        model_state="disabled",
        pem_state=pem_state,
        tools_state="disabled",
    )


def render_status(snapshot: StatusSnapshot) -> str:
    return "\n".join(
        [
            "CCE status",
            f"- gateway state: {snapshot.gateway_state}",
            f"- Matrix connection state: {snapshot.matrix_connection_state}",
            f"- Matrix cursor state: {snapshot.matrix_cursor_state}",
            f"- active workspace state: {snapshot.active_workspace_state}",
            f"- workspace persistence state: {snapshot.workspace_persistence_state}",
            f"- model state: {snapshot.model_state}",
            f"- PEM state: {snapshot.pem_state}",
            f"- tools state: {snapshot.tools_state}",
        ]
    )


def handle_command(command: str, snapshot: StatusSnapshot) -> str | None:
    normalized = command.strip().lower()
    if not normalized:
        return None
    if normalized == "status":
        return render_status(snapshot)
    return "Unknown command. Supported commands: status, workspace list, workspace open <id>, workspace status, sources, read <source>, ask <question>"


def handle_workspace_command(
    command: str,
    *,
    workspace: WorkspaceRuntime,
    workspace_persistence_state: str,
    on_workspace_opened: callable | None,
) -> tuple[str | None, str]:
    parts = command.strip().split()
    if not parts:
        return None, workspace_persistence_state
    keyword = parts[0].lower()

    if keyword == "workspace":
        sub = parts[1].lower() if len(parts) >= 2 else ""
        if len(parts) == 2 and sub == "list":
            items = workspace.list_workspaces()
            if not items:
                return "No workspaces found.", workspace_persistence_state
            lines = ["Workspaces:"]
            for ws in items:
                lines.append(f"- {ws.workspace_id}: {ws.title}")
            return "\n".join(lines), workspace_persistence_state

        if len(parts) >= 2 and sub == "open":
            if len(parts) != 3:
                return "Usage: workspace open <id>"
            try:
                manifest = workspace.open(parts[2])
            except WorkspaceError as exc:
                return f"Workspace error: {exc}", workspace_persistence_state

            new_state = workspace_persistence_state
            if on_workspace_opened is not None:
                new_state = on_workspace_opened(manifest.workspace_id)
            return f"Workspace open: {manifest.workspace_id}; status: open ({manifest.workspace_id}); persistence: {new_state}", new_state

        if len(parts) == 2 and sub == "status":
            if workspace.active_workspace_id is None:
                return f"Workspace status: not open; persistence: {workspace_persistence_state}", workspace_persistence_state
            return (
                f"Workspace status: open ({workspace.active_workspace_id}); persistence: {workspace_persistence_state}",
                workspace_persistence_state,
            )

        return "Unknown workspace command. Supported: workspace list, workspace open <id>, workspace status", workspace_persistence_state

    if keyword == "sources" and len(parts) == 1:
        try:
            sources = workspace.sources()
        except WorkspaceError as exc:
            return f"Workspace error: {exc}", workspace_persistence_state
        if not sources:
            return "Sources: none declared", workspace_persistence_state
        lines = ["Sources:"]
        for s in sources:
            flags = []
            if not s.exists:
                flags.append("missing")
            if s.exists and not s.supported_type:
                flags.append("unsupported_type")
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"- {s.source_id}: {s.rel_path}{suffix}")
        return "\n".join(lines), workspace_persistence_state

    if keyword == "read":
        if len(parts) != 2:
            return "Usage: read <source>", workspace_persistence_state
        try:
            content = workspace.read_source(parts[1])
        except WorkspaceError as exc:
            return f"Workspace error: {exc}", workspace_persistence_state
        return content, workspace_persistence_state

    return None, workspace_persistence_state
