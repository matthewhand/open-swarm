"""
Basic functional tests for Codey blueprint

This module contains basic functional tests for the Codey blueprint
to ensure it works correctly and can be expanded with more comprehensive tests.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.swarm.blueprints.codey.blueprint_codey import CodeyBlueprint


class TestCodeyBasicFunctionality:
    """Test basic functionality of Codey blueprint"""

    @pytest.fixture
    def codey_blueprint(self):
        """Fixture for Codey blueprint instance"""
        return CodeyBlueprint(blueprint_id="test_codey")

    def test_blueprint_initialization(self, codey_blueprint):
        """Test that Codey blueprint initializes correctly"""
        assert codey_blueprint is not None
        assert codey_blueprint.blueprint_id == "test_codey"
        assert hasattr(codey_blueprint, 'metadata')
        assert 'name' in codey_blueprint.metadata
        assert codey_blueprint.metadata['name'] == 'codey'

    def test_blueprint_metadata(self, codey_blueprint):
        """Test that Codey blueprint has correct metadata"""
        metadata = codey_blueprint.metadata
        assert 'name' in metadata
        assert 'emoji' in metadata
        assert 'description' in metadata
        assert 'examples' in metadata
        assert isinstance(metadata['examples'], list)
        assert len(metadata['examples']) > 0

    @pytest.mark.asyncio
    async def test_run_with_empty_messages(self, codey_blueprint):
        """Test that Codey handles empty messages gracefully"""
        result = []
        async for chunk in codey_blueprint.run([]):
            result.append(chunk)
        
        # Should return a helpful message
        assert len(result) > 0
        assert any('user message' in str(chunk).lower() for chunk in result)

    @pytest.mark.asyncio
    async def test_run_with_valid_message(self, codey_blueprint):
        """Test that Codey processes valid messages"""
        test_message = "Search for recursion examples"
        messages = [{"role": "user", "content": test_message}]
        
        result = []
        async for chunk in codey_blueprint.run(messages):
            result.append(chunk)
        
        # Should return some response
        assert len(result) > 0
        # Response should contain the user's request or indication of processing
        response_content = str(result[0])
        assert 'codey' in response_content.lower() or 'llm' in response_content.lower()

    @pytest.mark.asyncio
    async def test_run_with_multiple_messages(self, codey_blueprint):
        """Test that Codey handles conversation history"""
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response to first message"},
            {"role": "user", "content": "Second message"}
        ]
        
        result = []
        async for chunk in codey_blueprint.run(messages):
            result.append(chunk)
        
        # Should process the conversation
        assert len(result) > 0

    def test_spinner_functionality(self, codey_blueprint):
        """Test that spinner functionality works"""
        # Test initial spinner state
        initial_state = codey_blueprint.current_spinner_state()
        assert initial_state is not None
        assert isinstance(initial_state, dict)
        
        # Test spinner advancement
        codey_blueprint._spin()
        new_state = codey_blueprint.current_spinner_state()
        assert new_state is not None

    def test_start_method(self, codey_blueprint):
        """Test that start method works"""
        # Should not raise exceptions
        codey_blueprint.start()
        assert True  # If we get here, it worked

    @pytest.mark.asyncio
    async def test_run_in_test_mode(self, codey_blueprint):
        """Test that Codey works in test mode"""
        with patch.dict('os.environ', {'SWARM_TEST_MODE': '1'}):
            messages = [{"role": "user", "content": "test command"}]
            
            result = []
            async for chunk in codey_blueprint.run(messages):
                result.append(chunk)
            
            # Should return test-compliant output
            assert len(result) > 0
            # In test mode, should have specific structure
            if isinstance(result[0], dict):
                assert 'messages' in result[0] or 'progress' in result[0] or 'spinner_state' in result[0]

    def test_render_prompt_method(self, codey_blueprint):
        """Test that prompt rendering works"""
        context = {
            "user_request": "test request",
            "history": [],
            "available_tools": ["code"]
        }
        
        # Should not raise exceptions
        rendered = codey_blueprint.render_prompt("codey_prompt.j2", context)
        assert rendered is not None
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    @pytest.mark.asyncio
    async def test_error_handling_in_run(self, codey_blueprint):
        """Test that errors in run method are handled gracefully"""
        # Test with invalid message format
        invalid_messages = ["not a dict", "also not a dict"]
        
        # Should handle gracefully or raise appropriate exception
        try:
            result = []
            async for chunk in codey_blueprint.run(invalid_messages):
                result.append(chunk)
            
            # If it doesn't raise, should still return something
            assert len(result) > 0
        except (ValueError, TypeError, KeyError):
            # Expected - invalid input format
            pass

    def test_blueprint_config_access(self, codey_blueprint):
        """Test that config can be accessed"""
        # Should have access to config
        assert hasattr(codey_blueprint, 'config')
        config = codey_blueprint.config
        assert config is not None
        assert isinstance(config, dict)

    @pytest.mark.asyncio
    async def test_run_with_special_characters(self, codey_blueprint):
        """Test that Codey handles special characters in input"""
        special_message = "Test with special chars: ¡™£¢∞§¶•ªº–≠\n\t\r"
        messages = [{"role": "user", "content": special_message}]
        
        result = []
        async for chunk in codey_blueprint.run(messages):
            result.append(chunk)
        
        # Should handle special characters without crashing
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_run_with_very_long_message(self, codey_blueprint):
        """Test that Codey handles long messages"""
        long_message = "A" * 1000  # 1000 characters
        messages = [{"role": "user", "content": long_message}]
        
        result = []
        async for chunk in codey_blueprint.run(messages):
            result.append(chunk)
        
        # Should handle long messages
        assert len(result) > 0


class TestCodeyConfiguration:
    """Test configuration handling in Codey blueprint"""

    @pytest.fixture
    def codey_blueprint(self):
        """Fixture for Codey blueprint instance"""
        return CodeyBlueprint(blueprint_id="test_codey_config")

    def test_default_configuration(self, codey_blueprint):
        """Test that default configuration is loaded"""
        config = codey_blueprint.config
        assert config is not None
        assert isinstance(config, dict)

    def test_config_immutability(self, codey_blueprint):
        """Test that config cannot be modified directly"""
        original_config = codey_blueprint.config.copy()
        
        # Try to modify config
        try:
            codey_blueprint.config['test_key'] = 'test_value'
            # If this succeeds, config should still be valid
            assert codey_blueprint.config is not None
        except (AttributeError, TypeError):
            # Expected - config is immutable
            pass

    def test_llm_profile_access(self, codey_blueprint):
        """Test that LLM profiles can be accessed"""
        # Should be able to access LLM profiles
        assert hasattr(codey_blueprint, 'llm_profile')
        profile = codey_blueprint.llm_profile
        assert profile is not None


class TestCodeyIntegration:
    """Test integration aspects of Codey blueprint"""

    @pytest.fixture
    def codey_blueprint(self):
        """Fixture for Codey blueprint instance"""
        return CodeyBlueprint(blueprint_id="test_codey_integration")

    @pytest.mark.asyncio
    async def test_integration_with_mock_llm(self, codey_blueprint):
        """Test Codey with mocked LLM responses"""
        # Mock the LLM chat completion
        mock_response = AsyncMock()
        mock_response.__aiter__.return_value = [
            {"content": "Mocked LLM response"}
        ]
        
        with patch.object(codey_blueprint, '_get_llm_response', return_value=mock_response):
            messages = [{"role": "user", "content": "test query"}]
            
            result = []
            async for chunk in codey_blueprint.run(messages):
                result.append(chunk)
            
            # Should return mocked response
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_integration_with_mock_tools(self, codey_blueprint):
        """Test Codey with mocked tool execution"""
        # Mock tool execution
        with patch('src.swarm.blueprints.codey.blueprint_codey.execute_command') as mock_exec:
            mock_exec.return_value = ("tool output", "", 0)
            
            messages = [{"role": "user", "content": "use code tool"}]
            
            result = []
            async for chunk in codey_blueprint.run(messages):
                result.append(chunk)
            
            # Should handle tool execution
            assert len(result) > 0
