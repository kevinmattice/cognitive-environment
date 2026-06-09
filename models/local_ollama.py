from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from models.interface import LocalModel, ModelRequest, ModelResponse


def _resolve_ollama_bin() -> str | None:
    resolved = shutil.which("ollama")
    if resolved:
        return resolved

    # Fallbacks for common macOS/Homebrew installs where PATH may be sanitized for
    # non-interactive processes.
    candidates = (
        Path("/opt/homebrew/bin/ollama"),
        Path("/usr/local/bin/ollama"),
    )
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.stat().st_mode & 0o111:
                return str(candidate)
        except OSError:
            continue

    return None


class OllamaModel(LocalModel):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def generate(self, request: ModelRequest) -> ModelResponse:
        # Use stdin to avoid shell interpolation and keep invocation inspectable.
        prompt = f"{request.system_prompt}\n\n{request.user_prompt}\n"
        bin_path = _resolve_ollama_bin()
        if not bin_path:
            return ModelResponse(ok=False, text="", error="ollama not found on PATH")

        try:
            result = subprocess.run(
                [bin_path, "run", "--hidethinking", self.model_name],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=request.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ModelResponse(ok=False, text="", error="model timeout")
        except FileNotFoundError:
            # In case the binary disappears between resolution and execution.
            return ModelResponse(ok=False, text="", error="ollama not found on PATH")

        if result.returncode != 0:
            err = (result.stderr or "").strip()
            return ModelResponse(ok=False, text="", error=err or f"ollama exited {result.returncode}")

        return ModelResponse(ok=True, text=(result.stdout or "").strip())
