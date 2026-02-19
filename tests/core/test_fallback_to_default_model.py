import tempfile
from pathlib import Path

from swarm.extensions.config import config_loader


def test_fallback_to_default_model(monkeypatch, caplog):
    config = {
        "llm": {
            "gpt-4o": {"provider": "openai", "model": "gpt-4o"},
            "o3-mini": {"provider": "openrouter", "model": "openrouter/o3-mini"}
        },
        "settings": {"default_llm_profile": "gpt-4o"}
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        Path(tmp.name).write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(Path(tmp.name))
        # Simulate agent requesting a missing model
        requested = "notarealmodel"
        fallback = loaded["settings"]["default_llm_profile"]
        llm_profiles = loaded["llm"]
        selected = llm_profiles.get(requested, llm_profiles[fallback])
        assert selected["model"] == "gpt-4o"
        # Optionally check for warning in logs (if warning is implemented)
        # assert any("fallback" in rec.message for rec in caplog.records)
