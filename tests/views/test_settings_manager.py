from unittest.mock import patch

import pytest
from django.conf import settings

from swarm.views.settings_manager import SettingsManager, load_config


@pytest.fixture
def settings_manager():
    return SettingsManager()


def test_settings_manager_initialization(settings_manager):
    assert 'django' in settings_manager.settings_groups
    assert 'swarm_core' in settings_manager.settings_groups
    assert 'authentication' in settings_manager.settings_groups
    assert 'llm_providers' in settings_manager.settings_groups
    assert 'blueprints' in settings_manager.settings_groups
    assert 'mcp_servers' in settings_manager.settings_groups
    assert 'database' in settings_manager.settings_groups
    assert 'logging' in settings_manager.settings_groups
    assert 'performance' in settings_manager.settings_groups
    assert 'ui_features' in settings_manager.settings_groups


def test_collect_django_settings(settings_manager, mock_load_config):
    with patch.object(settings, 'DEBUG', True), \
         patch.object(settings, 'SECRET_KEY', 'test-secret-key'), \
         patch.object(settings, 'ALLOWED_HOSTS', ['localhost', '127.0.0.1']), \
         patch.object(settings, 'TIME_ZONE', 'UTC'), \
         patch.object(settings, 'LANGUAGE_CODE', 'en-us'):

        settings_manager._collect_django_settings()

        django_settings = settings_manager.settings_groups['django']['settings']
        assert django_settings['DEBUG']['value'] is True
        assert django_settings['SECRET_KEY']['value'] == '***HIDDEN***'
        assert django_settings['ALLOWED_HOSTS']['value'] == ['localhost', '127.0.0.1']
        assert django_settings['TIME_ZONE']['value'] == 'UTC'
        assert django_settings['LANGUAGE_CODE']['value'] == 'en-us'


def test_collect_swarm_core_settings(settings_manager, mock_load_config):
    with patch.object(settings, 'SWARM_CONFIG_PATH', '/test/config.json'), \
         patch.object(settings, 'BLUEPRINT_DIRECTORY', '/test/blueprints'), \
         patch.object(settings, 'BASE_DIR', '/test/base'):

        settings_manager._collect_swarm_core_settings()

        swarm_settings = settings_manager.settings_groups['swarm_core']['settings']
        assert swarm_settings['SWARM_CONFIG_PATH']['value'] == '/test/config.json'
        assert swarm_settings['BLUEPRINT_DIRECTORY']['value'] == '/test/blueprints'
        assert swarm_settings['BASE_DIR']['value'] == '/test/base'


def test_collect_auth_settings(settings_manager, mock_load_config):
    with patch.object(settings, 'ENABLE_API_AUTH', True), \
         patch.object(settings, 'SWARM_API_KEY', 'test-api-key'), \
         patch.object(settings, 'LOGIN_URL', '/login/'), \
         patch('swarm.views.settings_manager.get_django_csrf_trusted_origins', return_value=['http://localhost:8000']):

        settings_manager._collect_auth_settings()

        auth_settings = settings_manager.settings_groups['authentication']['settings']
        assert auth_settings['ENABLE_API_AUTH']['value'] is True
        assert auth_settings['SWARM_API_KEY']['value'] == '***SET***'
        assert auth_settings['CSRF_TRUSTED_ORIGINS']['value'] == ['http://localhost:8000']
        assert auth_settings['LOGIN_URL']['value'] == '/login/'


def test_collect_llm_settings(settings_manager, mock_load_config):
    mock_load_config.return_value = {
        'llm': {
            'openai': {'api_key': 'test-openai-key', 'model': 'gpt-4'},
            'anthropic': {'api_key': 'test-anthropic-key'}
        },
        'profiles': {
            'default': {'provider': 'openai', 'model': 'gpt-4'}
        }
    }

    with patch('swarm.views.settings_manager.get_openai_api_key', return_value='test-openai-key'), \
         patch('swarm.views.settings_manager.get_anthropic_api_key', return_value='test-anthropic-key'), \
         patch('swarm.views.settings_manager.get_ollama_base_url', return_value='http://localhost:11434'):

        settings_manager._collect_llm_settings()

        llm_settings = settings_manager.settings_groups['llm_providers']['settings']
        assert 'LLM_OPENAI' in llm_settings
        assert 'LLM_ANTHROPIC' in llm_settings
        assert 'PROFILE_DEFAULT' in llm_settings
        assert llm_settings['OPENAI_API_KEY']['value'] == '***SET***'
        assert llm_settings['ANTHROPIC_API_KEY']['value'] == '***SET***'
        assert llm_settings['OLLAMA_BASE_URL']['value'] == 'http://localhost:11434'


def test_collect_llm_settings_error(settings_manager, mock_load_config):
    mock_load_config.side_effect = Exception("Test error")

    settings_manager._collect_llm_settings()

    llm_settings = settings_manager.settings_groups['llm_providers']['settings']
    assert 'CONFIG_ERROR' in llm_settings
    assert 'Error loading LLM config' in llm_settings['CONFIG_ERROR']['value']


def test_collect_blueprint_settings(settings_manager, mock_load_config):
    mock_load_config.return_value = {
        'blueprints': {
            'defaults': {'timeout': 30},
            'enabled': ['blueprint1', 'blueprint2']
        }
    }

    with patch('swarm.views.settings_manager.get_swarm_debug', return_value='1'), \
         patch('swarm.views.settings_manager.get_swarm_command_timeout', return_value=60):

        settings_manager._collect_blueprint_settings()

        blueprint_settings = settings_manager.settings_groups['blueprints']['settings']
        assert blueprint_settings['BLUEPRINT_DEFAULTS']['value'] == {'timeout': 30}
        assert blueprint_settings['ENABLED_BLUEPRINTS']['value'] == ['blueprint1', 'blueprint2']
        assert blueprint_settings['SWARM_DEBUG']['value'] == '1'
        assert blueprint_settings['SWARM_COMMAND_TIMEOUT']['value'] == '60'


def test_collect_mcp_settings(settings_manager, mock_load_config):
    mock_load_config.return_value = {
        'mcpServers': {
            'server1': {'command': 'python', 'args': ['-m', 'server1']},
            'server2': {'command': 'node', 'args': ['server2.js']}
        }
    }

    settings_manager._collect_mcp_settings()

    mcp_settings = settings_manager.settings_groups['mcp_servers']['settings']
    assert 'MCP_SERVER1' in mcp_settings
    assert 'MCP_SERVER2' in mcp_settings
    assert mcp_settings['MCP_SERVER1']['value'] == {'command': 'python', 'args': ['-m', 'server1']}


def test_collect_mcp_settings_no_servers(settings_manager, mock_load_config):
    mock_load_config.return_value = {}

    settings_manager._collect_mcp_settings()

    mcp_settings = settings_manager.settings_groups['mcp_servers']['settings']
    assert 'NO_MCP_SERVERS' in mcp_settings
    assert mcp_settings['NO_MCP_SERVERS']['value'] == 'No MCP servers configured'


def test_collect_database_settings(settings_manager, mock_load_config):
    with patch.object(settings, 'DATABASES', {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
            'TEST': {'NAME': 'test_db.sqlite3'}
        }
    }):

        settings_manager._collect_database_settings()

        database_settings = settings_manager.settings_groups['database']['settings']
        assert database_settings['ENGINE']['value'] == 'django.db.backends.sqlite3'
        assert database_settings['NAME']['value'] == 'db.sqlite3'
        assert database_settings['TEST_NAME']['value'] == 'test_db.sqlite3'


def test_collect_logging_settings(settings_manager, mock_load_config):
    with patch('swarm.views.settings_manager.get_django_log_level', return_value='INFO'), \
         patch('swarm.views.settings_manager.get_swarm_log_level', return_value='DEBUG'), \
         patch('swarm.views.settings_manager.get_log_level', return_value='WARNING'), \
         patch('swarm.views.settings_manager.get_loglevel', return_value='ERROR'):

        settings_manager._collect_logging_settings()

        logging_settings = settings_manager.settings_groups['logging']['settings']
        assert logging_settings['DJANGO_LOG_LEVEL']['value'] == 'INFO'
        assert logging_settings['SWARM_LOG_LEVEL']['value'] == 'DEBUG'
        assert logging_settings['LOG_LEVEL']['value'] == 'WARNING'
        assert logging_settings['LOGLEVEL']['value'] == 'ERROR'


def test_collect_performance_settings(settings_manager, mock_load_config):
    with patch.object(settings, 'REDIS_HOST', 'redis.example.com'), \
         patch.object(settings, 'REDIS_PORT', 6380), \
         patch('swarm.views.settings_manager.get_swarm_command_timeout', return_value=120):

        settings_manager._collect_performance_settings()

        performance_settings = settings_manager.settings_groups['performance']['settings']
        assert performance_settings['REDIS_HOST']['value'] == 'redis.example.com'
        assert performance_settings['REDIS_PORT']['value'] == 6380
        assert performance_settings['SWARM_COMMAND_TIMEOUT']['value'] == '120'


def test_collect_ui_settings(settings_manager, mock_load_config):
    with patch('swarm.views.settings_manager.is_enable_webui', return_value=True), \
         patch('swarm.views.settings_manager.is_enable_admin', return_value=False):

        settings_manager._collect_ui_settings()

        ui_settings = settings_manager.settings_groups['ui_features']['settings']
        assert ui_settings['ENABLE_WEBUI']['value'] == 'true'
        assert ui_settings['ENABLE_ADMIN']['value'] == 'false'


def test_collect_all_settings(settings_manager, mock_load_config):
    mock_load_config.return_value = {}

    patches = [
        patch.object(settings, 'DEBUG', True),
        patch.object(settings, 'SECRET_KEY', 'test-secret-key'),
        patch.object(settings, 'ALLOWED_HOSTS', ['localhost']),
        patch.object(settings, 'TIME_ZONE', 'UTC'),
        patch.object(settings, 'LANGUAGE_CODE', 'en-us'),
        patch.object(settings, 'SWARM_CONFIG_PATH', '/test/config.json'),
        patch.object(settings, 'BLUEPRINT_DIRECTORY', '/test/blueprints'),
        patch.object(settings, 'BASE_DIR', '/test/base'),
        patch.object(settings, 'ENABLE_API_AUTH', True),
        patch.object(settings, 'SWARM_API_KEY', 'test-api-key'),
        patch.object(settings, 'LOGIN_URL', '/login/'),
        patch.object(
            settings, 'DATABASES',
            {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'db.sqlite3'}}
        ),
        patch.object(settings, 'REDIS_HOST', 'localhost'),
        patch.object(settings, 'REDIS_PORT', 6379),
        patch(
            'swarm.views.settings_manager.get_django_csrf_trusted_origins',
            return_value=['http://localhost:8000']
        ),
        patch(
            'swarm.views.settings_manager.get_openai_api_key',
            return_value='test-openai-key'
        ),
        patch('swarm.views.settings_manager.get_anthropic_api_key', return_value='test-anthropic-key'),
        patch('swarm.views.settings_manager.get_ollama_base_url', return_value='http://localhost:11434'),
        patch('swarm.views.settings_manager.get_swarm_debug', return_value='1'),
        patch(
            'swarm.views.settings_manager.get_swarm_command_timeout',
            return_value=60
        ),
        patch('swarm.views.settings_manager.get_django_log_level', return_value='INFO'),
        patch('swarm.views.settings_manager.get_swarm_log_level', return_value='DEBUG'),
        patch('swarm.views.settings_manager.get_log_level', return_value='WARNING'),
        patch('swarm.views.settings_manager.get_loglevel', return_value='ERROR'),
        patch('swarm.views.settings_manager.is_enable_webui', return_value=True),
        patch('swarm.views.settings_manager.is_enable_admin', return_value=False),
    ]

    with patch.multiple(settings, **{
        'DEBUG': True,
        'SECRET_KEY': 'test-secret-key',
        'ALLOWED_HOSTS': ['localhost'],
        'TIME_ZONE': 'UTC',
        'LANGUAGE_CODE': 'en-us',
        'SWARM_CONFIG_PATH': '/test/config.json',
        'BLUEPRINT_DIRECTORY': '/test/blueprints',
        'BASE_DIR': '/test/base',
        'ENABLE_API_AUTH': True,
        'SWARM_API_KEY': 'test-api-key',
        'LOGIN_URL': '/login/',
        'DATABASES': {
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'db.sqlite3'}
        },
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': 6379,
    }), \
         patch(
             'swarm.views.settings_manager.get_django_csrf_trusted_origins',
             return_value=['http://localhost:8000']
         ), \
         patch(
             'swarm.views.settings_manager.get_openai_api_key',
             return_value='test-openai-key'
         ), \
         patch(
             'swarm.views.settings_manager.get_anthropic_api_key',
             return_value='test-anthropic-key'
         ), \
         patch(
             'swarm.views.settings_manager.get_ollama_base_url',
             return_value='http://localhost:11434'
         ), \
         patch('swarm.views.settings_manager.get_swarm_debug', return_value='1'), \
         patch(
             'swarm.views.settings_manager.get_swarm_command_timeout',
             return_value=60
         ), \
         patch(
             'swarm.views.settings_manager.get_django_log_level',
             return_value='INFO'
         ), \
         patch(
             'swarm.views.settings_manager.get_swarm_log_level',
             return_value='DEBUG'
         ), \
         patch('swarm.views.settings_manager.get_log_level', return_value='WARNING'), \
         patch('swarm.views.settings_manager.get_loglevel', return_value='ERROR'), \
         patch('swarm.views.settings_manager.is_enable_webui', return_value=True), \
         patch('swarm.views.settings_manager.is_enable_admin', return_value=False):

        all_settings = settings_manager.collect_all_settings()

        assert 'django' in all_settings
        assert 'swarm_core' in all_settings
        assert 'authentication' in all_settings
        assert 'llm_providers' in all_settings
        assert 'blueprints' in all_settings
        assert 'mcp_servers' in all_settings
        assert 'database' in all_settings
        assert 'logging' in all_settings
        assert 'performance' in all_settings
        assert 'ui_features' in all_settings


@patch('swarm.views.settings_manager._find_config_file')
@patch('swarm.views.settings_manager._load_config')
def test_load_config_success(mock_load_config, mock_find_config_file):
    mock_find_config_file.return_value = '/test/config.json'
    mock_load_config.return_value = {'key': 'value'}

    result = load_config()

    assert result == {'key': 'value'}
    mock_find_config_file.assert_called_once()
    mock_load_config.assert_called_once_with('/test/config.json')


@patch('swarm.views.settings_manager._find_config_file')
def test_load_config_no_file(mock_find_config_file):
    mock_find_config_file.return_value = None

    result = load_config()

    assert result == {}
    mock_find_config_file.assert_called_once()


@patch('swarm.views.settings_manager._find_config_file')
@patch('swarm.views.settings_manager._load_config')
def test_load_config_exception(mock_load_config, mock_find_config_file):
    mock_find_config_file.return_value = '/test/config.json'
    mock_load_config.side_effect = Exception("Test error")

    result = load_config()

    assert result == {}
    mock_find_config_file.assert_called_once()
    mock_load_config.assert_called_once_with('/test/config.json')


@patch('swarm.views.settings_manager._find_config_file', None)
@patch('swarm.views.settings_manager._load_config', None)
def test_load_config_no_import():
    result = load_config()

    assert result == {}
