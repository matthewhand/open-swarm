import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import subprocess
import re # For strip_ansi

# --- Placeholder Tests ---
## TODO: Implement tests for JeevesBlueprint

@pytest.fixture
def jeeves_blueprint_instance():
    with patch('swarm.core.blueprint_base.BlueprintBase._load_and_process_config', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}):
        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
            mock_model_instance = MagicMock()
            mock_get_model.return_value = mock_model_instance
            from swarm.blueprints.jeeves.blueprint_jeeves import JeevesBlueprint
            instance = JeevesBlueprint(blueprint_id="test_jeeves", config={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}} , debug=True)
            instance._config = {'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}
            instance.mcp_server_configs = {}
            return instance

def test_jeeves_agent_creation(jeeves_blueprint_instance):
    """Test if Jeeves agent is created correctly."""
    blueprint = jeeves_blueprint_instance
    m1 = MagicMock(); m1.name = "memory"
    m2 = MagicMock(); m2.name = "filesystem"
    m3 = MagicMock(); m3.name = "mcp-shell"
    mock_mcp_list = [m1, m2, m3]
    agent = blueprint.create_starting_agent(mcp_servers=mock_mcp_list)
    assert agent is not None
    assert agent.name == "Jeeves"

@pytest.mark.asyncio
async def test_jeeves_delegation_to_mycroft(monkeypatch, jeeves_blueprint_instance):
    """In test mode, run() should route to search/semantic_search based on search_mode."""
    os.environ['SWARM_TEST_MODE'] = '1'
    bp = jeeves_blueprint_instance

    called = {"search": False, "semantic": False}

    async def fake_search(query, directory="."):
        called["search"] = True
        return ["match1"]

    async def fake_semantic_search(query, directory="."):
        called["semantic"] = True
        return ["sem_match1"]

    monkeypatch.setattr(bp, "search", fake_search)
    monkeypatch.setattr(bp, "semantic_search", fake_semantic_search)

    # Route to code search
    messages = [{"role": "user", "content": "find foo"}]
    async for _ in bp.run(messages, search_mode='code'):
        pass
    assert called["search"] and not called["semantic"], "Expected code search path to be taken"

    # Reset and route to semantic search
    called = {"search": False, "semantic": False}
    async for _ in bp.run(messages, search_mode='semantic'):
        pass
    assert called["semantic"] and not called["search"], "Expected semantic search path to be taken"

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_jeeves_delegation_to_gutenberg():
    assert False

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.integration
# Removed @pytest.mark.asyncio as the test function is synchronous
def test_jeeves_cli_execution():
    """Test running the Jeeves blueprint via CLI and check for spinner/box output."""
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    env['SWARM_TEST_MODE'] = '1'

    cli_path = os.path.join(os.path.dirname(__file__), '../../src/swarm/blueprints/jeeves/jeeves_cli.py')
    cmd = [sys.executable, cli_path, '--instruction', 'Turn on the lights']

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=15)
    output = strip_ansi(result.stdout + result.stderr)

    print(f"CLI Output for Jeeves test:\n{output}")

    # In SWARM_TEST_MODE=1, JeevesSpinner.start() prints the first state.
    # The JeevesBlueprint.run() in test mode then prints its own box outputs.
    expected_initial_spinner_message = "[SPINNER] Polishing the silver"
    assert expected_initial_spinner_message in output, \
        f"Expected initial spinner message '{expected_initial_spinner_message}' not found in output: {output}"

    # The JeevesBlueprint.run() in test mode prints several boxes.
    # We can check for a part of the title or content of those boxes.
    # For example, the title "Jeeves Spinner" or "Jeeves Results"
    # or content like "Searching for: 'Turn on the lights'"
    assert "Jeeves Spinner" in output or "Jeeves Results" in output or "Searching for: 'Turn on the lights'" in output, \
        f"Expected Jeeves test mode box output not found: {output}"
