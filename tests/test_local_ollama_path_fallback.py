import unittest
from unittest import mock

from models.interface import ModelRequest
from models.local_ollama import OllamaModel


class LocalOllamaPathFallbackTests(unittest.TestCase):
    def test_returns_clear_error_when_ollama_missing(self) -> None:
        with mock.patch("models.local_ollama._resolve_ollama_bin", return_value=None):
            model = OllamaModel(model_name="whatever")
            resp = model.generate(ModelRequest(system_prompt="sys", user_prompt="user", timeout_s=1))
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error, "ollama not found on PATH")

    def test_uses_resolved_ollama_path(self) -> None:
        with mock.patch("models.local_ollama._resolve_ollama_bin", return_value="/opt/homebrew/bin/ollama"):
            with mock.patch("subprocess.run") as run_mock:
                run_mock.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
                model = OllamaModel(model_name="m")
                resp = model.generate(ModelRequest(system_prompt="sys", user_prompt="user", timeout_s=1))

        self.assertTrue(resp.ok)
        self.assertEqual(resp.text, "ok")
        argv = run_mock.call_args.args[0]
        self.assertEqual(argv[0], "/opt/homebrew/bin/ollama")
        self.assertEqual(argv[1:4], ["run", "--hidethinking", "m"])
