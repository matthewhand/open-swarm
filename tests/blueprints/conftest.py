"""Isolate LiteLLM/OpenAI env overrides so unit tests use their own config."""
import os
import pytest

_LITELLM_VARS = (
    "LITELLM_BASE_URL", "LITELLM_API_KEY", "LITELLM_MODEL",
    "OPENAI_BASE_URL", "OPENAI_API_KEY", "DEFAULT_LLM",
)

@pytest.fixture(autouse=True)
def clear_litellm_env(monkeypatch):
    for var in _LITELLM_VARS:
        monkeypatch.delenv(var, raising=False)
