import pytest
import os
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from openai import AsyncOpenAI # Import the actual class for type hints if needed

from swarm.core import Swarm
# Assume DummyAsyncOpenAI is defined here or imported if needed for tests
class DummyAsyncOpenAI:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock() # Make create an async mock

def test_swarm_init_default_model(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "defaultTest")
    monkeypatch.setattr("swarm.core.AsyncOpenAI", DummyAsyncOpenAI)
    # Mock config with 'default' and the custom profile
    mock_config = {
        "llm": {
            "default": {"model": "should_be_ignored", "api_key": "key1"}, # Include default
            # Note: No provider specified for defaultTest
            "defaultTest": {"model": "defaultTestModel", "api_key": "key2", "base_url": "http://test.url"}
        }
    }
    # --- FIX: Ensure OPENAI_API_KEY is not set for this specific test ---
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    swarm = Swarm(config=mock_config)
    assert swarm.model == "defaultTestModel" # Check model name loaded
    assert swarm.client.api_key == "key2" # Should now use the config key
    assert swarm.client.base_url == "http://test.url"

def test_swarm_init_with_client(monkeypatch):
    # Temporarily remove OPENAI_API_KEY to test config loading without env override
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    dummy_client = DummyAsyncOpenAI(api_key="existing") # This client isn't passed anymore
    # Mock config with 'default' to check if its key is used
    mock_config = {
        "llm": {
            "default": {"model": "default", "api_key": "config_key"}
        }
    }
    # Patch the AsyncOpenAI used internally by Swarm
    monkeypatch.setattr("swarm.core.AsyncOpenAI", DummyAsyncOpenAI)
    swarm = Swarm(config=mock_config)
    # Assert that the client used the key from the mock_config
    assert swarm.client.api_key == mock_config['llm']['default']['api_key']

def test_swarm_init_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env_key")
    # Mock config with 'default'
    mock_config = {
        "llm": {
            # Provider is openai (implicitly or explicitly)
            "default": {"provider": "openai", "model": "default", "api_key": "config_key"}
        }
    }
    monkeypatch.setattr("swarm.core.AsyncOpenAI", DummyAsyncOpenAI)
    swarm = Swarm(config=mock_config)
    # Assert that the client used the key from the environment variable
    # OPENAI_API_KEY is both specific (for provider openai) and fallback
    assert swarm.client.api_key == "env_key"

