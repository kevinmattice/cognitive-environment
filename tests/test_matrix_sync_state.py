import json
import tempfile
import unittest
from pathlib import Path

from gateway.matrix_sync_state import load_cursor, save_cursor


class MatrixSyncStateTests(unittest.TestCase):
    def test_missing_state_file_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            result = load_cursor(path)
            self.assertEqual(result.status, "absent")
            self.assertIsNone(result.cursor)

    def test_invalid_json_is_unavailable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{not valid json", encoding="utf-8")
            result = load_cursor(path)
            self.assertEqual(result.status, "unavailable/error")
            self.assertIsNone(result.cursor)
            self.assertIsNotNone(result.error)

    def test_missing_next_batch_is_unavailable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps({"updated_at": "2026-01-01T00:00:00+00:00"}), encoding="utf-8")
            result = load_cursor(path)
            self.assertEqual(result.status, "unavailable/error")
            self.assertIsNone(result.cursor)

    def test_save_then_load_cursor_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            saved = save_cursor(path, "s12345")
            self.assertEqual(saved.status, "updated")

            loaded = load_cursor(path)
            self.assertEqual(loaded.status, "loaded")
            self.assertEqual(loaded.cursor, "s12345")
