import unittest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, call

# Mock the agents library classes before importing BlueprintBase
# This is crucial if agents library isn't fully installed/functional in test env
mock_agent = MagicMock()
mock_mcp_server = MagicMock()
mock_mcp_server_stdio = MagicMock()
sys.modules['agents'] = MagicMock(Agent=mock_agent)
sys.modules['agents.mcp'] = MagicMock(MCPServer=mock_mcp_server, MCPServerStdio=mock_mcp_server_stdio)

# Now import BlueprintBase
from src.swarm.extensions.blueprint.blueprint_base import BlueprintBase

# --- Test Fixtures ---

# Minimal concrete Blueprint for MCP testing
class MCPTestBlueprint(BlueprintBase):
    # We need to override metadata for MCP tests
    metadata = { "name": "MCPTestBlueprint" } # Required servers set per test

    def __init__(self, required_servers=None, **kwargs):
        self.metadata = self.metadata.copy() # Avoid modifying class attribute directly
        self.metadata["required_mcp_servers"] = required_servers or []
        super().__init__(**kwargs)

    def create_starting_agent(self, mcp_servers):
        # Return a mock agent that accepts mcp_servers list
        mock_agent_instance = MagicMock()
        mock_agent_instance.name = "MCPTestAgent"
        # We don't actually run the agent, just need to create it
        return mock_agent_instance

# --- Test Cases ---

@unittest.skip('Skipping MCP tests until mocking strategy is refined')
class TestBlueprintBaseMCPStartup(unittest.TestCase):

    def setUp(self):
        # Mock necessary parts of BlueprintBase dependencies
        self.mock_project_root = Path("/fake/mcp/project/root")
        patcher_path = patch('src.swarm.extensions.blueprint.blueprint_base.PROJECT_ROOT', self.mock_project_root)
        self.addCleanup(patcher_path.stop)
        patcher_path.start()

        # Prevent actual config loading, provide mock configs directly
        patcher_load_config = patch.object(BlueprintBase, '_load_configuration', return_value={
            "llm": {"default": {"model": "mock-model"}},
            "mcpServers": {
                "server_a": {"command": "cmd_a", "args": ["arg_a"]},
                "server_b": {"command": ["cmd_b", "--flag"], "env": {"K": "V"}},
                "server_missing_cmd": {"args": ["arg"]},
                "server_unfindable": {"command": "unfindable_cmd"}
            },
            "defaults": {} # Add other necessary keys if init fails
        })
        self.addCleanup(patcher_load_config.stop)
        self.mock_load_configuration = patcher_load_config.start()

        # Mock environment loading
        patcher_load_env = patch.object(BlueprintBase, '_load_environment')
        self.addCleanup(patcher_load_env.stop)
        patcher_load_env.start()


    # Use async test runner if available, else wrap in asyncio.run
    @patch('shutil.which')
    @patch('src.swarm.extensions.blueprint.blueprint_base.MCPServerStdio', new_callable=AsyncMock) # Mock the class constructor/instance
    @patch('asyncio.gather', new_callable=AsyncMock) # Mock gather
    def test_start_single_mcp_server_success(self, mock_gather, MockMCPServerStdio, mock_shutil_which):
        """Test starting a single valid MCP server successfully."""

        async def run_test():
             # --- Mocks Setup ---
             # Mock shutil.which to return a path
             mock_shutil_which.return_value = "/usr/bin/cmd_a"

             # Configure the AsyncMock for MCPServerStdio instance and its context manager
             mock_mcp_instance = AsyncMock(spec=mock_mcp_server) # Use the original mock as spec
             mock_mcp_instance.name = "server_a" # Set name for identification
             # Mock the async context manager __aenter__ to return the instance
             mock_mcp_instance.__aenter__.return_value = mock_mcp_instance
             MockMCPServerStdio.return_value = mock_mcp_instance # Constructor returns our mock instance

             # Mock asyncio.gather to return the started server instance
             mock_gather.return_value = [mock_mcp_instance]

             # --- Test Execution ---
             # Create blueprint requiring 'server_a'
             bp = MCPTestBlueprint(required_servers=["server_a"])

             # Mock the create_starting_agent method for this instance
             bp.create_starting_agent = MagicMock(return_value=MagicMock(name="TestAgent"))

             # Run the non-interactive part which triggers MCP startup
             await bp._run_non_interactive("Test instruction")

             # --- Assertions ---
             # Assert shutil.which was called correctly
             mock_shutil_which.assert_called_once_with("cmd_a")

             # Assert MCPServerStdio was instantiated correctly
             expected_params = {"command": "/usr/bin/cmd_a", "args": ["arg_a"]}
             MockMCPServerStdio.assert_called_once_with(name="server_a", params=expected_params)

             # Assert the async context manager was entered
             mock_mcp_instance.__aenter__.assert_awaited_once()

             # Assert asyncio.gather was called with one task (the result of _start_mcp_server_instance)
             # We don't easily check the task object itself, but check call count
             mock_gather.assert_awaited_once()
             self.assertEqual(len(mock_gather.await_args[0][0]), 1) # Check list of awaitables

             # Assert create_starting_agent was called with the started server
             bp.create_starting_agent.assert_called_once_with(mcp_servers=[mock_mcp_instance])

             # Assert the context manager __aexit__ was called upon stack exit
             mock_mcp_instance.__aexit__.assert_awaited_once()

        asyncio.run(run_test()) # Run the async test function


    @patch('shutil.which')
    @patch('src.swarm.extensions.blueprint.blueprint_base.MCPServerStdio', new_callable=AsyncMock)
    @patch('asyncio.gather', new_callable=AsyncMock)
    def test_start_multiple_mcp_servers(self, mock_gather, MockMCPServerStdio, mock_shutil_which):
        """Test starting multiple MCP servers."""
        async def run_test():
            # Mock shutil.which to return paths for both commands
            mock_shutil_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" # Simple dynamic mock

            # Create mock instances for each server
            mock_mcp_a = AsyncMock(spec=mock_mcp_server, name="server_a")
            mock_mcp_a.__aenter__.return_value = mock_mcp_a
            mock_mcp_b = AsyncMock(spec=mock_mcp_server, name="server_b")
            mock_mcp_b.__aenter__.return_value = mock_mcp_b

            # Make MCPServerStdio constructor return the correct mock based on name
            def mcp_constructor_side_effect(*args, **kwargs):
                if kwargs.get("name") == "server_a": return mock_mcp_a
                if kwargs.get("name") == "server_b": return mock_mcp_b
                raise ValueError("Unexpected server name in mock constructor")
            MockMCPServerStdio.side_effect = mcp_constructor_side_effect

            # Mock asyncio.gather to return both started servers
            mock_gather.return_value = [mock_mcp_a, mock_mcp_b]

            bp = MCPTestBlueprint(required_servers=["server_a", "server_b"])
            bp.create_starting_agent = MagicMock(return_value=MagicMock(name="TestAgent"))
            await bp._run_non_interactive("Test instruction")

            # Assert MCPServerStdio was called twice with correct params
            expected_calls_mcp = [
                call(name="server_a", params={'command': '/usr/bin/cmd_a', 'args': ['arg_a']}),
                call(name="server_b", params={'command': '/usr/bin/cmd_b', 'args': ['--flag'], 'env': {'K': 'V'}})
            ]
            MockMCPServerStdio.assert_has_calls(expected_calls_mcp, any_order=True)

            # Assert context managers entered
            mock_mcp_a.__aenter__.assert_awaited_once()
            mock_mcp_b.__aenter__.assert_awaited_once()

            # Assert gather called with two tasks
            mock_gather.assert_awaited_once()
            self.assertEqual(len(mock_gather.await_args[0][0]), 2)

            # Assert agent created with both servers
            bp.create_starting_agent.assert_called_once_with(mcp_servers=[mock_mcp_a, mock_mcp_b])

            # Assert cleanup called for both
            mock_mcp_a.__aexit__.assert_awaited_once()
            mock_mcp_b.__aexit__.assert_awaited_once()

        asyncio.run(run_test())


    @patch('shutil.which')
    @patch('src.swarm.extensions.blueprint.blueprint_base.MCPServerStdio', new_callable=AsyncMock)
    @patch('asyncio.gather', new_callable=AsyncMock)
    def test_start_mcp_server_fails_config(self, mock_gather, MockMCPServerStdio, mock_shutil_which):
        """Test failure when MCP server config is invalid (missing command)."""
        async def run_test():
            mock_gather.return_value = [None] # Simulate gather returning None for the failed start

            bp = MCPTestBlueprint(required_servers=["server_missing_cmd"])
            bp.create_starting_agent = MagicMock() # Should not be called

            # Capture print output to check error message
            with patch('builtins.print') as mock_print:
                await bp._run_non_interactive("Test instruction")

            # Assert MCPServerStdio was NOT instantiated
            MockMCPServerStdio.assert_not_called()
            # Assert gather was called (attempting the start)
            mock_gather.assert_awaited_once()
            # Assert agent creation was NOT called
            bp.create_starting_agent.assert_not_called()
            # Assert error message was printed (or logged at error level)
            # This depends on exact error handling, check logs or print output
            self.assertTrue(any("Failed to start all required MCP servers" in str(call_args) for call_args in mock_print.call_args_list))


        asyncio.run(run_test())

    @patch('shutil.which', return_value=None) # Simulate command not found
    @patch('src.swarm.extensions.blueprint.blueprint_base.MCPServerStdio', new_callable=AsyncMock)
    @patch('asyncio.gather', new_callable=AsyncMock)
    def test_start_mcp_server_fails_which(self, mock_gather, MockMCPServerStdio, mock_shutil_which):
        """Test failure when MCP server command cannot be found."""
        async def run_test():
            mock_gather.return_value = [None] # Simulate failure

            bp = MCPTestBlueprint(required_servers=["server_unfindable"])
            bp.create_starting_agent = MagicMock()

            with patch('builtins.print') as mock_print:
                 await bp._run_non_interactive("Test instruction")

            mock_shutil_which.assert_called_with("unfindable_cmd")
            MockMCPServerStdio.assert_not_called()
            mock_gather.assert_awaited_once()
            bp.create_starting_agent.assert_not_called()
            self.assertTrue(any("Failed to start all required MCP servers" in str(call_args) for call_args in mock_print.call_args_list))


        asyncio.run(run_test())


if __name__ == '__main__':
    # Need to use an async test runner or wrap calls if running directly
    # For simplicity, assume running via 'python -m unittest ...' which handles discovery
    unittest.main()
