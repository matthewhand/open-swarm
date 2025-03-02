import pytest
from swarm.core import Swarm

class DummyAsyncOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

def test_swarm_init_default_model(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "defaultTest")
    monkeypatch.setattr("swarm.core.AsyncOpenAI", DummyAsyncOpenAI)
    # Mock config with 'default' to avoid ValueError
    mock_config = {
        "llm": {
            "default": {"model": "defaultTest", "api_key": "dummy"},
            "defaultTest": {"model": "defaultTest", "api_key": "dummy"}
        }
    }
    swarm = Swarm(config=mock_config)
    assert swarm.model == "defaultTest"
    assert isinstance(swarm.client, DummyAsyncOpenAI)

def test_swarm_init_with_client(monkeypatch):
    dummy_client = DummyAsyncOpenAI(api_key="existing")
    # Mock config with 'default' to avoid ValueError
    mock_config = {
        "llm": {
            "default": {"model": "default", "api_key": "existing"}
        }
    }
    swarm = Swarm(client=dummy_client, config=mock_config)
    assert swarm.client == dummy_client
