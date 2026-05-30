import json
import tempfile
import unittest
from pathlib import Path

from gateway.workspace_state import load_workspace_state, save_workspace_state


class WorkspaceStateTests(unittest.TestCase):
    def test_missing_state_file_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace-state.json"
            result = load_workspace_state(path)
            self.assertEqual(result.status, "absent")
            self.assertIsNone(result.active_workspace_id)

    def test_invalid_json_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace-state.json"
            path.write_text("{not json", encoding="utf-8")
            result = load_workspace_state(path)
            self.assertEqual(result.status, "invalid")
            self.assertIsNone(result.active_workspace_id)
            self.assertIsNotNone(result.error)

    def test_save_then_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace-state.json"
            saved = save_workspace_state(path, "example-workspace")
            self.assertEqual(saved.status, "updated")

            loaded = load_workspace_state(path)
            self.assertEqual(loaded.status, "loaded")
            self.assertEqual(loaded.active_workspace_id, "example-workspace")

    def test_missing_active_workspace_id_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace-state.json"
            path.write_text(json.dumps({"updated_at": "2026-01-01T00:00:00+00:00"}), encoding="utf-8")
            result = load_workspace_state(path)
            self.assertEqual(result.status, "invalid")
            self.assertIsNone(result.active_workspace_id)

