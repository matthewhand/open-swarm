"""
Centralized environment variable utility module.

This module provides a single source of truth for environment variables used across the codebase,
reducing direct os.getenv() calls and providing consistent defaults and type handling.
"""

import os
import secrets
import logging as _logging
from pathlib import Path

_logger = _logging.getLogger(__name__)
_api_auth_disabled_warning_emitted: bool = False
_bootstrap_no_base_url_warned: bool = False
_generated_testuser_password: str | None = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Points to src/


# Django Settings
def get_django_secret_key() -> str:
    """Get Django secret key. Requires DJANGO_SECRET_KEY in non-debug (prod) mode."""
    key = os.getenv('DJANGO_SECRET_KEY')
    if key:
        return key
    debug = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 't')
    if debug:
        return 'django-insecure-fallback-key-for-dev'
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable is required when DJANGO_DEBUG is not enabled (production). "
        "Set DJANGO_SECRET_KEY, or set DJANGO_DEBUG=true for local development."
    )


def is_django_debug() -> bool:
    """Check if Django debug is enabled.

    Secure-by-default: when ``DJANGO_DEBUG`` is unset, returns False (production).
    Local dev and tests must set ``DJANGO_DEBUG=true`` explicitly (settings.py
    auto-sets it under pytest).
    """
    return os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 't')


def get_django_allowed_hosts() -> list[str]:
    """Get allowed hosts for Django. Required in non-debug (prod) mode."""
    hosts = os.getenv('DJANGO_ALLOWED_HOSTS')
    if hosts:
        return [h.strip() for h in hosts.split(',') if h.strip()]
    debug = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 't')
    if debug:
        return ['localhost', '127.0.0.1']
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS environment variable is required when DJANGO_DEBUG is not enabled (production), "
        "e.g. DJANGO_ALLOWED_HOSTS=example.com,www.example.com. Set DJANGO_DEBUG=true for local development."
    )


def get_django_site_id() -> int:
    """Get Django site ID."""
    return int(os.getenv('DJANGO_SITE_ID', '1'))


def get_django_log_level() -> str:
    """Get Django log level."""
    return os.getenv('DJANGO_LOG_LEVEL', 'INFO')


def get_django_csrf_trusted_origins() -> list[str]:
    """Get CSRF trusted origins."""
    val = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
    return [v.strip() for v in val.split(',') if v.strip()]


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
def get_api_auth_tokens() -> list[str]:
    """All accepted API auth secrets, deduped (order preserved).

    Sources (merged):
    - singles: ``API_AUTH_TOKEN``, ``SWARM_API_KEY``
    - multi (comma-separated): ``API_AUTH_TOKENS``, ``SWARM_API_KEYS``

    Returns an empty list when ``SWARM_ALLOW_NO_AUTH`` is truthy (built-in
    auth intentionally disabled).
    """
    if os.getenv('SWARM_ALLOW_NO_AUTH', 'false').lower() in ('true', '1', 'yes'):
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for key in ('API_AUTH_TOKEN', 'SWARM_API_KEY'):
        val = os.getenv(key)
        if not val:
            continue
        t = val.strip()
        if t and t not in seen:
            tokens.append(t)
            seen.add(t)
    for key in ('API_AUTH_TOKENS', 'SWARM_API_KEYS'):
        for t in get_csv_env(key):
            if t not in seen:
                tokens.append(t)
                seen.add(t)
    return tokens


def get_api_auth_token() -> str | None:
    """Return the primary accepted API auth token, if authentication is enabled.

    The first value from :func:`get_api_auth_tokens` is used. When
    ``SWARM_ALLOW_NO_AUTH`` is truthy, built-in authentication is explicitly
    disabled and this returns ``None``.
    """
    tokens = get_api_auth_tokens()
    return tokens[0] if tokens else None


# OpenAI/LiteLLM getters consolidated below with get_openai_* that support both prefixes.


def get_anthropic_api_key() -> str | None:
    """Get Anthropic API key."""
    return os.getenv('ANTHROPIC_API_KEY')


def get_ollama_base_url() -> str | None:
    """Get Ollama base URL."""
    return os.getenv('OLLAMA_BASE_URL')


# --- Simple bootstrap support (env-only, no full swarm_config.json) ---

def get_openai_bootstrap() -> dict | None:
    """Return a minimal llm.default profile dict if OPENAI/LITELLM key (base_url recommended) are set.

    This powers the "just works" case for pure-env usage. Returns None only if no api_key.
    Warns (once) if a key is present without a base_url — the resulting profile will have
    base_url=None and client setup will typically skip setting a default (to avoid
    unintentionally targeting api.openai.com).
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LITELLM_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LITELLM_BASE_URL")
    if not api_key:
        return None
    if not base_url:
        global _bootstrap_no_base_url_warned
        if not _bootstrap_no_base_url_warned:
            _bootstrap_no_base_url_warned = True
            _logger.warning(
                "OPENAI_API_KEY (or LITELLM_API_KEY) present but no OPENAI_BASE_URL "
                "(or LITELLM_BASE_URL). Bootstrap will produce a profile without base_url. "
                "LLM client setup will not auto-target api.openai.com. Set a base_url "
                "for gateways (or explicitly https://api.openai.com/v1 for real OpenAI)."
            )
    return {
        "provider": "openai",
        "model": "gpt-5.5",
        "base_url": base_url,
        "api_key": api_key,
        "intelligence": 0.6,
        "speed": 0.6,
        "cost": 0.6,
    }


def get_openai_api_key() -> str | None:
    """Convenience: return an OpenAI-compatible API key from env."""
    return os.getenv("OPENAI_API_KEY") or os.getenv("LITELLM_API_KEY")


def get_openai_base_url() -> str | None:
    """Convenience: return base URL from env."""
    return os.getenv("OPENAI_BASE_URL") or os.getenv("LITELLM_BASE_URL")


def ensure_default_openai_client() -> bool:
    """Ensure a default OpenAI client is set for the agents library.

    Prefers a loaded swarm config's 'default' profile (after AppConfig load/synthesis);
    falls back to env bootstrap. Returns True if a client was set.

    Validation & messages:
    - Warns (once) via get_openai_bootstrap when key present but no base_url.
    - Explicit warnings (instead of silent) when key is present without base_url
      during config or direct paths (prevents accidental api.openai.com usage).
    - Clearer messages for misconfiguration.
    """
    try:
        from openai import AsyncOpenAI
        from agents import set_default_openai_client

        # Try to read from already-loaded config if available (e.g. in Django AppConfig)
        # Must be set early after loading/synthesis for this path to be used.
        try:
            from django.conf import settings as dj_settings
            if hasattr(dj_settings, 'SWARM_CONFIG') and isinstance(dj_settings.SWARM_CONFIG, dict):
                prof = dj_settings.SWARM_CONFIG.get("llm", {}).get("default", {})
                if prof.get("base_url") and prof.get("api_key"):
                    set_default_openai_client(AsyncOpenAI(
                        base_url=prof["base_url"], api_key=prof["api_key"]
                    ))
                    _logger.debug("Default OpenAI client set from SWARM_CONFIG llm.default")
                    return True
                if prof.get("api_key") and not prof.get("base_url"):
                    _logger.warning(
                        "SWARM_CONFIG llm.default has api_key but no base_url. "
                        "Not setting default client from config profile."
                    )
        except Exception:
            pass

        # Bootstrap from env (calls get_openai_bootstrap which warns on key+no-base)
        bootstrap = get_openai_bootstrap()
        if bootstrap and bootstrap.get("base_url") and bootstrap.get("api_key"):
            set_default_openai_client(
                AsyncOpenAI(base_url=bootstrap["base_url"], api_key=bootstrap["api_key"])
            )
            _logger.debug("Default OpenAI client set from env bootstrap")
            return True
        if bootstrap and bootstrap.get("api_key") and not bootstrap.get("base_url"):
            _logger.warning(
                "Env bootstrap (OPENAI/LITELLM key) present without base_url; "
                "skipping set_default_openai_client to avoid defaulting to api.openai.com. "
                "Provide OPENAI_BASE_URL (or LITELLM_BASE_URL) for the simple bootstrap path."
            )

        # Direct env fallback (hardened: require url too; warn on key-only)
        key = get_openai_api_key()
        url = get_openai_base_url()
        if key and url:
            set_default_openai_client(AsyncOpenAI(base_url=url, api_key=key))
            _logger.debug("Default OpenAI client set from direct env")
            return True
        if key and not url:
            _logger.warning(
                "LLM API key present in environment (OPENAI_API_KEY or LITELLM_API_KEY) "
                "but no corresponding base_url. Not setting default OpenAI client. "
                "This is required for non-OpenAI gateways; for the real OpenAI API set "
                "OPENAI_BASE_URL=https://api.openai.com/v1 explicitly."
            )
    except ImportError as ie:
        _logger.debug("Skipping default OpenAI client (agents/openai not importable): %s", ie)
    except Exception as e:
        _logger.warning("Failed to ensure_default_openai_client: %s", e)
    return False



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
    """Get a CSV environment variable as a list, stripping whitespace and empty entries."""
    val = os.getenv(name, default)
    return [v.strip() for v in val.split(',') if v.strip()] if val else []


def is_truthy(value: str) -> bool:
    """Check if a string value is truthy."""
    return value.lower() in ('true', '1', 't', 'yes', 'y')


def get_enforced_api_auth_token() -> str | None:
    """Get the API auth token, enforcing the production requirement."""
    global _api_auth_disabled_warning_emitted
    token = get_api_auth_token()
    if token:
        return token
    allow_no_auth = os.getenv('SWARM_ALLOW_NO_AUTH', 'false').lower() in ('true', '1', 't', 'yes', 'y')
    if is_django_debug() or allow_no_auth:
        if not _api_auth_disabled_warning_emitted:
            _api_auth_disabled_warning_emitted = True
            reason = "DJANGO_DEBUG=true" if is_django_debug() else "SWARM_ALLOW_NO_AUTH is set"
            _logger.warning(
                "API authentication is DISABLED because API_AUTH_TOKEN is not set (%s).",
                reason,
            )
        return None
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "API_AUTH_TOKEN (or API_AUTH_TOKENS / SWARM_API_KEY / SWARM_API_KEYS) is required "
        "when DJANGO_DEBUG is not enabled. "
        "Set a token, or set SWARM_ALLOW_NO_AUTH=true if an external layer gates access."
    )


def is_testuser_autologin_allowed() -> bool:
    """Check whether dev-only 'testuser' auto-login is enabled AND permitted."""
    enabled = os.getenv('ALLOW_TESTUSER_AUTOLOGIN', 'false').lower() in ('true', '1', 't', 'yes', 'y')
    if not enabled:
        return False
    if not is_django_debug():
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "ALLOW_TESTUSER_AUTOLOGIN is enabled but DJANGO_DEBUG is not. "
            "This would create an authentication bypass in production."
        )
    return True


def is_swarm_test_mode() -> bool:
    """True when SWARM_TEST_MODE is set to a truthy value."""
    return os.getenv('SWARM_TEST_MODE', '').lower() in ('true', '1', 't', 'yes', 'y')


def assert_test_mode_allowed() -> None:
    """Refuse SWARM_TEST_MODE outside debug/pytest so prod cannot return canned answers.

    Allowed when:
    - SWARM_TEST_MODE is unset/false
    - DJANGO_DEBUG is true
    - running under pytest (tests force SWARM_TEST_MODE)
    """
    if not is_swarm_test_mode():
        return
    import sys
    if is_django_debug():
        return
    if 'pytest' in sys.modules or 'PYTEST_VERSION' in os.environ:
        return
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "SWARM_TEST_MODE is set but DJANGO_DEBUG is not enabled. "
        "This would return canned/fake agent answers in production. "
        "Unset SWARM_TEST_MODE, or set DJANGO_DEBUG=true for local testing."
    )


def client_safe_error_message(
    exc: Exception | None = None,
    *,
    public: str = "Internal server error during generation.",
) -> str:
    """Return an error string safe to send to API clients.

    In DEBUG, append a short exception type/message for operators. In production,
    never echo raw exception strings (paths, CLI stderr, stack fragments).
    """
    if exc is None or not is_django_debug():
        return public
    detail = str(exc).strip()
    if not detail:
        return f"{public} ({type(exc).__name__})"
    # Cap length so clients never get multi-KB dumps even in debug.
    if len(detail) > 500:
        detail = detail[:500] + "…"
    return f"{public} ({type(exc).__name__}: {detail})"


def get_testuser_password() -> str:
    """Get the password for the dev-only 'testuser' account."""
    pw = os.getenv('TESTUSER_PASSWORD')
    if pw:
        return pw
    global _generated_testuser_password
    if _generated_testuser_password is None:
        _generated_testuser_password = secrets.token_urlsafe(32)
    return _generated_testuser_password
