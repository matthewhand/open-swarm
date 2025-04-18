import os
import json
import tempfile
import pytest
from click.testing import CliRunner

# Assume the CLI entrypoint is swarm_cli (adjust import if different)
from swarm_cli import cli
from swarm.core import config_loader, config_manager
from swarm.core.server_config import load_server_config, save_server_config

@pytest.fixture
def temp_config_file():
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tf:
        tf.write(b'{}')
        tf.flush()
        yield tf.name
    os.unlink(tf.name)

def test_create_llm_config(temp_config_file):
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'create', '--name', 'my-llm', '--provider', 'openai', '--model', 'gpt-4', '--api-key', 'sk-xxx', '--config-path', temp_config_file
    ])
    assert result.exit_code == 0
    with open(temp_config_file) as f:
        data = json.load(f)
    assert 'llms' in data
    assert 'my-llm' in data['llms']
    assert data['llms']['my-llm']['provider'] == 'openai'
    assert data['llms']['my-llm']['model'] == 'gpt-4'
    assert data['llms']['my-llm']['api_key'] == 'sk-xxx'

def test_read_llm_config(temp_config_file):
    # Pre-populate config
    with open(temp_config_file, 'w') as f:
        json.dump({'llms': {'my-llm': {'provider': 'openai', 'model': 'gpt-4', 'api_key': 'sk-xxx'}}}, f)
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'read', '--name', 'my-llm', '--config-path', temp_config_file
    ])
    assert result.exit_code == 0
    assert 'gpt-4' in result.output
    assert 'openai' in result.output

def test_update_llm_config(temp_config_file):
    # Pre-populate config
    with open(temp_config_file, 'w') as f:
        json.dump({'llms': {'my-llm': {'provider': 'openai', 'model': 'gpt-4', 'api_key': 'sk-xxx'}}}, f)
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'update', '--name', 'my-llm', '--model', 'gpt-3.5-turbo', '--config-path', temp_config_file
    ])
    assert result.exit_code == 0
    with open(temp_config_file) as f:
        data = json.load(f)
    assert data['llms']['my-llm']['model'] == 'gpt-3.5-turbo'
    assert data['llms']['my-llm']['provider'] == 'openai'  # unchanged

def test_partial_update_llm_config(temp_config_file):
    # Pre-populate config
    with open(temp_config_file, 'w') as f:
        json.dump({'llms': {'my-llm': {'provider': 'openai', 'model': 'gpt-4', 'api_key': 'sk-xxx'}}}, f)
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'update', '--name', 'my-llm', '--api-key', 'sk-yyy', '--config-path', temp_config_file
    ])
    assert result.exit_code == 0
    with open(temp_config_file) as f:
        data = json.load(f)
    assert data['llms']['my-llm']['api_key'] == 'sk-yyy'
    assert data['llms']['my-llm']['model'] == 'gpt-4'  # unchanged

def test_delete_llm_config(temp_config_file):
    # Pre-populate config
    with open(temp_config_file, 'w') as f:
        json.dump({'llms': {'my-llm': {'provider': 'openai', 'model': 'gpt-4', 'api_key': 'sk-xxx'}}}, f)
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'delete', '--name', 'my-llm', '--config-path', temp_config_file
    ])
    assert result.exit_code == 0
    with open(temp_config_file) as f:
        data = json.load(f)
    assert 'my-llm' not in data.get('llms', {})

def test_invalid_config_handling(temp_config_file):
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'read', '--name', 'nonexistent', '--config-path', temp_config_file
    ])
    assert result.exit_code != 0
    assert 'not found' in result.output.lower()

def test_config_list_all(temp_config_file):
    # Pre-populate config
    with open(temp_config_file, 'w') as f:
        json.dump({'llms': {
            'llm1': {'provider': 'openai', 'model': 'gpt-4', 'api_key': 'sk-xxx'},
            'llm2': {'provider': 'litellm', 'model': 'qwen', 'base_url': 'http://localhost:4000'}
        }}, f)
    runner = CliRunner()
    result = runner.invoke(cli, [
        'config', 'llm', 'list', '--config-path', temp_config_file
    ])
    assert result.exit_code == 0
    assert 'llm1' in result.output
    assert 'llm2' in result.output
