import pytest
import asyncio
from typing import List, Dict, AsyncGenerator

# Assuming EchoAgent is no longer used/defined
from swarm.blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint
# from swarm.blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint, EchoAgent # <--- REMOVE EchoAgent

# Use pytest-asyncio decorator for async tests
@pytest.mark.asyncio
async def test_echocraft_blueprint_run():
    """Tests the basic run functionality of EchoCraftBlueprint."""
    blueprint = EchoCraftBlueprint()
    test_messages: List[Dict[str, str]] = [
        {"role": "user", "content": "Hello Echo!"}
    ]

    # Run the blueprint (which should be an async generator)
    result_generator: AsyncGenerator[Dict, None] = blueprint.run(test_messages)

    # Get the result from the async generator
    final_result = None
    async for chunk in result_generator:
        # In non-streaming, the final result might be the last chunk
        # or accumulated. EchoCraft yields one final chunk.
        final_result = chunk

    assert final_result is not None
    assert isinstance(final_result, dict)
    assert "messages" in final_result
    assert isinstance(final_result["messages"], list)
    assert len(final_result["messages"]) == 1
    assert final_result["messages"][0]["role"] == "assistant"
    assert final_result["messages"][0]["content"] == "Echo: Hello Echo!"

@pytest.mark.asyncio
async def test_echocraft_blueprint_no_user_message():
    """Tests that EchoCraft handles cases with no user message gracefully."""
    blueprint = EchoCraftBlueprint()
    test_messages: List[Dict[str, str]] = [
        {"role": "system", "content": "System prompt"}
        # No user message
    ]
    result_generator = blueprint.run(test_messages)
    final_result = None
    async for chunk in result_generator:
        final_result = chunk

    assert final_result is not None
    assert final_result["messages"][0]["content"] == "Echo: No user message found."

@pytest.mark.asyncio
async def test_echocraft_blueprint_multiple_messages():
    """Tests that EchoCraft uses the *last* user message."""
    blueprint = EchoCraftBlueprint()
    test_messages: List[Dict[str, str]] = [
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "Assistant reply"},
        {"role": "user", "content": "Second message - use this one!"}
    ]
    result_generator = blueprint.run(test_messages)
    final_result = None
    async for chunk in result_generator:
        final_result = chunk

    assert final_result is not None
    assert final_result["messages"][0]["content"] == "Echo: Second message - use this one!"

# --- Remove any tests that were specifically testing EchoAgent ---
# Example:
# def test_echo_agent_functionality():
#     agent = EchoAgent()
#     # ... assertions for the old agent ...
#     pass # Remove this whole test if it existed

