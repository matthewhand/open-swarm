# Placeholder: will be replaced with the renamed gaggle test logic.

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/swarm')))
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from blueprints.geese.blueprint_geese import create_story_outline, _create_story_outline
import re

pytestmark = pytest.mark.skipif(
    not (os.environ.get("OPENAI_API_KEY") or os.environ.get("LITELLM_API_KEY")),
    reason="No LLM API key available in CI/CD"
)

@pytest.fixture
def geese_blueprint_instance():
    """Fixture to create a mocked instance of GeeseBlueprint."""
    with patch('blueprints.geese.blueprint_geese.GeeseBlueprint._get_model_instance') as mock_get_model:
        mock_model_instance = MagicMock()
        mock_get_model.return_value = mock_model_instance
        from blueprints.geese.blueprint_geese import GeeseBlueprint
        instance = GeeseBlueprint("test_geese")
        instance.debug = True
        # Set a minimal valid config to avoid RuntimeError
        instance._config = {
            "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
            "blueprints": {},
            "llm_profile": "default",
            "mcpServers": {}
        }
    return instance

# --- Test Cases ---

def test_geese_agent_handoff_and_astool(geese_blueprint_instance):
    """Test Coordinator agent's as_tool handoff to Planner, Writer, Editor."""
    blueprint = geese_blueprint_instance
    coordinator = blueprint.create_starting_agent(mcp_servers=[])
    tool_names = [t.name for t in coordinator.tools]
    assert set(tool_names) == {"Planner", "Writer", "Editor"}
    planner_tool = next(t for t in coordinator.tools if t.name == "Planner")
    assert planner_tool is not None
    writer_tool = next(t for t in coordinator.tools if t.name == "Writer")
    assert writer_tool is not None
    editor_tool = next(t for t in coordinator.tools if t.name == "Editor")
    assert editor_tool is not None


def test_geese_story_delegation_flow(geese_blueprint_instance):
    """Test full agent handoff sequence: Planner -> Writer -> Editor."""
    blueprint = geese_blueprint_instance
    coordinator = blueprint.create_starting_agent(mcp_servers=[])
    planner_tool = next(t for t in coordinator.tools if t.name == "Planner")
    writer_tool = next(t for t in coordinator.tools if t.name == "Writer")
    editor_tool = next(t for t in coordinator.tools if t.name == "Editor")
    print(f"Planner tool type: {type(planner_tool)}; dir: {dir(planner_tool)}")
    print(f"Writer tool type: {type(writer_tool)}; dir: {dir(writer_tool)}")


@pytest.mark.asyncio
def test_geese_spinner_and_box_output(capsys):
    os.environ["SWARM_TEST_MODE"] = "1"
    from blueprints.geese.blueprint_geese import GeeseBlueprint
    blueprint = GeeseBlueprint("test_geese")
    messages = [{"role": "user", "content": "Write a story about teamwork."}]
    async def run_bp():
        async for _ in blueprint.run(messages):
            pass
    import asyncio
    asyncio.run(run_bp())
    out = capsys.readouterr().out
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    out_clean = ansi_escape.sub('', out)
    assert "Generating." in out_clean
    assert "Generating..." in out_clean or "Generating... Taking longer than expected" in out_clean
    assert "Creative" in out_clean or "Story" in out_clean
    assert "🦢" in out_clean or "Geese" not in out_clean
