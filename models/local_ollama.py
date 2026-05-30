from __future__ import annotations

import subprocess

from models.interface import LocalModel, ModelRequest, ModelResponse


class OllamaModel(LocalModel):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def generate(self, request: ModelRequest) -> ModelResponse:
        # Use stdin to avoid shell interpolation and keep invocation inspectable.
        prompt = f"{request.system_prompt}\n\n{request.user_prompt}\n"
        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=request.timeout_s,
                check=False,
            )
        except FileNotFoundError:
            return ModelResponse(ok=False, text="", error="ollama not found on PATH")
        except subprocess.TimeoutExpired:
            return ModelResponse(ok=False, text="", error="model timeout")

        if result.returncode != 0:
            err = (result.stderr or "").strip()
            return ModelResponse(ok=False, text="", error=err or f"ollama exited {result.returncode}")

        return ModelResponse(ok=True, text=(result.stdout or "").strip())

