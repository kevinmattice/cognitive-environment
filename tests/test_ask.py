import unittest
from pathlib import Path

from gateway.ask import AskConfig, answer_question, build_context
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.runtime import WorkspaceRuntime


class FakeModel(LocalModel):
    def __init__(self) -> None:
        self.last_request: ModelRequest | None = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        # Return a minimal response that includes sources section as required.
        return ModelResponse(ok=True, text="Answer:\nOK\n\nSources:\n- notes.md")


class AskTests(unittest.TestCase):
    def test_ask_requires_active_workspace(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        model = FakeModel()
        cfg = AskConfig(provider="ollama", model_name="x", max_context_bytes=1000, timeout_s=1)
        resp = answer_question(question="what is this", workspace=rt, model=model, cfg=cfg)
        self.assertIn("Ask error:", resp)

    def test_build_context_uses_declared_readable_sources_only(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        rt.open("example-workspace")
        ctx = build_context(rt, max_context_bytes=10000)
        self.assertTrue(ctx.ok)
        self.assertIn("sources/sample.md", "\n".join(ctx.sources_used))
        self.assertIn("notes.md", "\n".join(ctx.sources_used))

    def test_context_truncation_is_flagged(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        rt.open("example-workspace")
        ctx = build_context(rt, max_context_bytes=50)
        self.assertTrue(ctx.ok)
        self.assertTrue(ctx.truncated)

    def test_ask_calls_model_with_context(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        rt.open("example-workspace")
        model = FakeModel()
        cfg = AskConfig(provider="ollama", model_name="x", max_context_bytes=10000, timeout_s=1)
        resp = answer_question(question="what is in the workspace", workspace=rt, model=model, cfg=cfg)
        self.assertIn("Answer:", resp)
        self.assertIsNotNone(model.last_request)
        assert model.last_request is not None
        self.assertIn("Sources:", model.last_request.user_prompt)

