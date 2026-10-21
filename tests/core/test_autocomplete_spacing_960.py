"""Inline continuations preserve word boundaries and release their SDK client."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from swarm.core.llm_autocomplete import generate_autocomplete
from swarm.core.model_text import sanitize_model_text


@pytest.fixture
def autocomplete_client(monkeypatch):
    import openai
    from swarm.core import llm_task_routing

    monkeypatch.setenv("SWARM_LLM_ASSIST", "1")
    monkeypatch.setattr(llm_task_routing, "load_swarm_config", lambda: {"test_config": True})
    monkeypatch.setattr(llm_task_routing, "resolve_autocomplete_model", lambda config: SimpleNamespace(profile="autocomplete"))
    monkeypatch.setattr(llm_task_routing, "get_profile_dict", lambda *args: {"api_key": "test-only", "base_url": "http://127.0.0.1:1"})
    monkeypatch.setattr(llm_task_routing, "model_id_for_profile", lambda *args: "test-model")
    client = Mock()
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: client)
    return client


@pytest.mark.parametrize("content,expected", [
    (" world", " world"),
    ("\n    next_line()\n", "\n    next_line()\n"),
    ("Hello world", " world"),
    ("<unused50> world\x1b[0m", " world"),
])
def test_completion_preserves_spacing_and_closes_client(autocomplete_client, content, expected):
    autocomplete_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )
    completion, duration = generate_autocomplete("Hello")
    assert completion == expected
    assert duration >= 0
    autocomplete_client.close.assert_called_once_with()


def test_completion_failure_closes_client(autocomplete_client):
    autocomplete_client.chat.completions.create.side_effect = RuntimeError("synthetic backend failure")
    assert generate_autocomplete("Hello")[0] == ""
    autocomplete_client.close.assert_called_once_with()


def test_whitespace_preservation_does_not_change_default_transcript_sanitizing():
    raw = "\n    code()<unused50>\n\n\n"
    assert sanitize_model_text(raw) == "code()"
    assert sanitize_model_text(raw, preserve_whitespace=True) == "\n    code()\n\n\n"
