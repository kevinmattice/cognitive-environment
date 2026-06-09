import unittest
from unittest import mock

from gateway.ask import AskConfig, answer_question
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.runtime import WorkspaceRuntime


class _FakeModel(LocalModel):
    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(ok=True, text=self._text)


class GroundedSourcesEnforcedTests(unittest.TestCase):
    def test_sources_section_overwritten_with_actual_paths(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            mock.Mock(
                source_id="a",
                rel_path="sources/a.md",
                display_name="Source A",
                exists=True,
                supported_type=True,
            ),
        ]
        fake_ws.read_source.return_value = "hello"

        model = _FakeModel("Answer:\nX\n\nSources:\n- None")
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)

        out = answer_question(question="q", workspace=fake_ws, model=model, cfg=cfg)
        self.assertIn("- Source A", out)
        self.assertNotIn("- None", out)
        self.assertNotIn("Sources:", out)
