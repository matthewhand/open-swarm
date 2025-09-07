from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
    NebulaShellzzarBlueprint,
)

# TODO: Add actual tests for the NebulaShellzzar blueprint
# These will likely involve mocking Agent/Runner.run and asserting tool calls
# or checking final output for specific scenarios.

def test_nebula_shellz_agent_creation():
    """Test if NebulaShellzzar agents are created correctly."""
    with patch('src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz.BlueprintBase._get_model_instance') as mock_get_model:
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        blueprint = NebulaShellzzarBlueprint(blueprint_id="test_nebula", debug=True)
        mock_mcp = MagicMock()
        agent = blueprint.create_starting_agent(mcp_servers=[mock_mcp])

        assert agent is not None
        assert agent.name == "NebulaShellzzar"
        assert len(blueprint.agents) > 0

@pytest.mark.asyncio
async def test_nebula_shellz_code_review_tool():
    """Test the code review tool functionality."""
    blueprint = NebulaShellzzarBlueprint(blueprint_id="test_nebula", debug=True)

    # Mock the review_code tool
    mock_agent = blueprint.agents[0]  # Assuming first agent has the tool
    mock_tool = MagicMock()
    mock_agent.tools = [mock_tool]

    with patch.object(mock_tool, 'func', new_callable=AsyncMock) as mock_func:
        mock_func.return_value = "Code review: Found TODO comment on line 10"

        messages = [{"role": "user", "content": "Review this code for issues"}]
        result = [msg async for msg in blueprint.run(messages)]

        mock_func.assert_called_once()
        assert "review" in mock_func.call_args[0][0].lower()
        assert "TODO" in result[0]["content"]

@pytest.mark.asyncio
async def test_nebula_shellz_documentation_generation():
    """Test the documentation generation tool."""
    blueprint = NebulaShellzzarBlueprint(blueprint_id="test_nebula", debug=True)

    # Mock the generate_docs tool
    mock_agent = blueprint.agents[0]
    mock_docs_tool = MagicMock()
    mock_agent.tools = [mock_docs_tool]

    with patch.object(mock_docs_tool, 'func', new_callable=AsyncMock) as mock_docs_func:
        mock_docs_func.return_value = "/** Generated docs for function */"

        messages = [{"role": "user", "content": "Generate documentation for this function"}]
        result = [msg async for msg in blueprint.run(messages)]

        mock_docs_func.assert_called_once()
        assert "documentation" in mock_docs_func.call_args[0][0].lower()
        assert "/**" in result[0]["content"]

@pytest.mark.asyncio
async def test_nebula_shellz_shell_command_execution():
    """Test shell command execution through delegation."""
    blueprint = NebulaShellzzarBlueprint(blueprint_id="test_nebula", debug=True)

    # Mock shell execution tool
    mock_agent = blueprint.agents[-1]  # Assuming last agent handles shell
    mock_shell_tool = MagicMock()
    mock_agent.tools = [mock_shell_tool]

    with patch.object(mock_shell_tool, 'func', new_callable=AsyncMock) as mock_shell_func:
        mock_shell_func.return_value = "Shell command executed: ls -la"

        messages = [{"role": "user", "content": "List files in current directory"}]
        result = [msg async for msg in blueprint.run(messages)]

        mock_shell_func.assert_called_once()
        assert "ls" in mock_shell_func.call_args[0][0] or "list" in mock_shell_func.call_args[0][0].lower()
        assert "executed" in result[0]["content"]
