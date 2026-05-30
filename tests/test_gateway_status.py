import unittest

from gateway.status import build_status_snapshot, handle_command


class GatewayStatusTests(unittest.TestCase):
    def test_status_command_renders_expected_sections(self) -> None:
        snapshot = build_status_snapshot(
            matrix_connection_state="connected (last sync ok at 2026-05-26T17:30:00+00:00)",
            matrix_cursor_state="updated",
            active_workspace_state="not configured",
            workspace_persistence_state="absent",
        )

        response = handle_command("status", snapshot)

        assert response is not None
        self.assertIn("CCE status", response)
        self.assertIn("- gateway state: running (status command active)", response)
        self.assertIn("- Matrix connection state: connected", response)
        self.assertIn("- Matrix cursor state: updated", response)
        self.assertIn("- active workspace state: not configured", response)
        self.assertIn("- workspace persistence state: absent", response)
        self.assertIn("- model state: disabled", response)
        self.assertIn("- PEM state: disabled", response)
        self.assertIn("- tools state: disabled", response)

    def test_unknown_command_is_safe_and_explicit(self) -> None:
        snapshot = build_status_snapshot(
            matrix_connection_state="not connected",
            matrix_cursor_state="absent",
            active_workspace_state="not configured",
            workspace_persistence_state="absent",
        )

        response = handle_command("please think harder", snapshot)

        self.assertEqual(
            response,
            "Unknown command. Supported commands: status, workspace list, workspace open <id>, workspace status, sources, read <source>, ask <question>",
        )

    def test_blank_command_is_ignored(self) -> None:
        snapshot = build_status_snapshot(
            matrix_connection_state="not connected",
            matrix_cursor_state="absent",
            active_workspace_state="not configured",
            workspace_persistence_state="absent",
        )

        self.assertIsNone(handle_command("   ", snapshot))
