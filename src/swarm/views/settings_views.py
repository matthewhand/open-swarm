"""
Comprehensive Settings Management for Open Swarm
Groups and displays all configuration options in a professional web UI
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

try:
    # Use the extensions config loader which provides discovery utilities
    from swarm.extensions.config.config_loader import (
        find_config_file as _find_config_file,
        load_config as _load_config,
    )
except Exception:
    _find_config_file = None
    _load_config = None

def load_config():
    """Load the primary swarm configuration as a dictionary.

    This wrapper locates the config file using the extensions discovery
    logic and loads it. Tests patch this symbol directly, so we keep it
    as a simple no-arg function.
    """
    try:
        if _find_config_file is None or _load_config is None:
            return {}
        config_path = _find_config_file()
        if not config_path:
            return {}
        return _load_config(config_path)
    except Exception:
        # Fail gracefully; callers handle empty config or report errors
        return {}
from swarm.core.paths import get_user_config_dir_for_swarm


class SettingsManager:
    """Comprehensive settings management for Open Swarm"""
    
    def __init__(self):
        self.settings_groups = {
            'django': {
                'title': 'Django Framework',
                'description': 'Core Django application settings',
                'icon': '🌐',
                'settings': {}
            },
            'swarm_core': {
                'title': 'Swarm Core',
                'description': 'Core Open Swarm functionality settings',
                'icon': '🚀',
                'settings': {}
            },
            'authentication': {
                'title': 'Authentication & Security',
                'description': 'API authentication and security settings',
                'icon': '🔐',
                'settings': {}
            },
            'llm_providers': {
                'title': 'LLM Providers',
                'description': 'Language model provider configurations',
                'icon': '🧠',
                'settings': {}
            },
            'blueprints': {
                'title': 'Blueprints & Agents',
                'description': 'Blueprint and agent configuration settings',
                'icon': '🤖',
                'settings': {}
            },
            'mcp_servers': {
                'title': 'MCP Servers',
                'description': 'Model Context Protocol server configurations',
                'icon': '🔌',
                'settings': {}
            },
            'database': {
                'title': 'Database',
                'description': 'Database connection and configuration',
                'icon': '🗄️',
                'settings': {}
            },
            'logging': {
                'title': 'Logging & Debugging',
                'description': 'Logging levels and debug settings',
                'icon': '📝',
                'settings': {}
            },
            'performance': {
                'title': 'Performance & Limits',
                'description': 'Performance tuning and resource limits',
                'icon': '⚡',
                'settings': {}
            },
            'ui_features': {
                'title': 'UI Features',
                'description': 'Web interface feature toggles',
                'icon': '🎨',
                'settings': {}
            }
        }
    
    def collect_all_settings(self) -> Dict[str, Any]:
        """Collect all settings from various sources"""
        
        # Django settings
        self._collect_django_settings()
        
        # Swarm core settings
        self._collect_swarm_core_settings()
        
        # Authentication settings
        self._collect_auth_settings()
        
        # LLM provider settings
        self._collect_llm_settings()
        
        # Blueprint settings
        self._collect_blueprint_settings()
        
        # MCP server settings
        self._collect_mcp_settings()
        
        # Database settings
        self._collect_database_settings()
        
        # Logging settings
        self._collect_logging_settings()
        
        # Performance settings
        self._collect_performance_settings()
        
        # UI feature settings
        self._collect_ui_settings()
        
        return self.settings_groups
    
    def _collect_django_settings(self):
        """Collect Django framework settings"""
        django_settings = {
            'DEBUG': {
                'value': getattr(settings, 'DEBUG', False),
                'env_var': 'DJANGO_DEBUG',
                'type': 'boolean',
                'description': 'Enable Django debug mode',
                'category': 'development',
                'sensitive': False
            },
            'SECRET_KEY': {
                'value': '***HIDDEN***' if getattr(settings, 'SECRET_KEY', None) else None,
                'env_var': 'DJANGO_SECRET_KEY',
                'type': 'string',
                'description': 'Django secret key for cryptographic signing',
                'category': 'security',
                'sensitive': True
            },
            'ALLOWED_HOSTS': {
                'value': getattr(settings, 'ALLOWED_HOSTS', []),
                'env_var': 'DJANGO_ALLOWED_HOSTS',
                'type': 'list',
                'description': 'List of allowed hostnames for this Django site',
                'category': 'security',
                'sensitive': False
            },
            'TIME_ZONE': {
                'value': getattr(settings, 'TIME_ZONE', 'UTC'),
                'env_var': None,
                'type': 'string',
                'description': 'Default timezone for the application',
                'category': 'localization',
                'sensitive': False
            },
            'LANGUAGE_CODE': {
                'value': getattr(settings, 'LANGUAGE_CODE', 'en-us'),
                'env_var': None,
                'type': 'string',
                'description': 'Default language code',
                'category': 'localization',
                'sensitive': False
            }
        }
        self.settings_groups['django']['settings'] = django_settings
    
    def _collect_swarm_core_settings(self):
        """Collect Swarm core settings"""
        swarm_settings = {
            'SWARM_CONFIG_PATH': {
                'value': getattr(settings, 'SWARM_CONFIG_PATH', None),
                'env_var': 'SWARM_CONFIG_PATH',
                'type': 'path',
                'description': 'Path to the main swarm configuration file',
                'category': 'core',
                'sensitive': False
            },
            'BLUEPRINT_DIRECTORY': {
                'value': getattr(settings, 'BLUEPRINT_DIRECTORY', None),
                'env_var': 'BLUEPRINT_DIRECTORY',
                'type': 'path',
                'description': 'Directory containing blueprint definitions',
                'category': 'core',
                'sensitive': False
            },
            'BASE_DIR': {
                'value': str(getattr(settings, 'BASE_DIR', '')),
                'env_var': None,
                'type': 'path',
                'description': 'Base directory of the Django application',
                'category': 'core',
                'sensitive': False
            }
        }
        self.settings_groups['swarm_core']['settings'] = swarm_settings
    
    def _collect_auth_settings(self):
        """Collect authentication and security settings"""
        auth_settings = {
            'ENABLE_API_AUTH': {
                'value': getattr(settings, 'ENABLE_API_AUTH', False),
                'env_var': 'API_AUTH_TOKEN',
                'type': 'boolean',
                'description': 'Enable API token authentication',
                'category': 'authentication',
                'sensitive': False
            },
            'SWARM_API_KEY': {
                'value': '***SET***' if getattr(settings, 'SWARM_API_KEY', None) else 'Not Set',
                'env_var': 'API_AUTH_TOKEN',
                'type': 'string',
                'description': 'API authentication token',
                'category': 'authentication',
                'sensitive': True
            },
            'CSRF_TRUSTED_ORIGINS': {
                # Prefer environment variable so tests with patched env behave predictably
                'value': (
                    os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS')
                ),
                'env_var': 'DJANGO_CSRF_TRUSTED_ORIGINS',
                'type': 'list',
                'description': 'Trusted origins for CSRF protection',
                'category': 'security',
                'sensitive': False
            },
            'LOGIN_URL': {
                'value': getattr(settings, 'LOGIN_URL', '/login/'),
                'env_var': None,
                'type': 'string',
                'description': 'URL for user login',
                'category': 'authentication',
                'sensitive': False
            }
        }
        # Normalize CSRF_TRUSTED_ORIGINS value into a list or 'Not Set'
        csrf_val = auth_settings['CSRF_TRUSTED_ORIGINS']['value']
        if csrf_val:
            auth_settings['CSRF_TRUSTED_ORIGINS']['value'] = [s for s in csrf_val.split(',') if s]
        else:
            auth_settings['CSRF_TRUSTED_ORIGINS']['value'] = []

        self.settings_groups['authentication']['settings'] = auth_settings
    
    def _collect_llm_settings(self):
        """Collect LLM provider settings from swarm_config.json"""
        try:
            config = load_config()
            llm_config = config.get('llm', {})
            profiles_config = config.get('profiles', {})
            
            llm_settings = {}
            
            # LLM providers
            for provider, config_data in llm_config.items():
                llm_settings[f'LLM_{provider.upper()}'] = {
                    'value': config_data,
                    'env_var': None,
                    'type': 'object',
                    'description': f'Configuration for {provider} LLM provider',
                    'category': 'provider',
                    'sensitive': 'api_key' in str(config_data).lower()
                }
            
            # LLM profiles
            for profile, profile_data in profiles_config.items():
                llm_settings[f'PROFILE_{profile.upper()}'] = {
                    'value': profile_data,
                    'env_var': None,
                    'type': 'object',
                    'description': f'LLM profile configuration for {profile}',
                    'category': 'profile',
                    'sensitive': False
                }
            
            # Environment variables for common LLM providers
            env_llm_settings = {
                'OPENAI_API_KEY': {
                    'value': '***SET***' if os.getenv('OPENAI_API_KEY') else 'Not Set',
                    'env_var': 'OPENAI_API_KEY',
                    'type': 'string',
                    'description': 'OpenAI API key',
                    'category': 'api_key',
                    'sensitive': True
                },
                'ANTHROPIC_API_KEY': {
                    'value': '***SET***' if os.getenv('ANTHROPIC_API_KEY') else 'Not Set',
                    'env_var': 'ANTHROPIC_API_KEY',
                    'type': 'string',
                    'description': 'Anthropic API key',
                    'category': 'api_key',
                    'sensitive': True
                },
                'OLLAMA_BASE_URL': {
                    'value': os.getenv('OLLAMA_BASE_URL', 'Not Set'),
                    'env_var': 'OLLAMA_BASE_URL',
                    'type': 'string',
                    'description': 'Ollama server base URL',
                    'category': 'endpoint',
                    'sensitive': False
                }
            }
            
            llm_settings.update(env_llm_settings)
            
        except Exception as e:
            llm_settings = {
                'CONFIG_ERROR': {
                    'value': f'Error loading LLM config: {str(e)}',
                    'env_var': None,
                    'type': 'error',
                    'description': 'LLM configuration loading error',
                    'category': 'error',
                    'sensitive': False
                }
            }
        
        self.settings_groups['llm_providers']['settings'] = llm_settings
    
    def _collect_blueprint_settings(self):
        """Collect blueprint-related settings"""
        try:
            config = load_config()
            blueprint_config = config.get('blueprints', {})
            
            blueprint_settings = {
                'BLUEPRINT_DEFAULTS': {
                    'value': blueprint_config.get('defaults', {}),
                    'env_var': None,
                    'type': 'object',
                    'description': 'Default settings for all blueprints',
                    'category': 'defaults',
                    'sensitive': False
                },
                'ENABLED_BLUEPRINTS': {
                    'value': blueprint_config.get('enabled', []),
                    'env_var': None,
                    'type': 'list',
                    'description': 'List of enabled blueprints',
                    'category': 'enabled',
                    'sensitive': False
                }
            }
            
            # Add environment variables related to blueprints
            env_blueprint_settings = {
                'SWARM_DEBUG': {
                    'value': os.getenv('SWARM_DEBUG', 'Not Set'),
                    'env_var': 'SWARM_DEBUG',
                    'type': 'string',
                    'description': 'Enable Swarm debug mode',
                    'category': 'debug',
                    'sensitive': False
                },
                'SWARM_COMMAND_TIMEOUT': {
                    'value': os.getenv('SWARM_COMMAND_TIMEOUT', '60'),
                    'env_var': 'SWARM_COMMAND_TIMEOUT',
                    'type': 'integer',
                    'description': 'Timeout for blueprint command execution (seconds)',
                    'category': 'performance',
                    'sensitive': False
                }
            }
            
            blueprint_settings.update(env_blueprint_settings)
            
        except Exception as e:
            blueprint_settings = {
                'CONFIG_ERROR': {
                    'value': f'Error loading blueprint config: {str(e)}',
                    'env_var': None,
                    'type': 'error',
                    'description': 'Blueprint configuration loading error',
                    'category': 'error',
                    'sensitive': False
                }
            }
        
        self.settings_groups['blueprints']['settings'] = blueprint_settings
    
    def _collect_mcp_settings(self):
        """Collect MCP server settings"""
        try:
            config = load_config()
            mcp_config = config.get('mcpServers', {})
            
            mcp_settings = {}
            
            for server_name, server_config in mcp_config.items():
                mcp_settings[f'MCP_{server_name.upper()}'] = {
                    'value': server_config,
                    'env_var': None,
                    'type': 'object',
                    'description': f'MCP server configuration for {server_name}',
                    'category': 'server',
                    'sensitive': False
                }
            
            if not mcp_settings:
                mcp_settings['NO_MCP_SERVERS'] = {
                    'value': 'No MCP servers configured',
                    'env_var': None,
                    'type': 'info',
                    'description': 'No MCP servers are currently configured',
                    'category': 'info',
                    'sensitive': False
                }
            
        except Exception as e:
            mcp_settings = {
                'CONFIG_ERROR': {
                    'value': f'Error loading MCP config: {str(e)}',
                    'env_var': None,
                    'type': 'error',
                    'description': 'MCP configuration loading error',
                    'category': 'error',
                    'sensitive': False
                }
            }
        
        self.settings_groups['mcp_servers']['settings'] = mcp_settings
    
    def _collect_database_settings(self):
        """Collect database settings"""
        db_config = getattr(settings, 'DATABASES', {}).get('default', {})
        
        database_settings = {
            'ENGINE': {
                'value': db_config.get('ENGINE', 'Not Set'),
                'env_var': None,
                'type': 'string',
                'description': 'Database engine',
                'category': 'connection',
                'sensitive': False
            },
            'NAME': {
                'value': db_config.get('NAME', 'Not Set'),
                'env_var': 'DJANGO_DB_NAME',
                'type': 'string',
                'description': 'Database name or file path',
                'category': 'connection',
                'sensitive': False
            },
            'TEST_NAME': {
                'value': db_config.get('TEST', {}).get('NAME', 'Not Set'),
                'env_var': 'DJANGO_TEST_DB_NAME',
                'type': 'string',
                'description': 'Test database name or file path',
                'category': 'testing',
                'sensitive': False
            }
        }
        
        self.settings_groups['database']['settings'] = database_settings
    
    def _collect_logging_settings(self):
        """Collect logging and debug settings"""
        logging_settings = {
            'DJANGO_LOG_LEVEL': {
                'value': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
                'env_var': 'DJANGO_LOG_LEVEL',
                'type': 'string',
                'description': 'Django logging level',
                'category': 'level',
                'sensitive': False
            },
            'SWARM_LOG_LEVEL': {
                'value': os.getenv('SWARM_LOG_LEVEL', 'DEBUG'),
                'env_var': 'SWARM_LOG_LEVEL',
                'type': 'string',
                'description': 'Swarm logging level',
                'category': 'level',
                'sensitive': False
            },
            'LOG_LEVEL': {
                'value': os.getenv('LOG_LEVEL', 'Not Set'),
                'env_var': 'LOG_LEVEL',
                'type': 'string',
                'description': 'General log level',
                'category': 'level',
                'sensitive': False
            },
            'LOGLEVEL': {
                'value': os.getenv('LOGLEVEL', 'Not Set'),
                'env_var': 'LOGLEVEL',
                'type': 'string',
                'description': 'Alternative log level variable',
                'category': 'level',
                'sensitive': False
            }
        }
        
        self.settings_groups['logging']['settings'] = logging_settings
    
    def _collect_performance_settings(self):
        """Collect performance and resource limit settings"""
        performance_settings = {
            'REDIS_HOST': {
                'value': getattr(settings, 'REDIS_HOST', 'localhost'),
                'env_var': 'REDIS_HOST',
                'type': 'string',
                'description': 'Redis server hostname',
                'category': 'redis',
                'sensitive': False
            },
            'REDIS_PORT': {
                'value': getattr(settings, 'REDIS_PORT', 6379),
                'env_var': 'REDIS_PORT',
                'type': 'integer',
                'description': 'Redis server port',
                'category': 'redis',
                'sensitive': False
            },
            'SWARM_COMMAND_TIMEOUT': {
                'value': os.getenv('SWARM_COMMAND_TIMEOUT', '60'),
                'env_var': 'SWARM_COMMAND_TIMEOUT',
                'type': 'integer',
                'description': 'Command execution timeout in seconds',
                'category': 'limits',
                'sensitive': False
            }
        }
        
        self.settings_groups['performance']['settings'] = performance_settings
    
    def _collect_ui_settings(self):
        """Collect UI feature toggle settings"""
        ui_settings = {
            'ENABLE_WEBUI': {
                'value': os.getenv('ENABLE_WEBUI', 'false'),
                'env_var': 'ENABLE_WEBUI',
                'type': 'boolean',
                'description': 'Enable web user interface',
                'category': 'features',
                'sensitive': False
            },
            'ENABLE_ADMIN': {
                'value': os.getenv('ENABLE_ADMIN', 'false'),
                'env_var': 'ENABLE_ADMIN',
                'type': 'boolean',
                'description': 'Enable Django admin interface',
                'category': 'features',
                'sensitive': False
            }
        }
        
        self.settings_groups['ui_features']['settings'] = ui_settings


# Global settings manager instance
settings_manager = SettingsManager()


@csrf_exempt
def settings_dashboard(request):
    """Render the comprehensive settings dashboard"""
    try:
        all_settings = settings_manager.collect_all_settings()
        
        # Calculate statistics
        total_settings = sum(len(group['settings']) for group in all_settings.values())
        configured_settings = sum(
            1 for group in all_settings.values() 
            for setting in group['settings'].values() 
            if setting['value'] not in ['Not Set', None, '']
        )
        sensitive_settings = sum(
            1 for group in all_settings.values() 
            for setting in group['settings'].values() 
            if setting.get('sensitive', False)
        )
        
        context = {
            'page_title': 'Settings Dashboard',
            'settings_groups': all_settings,
            'stats': {
                'total': total_settings,
                'configured': configured_settings,
                'sensitive': sensitive_settings,
                'completion_rate': round((configured_settings / total_settings) * 100) if total_settings > 0 else 0
            }
        }
        
        return render(request, 'settings_dashboard.html', context)
        
    except Exception as e:
        return HttpResponse(f"Error loading settings: {str(e)}", status=500)


@csrf_exempt
@require_http_methods(["GET"])
def settings_api(request):
    """API endpoint to get all settings as JSON"""
    try:
        all_settings = settings_manager.collect_all_settings()
        
        # Remove sensitive values for API response
        safe_settings = {}
        for group_name, group_data in all_settings.items():
            safe_settings[group_name] = {
                'title': group_data['title'],
                'description': group_data['description'],
                'icon': group_data['icon'],
                'settings': {}
            }
            
            for setting_name, setting_data in group_data['settings'].items():
                safe_setting = setting_data.copy()
                if setting_data.get('sensitive', False):
                    safe_setting['value'] = '***HIDDEN***'
                safe_settings[group_name]['settings'][setting_name] = safe_setting
        
        return JsonResponse({
            'success': True,
            'settings': safe_settings
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def environment_variables(request):
    """Get all environment variables related to Open Swarm"""
    try:
        # Collect all environment variables that might be relevant
        relevant_prefixes = [
            'DJANGO_', 'SWARM_', 'API_', 'ENABLE_', 'OPENAI_', 
            'ANTHROPIC_', 'OLLAMA_', 'REDIS_', 'LOG'
        ]
        
        env_vars = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in relevant_prefixes):
                # Hide sensitive values
                if any(sensitive in key.lower() for sensitive in ['key', 'token', 'secret', 'password']):
                    env_vars[key] = '***SET***' if value else 'Not Set'
                else:
                    env_vars[key] = value
        
        return JsonResponse({
            'success': True,
            'environment_variables': env_vars,
            'count': len(env_vars)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)