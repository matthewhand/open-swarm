"""
Comprehensive tests for Settings Dashboard functionality
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from src.swarm.views.settings_views import (
    SettingsManager, settings_manager, 
    settings_dashboard, settings_api, environment_variables
)


class TestSettingsManager(TestCase):
    """Test the SettingsManager class functionality"""
    
    def setUp(self):
        self.settings_manager = SettingsManager()
    
    def test_settings_manager_initialization(self):
        """Test SettingsManager initializes with correct groups"""
        expected_groups = [
            'django', 'swarm_core', 'authentication', 'llm_providers',
            'blueprints', 'mcp_servers', 'database', 'logging', 
            'performance', 'ui_features'
        ]
        
        for group in expected_groups:
            self.assertIn(group, self.settings_manager.settings_groups)
            self.assertIn('title', self.settings_manager.settings_groups[group])
            self.assertIn('description', self.settings_manager.settings_groups[group])
            self.assertIn('icon', self.settings_manager.settings_groups[group])
            self.assertIn('settings', self.settings_manager.settings_groups[group])
    
    def test_collect_django_settings(self):
        """Test Django settings collection"""
        self.settings_manager._collect_django_settings()
        django_settings = self.settings_manager.settings_groups['django']['settings']
        
        # Check for expected Django settings
        expected_settings = ['DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'TIME_ZONE', 'LANGUAGE_CODE']
        for setting in expected_settings:
            self.assertIn(setting, django_settings)
            self.assertIn('value', django_settings[setting])
            self.assertIn('type', django_settings[setting])
            self.assertIn('description', django_settings[setting])
            self.assertIn('sensitive', django_settings[setting])
        
        # Verify sensitive data is marked correctly
        self.assertTrue(django_settings['SECRET_KEY']['sensitive'])
        self.assertFalse(django_settings['DEBUG']['sensitive'])
    
    def test_collect_swarm_core_settings(self):
        """Test Swarm core settings collection"""
        self.settings_manager._collect_swarm_core_settings()
        swarm_settings = self.settings_manager.settings_groups['swarm_core']['settings']
        
        expected_settings = ['SWARM_CONFIG_PATH', 'BLUEPRINT_DIRECTORY', 'BASE_DIR']
        for setting in expected_settings:
            self.assertIn(setting, swarm_settings)
            self.assertEqual(swarm_settings[setting]['type'], 'path')
    
    def test_collect_auth_settings(self):
        """Test authentication settings collection"""
        self.settings_manager._collect_auth_settings()
        auth_settings = self.settings_manager.settings_groups['authentication']['settings']
        
        expected_settings = ['ENABLE_API_AUTH', 'SWARM_API_KEY', 'CSRF_TRUSTED_ORIGINS', 'LOGIN_URL']
        for setting in expected_settings:
            self.assertIn(setting, auth_settings)
        
        # Verify sensitive settings are marked
        self.assertTrue(auth_settings['SWARM_API_KEY']['sensitive'])
        self.assertFalse(auth_settings['ENABLE_API_AUTH']['sensitive'])
    
    @patch('src.swarm.views.settings_views.load_config')
    def test_collect_llm_settings_success(self, mock_load_config):
        """Test LLM settings collection with valid config"""
        mock_config = {
            'llm': {
                'openai': {
                    'provider': 'openai',
                    'api_key': 'sk-test123',
                    'model': 'gpt-4'
                }
            },
            'profiles': {
                'default': {
                    'llm': 'gpt-4',
                    'temperature': 0.7
                }
            }
        }
        mock_load_config.return_value = mock_config
        
        self.settings_manager._collect_llm_settings()
        llm_settings = self.settings_manager.settings_groups['llm_providers']['settings']
        
        # Should have LLM provider settings
        self.assertIn('LLM_OPENAI', llm_settings)
        self.assertIn('PROFILE_DEFAULT', llm_settings)
        
        # Should have environment variable settings
        self.assertIn('OPENAI_API_KEY', llm_settings)
        self.assertIn('ANTHROPIC_API_KEY', llm_settings)
        self.assertIn('OLLAMA_BASE_URL', llm_settings)
    
    @patch('src.swarm.views.settings_views.load_config')
    def test_collect_llm_settings_error(self, mock_load_config):
        """Test LLM settings collection with config error"""
        mock_load_config.side_effect = Exception("Config load failed")
        
        self.settings_manager._collect_llm_settings()
        llm_settings = self.settings_manager.settings_groups['llm_providers']['settings']
        
        # Should have error setting
        self.assertIn('CONFIG_ERROR', llm_settings)
        self.assertEqual(llm_settings['CONFIG_ERROR']['type'], 'error')
    
    def test_collect_database_settings(self):
        """Test database settings collection"""
        self.settings_manager._collect_database_settings()
        db_settings = self.settings_manager.settings_groups['database']['settings']
        
        expected_settings = ['ENGINE', 'NAME', 'TEST_NAME']
        for setting in expected_settings:
            self.assertIn(setting, db_settings)
    
    def test_collect_logging_settings(self):
        """Test logging settings collection"""
        self.settings_manager._collect_logging_settings()
        logging_settings = self.settings_manager.settings_groups['logging']['settings']
        
        expected_settings = ['DJANGO_LOG_LEVEL', 'SWARM_LOG_LEVEL', 'LOG_LEVEL', 'LOGLEVEL']
        for setting in expected_settings:
            self.assertIn(setting, logging_settings)
            self.assertEqual(logging_settings[setting]['category'], 'level')
    
    def test_collect_performance_settings(self):
        """Test performance settings collection"""
        self.settings_manager._collect_performance_settings()
        perf_settings = self.settings_manager.settings_groups['performance']['settings']
        
        expected_settings = ['REDIS_HOST', 'REDIS_PORT', 'SWARM_COMMAND_TIMEOUT']
        for setting in expected_settings:
            self.assertIn(setting, perf_settings)
    
    def test_collect_ui_settings(self):
        """Test UI settings collection"""
        self.settings_manager._collect_ui_settings()
        ui_settings = self.settings_manager.settings_groups['ui_features']['settings']
        
        expected_settings = ['ENABLE_WEBUI', 'ENABLE_ADMIN']
        for setting in expected_settings:
            self.assertIn(setting, ui_settings)
            self.assertEqual(ui_settings[setting]['type'], 'boolean')
    
    def test_collect_all_settings(self):
        """Test collecting all settings at once"""
        all_settings = self.settings_manager.collect_all_settings()
        
        # Should return all groups
        expected_groups = [
            'django', 'swarm_core', 'authentication', 'llm_providers',
            'blueprints', 'mcp_servers', 'database', 'logging', 
            'performance', 'ui_features'
        ]
        
        for group in expected_groups:
            self.assertIn(group, all_settings)
            self.assertIn('settings', all_settings[group])
            self.assertIsInstance(all_settings[group]['settings'], dict)


@pytest.mark.django_db
class TestSettingsDashboardViews(TestCase):
    """Test the Settings Dashboard web views"""
    
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_settings_dashboard_get(self):
        """Test GET request to settings dashboard"""
        response = self.client.get('/settings/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings Dashboard')
        self.assertContains(response, 'settings_groups')
        self.assertContains(response, 'stats')
    
    def test_settings_dashboard_context(self):
        """Test context data in settings dashboard"""
        response = self.client.get('/settings/')
        
        context = response.context
        self.assertIn('page_title', context)
        self.assertIn('settings_groups', context)
        self.assertIn('stats', context)
        
        stats = context['stats']
        self.assertIn('total', stats)
        self.assertIn('configured', stats)
        self.assertIn('sensitive', stats)
        self.assertIn('completion_rate', stats)
        
        # Stats should be reasonable
        self.assertGreaterEqual(stats['total'], 0)
        self.assertGreaterEqual(stats['configured'], 0)
        self.assertGreaterEqual(stats['completion_rate'], 0)
        self.assertLessEqual(stats['completion_rate'], 100)
    
    @patch('src.swarm.views.settings_views.settings_manager')
    def test_settings_dashboard_error_handling(self, mock_manager):
        """Test settings dashboard handles errors gracefully"""
        mock_manager.collect_all_settings.side_effect = Exception("Collection failed")
        
        response = self.client.get('/settings/')
        
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error loading settings", response.content)
    
    def test_settings_api_get(self):
        """Test GET request to settings API"""
        response = self.client.get('/settings/api/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('success', data)
        self.assertIn('settings', data)
        self.assertTrue(data['success'])
    
    def test_settings_api_sensitive_data_filtering(self):
        """Test that settings API filters sensitive data"""
        response = self.client.get('/settings/api/')
        data = json.loads(response.content)
        
        # Check that sensitive values are hidden
        settings = data['settings']
        for group_name, group_data in settings.items():
            for setting_name, setting_data in group_data['settings'].items():
                if setting_data.get('sensitive', False):
                    self.assertEqual(setting_data['value'], '***HIDDEN***')
    
    def test_environment_variables_get(self):
        """Test GET request to environment variables endpoint"""
        response = self.client.get('/settings/environment/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('success', data)
        self.assertIn('environment_variables', data)
        self.assertIn('count', data)
        self.assertTrue(data['success'])
    
    @patch.dict(os.environ, {
        'DJANGO_DEBUG': 'True',
        'SWARM_LOG_LEVEL': 'DEBUG',
        'OPENAI_API_KEY': 'sk-test123',
        'SOME_OTHER_VAR': 'not_relevant'
    })
    def test_environment_variables_filtering(self):
        """Test that environment variables are properly filtered"""
        response = self.client.get('/settings/environment/')
        data = json.loads(response.content)
        
        env_vars = data['environment_variables']
        
        # Should include relevant variables
        self.assertIn('DJANGO_DEBUG', env_vars)
        self.assertIn('SWARM_LOG_LEVEL', env_vars)
        self.assertIn('OPENAI_API_KEY', env_vars)
        
        # Should not include irrelevant variables
        self.assertNotIn('SOME_OTHER_VAR', env_vars)
        
        # Sensitive variables should be masked
        self.assertEqual(env_vars['OPENAI_API_KEY'], '***SET***')
        
        # Non-sensitive variables should show actual values
        self.assertEqual(env_vars['DJANGO_DEBUG'], 'True')
        self.assertEqual(env_vars['SWARM_LOG_LEVEL'], 'DEBUG')


class TestSettingsManagerEdgeCases(TestCase):
    """Test edge cases and error handling in SettingsManager"""
    
    def setUp(self):
        self.settings_manager = SettingsManager()
    
    @patch('django.conf.settings')
    def test_missing_django_settings(self, mock_settings):
        """Test handling of missing Django settings"""
        # Mock settings that might not exist
        mock_settings.DEBUG = None
        mock_settings.SECRET_KEY = None
        
        self.settings_manager._collect_django_settings()
        django_settings = self.settings_manager.settings_groups['django']['settings']
        
        # Should handle None values gracefully
        self.assertIn('DEBUG', django_settings)
        self.assertIn('SECRET_KEY', django_settings)
    
    @patch('src.swarm.views.settings_views.load_config')
    def test_empty_config_file(self, mock_load_config):
        """Test handling of empty config file"""
        mock_load_config.return_value = {}
        
        self.settings_manager._collect_llm_settings()
        self.settings_manager._collect_blueprint_settings()
        self.settings_manager._collect_mcp_settings()
        
        # Should handle empty config gracefully
        llm_settings = self.settings_manager.settings_groups['llm_providers']['settings']
        blueprint_settings = self.settings_manager.settings_groups['blueprints']['settings']
        mcp_settings = self.settings_manager.settings_groups['mcp_servers']['settings']
        
        # Should still have environment variable settings
        self.assertIn('OPENAI_API_KEY', llm_settings)
        self.assertIn('SWARM_DEBUG', blueprint_settings)
        self.assertIn('NO_MCP_SERVERS', mcp_settings)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_no_environment_variables(self):
        """Test handling when no relevant environment variables are set"""
        self.settings_manager._collect_auth_settings()
        self.settings_manager._collect_logging_settings()
        
        # Should handle missing env vars gracefully
        auth_settings = self.settings_manager.settings_groups['authentication']['settings']
        logging_settings = self.settings_manager.settings_groups['logging']['settings']
        
        # Values should be 'Not Set' or defaults
        for setting_data in auth_settings.values():
            if setting_data.get('env_var'):
                self.assertIn(setting_data['value'], ['Not Set', False, None, []])


class TestSettingsIntegration(TestCase):
    """Integration tests for settings functionality"""
    
    def setUp(self):
        self.client = Client()
    
    @patch.dict(os.environ, {
        'DJANGO_DEBUG': 'True',
        'ENABLE_WEBUI': 'true',
        'SWARM_LOG_LEVEL': 'INFO',
        'OPENAI_API_KEY': 'sk-test123'
    })
    def test_full_settings_collection_workflow(self):
        """Test the complete settings collection and display workflow"""
        # Test dashboard page
        response = self.client.get('/settings/')
        self.assertEqual(response.status_code, 200)
        
        # Test API endpoint
        api_response = self.client.get('/settings/api/')
        self.assertEqual(api_response.status_code, 200)
        api_data = json.loads(api_response.content)
        
        # Test environment endpoint
        env_response = self.client.get('/settings/environment/')
        self.assertEqual(env_response.status_code, 200)
        env_data = json.loads(env_response.content)
        
        # Verify data consistency
        self.assertTrue(api_data['success'])
        self.assertTrue(env_data['success'])
        
        # Verify environment variables are detected
        self.assertIn('DJANGO_DEBUG', env_data['environment_variables'])
        self.assertIn('ENABLE_WEBUI', env_data['environment_variables'])
        self.assertIn('OPENAI_API_KEY', env_data['environment_variables'])
        
        # Verify sensitive data is masked
        self.assertEqual(env_data['environment_variables']['OPENAI_API_KEY'], '***SET***')


if __name__ == '__main__':
    pytest.main([__file__])