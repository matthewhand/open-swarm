import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from swarm.views import web_views


@pytest.fixture
def request_factory():
    return RequestFactory()


def test_serve_swarm_config_file_found(request_factory):
    """Test serving swarm config when the file exists and is valid JSON."""
    mock_config_data = {"llm": {"default": {"provider": "openai"}}, "mcpServers": {}}
    config_path = Path("/fake/base/swarm_config.json")

    with patch('swarm.views.web_views.settings.BASE_DIR', "/fake/base"), \
         patch('pathlib.Path.read_text', return_value=json.dumps(mock_config_data)), \
         patch('pathlib.Path.exists', return_value=True):

        request = request_factory.get('/config/')
        response = web_views.serve_swarm_config(request)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 200
        # Parse the response content to check the data
        content = json.loads(response.content.decode())
        assert content == mock_config_data


def test_serve_swarm_config_file_not_found(request_factory):
    """Test serving swarm config when the file doesn't exist."""
    with patch('swarm.views.web_views.settings.BASE_DIR', "/fake/base"), \
         patch('pathlib.Path.exists', return_value=False):

        request = request_factory.get('/config/')
        response = web_views.serve_swarm_config(request)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 404
        content = json.loads(response.content.decode())
        assert content == web_views.DEFAULT_CONFIG


def test_serve_swarm_config_invalid_json(request_factory):
    """Test serving swarm config when the file contains invalid JSON."""
    with patch('swarm.views.web_views.settings.BASE_DIR', "/fake/base"), \
         patch('pathlib.Path.read_text', return_value="{invalid json"), \
         patch('pathlib.Path.exists', return_value=True):

        request = request_factory.get('/config/')
        response = web_views.serve_swarm_config(request)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 500
        content = json.loads(response.content.decode())
        assert "error" in content
        assert "Invalid JSON format" in content["error"]


def test_serve_swarm_config_unexpected_error(request_factory):
    """Test serving swarm config when an unexpected error occurs."""
    with patch('swarm.views.web_views.settings.BASE_DIR', "/fake/base"), \
         patch('pathlib.Path.read_text', side_effect=Exception("Unexpected error")), \
         patch('pathlib.Path.exists', return_value=True):

        request = request_factory.get('/config/')
        response = web_views.serve_swarm_config(request)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 500
        content = json.loads(response.content.decode())
        assert "error" in content
        assert "unexpected error" in content["error"].lower()


def test_webui_enabled():
    """Test the _webui_enabled helper function."""
    with patch('swarm.views.web_views.is_enable_webui', return_value=True):
        assert web_views._webui_enabled() is True

    with patch('swarm.views.web_views.is_enable_webui', return_value=False):
        assert web_views._webui_enabled() is False


@patch('swarm.views.web_views._webui_enabled', return_value=True)
def test_team_launcher_webui_enabled(mock_webui_enabled, request_factory):
    """Test team launcher when web UI is enabled."""
    request = request_factory.get('/teams/launcher/')
    response = web_views.team_launcher(request)

    assert response.status_code == 200
    # Check that the response contains the expected template


@patch('swarm.views.web_views._webui_enabled', return_value=False)
def test_team_launcher_webui_disabled(mock_webui_enabled, request_factory):
    """Test team launcher when web UI is disabled."""
    request = request_factory.get('/teams/launcher/')
    response = web_views.team_launcher(request)

    assert response.status_code == 404
    content = response.content.decode()
    assert "Web UI disabled" in content


@patch('swarm.views.web_views._webui_enabled', return_value=True)
def test_team_admin_webui_enabled(mock_webui_enabled, request_factory):
    """Test team admin when web UI is enabled."""
    request = request_factory.get('/teams/admin/')
    response = web_views.team_admin(request)

    assert response.status_code == 200
    # Check that the response contains the expected template


@patch('swarm.views.web_views._webui_enabled', return_value=False)
def test_team_admin_webui_disabled(mock_webui_enabled, request_factory):
    """Test team admin when web UI is disabled."""
    request = request_factory.get('/teams/admin/')
    response = web_views.team_admin(request)

    assert response.status_code == 404
    content = response.content.decode()
    assert "Web UI disabled" in content


@patch('swarm.views.web_views._webui_enabled', return_value=True)
def test_teams_export_json(mock_webui_enabled, request_factory):
    """Test teams export in JSON format."""
    with patch(
        'swarm.views.web_views.load_dynamic_registry',
        return_value={'team1': {'description': 'Test team'}}
    ):
        request = request_factory.get('/teams/export/')
        response = web_views.teams_export(request)

        assert response.status_code == 200
        content_type = response.get('Content-Type')
        if content_type:
            assert 'application/json' in content_type
        content = json.loads(response.content.decode())
        assert content == {'team1': {'description': 'Test team'}}


@patch('swarm.views.web_views._webui_enabled', return_value=True)
def test_teams_export_csv(mock_webui_enabled, request_factory):
    """Test teams export in CSV format."""
    with patch(
        'swarm.views.web_views.load_dynamic_registry',
        return_value={'team1': {'description': 'Test team', 'llm_profile': 'gpt-4'}}
    ):
        request = request_factory.get('/teams/export/?format=csv')
        response = web_views.teams_export(request)

        assert response.status_code == 200
        content_type = response.get('Content-Type')
        if content_type:
            assert 'text/csv' in content_type
        disposition = response.get('Content-Disposition')
        if disposition:
            assert 'attachment; filename=teams.csv' in disposition
        content = response.content.decode()
        assert 'id,llm_profile,description' in content
        assert 'team1,gpt-4,Test team' in content
