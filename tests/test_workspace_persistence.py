import json
import tempfile
import unittest
from pathlib import Path

from gateway.runtime import restore_active_workspace
from gateway.status import handle_workspace_command
from gateway.workspace_state import save_workspace_state
from workspace_runtime.runtime import WorkspaceRuntime


class WorkspacePersistenceTests(unittest.TestCase):
    def test_restore_missing_workspace_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            workspaces_dir.mkdir()
            state_path = Path(tmp) / "runtime" / "workspace-state.json"
            state_path.parent.mkdir()
            state_path.write_text(
                json.dumps({"active_workspace_id": "does-not-exist", "updated_at": "2026-01-01T00:00:00+00:00"}),
                encoding="utf-8",
            )

            rt = WorkspaceRuntime(workspaces_dir)
            logs: list[tuple[str, str]] = []
            state = restore_active_workspace(workspace=rt, workspace_state_path=state_path, log_fn=lambda a, b: logs.append((a, b)))

            self.assertEqual(state, "missing_workspace")
            self.assertIsNone(rt.active_workspace_id)

    def test_workspace_open_persists_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            ws_dir = workspaces_dir / "one"
            (ws_dir / "sources").mkdir(parents=True)
            (ws_dir / "workspace.toml").write_text('workspace_id="one"\ntitle="One"\n', encoding="utf-8")

            rt = WorkspaceRuntime(workspaces_dir)
            state_path = Path(tmp) / "runtime" / "workspace-state.json"

            def on_open(wid: str) -> str:
                saved = save_workspace_state(state_path, wid)
                return saved.status

            reply, new_state = handle_workspace_command(
                "workspace open one",
                workspace=rt,
                workspace_persistence_state="absent",
                on_workspace_opened=on_open,
            )

            self.assertEqual(reply, "Workspace open: one; status: open (one); persistence: updated")
            self.assertEqual(new_state, "updated")
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved.get("active_workspace_id"), "one")
