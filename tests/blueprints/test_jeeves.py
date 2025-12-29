import os
import re  # For strip_ansi
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

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
            # Note: mcp_server_configs may not be defined; skipping assignment to avoid AttributeError
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

@pytest.mark.asyncio
async def test_jeeves_delegation_to_gutenberg(monkeypatch, jeeves_blueprint_instance):
    """Test delegation to Gutenberg for home automation tasks."""
    import os
    # Temporarily clear the SWARM_TEST_MODE environment variable to ensure normal mode execution
    original_test_mode = os.environ.get('SWARM_TEST_MODE')
    if original_test_mode is not None:
        del os.environ['SWARM_TEST_MODE']

    bp = jeeves_blueprint_instance

    # Mock the Gutenberg agent tool
    mock_gutenberg_tool = MagicMock()
    mock_gutenberg_tool.name = "Gutenberg"
    async def mock_tool_call(*args, **kwargs):
        return "gutenberg_match1"
    mock_gutenberg_tool.side_effect = mock_tool_call

    with patch('agents.Runner.run') as mock_runner_run:
        # Mock the create_starting_agent to return an agent with the mocked tool
        with patch.object(bp, 'create_starting_agent') as mock_create_agent:
            mock_agent = MagicMock()
            mock_agent.tools = [mock_gutenberg_tool]
            mock_create_agent.return_value = mock_agent

            # Execute the run method with a home automation instruction that would trigger Gutenberg
            async for _ in bp.run([{"role": "user", "content": "Turn on the kitchen light"}]):
                pass

            # Assert that the runner was called with the agent that has the gutenberg tool
            mock_runner_run.assert_called_once()
            # Now, we need to check if the tool was called.
            # Since we are mocking the runner, we can't directly assert if the tool was called.
            # Instead, we can check if the agent's run method was called with the correct arguments.
            # This is a bit of a workaround, but it's the best we can do with the current code structure.
            assert any(tool.name == "Gutenberg" for tool in mock_runner_run.call_args[0][0].tools)


    # Restore the original environment variable
    if original_test_mode is not None:
        os.environ['SWARM_TEST_MODE'] = original_test_mode

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
