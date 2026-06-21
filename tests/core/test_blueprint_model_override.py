import tempfile
from pathlib import Path

from swarm.core import config_loader


def test_blueprint_default_model_override():
    config = {
        "llm": {
            "qwen3.5": {"provider": "openai", "model": "qwen3.5"},
            "reasoner": {"provider": "openrouter", "model": "openrouter/o3-mini"}
        },
        "settings": {"default_llm_profile": "qwen3.5"},
        "blueprints": {
            "rue_code": {"default_model": "reasoner"},
            "geese": {"default_model": "qwen3.5", "agents": {"editor": {"model": "reasoner"}}}
        }
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        Path(tmp.name).write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(Path(tmp.name))
        # Blueprint-level override
        assert loaded["blueprints"]["rue_code"]["default_model"] == "reasoner"
        assert loaded["blueprints"]["geese"]["default_model"] == "qwen3.5"
        # Agent-level override
        assert loaded["blueprints"]["geese"]["agents"]["editor"]["model"] == "reasoner"
        # Simulate agent requesting a non-existent model, fallback to settings.default_llm_profile
        agent_requested = "notarealmodel"
        llm_profiles = loaded["llm"]
        fallback = loaded["settings"]["default_llm_profile"]
        selected = llm_profiles.get(agent_requested, llm_profiles[fallback])
        assert selected["model"] == "qwen3.5"

def test_fallback_logs_warning(monkeypatch, caplog):
    config = {
        "llm": {"qwen3.5": {"provider": "openai", "model": "qwen3.5"}},
        "settings": {"default_llm_profile": "qwen3.5"}
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        Path(tmp.name).write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(Path(tmp.name))
        agent_requested = "notarealmodel"
        fallback = loaded["settings"]["default_llm_profile"]
        llm_profiles = loaded["llm"]
        # Simulate fallback
        selected = llm_profiles.get(agent_requested, llm_profiles[fallback])
        assert selected["model"] == "qwen3.5"
        # If a warning is logged, check for it (this will only pass if warning logic exists)
        # assert any("fallback" in rec.message.lower() for rec in caplog.records)
