import unittest
from unittest import mock

from gateway.ask import AskConfig, answer_question
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.runtime import WorkspaceRuntime


class _EchoModel(LocalModel):
    def __init__(self) -> None:
        self.last_request: ModelRequest | None = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        return ModelResponse(ok=True, text="Answer:\nX")


class GroundedSourceNarrowingTests(unittest.TestCase):
    def test_question_with_rel_path_narrows_context(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            mock.Mock(source_id="a", rel_path="sources/a.md", display_name="Source A", exists=True, supported_type=True),
            mock.Mock(source_id="b", rel_path="sources/b.md", display_name="Source B", exists=True, supported_type=True),
        ]
        fake_ws.read_source.side_effect = lambda sid: {"a": "AAA", "b": "BBB"}[sid]

        model = _EchoModel()
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)

        out = answer_question(question="In sources/b.md what is here?", workspace=fake_ws, model=model, cfg=cfg)
        self.assertIn("- Source B", out)
        self.assertNotIn("- Source A", out)
        self.assertNotIn("Sources:", out)

    def test_question_with_source_id_narrows_context(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            mock.Mock(
                source_id="aa_trip_confirmation",
                rel_path="sources/aa.pdf",
                display_name="AA Trip Confirmation",
                exists=True,
                supported_type=True,
            ),
            mock.Mock(source_id="notes", rel_path="notes.md", display_name="Workspace Notes", exists=True, supported_type=True),
        ]
        fake_ws.read_source.side_effect = lambda sid: {"aa_trip_confirmation": "PDF", "notes": "NOTES"}[sid]

        model = _EchoModel()
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)

        out = answer_question(
            question="Using aa_trip_confirmation only, what is the time?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
        )
        self.assertIn("- AA Trip Confirmation", out)
        self.assertNotIn("- Workspace Notes", out)
        self.assertNotIn("Sources:", out)
