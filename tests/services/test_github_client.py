
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before importing the module under test
sys.modules['django'] = MagicMock()
sys.modules['django.db'] = MagicMock()
sys.modules['httpx'] = MagicMock()

# Mock models
mock_models = MagicMock()
sys.modules['swarm.models.core_models'] = mock_models

# Mock settings
mock_settings = MagicMock()
mock_settings.GITHUB_MARKETPLACE_ORG_ALLOWLIST = []
mock_settings.GITHUB_MARKETPLACE_TOPICS = []
mock_settings.GITHUB_TOKEN = "fake-token"
sys.modules['swarm.settings'] = mock_settings

import pytest
from swarm.services.github_client import create_blueprint_from_manifest, create_mcp_config_from_manifest

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_models.Blueprint.objects.reset_mock()
    mock_models.Blueprint.objects.filter.return_value.exists.side_effect = None
    mock_models.Blueprint.objects.filter.return_value.exists.return_value = False

    mock_models.MCPConfig.objects.reset_mock()
    mock_models.MCPConfig.objects.filter.return_value.exists.side_effect = None
    mock_models.MCPConfig.objects.filter.return_value.exists.return_value = False
    yield

class TestCreateBlueprintFromManifest:
    """Tests for create_blueprint_from_manifest function."""

    def test_create_blueprint_from_manifest_basic(self):
        """Test successful blueprint creation with standard manifest data."""
        manifest_data = {
            'name': 'Test Blueprint',
            'description': 'A test description',
            'version': '1.2.3',
            'tags': ['tag1', 'tag2'],
            'category': 'test_category',
            'code_template': 'print("hello")',
            'required_mcp_servers': ['server1']
        }
        source_repo = {'html_url': 'https://github.com/test/repo'}

        mock_models.Blueprint.objects.create.return_value = MagicMock()

        create_blueprint_from_manifest(manifest_data, source_repo)

        mock_models.Blueprint.objects.create.assert_called_once()
        call_args = mock_models.Blueprint.objects.create.call_args[1]

        assert call_args['name'] == 'test_blueprint'
        assert call_args['title'] == 'Test Blueprint'
        assert call_args['description'] == 'A test description'
        assert call_args['version'] == '1.2.3'
        assert call_args['tags'] == 'tag1,tag2'
        assert call_args['repository_url'] == 'https://github.com/test/repo'
        assert call_args['category'] == 'test_category'
        assert call_args['code_template'] == 'print("hello")'
        assert call_args['required_mcp_servers'] == ['server1']

    def test_create_blueprint_from_manifest_name_normalization(self):
        """Ensure names are correctly formatted (lowercase, underscores)."""
        manifest_data = {'name': 'My Awesome Blueprint'}

        create_blueprint_from_manifest(manifest_data)

        call_args = mock_models.Blueprint.objects.create.call_args[1]
        assert call_args['name'] == 'my_awesome_blueprint'

    def test_create_blueprint_from_manifest_collision_handling(self):
        """Verify unique name generation when a blueprint with the same name already exists."""
        manifest_data = {'name': 'Collision'}

        # Mock exists() to return True first time, then False
        mock_models.Blueprint.objects.filter.return_value.exists.side_effect = [True, False]

        create_blueprint_from_manifest(manifest_data)

        # It should check for 'collision' then 'collision_1'
        assert mock_models.Blueprint.objects.filter.call_count == 2
        mock_models.Blueprint.objects.filter.assert_any_call(name='collision')
        mock_models.Blueprint.objects.filter.assert_any_call(name='collision_1')

        call_args = mock_models.Blueprint.objects.create.call_args[1]
        assert call_args['name'] == 'collision_1'

    def test_create_blueprint_from_manifest_multiple_collisions(self):
        """Verify that counter increments correctly across multiple collisions."""
        manifest_data = {'name': 'Heavy Collision'}

        # Mock exists() to return True three times, then False
        # collision, heavy_collision_1, heavy_collision_2 -> exist
        # heavy_collision_3 -> doesn't exist
        mock_models.Blueprint.objects.filter.return_value.exists.side_effect = [True, True, True, False]

        create_blueprint_from_manifest(manifest_data)

        assert mock_models.Blueprint.objects.filter.call_count == 4
        mock_models.Blueprint.objects.filter.assert_any_call(name='heavy_collision')
        mock_models.Blueprint.objects.filter.assert_any_call(name='heavy_collision_1')
        mock_models.Blueprint.objects.filter.assert_any_call(name='heavy_collision_2')
        mock_models.Blueprint.objects.filter.assert_any_call(name='heavy_collision_3')

        call_args = mock_models.Blueprint.objects.create.call_args[1]
        assert call_args['name'] == 'heavy_collision_3'

    def test_create_blueprint_from_manifest_fallback_name(self):
        """Check timestamp-based name generation when no name is provided."""
        manifest_data = {} # No name

        with patch('time.time', return_value=123456789):
            create_blueprint_from_manifest(manifest_data)

        call_args = mock_models.Blueprint.objects.create.call_args[1]
        assert call_args['name'] == 'blueprint_123456789'

class TestCreateMCPConfigFromManifest:
    """Tests for create_mcp_config_from_manifest function."""

    def test_create_mcp_config_from_manifest_basic(self):
        """Test successful MCP config creation with standard manifest data."""
        manifest_data = {
            'name': 'Test MCP',
            'description': 'A test MCP description',
            'version': '0.1.0',
            'tags': ['mcp', 'test'],
            'config_template': '{}',
            'server_name': 'test-server'
        }
        source_repo = {'html_url': 'https://github.com/test/mcp-repo'}

        mock_models.MCPConfig.objects.create.return_value = MagicMock()

        create_mcp_config_from_manifest(manifest_data, source_repo)

        mock_models.MCPConfig.objects.create.assert_called_once()
        call_args = mock_models.MCPConfig.objects.create.call_args[1]

        assert call_args['name'] == 'test_mcp'
        assert call_args['title'] == 'Test MCP'
        assert call_args['description'] == 'A test MCP description'
        assert call_args['version'] == '0.1.0'
        assert call_args['tags'] == 'mcp,test'
        assert call_args['repository_url'] == 'https://github.com/test/mcp-repo'
        assert call_args['config_template'] == '{}'
        assert call_args['server_name'] == 'test-server'

    def test_create_mcp_config_from_manifest_name_normalization(self):
        """Ensure names are correctly formatted (lowercase, underscores)."""
        manifest_data = {'name': 'My Awesome MCP'}

        create_mcp_config_from_manifest(manifest_data)

        call_args = mock_models.MCPConfig.objects.create.call_args[1]
        assert call_args['name'] == 'my_awesome_mcp'

    def test_create_mcp_config_from_manifest_collision_handling(self):
        """Verify unique name generation when an MCP config with the same name already exists."""
        manifest_data = {'name': 'Collision'}

        # Mock exists() to return True first time, then False
        mock_models.MCPConfig.objects.filter.return_value.exists.side_effect = [True, False]

        create_mcp_config_from_manifest(manifest_data)

        # It should check for 'collision' then 'collision_1'
        assert mock_models.MCPConfig.objects.filter.call_count == 2
        mock_models.MCPConfig.objects.filter.assert_any_call(name='collision')
        mock_models.MCPConfig.objects.filter.assert_any_call(name='collision_1')

        call_args = mock_models.MCPConfig.objects.create.call_args[1]
        assert call_args['name'] == 'collision_1'

    def test_create_mcp_config_from_manifest_fallback_name(self):
        """Check timestamp-based name generation when no name is provided."""
        manifest_data = {} # No name

        with patch('time.time', return_value=987654321):
            create_mcp_config_from_manifest(manifest_data)

        call_args = mock_models.MCPConfig.objects.create.call_args[1]
        assert call_args['name'] == 'mcp_config_987654321'
