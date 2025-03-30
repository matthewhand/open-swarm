import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import logging
import asyncio
import platformdirs
from pathlib import Path

# Add project root to sys.path to allow importing src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "blueprints")) # Add blueprints dir too

# --- Environment Variable Setup for Tests ---

# Set RUN_LLM_TESTS based on environment or default to False
RUN_LLM_TESTS = os.environ.get("RUN_LLM_TESTS", "false").lower() == "true"

skip_llm = pytest.mark.skipif(
    not RUN_LLM_TESTS, reason="Requires RUN_LLM_TESTS=true env var."
)

# --- Constants and Mock Data ---

# Define the mock config for Echocraft with the default LLM profile
MOCK_CONFIG_ECHOCRAFT = {
    "llm": {
        "default": {
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1",
            # Add other potential keys like api_key if needed by the Agent/Runner later
            # Using placeholder - ideally mocked or sourced securely if real calls needed
            "api_key": "sk-mock-test-key",
            # Add temperature or other common params if needed by agent init
            # "temperature": 0.7,
        }
    },
    "agents": {
        # Placeholder for any agent-specific config if needed by EchoAgent
        # "some_agent_setting": "value"
    }
}

# Mock config for Swarm CLI tests (Can remain separate or be merged if needed)
MOCK_CONFIG_CLI = {
    'swarm': {
        'name': 'TestSwarm',
        'profile': 'test_profile'
    },
    'logging': {
        'level': 'DEBUG'
    },
    # Include LLM section here too if CLI commands interact with profiles
    "llm": {
        "default": { # Keep consistent default profile for CLI tests too
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1",
            "api_key": "sk-mock-test-key-cli",
        },
         "test_profile": { # Example specific profile for CLI tests
            "model": "gpt-3.5-turbo",
            "api_base": "https://api.openai.com/v1",
            "api_key": "sk-mock-test-key-profile",
        }
    },
    'blueprints': {
         'echocraft': { 'some_key': 'some_value'}
    }
}


# --- Mock Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest-asyncio default event_loop to session scope."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def mock_platformdirs(mocker):
    """Mock platformdirs functions to return predictable paths during tests."""
    mock_user_data_dir = Path("/tmp/test_swarm_user_data")
    mock_user_config_dir = Path("/tmp/test_swarm_user_config")
    mock_user_cache_dir = Path("/tmp/test_swarm_user_cache")

    mocker.patch('platformdirs.user_data_dir', return_value=str(mock_user_data_dir))
    mocker.patch('platformdirs.user_config_dir', return_value=str(mock_user_config_dir))
    mocker.patch('platformdirs.user_cache_dir', return_value=str(mock_user_cache_dir))

    # Ensure the mocked dirs exist if tests need to write to them
    mock_user_data_dir.mkdir(parents=True, exist_ok=True)
    mock_user_config_dir.mkdir(parents=True, exist_ok=True)
    mock_user_cache_dir.mkdir(parents=True, exist_ok=True)

    return {
        "data": mock_user_data_dir,
        "config": mock_user_config_dir,
        "cache": mock_user_cache_dir,
    }

@pytest.fixture
def mock_config_loader(mocker):
    """
    Fixture to mock the config loading mechanism.
    It patches load_config to return a predefined mock config (defaulting to CLI).
    Tests needing specific config (like echocraft) should use config_override
    or potentially enhance this fixture later.
    """
    mock_load = mocker.patch('swarm.extensions.config.config_loader.load_config', return_value=MOCK_CONFIG_CLI)
    # Add mocks for save_config etc. if needed by tests
    # mocker.patch('swarm.extensions.config.config_loader.save_config')
    return mock_load


@pytest.fixture
def mock_openai_client(mocker):
    """Mocks the openai.AsyncOpenAI client."""
    # Make sure openai is importable before mocking it
    try:
        import openai
        # Mock the class itself
        mock_client_instance = MagicMock(spec=openai.AsyncOpenAI)
        # Mock specific nested attributes/methods if needed by agents
        # mock_response = MagicMock()
        # mock_response.choices = [MagicMock(message=MagicMock(content="Mocked LLM response"))]
        # mock_client_instance.chat.completions.create.return_value = asyncio.Future()
        # mock_client_instance.chat.completions.create.return_value.set_result(mock_response)

        # Patch the class being instantiated
        mocker.patch('openai.AsyncOpenAI', return_value=mock_client_instance)
        return mock_client_instance
    except ImportError:
        logging.warning("OpenAI library not found, cannot mock openai.AsyncOpenAI. Tests requiring it may fail.")
        # Return a simple MagicMock if openai is not installed,
        # allowing tests that don't rely on it to potentially proceed.
        return MagicMock()


# --- Test Helper Functions ---

# Example: A function to clean up created files after a test
# def cleanup_files(*paths):
#     for path in paths:
#         if os.path.exists(path):
#             os.remove(path)

# --- Pytest Hooks (if needed) ---

# def pytest_sessionstart(session):
#     """Called after the Session object has been created and before running collection."""
#     logging.info("Pytest session starting...")

# def pytest_sessionfinish(session, exitstatus):
#     """Called after whole test run finished, right before returning the exit status."""
#     logging.info(f"Pytest session finished. Exit status: {exitstatus}")

