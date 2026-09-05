"""REQ-42 definition briefs + default-LLM summarise (no secrets in prompts)."""

import re
from unittest.mock import MagicMock

from swarm.core.definition_explain import (
    REQ42_INJECTED_FIXTURE,
    build_definition,
    build_summarize_prompt,
    default_llm_status,
    static_explanation,
    summarise_definition,
    summarize_with_default_llm,
)


def test_static_briefs_cover_roles_without_llm():
    assert "YES/NO" in static_explanation("role", "gate")
    assert "submit_gate_verdict" in static_explanation("role", "gate")
    assert "retry" in static_explanation("role", "skeptic")
    assert "submit_skeptic_verdict" in static_explanation("role", "skeptic")
    assert "Socratic" in static_explanation("role", "support")
    assert "talks to any team" in static_explanation("role", "cos")
    assert "roster" in static_explanation("team", "default")


def test_prompt_includes_injected_fixture_and_no_secrets():
    payload = build_definition(
        "role",
        "gate",
        extra=REQ42_INJECTED_FIXTURE,
    )
    prompt = build_summarize_prompt(
        payload["kind"],
        payload["id"],
        payload["explanation"],
        payload["source"],
        payload["injected"],
    )
    assert REQ42_INJECTED_FIXTURE in prompt
    assert "YES/NO" in prompt
    assert "api_key" not in prompt.lower()
    # Gate source mentions "ask-user-on-dangerous" (contains the letters sk-).
    # Reject key-shaped tokens, not that English phrase.
    assert re.search(r"sk-[a-zA-Z0-9]{8,}", prompt) is None
    assert "sk-proj-" not in prompt.lower()
    assert "sk-test" not in prompt.lower()


def test_default_llm_status_from_env(monkeypatch):
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DEFAULT_LLM", raising=False)
    status = default_llm_status()
    assert status["configured"] is False

    monkeypatch.setenv("DEFAULT_LLM", "stub-llm")
    status = default_llm_status()
    assert status["configured"] is True
    assert status["model"] == "stub-llm"


def test_summarise_uses_stub_default_llm_and_keeps_injected(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "stub-llm")

    def fake_llm(prompt: str):
        return True, "stub-llm", f"Summary mentions {REQ42_INJECTED_FIXTURE}"

    monkeypatch.setattr(
        "swarm.core.definition_explain.summarize_with_default_llm",
        fake_llm,
    )
    result = summarise_definition("role", "skeptic", extra=REQ42_INJECTED_FIXTURE)
    assert result["configured"] is True
    assert REQ42_INJECTED_FIXTURE in result["summary"]
    assert result["injected_extra"] == REQ42_INJECTED_FIXTURE


def test_summarize_with_default_llm_short_circuits_when_missing(monkeypatch):
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DEFAULT_LLM", raising=False)
    configured, model, text = summarize_with_default_llm("unused")
    assert configured is False
    assert model is None
    assert text is None


def test_summarize_with_default_llm_calls_existing_openai_client(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "stub-llm")
    fake_message = MagicMock()
    fake_message.content = f"ok {REQ42_INJECTED_FIXTURE}"
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock(choices=[fake_choice])
    fake_openai = MagicMock(return_value=fake_client)
    monkeypatch.setattr("openai.OpenAI", fake_openai)
    monkeypatch.setattr(
        "swarm.utils.env_utils.openai_client_kwargs",
        lambda: {},
    )
    configured, model, text = summarize_with_default_llm(f"prompt {REQ42_INJECTED_FIXTURE}")
    assert configured is True
    assert model == "stub-llm"
    assert REQ42_INJECTED_FIXTURE in (text or "")
    sent = fake_client.chat.completions.create.call_args.kwargs
    assert sent["model"] == "stub-llm"
    assert "sk-" not in str(sent["messages"])


def test_summarize_with_default_llm_swallows_provider_errors(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "stub-llm")
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = RuntimeError("rate limited")
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=fake_client))
    monkeypatch.setattr("swarm.utils.env_utils.openai_client_kwargs", lambda: {})
    configured, model, text = summarize_with_default_llm("placeholder source")
    assert configured is True
    assert model == "stub-llm"
    assert text is None
