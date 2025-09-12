from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
    NebuchaShellzzarBlueprint,
)

# TODO: Add actual tests for the NebulaShellzzar blueprint
# These will likely involve mocking Agent/Runner.run and asserting tool calls
# or checking final output for specific scenarios.

def test_nebula_shellz_agent_creation():
    """Test if NebulaShellzzar agents are created correctly."""
    with patch('src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz.NebuchaShellzzarBlueprint._get_model_instance') as mock_get_model:
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
    from src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import code_review
    
    # Test the code_review tool directly - access the underlying function
    test_code = "def test_function():\n    # TODO: implement this\n    pass"
    result = await code_review.function(test_code)
    
    assert "TODO found on line 2" in result
    assert "implement this" in result

@pytest.mark.asyncio
async def test_nebula_shellz_documentation_generation():
    """Test the documentation generation tool directly."""
    from src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import generate_documentation
    
    # Test the generate_documentation tool directly - access the underlying function
    test_code = "def example_function(param1, param2):\n    return param1 + param2"
    result = generate_documentation.function(test_code)
    
    assert "/**" in result
    assert "example_function" in result
    assert "@param" in result
    assert "@returns" in result

@pytest.mark.asyncio
async def test_nebula_shellz_shell_command_execution():
    """Test shell command execution tool directly."""
    from src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import _execute_shell_command_raw
    
    # Test with a simple command that should work on most systems
    with patch('src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz.subprocess.run') as mock_run:
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
