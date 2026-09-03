"""Support welcome / inference status — laconic copy + role sort."""

from swarm.core.support_context import (
    inference_status,
    sort_support_first,
    welcome_markdown,
)


def test_welcome_is_laconic_and_has_required_chips():
    ctx = {
        "agents": [
            {"id": "codey", "name": "Codey", "role": ""},
            {"id": "support", "name": "Support", "role": "support"},
            {"id": "gate", "name": "Gate", "role": "gate"},
        ],
        "inference": {"configured": False, "profiles": []},
        "create": {
            "team": "/teams/launch/",
            "agent": "/agent-creator/",
            "blueprint": "/blueprint-library/",
            "settings": "/settings/",
            "profiles": "/profiles/",
        },
    }
    text = welcome_markdown(ctx)
    assert "**Support**" in text
    assert "**Agents**" in text
    assert "Support · support" in text
    assert "**Inference** off" in text
    assert "[Set inference](/settings/)" in text
    assert "[Quickstart](docs/QUICKSTART.md#4-configure-your-llm-provider)" in text
    assert "[New team](/teams/launch/)" in text
    assert "[Write blueprint](/agent-creator/)" in text
    assert "**Gate** — dangerous tool call? yes/no. Until wired, all approved." in text
    assert "**Skeptic** — prompt done? If not, findings go back to retry." in text
    assert "Welcome —" not in text
    assert "here to help" not in text
    assert "<details>" not in text


def test_welcome_inference_on_is_short():
    text = welcome_markdown(
        {
            "agents": [{"id": "support", "name": "Support", "role": "support"}],
            "inference": {"configured": True, "profiles": ["default"]},
            "create": {
                "team": "/teams/launch/",
                "agent": "/agent-creator/",
                "blueprint": "/blueprint-library/",
                "settings": "/settings/",
                "profiles": "/profiles/",
            },
        }
    )
    assert "**Inference** on · default" in text
    assert "[Set inference]" not in text
    assert "[New team](/teams/launch/)" in text


def test_sort_puts_special_roles_first():
    ordered = sort_support_first(
        [
            {"id": "codey", "role": ""},
            {"id": "skeptic", "role": "skeptic"},
            {"id": "gate", "role": "gate"},
            {"id": "support", "role": "support"},
        ]
    )
    assert [a["id"] for a in ordered] == ["support", "gate", "skeptic", "codey"]


def test_inference_status_unresolved_placeholder_is_off(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    status = inference_status(
        {
            "llm": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "api_key": "${OPENAI_API_KEY}",
                    "base_url": "${OPENAI_BASE_URL}",
                }
            }
        }
    )
    assert status["configured"] is False


def test_inference_status_ready_profile_is_on():
    status = inference_status(
        {
            "llm": {
                "local": {
                    "provider": "openai",
                    "model": "llama",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key": "n/a",
                }
            }
        }
    )
    assert status["configured"] is True
    assert "local" in status["profiles"]
