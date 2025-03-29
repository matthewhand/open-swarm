import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, call
import logging

# Configure logger for debugging test issues if needed
# logging.basicConfig(level=logging.DEBUG)
# test_logger = logging.getLogger("TestBlueprintBaseConfigLoading")

# Import the module containing the base class *and* the constants we need to patch
import src.swarm.extensions.blueprint.blueprint_base as blueprint_base_module
from src.swarm.extensions.blueprint.blueprint_base import BlueprintBase, _substitute_env_vars

# --- Test Fixtures ---

class MockAgent:
    """A simple mock Agent class for testing."""
    def __init__(self, name="MockAgent", **kwargs):
        self.name = name

class TestableBlueprint(BlueprintBase):
    """A concrete BlueprintBase subclass for testing config loading."""
    metadata = {
        "name": "TestableBlueprint", "title": "Test Blueprint", "version": "1.0",
        "description": "Used for testing BlueprintBase.", "author": "Tester",
        "tags": ["test"], "required_mcp_servers": ["test_mcp"]
    }
    def create_starting_agent(self, mcp_servers: list) -> MockAgent:
        """Creates a dummy agent for testing purposes."""
        return MockAgent()

# --- Test Cases ---

class TestBlueprintBaseConfigLoading(unittest.TestCase):
    """Test suite for BlueprintBase configuration loading logic."""

    def setUp(self):
        """Set up test environment before each test method."""
        self.original_expandvars = os.path.expandvars
        os.path.expandvars = lambda x: x # Default mock does no substitution

        # Define expected paths based on mocked root
        self.mock_project_root = Path("/fake/project/root")
        self.expected_default_config_path = self.mock_project_root / "swarm_config.json"
        self.expected_dotenv_path = self.mock_project_root / ".env"

        # Patch PROJECT_ROOT *before* any test runs (though module-level constants might still be tricky)
        self.patcher_project_root = patch.object(blueprint_base_module, 'PROJECT_ROOT', self.mock_project_root)
        self.patcher_project_root.start()
        self.addCleanup(self.patcher_project_root.stop)

        # Also patch DEFAULT_CONFIG_PATH directly to ensure tests use the mocked path
        self.patcher_default_config = patch.object(blueprint_base_module, 'DEFAULT_CONFIG_PATH', self.expected_default_config_path)
        self.patcher_default_config.start()
        self.addCleanup(self.patcher_default_config.stop)

        # Default base config data
        self.base_mock_config_data = {
            "defaults": {"base_key": "base_value", "use_markdown": False},
            "llm": {"default": {"model": "default_model"}},
            "mcpServers": {"default_mcp": {"command": "default_cmd"}},
            "blueprints": {}, "profiles": {}
        }

        # Default mock for load_dotenv - individual tests can override
        patcher_load_dotenv = patch.object(blueprint_base_module, 'load_dotenv')
        self.mock_load_dotenv = patcher_load_dotenv.start()
        self.addCleanup(patcher_load_dotenv.stop)

    def tearDown(self):
        """Clean up test environment after each test method."""
        os.path.expandvars = self.original_expandvars

    # --- Tests ---

    # Use autospec=True for Path.is_file patch
    @patch('pathlib.Path.is_file', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_load_configuration_defaults_only(self, mock_file_open, mock_path_is_file):
        """Verify loading base defaults when only defaults are present in config."""
        mock_path_is_file.side_effect = [False, True] # .env missing, config exists
        mock_data = {
            "defaults": {"key1": "value1_default", "use_markdown": True},
            "llm": {"default": {"model": "d_model"}}, # Top level LLM
            "mcpServers": {"test_mcp": {"command": "d_cmd"}}, # Top level MCP
            "blueprints": {}, "profiles": {}
        }
        mock_file_open.return_value.read.return_value = json.dumps(mock_data)
        bp = TestableBlueprint()
        self.assertEqual(bp.config['key1'], 'value1_default')
        self.assertTrue(bp.config['use_markdown'])
        self.assertTrue(bp.use_markdown)
        self.assertIn('default', bp.llm_profiles)
        self.assertEqual(bp.llm_profiles['default']['model'], 'd_model')
        self.assertIn('test_mcp', bp.mcp_server_configs)
        self.assertEqual(bp.mcp_server_configs['test_mcp']['command'], 'd_cmd')
        mock_file_open.assert_called_once_with(self.expected_default_config_path, "r", encoding="utf-8")
        self.mock_load_dotenv.assert_not_called()
        self.assertEqual(mock_path_is_file.call_count, 2)
        # Check args using call_args_list directly
        calls = mock_path_is_file.call_args_list
        self.assertEqual(calls[0].args[0], self.expected_dotenv_path)
        self.assertEqual(calls[1].args[0], self.expected_default_config_path)

    @patch('pathlib.Path.is_file', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_load_configuration_blueprint_override(self, mock_file_open, mock_path_is_file):
        """Verify blueprint-specific settings override base defaults."""
        mock_path_is_file.side_effect = [False, True]
        mock_data = {
            "defaults": {"key1": "default", "key2": "base", "use_markdown": False},
            "blueprints": { "TestableBlueprint": {"key1": "blueprint_override", "use_markdown": True} },
            "llm": {}, "mcpServers": {}, "profiles": {}
        }
        mock_file_open.return_value.read.return_value = json.dumps(mock_data)
        bp = TestableBlueprint()
        self.assertEqual(bp.config['key1'], 'blueprint_override')
        self.assertEqual(bp.config['key2'], 'base')
        self.assertTrue(bp.config['use_markdown'])
        self.assertTrue(bp.use_markdown)

    @patch('pathlib.Path.is_file', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_load_configuration_profile_override(self, mock_file_open, mock_path_is_file):
        """Verify profile settings override blueprint and base defaults, testing profile priority."""
        is_file_mock = MagicMock(side_effect=[False, True, False, True, False, True])
        mock_path_is_file.side_effect = is_file_mock
        mock_data_template = {
            "defaults": {"key1": "default", "default_profile": "prod"},
            "profiles": {
                "dev": {"key1": "dev", "p_key": "dev_val", "use_markdown": True},
                "prod": {"key1": "prod", "p_key": "prod_val", "use_markdown": False}
            },
            "blueprints": { "TestableBlueprint": {"key1": "blueprint", "default_profile": "dev"} },
            "llm": {"default": {"model":"base_llm"}}, "mcpServers": {}
        }
        mock_file_open.return_value.read.return_value = json.dumps(mock_data_template)

        # Case 1: CLI override
        bp_cli_dev = TestableBlueprint(profile_override="dev")
        self.assertEqual(bp_cli_dev.config['key1'], 'dev')
        self.assertEqual(bp_cli_dev.config['p_key'], 'dev_val')
        self.assertTrue(bp_cli_dev.config['use_markdown'])
        self.assertTrue(bp_cli_dev.use_markdown)
        self.assertEqual(bp_cli_dev.llm_profiles['default']['model'], 'base_llm')

        # Case 2: Blueprint default
        mock_file_open.return_value.read.return_value = json.dumps(mock_data_template)
        bp_bp_profile = TestableBlueprint()
        self.assertEqual(bp_bp_profile.config['key1'], 'dev')
        self.assertEqual(bp_bp_profile.config['p_key'], 'dev_val')
        self.assertTrue(bp_bp_profile.config['use_markdown'])
        self.assertTrue(bp_bp_profile.use_markdown)

        # Case 3: Base default
        mock_data_no_bp_profile = {
            "defaults": {"key1": "default", "default_profile": "prod"},
            "profiles": {"prod": {"key1": "prod", "p_key": "prod_val", "use_markdown": False}},
            "blueprints": {"TestableBlueprint": {"key1": "blueprint"}},
             "llm": {}, "mcpServers": {}
        }
        mock_file_open.return_value.read.return_value = json.dumps(mock_data_no_bp_profile)
        bp_base_profile = TestableBlueprint()
        self.assertEqual(bp_base_profile.config['key1'], 'prod')
        self.assertEqual(bp_base_profile.config['p_key'], 'prod_val')
        self.assertFalse(bp_base_profile.config['use_markdown'])
        self.assertFalse(bp_base_profile.use_markdown)
        self.assertEqual(is_file_mock.call_count, 6)

    @patch('pathlib.Path.is_file', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_load_configuration_cli_config_dict_override(self, mock_file_open, mock_path_is_file):
        """Verify explicit config overrides dictionary applies last."""
        mock_path_is_file.side_effect = [False, True]
        mock_data = {
            "defaults": {"key1": "default"},
            "profiles": {"prod": {"key1": "profile"}},
            "blueprints": {"TestableBlueprint": {"key1": "blueprint"}},
            "llm": {"default": {"model":"base_llm"}}, "mcpServers": {}
        }
        mock_file_open.return_value.read.return_value = json.dumps(mock_data)
        cli_overrides = {"key1": "cli_override", "new_key": "cli_val"}
        bp = TestableBlueprint(profile_override="prod", config_overrides=cli_overrides)
        self.assertEqual(bp.config['key1'], 'cli_override')
        self.assertEqual(bp.config['new_key'], 'cli_val')
        self.assertEqual(bp.llm_profiles['default']['model'], 'base_llm')

    @patch.dict(os.environ, {"TEST_VAR": "env_val", "OTHER_VAR": "other"}, clear=True)
    @patch('pathlib.Path.is_file', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_environment_variable_substitution(self, mock_file_open, mock_path_is_file):
        """Verify environment variable substitution works correctly after config merge."""
        os.path.expandvars = self.original_expandvars
        mock_path_is_file.side_effect = [False, True]
        mock_data = {
            "defaults": {
                "sub_key": "${TEST_VAR}", "mix_key": "$OTHER_VAR/data",
                "no_sub": "plain_value", "missing_var": "${MISSING_VAR:-default_val}"
            },
            "llm": {"profile1": {"api_key": "${TEST_VAR}"}},
            "mcpServers": { "mcp1": {"command": "$OTHER_VAR", "args": ["--path", "${TEST_VAR}/path"]} },
            "blueprints": {}, "profiles": {}
        }
        mock_file_open.return_value.read.return_value = json.dumps(mock_data)
        bp = TestableBlueprint()
        self.assertEqual(bp.config['sub_key'], 'env_val')
        self.assertEqual(bp.config['mix_key'], 'other/data')
        self.assertEqual(bp.config['no_sub'], 'plain_value')
        self.assertEqual(bp.config['missing_var'], '${MISSING_VAR:-default_val}')
        self.assertIn('profile1', bp.llm_profiles)
        self.assertEqual(bp.llm_profiles['profile1']['api_key'], 'env_val')
        self.assertIn('mcp1', bp.mcp_server_configs)
        self.assertEqual(bp.mcp_server_configs['mcp1']['command'], 'other')
        self.assertEqual(bp.mcp_server_configs['mcp1']['args'][1], 'env_val/path')

    # --- Dotenv Tests ---
    @patch.object(blueprint_base_module, 'load_dotenv') # Patch load_dotenv where it's imported
    @patch('pathlib.Path.is_file', autospec=True) # Use autospec
    @patch('builtins.open', new_callable=mock_open)
    def test_dotenv_loading_called_when_env_exists(self, mock_file_open, mock_path_is_file, specific_mock_load_dotenv):
        """Verify load_dotenv is called when .env file exists."""
        mock_path_is_file.side_effect = [True, True] # .env exists, config exists
        mock_file_open.return_value.read.return_value = json.dumps(self.base_mock_config_data)
        bp = TestableBlueprint()
        specific_mock_load_dotenv.assert_called_once_with(dotenv_path=self.expected_dotenv_path, override=True)
        self.assertEqual(mock_path_is_file.call_count, 2)
        # Check arguments using call_args_list
        calls = mock_path_is_file.call_args_list
        self.assertEqual(len(calls), 2)
        # The first argument to the method call on the instance is the instance itself
        self.assertEqual(calls[0].args[0], self.expected_dotenv_path)
        self.assertEqual(calls[1].args[0], self.expected_default_config_path)


    @patch.object(blueprint_base_module, 'load_dotenv')
    @patch('pathlib.Path.is_file', autospec=True) # Use autospec
    @patch('builtins.open', new_callable=mock_open)
    def test_dotenv_loading_not_called_when_env_missing(self, mock_file_open, mock_path_is_file, specific_mock_load_dotenv):
        """Verify load_dotenv is NOT called when .env file is missing."""
        mock_path_is_file.side_effect = [False, True] # .env missing, config exists
        mock_file_open.return_value.read.return_value = json.dumps(self.base_mock_config_data)
        bp = TestableBlueprint()
        specific_mock_load_dotenv.assert_not_called()
        self.assertEqual(mock_path_is_file.call_count, 2)
        # Check arguments using call_args_list
        calls = mock_path_is_file.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[0], self.expected_dotenv_path)
        self.assertEqual(calls[1].args[0], self.expected_default_config_path)


    # --- Missing Config File Tests ---
    @patch('pathlib.Path.is_file', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_load_config_file_missing_warning(self, mock_file_open, mock_path_is_file):
        """Verify a warning is logged if the default config file is missing."""
        mock_path_is_file.side_effect = [False, False] # .env missing, config missing
        with self.assertLogs('swarm', level='WARNING') as cm:
            bp = TestableBlueprint()
        self.assertTrue(any("Default configuration file not found" in msg for msg in cm.output))
        self.assertEqual(bp.config, {"llm": {}, "mcpServers": {}})
        mock_file_open.assert_not_called()
        self.mock_load_dotenv.assert_not_called()
        self.assertEqual(mock_path_is_file.call_count, 2)

    @patch('pathlib.Path.is_file', autospec=True)
    def test_load_config_override_path_missing_error(self, mock_path_is_file):
        """Verify ValueError if a specific config path override is missing."""
        override_path = Path("/fake/override/config.json")
        # Arrange: .env check False, override config check False
        mock_path_is_file.side_effect = [False, False] # Assume check order: .env, override_path

        with self.assertRaises(ValueError) as ctx:
             # Instantiate with the override path that will fail the is_file check
             TestableBlueprint(config_path_override=override_path)
        # Check the exception message includes the expected parts
        self.assertIn("Configuration loading failed", str(ctx.exception))
        self.assertIn("Specified config file not found", str(ctx.exception))
        self.assertIn(str(override_path), str(ctx.exception))
        # Check is_file calls
        self.assertEqual(mock_path_is_file.call_count, 2)
        calls = mock_path_is_file.call_args_list
        self.assertEqual(calls[0].args[0], self.expected_dotenv_path)
        self.assertEqual(calls[1].args[0], override_path)


if __name__ == '__main__':
    unittest.main()
