from __future__ import annotations

from models.interface import LocalModel
from models.local_ollama import OllamaModel


def build_local_model(provider: str, model_name: str) -> LocalModel:
    provider = (provider or "").strip().lower()
    if provider in ("ollama", ""):
        return OllamaModel(model_name=model_name)
    raise ValueError(f"unsupported model provider: {provider}")
