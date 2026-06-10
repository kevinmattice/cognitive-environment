import unittest
from pathlib import Path
from unittest import mock

from gateway.pem_status import PemStatusSnapshot
from gateway.runtime import process_event
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.runtime import WorkspaceRuntime


class _UnusedModel(LocalModel):
    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(ok=True, text="should not be called")


class PemRoutingTests(unittest.TestCase):
    def test_pem_unavailable_blocks_pem_required_work(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with (
            mock.patch("gateway.runtime.answer_question", side_effect=AssertionError("answer_question should not be called")),
            mock.patch(
                "gateway.runtime.get_pem_status",
                return_value=PemStatusSnapshot(
                    state="unavailable",
                    reachable=False,
                    active=False,
                    message="down",
                    diagnostics={},
                ),
            ) as mocked_status,
        ):
            reply, state = process_event(
                {"pem_enabled": True},
                last_sync_at="now",
                cursor_state="ok",
                workspace=workspace,
                workspace_persistence_state="absent",
                on_workspace_opened=None,
                ask_cfg=mock.Mock(),
                model=model,
                body="Fix this bug.",
            )

        self.assertIn("requires PEM-governed execution", reply or "")
        self.assertIn("not available right now", reply or "")
        self.assertEqual(state, "absent")
        mocked_status.assert_called_once()

    def test_pem_inactive_returns_activation_needed_message(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with (
            mock.patch("gateway.runtime.answer_question", side_effect=AssertionError("answer_question should not be called")),
            mock.patch(
                "gateway.runtime.get_pem_status",
                return_value=PemStatusSnapshot(
                    state="inactive",
                    reachable=True,
                    active=False,
                    message="inactive",
                    diagnostics={},
                ),
            ) as mocked_status,
        ):
            reply, state = process_event(
                {"pem_enabled": True},
                last_sync_at="now",
                cursor_state="ok",
                workspace=workspace,
                workspace_persistence_state="absent",
                on_workspace_opened=None,
                ask_cfg=mock.Mock(),
                model=model,
                body="Fix this bug.",
            )

        self.assertIn("reachable but inactive", reply or "")
        self.assertEqual(state, "absent")
        mocked_status.assert_called_once()

    def test_pem_active_transitions_to_governed_execution_response(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with (
            mock.patch("gateway.runtime.answer_question", side_effect=AssertionError("answer_question should not be called")),
            mock.patch(
                "gateway.runtime.get_pem_status",
                return_value=PemStatusSnapshot(
                    state="active",
                    reachable=True,
                    active=True,
                    message="active",
                    diagnostics={},
                ),
            ) as mocked_status,
        ):
            reply, state = process_event(
                {"pem_enabled": True},
                last_sync_at="now",
                cursor_state="ok",
                workspace=workspace,
                workspace_persistence_state="absent",
                on_workspace_opened=None,
                ask_cfg=mock.Mock(),
                model=model,
                body="Fix this bug.",
            )

        self.assertIn("pem_governed_execution", reply or "")
        self.assertEqual(state, "absent")
        mocked_status.assert_called_once()

    def test_malformed_pem_payload_is_treated_as_ambiguous(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with (
            mock.patch("gateway.runtime.answer_question", side_effect=AssertionError("answer_question should not be called")),
            mock.patch(
                "gateway.runtime.get_pem_status",
                return_value=PemStatusSnapshot(
                    state="ambiguous",
                    reachable=True,
                    active=False,
                    message="bad payload",
                    diagnostics={},
                ),
            ) as mocked_status,
        ):
            reply, state = process_event(
                {"pem_enabled": True},
                last_sync_at="now",
                cursor_state="ok",
                workspace=workspace,
                workspace_persistence_state="absent",
                on_workspace_opened=None,
                ask_cfg=mock.Mock(),
                model=model,
                body="Fix this bug.",
            )

        self.assertIn("requires PEM-governed execution", reply or "")
        self.assertIn("not available right now", reply or "")
        self.assertEqual(state, "absent")
        mocked_status.assert_called_once()

    def test_ordinary_conversation_still_calls_normal_answer_path(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with (
            mock.patch("gateway.runtime.answer_question", return_value="ordinary reply") as mocked,
            mock.patch("gateway.runtime.get_pem_status", side_effect=AssertionError("PEM status should not be called")),
        ):
            reply, _ = process_event(
                {},
                last_sync_at="now",
                cursor_state="ok",
                workspace=workspace,
                workspace_persistence_state="absent",
                on_workspace_opened=None,
                ask_cfg=mock.Mock(),
                model=model,
                body="What is the capital of France?",
            )

        self.assertEqual(reply, "ordinary reply")
        mocked.assert_called_once()

    def test_read_only_project_request_still_calls_normal_answer_path(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with (
            mock.patch("gateway.runtime.answer_question", return_value="grounded reply") as mocked,
            mock.patch("gateway.runtime.get_pem_status", side_effect=AssertionError("PEM status should not be called")),
        ):
            reply, _ = process_event(
                {},
                last_sync_at="now",
                cursor_state="ok",
                workspace=workspace,
                workspace_persistence_state="absent",
                on_workspace_opened=None,
                ask_cfg=mock.Mock(),
                model=model,
                body="Can you explain what is in this workspace?",
            )

        self.assertEqual(reply, "grounded reply")
        mocked.assert_called_once()
