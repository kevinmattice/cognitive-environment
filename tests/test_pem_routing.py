import unittest
from pathlib import Path
from unittest import mock

from gateway.runtime import process_event
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.runtime import WorkspaceRuntime


class _UnusedModel(LocalModel):
    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(ok=True, text="should not be called")


class PemRoutingTests(unittest.TestCase):
    def test_pem_required_request_does_not_call_normal_answer_path(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with mock.patch("gateway.runtime.answer_question", side_effect=AssertionError("answer_question should not be called")):
            reply, state = process_event(
                {},
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
        self.assertEqual(state, "absent")

    def test_ordinary_conversation_still_calls_normal_answer_path(self) -> None:
        workspace = WorkspaceRuntime(Path("workspaces"))
        model = _UnusedModel()

        with mock.patch("gateway.runtime.answer_question", return_value="ordinary reply") as mocked:
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

        with mock.patch("gateway.runtime.answer_question", return_value="grounded reply") as mocked:
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
