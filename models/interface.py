from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRequest:
    system_prompt: str
    user_prompt: str
    timeout_s: int


@dataclass(frozen=True)
class ModelResponse:
    ok: bool
    text: str
    error: str | None = None


class LocalModel:
    def generate(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
        raise NotImplementedError

