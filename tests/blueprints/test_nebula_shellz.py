from unittest.mock import MagicMock, patch

import pytest

from swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
    NebuchaShellzzarBlueprint,
)

# Tests for NebulaShellzzar blueprint implemented

def test_nebula_shellz_agent_creation():
    """Test if NebulaShellzzar agents are created correctly."""
    with patch('swarm.blueprints.nebula_shellz.blueprint_nebula_shellz.NebuchaShellzzarBlueprint._get_model_instance') as mock_get_model:
        # Create a proper mock that passes isinstance checks
        from agents.models.interface import Model
        mock_model = MagicMock(spec=Model)
        mock_get_model.return_value = mock_model

        blueprint = NebuchaShellzzarBlueprint(blueprint_id="test_nebula", debug=True)
        mock_mcp = MagicMock()
        agent = blueprint.create_starting_agent(mcp_servers=[mock_mcp])

        assert agent is not None
        assert agent.name == "Morpheus"  # The starting agent is Morpheus, not NebulaShellzzar
        assert hasattr(agent, 'tools')
        assert len(agent.tools) > 0

@pytest.mark.asyncio
async def test_nebula_shellz_code_review_tool():
    """Test the code review tool functionality directly."""
    import json
    from unittest.mock import MagicMock

    from swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import code_review

    # Test the code_review tool using on_invoke_tool with JSON input
    test_code = "def test_function():\n    # TODO: implement this\n    pass"
    input_json = json.dumps({"code_snippet": test_code})
    mock_ctx = MagicMock()

    result_cor = code_review.on_invoke_tool(mock_ctx, input_json)
    result = await result_cor

    assert "TODO found on line 2" in result
    assert "implement this" in result

@pytest.mark.asyncio
async def test_nebula_shellz_documentation_generation():
    """Test the documentation generation tool directly."""
    import json
    from unittest.mock import MagicMock

    from swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
        generate_documentation,
    )

    # Test the generate_documentation tool using on_invoke_tool with JSON input
    test_code = "def example_function(param1, param2):\n    return param1 + param2"
    input_json = json.dumps({"code_snippet": test_code})
    mock_ctx = MagicMock()

    result_cor = generate_documentation.on_invoke_tool(mock_ctx, input_json)
    result = await result_cor

    assert "/**" in result
    assert "example_function" in result
    assert "@param" in result
    assert "@returns" in result

@pytest.mark.asyncio
async def test_nebula_shellz_shell_command_execution():
    """Test shell command execution tool directly."""
    from swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
        _execute_shell_command_raw,
    )

    # Test with a simple command that should work on most systems
    with patch('swarm.blueprints.nebula_shellz.blueprint_nebula_shellz.subprocess.run') as mock_run:
        # Mock successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.txt\nfile2.txt"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = _execute_shell_command_raw("echo test")

        assert "Exit Code: 0" in result
        assert "STDOUT:" in result
        mock_run.assert_called_once()
