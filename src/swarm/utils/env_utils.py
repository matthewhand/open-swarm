"""
Centralized environment variable utility module.

This module provides a single source of truth for environment variables used across the codebase,
reducing direct os.getenv() calls and providing consistent defaults and type handling.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Points to src/


# Django Settings
def get_django_secret_key() -> str:
    """Get Django secret key."""
    return os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev')


def is_django_debug() -> bool:
    """Check if Django debug is enabled."""
    return os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 't')


def get_django_allowed_hosts() -> list[str]:
    """Get allowed hosts for Django."""
    return os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


def get_django_site_id() -> int:
    """Get Django site ID."""
    return int(os.getenv('DJANGO_SITE_ID', '1'))


def get_django_log_level() -> str:
    """Get Django log level."""
    return os.getenv('DJANGO_LOG_LEVEL', 'INFO')


def get_django_csrf_trusted_origins() -> list[str]:
    """Get CSRF trusted origins."""
    return os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')


# Swarm Core Settings
def get_swarm_config_path() -> str:
    """Get Swarm config path."""
    return os.getenv('SWARM_CONFIG_PATH', str(BASE_DIR.parent / 'swarm_config.json'))


def get_blueprint_directory() -> str:
    """Get blueprint directory."""
    return os.getenv('BLUEPRINT_DIRECTORY', str(BASE_DIR / 'swarm' / 'blueprints'))


def get_swarm_log_level() -> str:
    """Get Swarm log level."""
    return os.getenv('SWARM_LOG_LEVEL', 'DEBUG')


def get_swarm_log_format() -> str:
    """Get Swarm log format."""
    return os.getenv('SWARM_LOG_FORMAT', 'VERBOSE').upper()


def get_swarm_command_timeout() -> int:
    """Get Swarm command timeout in seconds."""
    return int(os.getenv('SWARM_COMMAND_TIMEOUT', '60'))


def get_swarm_debug() -> str | None:
    """Get Swarm debug setting."""
    return os.getenv('SWARM_DEBUG')


def get_swarm_llm_api_mode() -> str | None:
    """Get Swarm LLM API mode."""
    return os.getenv('SWARM_LLM_API_MODE')


def get_swarm_deterministic_hooks() -> bool:
    """Check if Swarm deterministic hooks are enabled."""
    return os.getenv('SWARM_DETERMINISTIC_HOOKS', '').lower() in ('true', '1', 't', 'yes', 'y')


def get_swarm_truncation_mode() -> str:
    """Get Swarm truncation mode."""
    return os.getenv('SWARM_TRUNCATION_MODE', 'pairs').lower()


def get_stateful_chat_id_path() -> str:
    """Get stateful chat ID path expression."""
    return os.getenv('STATEFUL_CHAT_ID_PATH', '').strip()


# API Tokens and Keys
def get_api_auth_token() -> str | None:
    """Get API auth token."""
    return os.getenv('API_AUTH_TOKEN')


def get_openai_api_key() -> str | None:
    """Get OpenAI API key."""
    return os.getenv('OPENAI_API_KEY')


def get_openai_model() -> str | None:
    """Get OpenAI model."""
    return os.getenv('OPENAI_MODEL')


def get_openai_base_url() -> str | None:
    """Get OpenAI base URL."""
    return os.getenv('OPENAI_BASE_URL')


def get_anthropic_api_key() -> str | None:
    """Get Anthropic API key."""
    return os.getenv('ANTHROPIC_API_KEY')


def get_ollama_base_url() -> str | None:
    """Get Ollama base URL."""
    return os.getenv('OLLAMA_BASE_URL')


def get_litellm_api_key() -> str | None:
    """Get LiteLLM API key."""
    return os.getenv('LITELLM_API_KEY')


def get_litellm_model() -> str | None:
    """Get LiteLLM model."""
    return os.getenv('LITELLM_MODEL')


def get_litellm_base_url() -> str | None:
    """Get LiteLLM base URL."""
    return os.getenv('LITELLM_BASE_URL')


def get_default_llm() -> str | None:
    """Get default LLM."""
    return os.getenv('DEFAULT_LLM')


def get_github_token() -> str | None:
    """Get GitHub token."""
    return os.getenv('GITHUB_TOKEN')


def get_wolfram_llm_app_id() -> str | None:
    """Get Wolfram LLM app ID."""
    return os.getenv('WOLFRAM_LLM_APP_ID')


def get_fly_api_token() -> str | None:
    """Get Fly API token."""
    return os.getenv('FLY_API_TOKEN')


# Feature Flags
def is_enable_wagtail() -> bool:
    """Check if Wagtail is enabled."""
    return os.getenv('ENABLE_WAGTAIL', 'false').lower() in ('1', 'true', 'yes')


def is_enable_saml_idp() -> bool:
    """Check if SAML IdP is enabled."""
    return os.getenv('ENABLE_SAML_IDP', 'false').lower() in ('1', 'true', 'yes')


def is_enable_mcp_server() -> bool:
    """Check if MCP server is enabled."""
    return os.getenv('ENABLE_MCP_SERVER', 'false').lower() in ('1', 'true', 'yes')


def is_enable_github_marketplace() -> bool:
    """Check if GitHub marketplace is enabled."""
    return os.getenv('ENABLE_GITHUB_MARKETPLACE', 'false').lower() in ('1', 'true', 'yes')


def is_enable_webui() -> bool:
    """Check if WebUI is enabled."""
    return os.getenv('ENABLE_WEBUI', 'false').lower() in ('true', '1', 't', 'yes', 'y')


def is_enable_admin() -> bool:
    """Check if admin is enabled."""
    return os.getenv('ENABLE_ADMIN', 'false').lower() in ('true', '1', 't', 'yes', 'y')


def is_enable_api_auth() -> bool:
    """Check if API auth is enabled."""
    return os.getenv('ENABLE_API_AUTH', 'true').lower() in ('true', '1', 't', 'yes', 'y')


def is_comfyui_enabled() -> bool:
    """Check if ComfyUI is enabled."""
    return os.getenv('COMFYUI_ENABLED', 'False').lower() in ('true', '1', 't')


def is_debug() -> bool:
    """Check if debug is enabled."""
    return os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')


# Server Configuration
def get_host() -> str:
    """Get host."""
    return os.getenv('HOST', '0.0.0.0')


def get_port() -> str:
    """Get port."""
    return os.getenv('PORT', '8000')


def get_redis_host() -> str:
    """Get Redis host."""
    return os.getenv('REDIS_HOST', 'localhost')


def get_redis_port() -> int:
    """Get Redis port."""
    return int(os.getenv('REDIS_PORT', '6379'))


def get_comfyui_host() -> str:
    """Get ComfyUI host."""
    return os.getenv('COMFYUI_HOST', 'http://localhost:8188')


def get_comfyui_api_endpoint() -> str:
    """Get ComfyUI API endpoint."""
    return f"{get_comfyui_host()}/api"


# SAML Configuration
def get_saml_idp_spconfig_json() -> str | None:
    """Get SAML IdP SP config JSON."""
    return os.getenv('SAML_IDP_SPCONFIG_JSON')


def get_saml_idp_spconfig_file() -> str | None:
    """Get SAML IdP SP config file."""
    return os.getenv('SAML_IDP_SPCONFIG_FILE')


def get_saml_idp_entity_id() -> str:
    """Get SAML IdP entity ID."""
    return os.getenv('SAML_IDP_ENTITY_ID', 'http://localhost:8000/idp/metadata/')


def get_saml_idp_cert_file() -> str | None:
    """Get SAML IdP cert file."""
    return os.getenv('SAML_IDP_CERT_FILE')


def get_saml_idp_private_key_file() -> str | None:
    """Get SAML IdP private key file."""
    return os.getenv('SAML_IDP_PRIVATE_KEY_FILE')


# Blueprint Specific
def get_stewie_main_name() -> str:
    """Get Stewie main name."""
    return os.getenv('STEWIE_MAIN_NAME', 'peter')


def get_echocraft_spinner_slow_threshold() -> int:
    """Get Echocraft spinner slow threshold."""
    return int(os.getenv('ECHOCRAFT_SPINNER_SLOW_THRESHOLD', '10'))


def get_mission_spinner_slow_threshold() -> int:
    """Get Mission spinner slow threshold."""
    return int(os.getenv('MISSION_SPINNER_SLOW_THRESHOLD', '10'))


def get_whinge_spinner_slow_threshold() -> int:
    """Get Whinge spinner slow threshold."""
    return int(os.getenv('WHINGE_SPINNER_SLOW_THRESHOLD', '10'))


def get_sqlite_db_path() -> str:
    """Get SQLite DB path."""
    return os.getenv('SQLITE_DB_PATH', './wtf_services.db')


def get_aws_region() -> str | None:
    """Get AWS region."""
    return os.getenv('AWS_REGION')


def get_fly_region() -> str | None:
    """Get Fly region."""
    return os.getenv('FLY_REGION')


def get_vercel_org_id() -> str | None:
    """Get Vercel org ID."""
    return os.getenv('VERCEL_ORG_ID')


# Logging Levels
def get_log_level() -> str | None:
    """Get log level."""
    return os.getenv('LOG_LEVEL')


def get_loglevel() -> str | None:
    """Get LOGLEVEL."""
    return os.getenv('LOGLEVEL')


# Utility Functions
def get_csv_env(name: str, default: str = '') -> list[str]:
    """Get a CSV environment variable as a list."""
    val = os.getenv(name, default)
    return val.split(',') if val else []


def is_truthy(value: str) -> bool:
    """Check if a string value is truthy."""
    return value.lower() in ('true', '1', 't', 'yes', 'y')
