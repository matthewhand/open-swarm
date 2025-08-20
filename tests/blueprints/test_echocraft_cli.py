import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys

from swarm.blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint, run_echocraft_cli, EchoCraftSpinner, print_operation_box

@pytest.fixture
def mock_blueprint_run():
    async def mock_run_generator():
        # Simulate the structure of final_message_chunk yielded by _original_run
        yield {
            "id": "chatcmpl-test-123",
            "object": "chat.completion",
            "created": 1678886400,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Echo: Test message from mock blueprint.run",
                    },
                    "finish_reason": "stop",
                    "logprobs": None,
                }
            ],
        }
    return mock_run_generator

@pytest.mark.asyncio
async def test_run_echocraft_cli_success(mock_blueprint_run, capsys):
    """Tests that run_echocraft_cli correctly processes output from blueprint.run."""
    blueprint = EchoCraftBlueprint(blueprint_id="test_cli_run")
    
    # Mock the blueprint.run method to return our controlled generator
    blueprint.run = MagicMock(return_value=mock_blueprint_run())

    messages = [{"role": "user", "content": "Test message"}]

    # Call the function under test
    await run_echocraft_cli(blueprint, messages)

    # Capture stdout
    captured = capsys.readouterr()
    
    # Assert that the expected content was printed
    # We need to be careful about the exact output of print_operation_box
    # For now, let's just check for the key part of the echoed message
    assert "Echo: Test message from mock blueprint.run" in captured.out
    assert "EchoCraft Output" in captured.out # Check for the box title
    assert "Results: 1" in captured.out # Check for results count

    # Ensure no KeyError occurred (this is the primary goal of this test)
    assert "KeyError: 'messages'" not in captured.err

@pytest.mark.asyncio
async def test_run_echocraft_cli_unexpected_response_format(mock_blueprint_run, capsys):
    """Tests run_echocraft_cli handles unexpected response formats gracefully."""
    blueprint = EchoCraftBlueprint(blueprint_id="test_cli_run_bad_format")

    async def bad_run_generator():
        yield {"unexpected_key": "unexpected_value"} # Simulate a bad format
        yield "plain string response" # Another bad format

    blueprint.run = MagicMock(return_value=bad_run_generator())

    messages = [{"role": "user", "content": "Test message"}]

    await run_echocraft_cli(blueprint, messages)

    captured = capsys.readouterr()
    
    # Expect the string representation of the unexpected dict/string
    assert "'unexpected_key': 'unexpected_value'" in captured.out
    assert "plain string response" in captured.out
    assert "KeyError: 'messages'" not in captured.err # Ensure no KeyError
