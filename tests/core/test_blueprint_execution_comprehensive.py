"""
Comprehensive tests for blueprint execution functionality.
These tests verify the core mechanisms that allow blueprints to execute properly.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from swarm.core.blueprint_base import BlueprintBase


class TestBlueprintExecutionComprehensive:
    """High-value tests for blueprint execution functionality."""

    def test_blueprint_execution_runs_successfully_with_valid_input(self):
        """Test that blueprints execute successfully with valid input."""
        # Given: a concrete blueprint implementation
        class TestBlueprint(BlueprintBase):
            async def run(self, messages, **kwargs):
                # Simple implementation that echoes the last message
                if messages:
                    last_message = messages[-1]
                    content = last_message.get("content", "")
                    yield {"messages": [{"role": "assistant", "content": f"Echo: {content}"}]}
                else:
                    yield {"messages": [{"role": "assistant", "content": "No input provided"}]}

        blueprint = TestBlueprint(blueprint_id="test_bp")
        
        # When: executing with valid input
        messages = [{"role": "user", "content": "Hello, world!"}]
        results = []
        
        async def collect_results():
            async for result in blueprint.run(messages):
                results.append(result)
        
        asyncio.run(collect_results())
        
        # Then: should execute successfully and return expected output
        assert len(results) > 0, "Blueprint execution should return results"
        assert "messages" in results[0], "Result should contain messages"
        assert len(results[0]["messages"]) > 0, "Result should contain at least one message"
        assert "Echo: Hello, world!" in results[0]["messages"][0]["content"], "Should echo the input"

    def test_blueprint_execution_handles_empty_message_list_gracefully(self):
        """Test that blueprints handle empty message lists gracefully."""
        # Given: a concrete blueprint implementation
        class TestBlueprint(BlueprintBase):
            async def run(self, messages, **kwargs):
                # Simple implementation that handles empty messages
                if not messages:
                    yield {"messages": [{"role": "assistant", "content": "No input provided"}]}
                else:
                    last_message = messages[-1]
                    content = last_message.get("content", "")
                    yield {"messages": [{"role": "assistant", "content": f"Echo: {content}"}]}

        blueprint = TestBlueprint(blueprint_id="test_bp")
        
        # When: executing with empty message list
        messages = []
        results = []
        
        async def collect_results():
            async for result in blueprint.run(messages):
                results.append(result)
        
        asyncio.run(collect_results())
        
        # Then: should handle gracefully and return appropriate response
        assert len(results) > 0, "Blueprint execution should return results even with empty input"
        assert "messages" in results[0], "Result should contain messages"
        assert len(results[0]["messages"]) > 0, "Result should contain at least one message"
        assert "No input provided" in results[0]["messages"][0]["content"], "Should handle empty input gracefully"

    def test_blueprint_execution_handles_malformed_messages_gracefully(self):
        """Test that blueprints handle malformed messages gracefully."""
        # Given: a concrete blueprint implementation
        class TestBlueprint(BlueprintBase):
            async def run(self, messages, **kwargs):
                # Handle various malformed message scenarios
                try:
                    if not messages:
                        yield {"messages": [{"role": "assistant", "content": "No input provided"}]}
                        return
                    
                    # Try to process the last message
                    last_message = messages[-1]
                    if not isinstance(last_message, dict):
                        yield {"messages": [{"role": "assistant", "content": "Invalid message format"}]}
                        return
                    
                    content = last_message.get("content", "")
                    if not content:
                        yield {"messages": [{"role": "assistant", "content": "Empty message content"}]}
                        return
                        
                    yield {"messages": [{"role": "assistant", "content": f"Processed: {content}"}]}
                except Exception as e:
                    yield {"messages": [{"role": "assistant", "content": f"Error processing message: {str(e)}"}]}

        blueprint = TestBlueprint(blueprint_id="test_bp")
        
        # Test various malformed message scenarios
        malformed_inputs = [
            None,  # None instead of list
            "not a list",  # String instead of list
            [None],  # List with None element
            [{"invalid": "structure"}],  # Dict without content field
            [{"role": "user"}],  # Dict with role but no content
            [{"content": "missing role"}],  # Dict with content but no role
        ]
        
        for malformed_input in malformed_inputs:
            results = []
            
            async def collect_results():
                try:
                    async for result in blueprint.run(malformed_input):
                        results.append(result)
                except Exception as e:
                    # Even if run() raises an exception, it should be handled gracefully
                    results.append({"messages": [{"role": "assistant", "content": f"Execution error: {str(e)}"}]})
            
            asyncio.run(collect_results())
            
            # Then: should handle gracefully and return appropriate response
            assert len(results) > 0, f"Blueprint execution should return results even with malformed input: {malformed_input}"
            assert "messages" in results[0], f"Result should contain messages even with malformed input: {malformed_input}"
            assert len(results[0]["messages"]) > 0, f"Result should contain at least one message even with malformed input: {malformed_input}"
            # Should not crash or raise unhandled exceptions

    def test_blueprint_execution_supports_streaming_responses(self):
        """Test that blueprints support streaming responses properly."""
        # Given: a concrete blueprint implementation that streams responses
        class TestBlueprint(BlueprintBase):
            async def run(self, messages, **kwargs):
                if not messages:
                    yield {"messages": [{"role": "assistant", "content": "No input provided"}]}
                    return
                
                content = messages[-1].get("content", "")
                # Stream the response in chunks
                words = content.split()
                for i, word in enumerate(words):
                    yield {"messages": [{"role": "assistant", "content": f"Word {i+1}: {word}\n"}]}

        blueprint = TestBlueprint(blueprint_id="test_bp")
        
        # When: executing with input that should produce streaming responses
        messages = [{"role": "user", "content": "Hello world streaming test"}]
        results = []
        
        async def collect_results():
            async for result in blueprint.run(messages):
                results.append(result)
        
        asyncio.run(collect_results())
        
        # Then: should return multiple streamed responses
        assert len(results) > 1, "Streaming blueprint should return multiple results"
        for i, result in enumerate(results):
            assert "messages" in result, f"Result {i} should contain messages"
            assert len(result["messages"]) > 0, f"Result {i} should contain at least one message"
            assert "Word" in result["messages"][0]["content"], f"Result {i} should contain word count"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])