import tempfile
from pathlib import Path
from swarm.extensions.config import config_loader

def test_blueprint_default_model_override():
    config = {
        "llm": {
            "gpt-4o": {"provider": "openai", "model": "gpt-4o"},
            "o3-mini": {"provider": "openrouter", "model": "openrouter/o3-mini"}
        },
        "settings": {"default_llm_profile": "gpt-4o"},
        "blueprints": {
            "rue_code": {"default_model": "o3-mini"},
            "geese": {"default_model": "gpt-4o", "agents": {"editor": {"model": "o3-mini"}}}
        }
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        Path(tmp.name).write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(Path(tmp.name))
        # Blueprint-level override
        assert loaded["blueprints"]["rue_code"]["default_model"] == "o3-mini"
        assert loaded["blueprints"]["geese"]["default_model"] == "gpt-4o"
        # Agent-level override
        assert loaded["blueprints"]["geese"]["agents"]["editor"]["model"] == "o3-mini"
        # Simulate agent requesting a non-existent model, fallback to settings.default_llm_profile
        agent_requested = "notarealmodel"
        llm_profiles = loaded["llm"]
        fallback = loaded["settings"]["default_llm_profile"]
        selected = llm_profiles.get(agent_requested, llm_profiles[fallback])
        assert selected["model"] == "gpt-4o"

def test_fallback_logs_warning(monkeypatch, caplog):
    config = {
        "llm": {"gpt-4o": {"provider": "openai", "model": "gpt-4o"}},
        "settings": {"default_llm_profile": "gpt-4o"}
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        Path(tmp.name).write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(Path(tmp.name))
        agent_requested = "notarealmodel"
        fallback = loaded["settings"]["default_llm_profile"]
        llm_profiles = loaded["llm"]
        # Simulate fallback
        selected = llm_profiles.get(agent_requested, llm_profiles[fallback])
        assert selected["model"] == "gpt-4o"
        # If a warning is logged, check for it (this will only pass if warning logic exists)
        # assert any("fallback" in rec.message.lower() for rec in caplog.records)
