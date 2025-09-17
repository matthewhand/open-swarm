"""
Standard Blueprint Test Template
================================

This template provides a comprehensive test suite that can be adapted
for any blueprint. Each blueprint should have these core test categories.

Usage: Copy this template and replace chatbot with actual blueprint name.
"""

from unittest.mock import MagicMock, patch

import pytest

# Specific imports for chatbot blueprint
from src.swarm.blueprints.chatbot.blueprint_chatbot import ChatbotBlueprint


class TestChatbotBlueprintBasicFunctionality:
    """Core functionality tests for chatbot blueprint."""

    def test_blueprint_initialization(self):
        """Test blueprint can be initialized with default parameters."""
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        assert blueprint is not None
        assert blueprint.blueprint_id == "test_chatbot"
        assert hasattr(blueprint, 'metadata')

    def test_blueprint_initialization_with_config(self):
        """Test blueprint initialization with custom config."""
        config = {"test": "value", "llm_profile": "custom"}
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot", config=config)
        assert blueprint is not None
        # Add specific config assertions based on blueprint

    def test_blueprint_metadata_present(self):
        """Test blueprint has required metadata."""
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        metadata = blueprint.metadata
        assert isinstance(metadata, dict)
        assert "name" in metadata
        assert "description" in metadata
        assert "version" in metadata


class TestChatbotBlueprintAgentCreation:
    """Tests for agent creation and configuration."""

    @patch('src.swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint._get_model_instance')
    def test_agent_creation_basic(self, mock_get_model):
        """Test basic agent creation."""
        from agents.models.interface import Model
        mock_model = MagicMock(spec=Model)
        mock_get_model.return_value = mock_model

        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        mock_mcp = MagicMock()
        agent = blueprint.create_starting_agent(mcp_servers=[mock_mcp])

        assert agent is not None
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'tools')

    @patch('src.swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint._get_model_instance')
    def test_agent_creation_with_multiple_mcp_servers(self, mock_get_model):
        """Test agent creation with multiple MCP servers."""
        from agents.models.interface import Model
        mock_model = MagicMock(spec=Model)
        mock_get_model.return_value = mock_model

        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        mock_mcps = [MagicMock(), MagicMock(), MagicMock()]
        agent = blueprint.create_starting_agent(mcp_servers=mock_mcps)

        assert agent is not None
        # Verify MCP servers are properly assigned

    @patch('src.swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint._get_model_instance')
    def test_agent_has_expected_tools(self, mock_get_model):
        """Test created agent has expected tools."""
        from agents.models.interface import Model
        mock_model = MagicMock(spec=Model)
        mock_get_model.return_value = mock_model

        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        agent = blueprint.create_starting_agent(mcp_servers=[])

        assert hasattr(agent, 'tools')
        assert isinstance(agent.tools, list)
        # Add specific tool assertions based on blueprint


class TestChatbotBlueprintExecution:
    """Tests for blueprint execution and run methods."""

    @pytest.mark.asyncio
    @patch('src.swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint.create_starting_agent')
    async def test_run_basic_message(self, mock_create_agent):
        """Test basic blueprint run with simple message."""
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        # Mock Runner.run to return predictable results
        with patch('agents.Runner.run') as mock_runner:
            mock_runner.return_value = iter([{"messages": [{"role": "assistant", "content": "Test response"}]}])

            blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
            messages = [{"role": "user", "content": "Test message"}]

            results = []
            async for result in blueprint.run(messages):
                results.append(result)

            assert len(results) > 0
            assert "messages" in results[-1]

    @pytest.mark.asyncio
    @patch('src.swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint.create_starting_agent')
    async def test_run_empty_message_list(self, mock_create_agent):
        """Test blueprint run with empty message list."""
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        with patch('agents.Runner.run') as mock_runner:
            mock_runner.return_value = iter([{"messages": [{"role": "assistant", "content": "No input provided"}]}])

            blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
            messages = []

            results = []
            async for result in blueprint.run(messages):
                results.append(result)

            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_run_handles_execution_error(self):
        """Test blueprint gracefully handles execution errors."""
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")

        with patch('agents.Runner.run', side_effect=Exception("Test error")):
            messages = [{"role": "user", "content": "Test message"}]

            results = []
            async for result in blueprint.run(messages):
                results.append(result)

            # Should yield error message instead of crashing
            assert len(results) > 0
            assert any("error" in str(result).lower() for result in results)


class TestChatbotBlueprintConfiguration:
    """Tests for configuration handling and model resolution."""

    def test_llm_profile_resolution_default(self):
        """Test default LLM profile resolution."""
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        # Test will depend on whether blueprint loads config successfully
        try:
            profile = blueprint.get_llm_profile("default")
            assert isinstance(profile, dict)
        except RuntimeError:
            # Expected if no config available in test environment
            pass

    def test_llm_profile_resolution_custom(self):
        """Test custom LLM profile resolution."""
        config = {
            "llm": {
                "profiles": {
                    "custom": {"model": "gpt-4", "temperature": 0.5}
                }
            }
        }
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot", config=config)
        profile = blueprint.get_llm_profile("custom")
        assert profile["model"] == "gpt-4"
        assert profile["temperature"] == 0.5

    def test_markdown_output_setting(self):
        """Test markdown output configuration."""
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        # Test default markdown setting
        markdown_enabled = blueprint.should_output_markdown
        assert isinstance(markdown_enabled, bool)


class TestChatbotBlueprintTools:
    """Tests for blueprint-specific tools and functionality."""

    # NOTE: Add blueprint-specific tool tests here
    # Example structure:

    # @pytest.mark.asyncio
    # async def test_specific_tool_functionality(self):
    #     """Test blueprint's specific tool."""
    #     # Import and test blueprint-specific tools
    #     pass

    def test_tools_are_defined(self):
        """Test that blueprint defines expected tools."""
        # This test should verify that the blueprint's expected tools exist
        # Implementation depends on specific blueprint
        pass


class TestChatbotBlueprintErrorHandling:
    """Tests for error handling and edge cases."""

    def test_initialization_with_invalid_config(self):
        """Test blueprint handles invalid configuration gracefully."""
        invalid_config = {"invalid": "structure", "profiles": "not_a_dict"}
        try:
            blueprint = ChatbotBlueprint(blueprint_id="test_chatbot", config=invalid_config)
            # Should not crash during initialization
            assert blueprint is not None
        except Exception as e:
            # If it does raise an exception, it should be informative
            assert len(str(e)) > 0

    def test_missing_model_profile_handling(self):
        """Test blueprint handles missing model profiles."""
        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        try:
            blueprint.get_llm_profile("nonexistent_profile")
            # Should either return default or raise informative error
        except Exception as e:
            assert "profile" in str(e).lower() or "not found" in str(e).lower()

    @patch('src.swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint._get_model_instance')
    def test_agent_creation_with_empty_mcp_list(self, mock_get_model):
        """Test agent creation with no MCP servers."""
        from agents.models.interface import Model
        mock_model = MagicMock(spec=Model)
        mock_get_model.return_value = mock_model

        blueprint = ChatbotBlueprint(blueprint_id="test_chatbot")
        agent = blueprint.create_starting_agent(mcp_servers=[])

        assert agent is not None


class TestChatbotBlueprintIntegration:
    """Integration tests with external components."""

    @pytest.mark.skipif(True, reason="Integration test - enable for full testing")
    def test_real_model_integration(self):
        """Test with actual model (requires API key)."""
        # This test would run with real models
        # Skip by default to avoid API costs
        pass

    @pytest.mark.skipif(True, reason="Integration test - enable for full testing")
    def test_mcp_server_integration(self):
        """Test with actual MCP servers."""
        # This test would run with real MCP servers
        # Skip by default for unit test isolation
        pass


# Additional test categories can be added based on blueprint complexity:
# - TestChatbotBlueprintCLI for command-line interface testing
# - TestChatbotBlueprintUX for user experience and spinner testing
# - TestChatbotBlueprintPerformance for performance-specific tests
# - TestChatbotBlueprintDelegation for multi-agent delegation flows
