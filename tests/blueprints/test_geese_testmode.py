import json
from unittest.mock import MagicMock, patch

import pytest

from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from swarm.core.interaction_types import AgentInteraction


@pytest.fixture
def geese_instance_test_mode(tmp_path):
    # Minimal config to satisfy blueprint init, though test mode bypasses agent usage
    cfg_path = tmp_path / "geese_testmode_config.json"
    cfg = {
        "llm": {"default": {"provider": "mock", "model": "mock-model"}},
        "settings": {"default_llm_profile": "default"},
        "blueprints": {"geese": {}},
    }
    cfg_path.write_text(json.dumps(cfg))

    with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
        mock_model = MagicMock(name="MockModelInstanceForTestMode")
        async def mock_stream(*args, **kwargs):
            if False:
                yield  # pragma: no cover (keeps as async generator)
        mock_model.chat_completion_stream = mock_stream
        mock_get_model.return_value = mock_model

        bp = GeeseBlueprint(blueprint_id="geese_testmode", config_path=str(cfg_path))
        bp._config = cfg
        return bp


@pytest.mark.asyncio
async def test_run_emits_spinner_and_final_in_test_mode(geese_instance_test_mode, monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    bp = geese_instance_test_mode

    chunks = []
    async for ch in bp.run([{"role": "user", "content": "Hello world"}]):
        chunks.append(ch)

    # Expect at least 5 outputs: 4 spinners + 1 final AgentInteraction
    assert len(chunks) >= 5
    # First four should be spinner_update dicts
    for i, label in enumerate(["Generating.", "Generating..", "Generating...", "Running..."]):
        assert isinstance(chunks[i], dict)
        assert chunks[i].get("type") == "spinner_update"
        assert chunks[i].get("spinner_state") == f"[SPINNER] {label}"

    # Final chunk must be an AgentInteraction with a test story
    final = chunks[-1]
    assert isinstance(final, AgentInteraction)
    assert final.type == "message"
    assert final.final is True
    assert isinstance(final.data, dict)
    assert "Once upon a time" in (final.content or final.data.get("final_story", ""))

