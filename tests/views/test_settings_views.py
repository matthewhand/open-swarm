import json
import os
from unittest.mock import patch, MagicMock

import pytest
from django.test import RequestFactory

from swarm.views import settings_views


@pytest.fixture
def request_factory():
    return RequestFactory()


@patch('swarm.views.settings_views.settings_manager')
def test_settings_dashboard_success(mock_settings_manager, request_factory):
    """Test the settings_dashboard view."""
    mock_settings_manager.collect_all_settings.return_value = {
        'django': {
            'title': 'Django Framework',
            'description': 'Core Django application settings',
            'icon': '🌐',
            'settings': {
                'DEBUG': {'value': True, 'sensitive': False},
                'SECRET_KEY': {'value': '***HIDDEN***', 'sensitive': True}
            }
        }
    }
    
    request = request_factory.get('/settings/')
    response = settings_views.settings_dashboard(request)
    
    assert response.status_code == 200
    # Check that the response contains the expected context
    # (this would require a more complex check of the rendered template)


@patch('swarm.views.settings_views.settings_manager')
def test_settings_dashboard_error(mock_settings_manager, request_factory):
    """Test the settings_dashboard view when an error occurs."""
    mock_settings_manager.collect_all_settings.side_effect = Exception("Test error")
    
    request = request_factory.get('/settings/')
    response = settings_views.settings_dashboard(request)
    
    assert response.status_code == 500
    content = response.content.decode()
    assert 'Error loading settings' in content


@patch('swarm.views.settings_views.settings_manager')
def test_settings_api_success(mock_settings_manager, request_factory):
    """Test the settings_api view."""
    mock_settings_manager.collect_all_settings.return_value = {
        'django': {
            'title': 'Django Framework',
            'description': 'Core Django application settings',
            'icon': '🌐',
            'settings': {
                'DEBUG': {'value': True, 'sensitive': False},
                'SECRET_KEY': {'value': 'test-secret', 'sensitive': True}
            }
        }
    }
    
    request = request_factory.get('/api/settings/')
    response = settings_views.settings_api(request)
    
    assert response.status_code == 200
    content = json.loads(response.content.decode())
    assert content['success'] is True
    assert 'django' in content['settings']
    assert content['settings']['django']['settings']['DEBUG']['value'] is True
    assert content['settings']['django']['settings']['SECRET_KEY']['value'] == '***HIDDEN***'


@patch('swarm.views.settings_views.settings_manager')
def test_settings_api_error(mock_settings_manager, request_factory):
    """Test the settings_api view when an error occurs."""
    mock_settings_manager.collect_all_settings.side_effect = Exception("Test error")
    
    request = request_factory.get('/api/settings/')
    response = settings_views.settings_api(request)
    
    assert response.status_code == 500
    content = json.loads(response.content.decode())
    assert content['success'] is False
    assert 'error' in content


def test_environment_variables_success(request_factory):
    """Test the environment_variables view."""
    with patch.dict(os.environ, {
        'DJANGO_DEBUG': 'True',
        'SWARM_API_KEY': 'test-key',
        'OTHER_VAR': 'other-value'
    }):
        request = request_factory.get('/api/environment/')
        response = settings_views.environment_variables(request)
        
        assert response.status_code == 200
        content = json.loads(response.content.decode())
        assert content['success'] is True
        assert 'DJANGO_DEBUG' in content['environment_variables']
        assert content['environment_variables']['DJANGO_DEBUG'] == 'True'
        assert 'SWARM_API_KEY' in content['environment_variables']
        assert content['environment_variables']['SWARM_API_KEY'] == '***SET***'
        assert 'OTHER_VAR' not in content['environment_variables']


@patch('os.environ.items')
def test_environment_variables_error(mock_environ, request_factory):
    """Test the environment_variables view when an error occurs."""
    mock_environ.side_effect = Exception("Test error")
    
    request = request_factory.get('/api/environment/')
    response = settings_views.environment_variables(request)
    
    assert response.status_code == 500
    content = json.loads(response.content.decode())
    assert content['success'] is False
    assert 'error' in content