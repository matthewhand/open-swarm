"""
Django settings for swarm project.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent # Points to src/

from swarm.utils.env_utils import *

# --- Load .env file ---
dotenv_path = BASE_DIR.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)
# ---

# Secure-by-default: DJANGO_DEBUG defaults to False, and production
# (DEBUG=False) requires DJANGO_SECRET_KEY and DJANGO_ALLOWED_HOSTS to be set
# (ImproperlyConfigured is raised otherwise — see swarm.utils.env_utils).
# The test suite runs in development mode: pytest-django imports settings
# before any conftest can run, so default DJANGO_DEBUG here when under pytest
# unless the caller explicitly set it.
TESTING = 'pytest' in sys.modules or 'PYTEST_VERSION' in os.environ
if TESTING:
    os.environ.setdefault('DJANGO_DEBUG', 'true')

SECRET_KEY = get_django_secret_key()
DEBUG = is_django_debug()
ALLOWED_HOSTS = get_django_allowed_hosts()

# --- Custom Swarm Settings ---
# Load the API auth token. In production (DEBUG=False) a missing token raises
# ImproperlyConfigured so the server refuses to start with auth silently disabled.
_raw_api_token = get_enforced_api_auth_token()

# *** Only enable API auth if the token is actually set ***
ENABLE_API_AUTH = bool(_raw_api_token)
SWARM_API_KEY = _raw_api_token # Assign the loaded token (or None)

if ENABLE_API_AUTH:
    # Add assertion to satisfy type checkers within this block
    assert SWARM_API_KEY is not None, "SWARM_API_KEY cannot be None when ENABLE_API_AUTH is True"

SWARM_CONFIG_PATH = get_swarm_config_path()
BLUEPRINT_DIRECTORY = get_blueprint_directory()


def _blueprint_extra_dirs() -> list[str]:
    """External/community blueprint roots, scanned in addition to the bundled dir.

    Order: the user data 'blueprints' dir (where community packs are installed),
    then any paths in ``SWARM_BLUEPRINT_PATHS`` (os.pathsep-separated). The bundled
    dir always wins on name collisions (see ``discover_all_blueprints``).
    """
    dirs: list[str] = []
    try:
        from swarm.core.paths import get_user_blueprints_dir
        dirs.append(str(get_user_blueprints_dir()))
    except Exception:
        pass
    extra = os.getenv("SWARM_BLUEPRINT_PATHS", "")
    dirs.extend(p for p in extra.split(os.pathsep) if p.strip())
    return dirs


BLUEPRINT_EXTRA_DIRS = _blueprint_extra_dirs()

# Web UI Configuration
ENABLE_WEBUI = os.getenv('ENABLE_WEBUI', 'true').lower() in ('true', '1', 'yes')
WEBUI_STATIC_DIR = BASE_DIR.parent / 'staticfiles' / 'webui'
# --- End Custom Swarm Settings ---

INSTALLED_APPS = [
    # 'daphne' must come first so its ASGI-aware `runserver` (which serves
    # websocket routes via ASGI_APPLICATION) overrides the default command.
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    # Django Channels: registers the ASGI/websocket machinery used by
    # swarm.asgi + swarm.routing (chat consumer at ws/ai-demo/<id>/).
    'channels',
    'swarm',
    'swarm.mcp',
]

# Optional MCP server integration. Disabled by default and currently
# aspirational — see docs/mcp_server_mode.md. The try/except here previously
# guarded a plain list append (which never raises), so enabling the flag
# without the package crashed django.setup() in apps.populate(). Only register
# the app if its module is actually importable.
ENABLE_MCP_SERVER = is_enable_mcp_server()
if ENABLE_MCP_SERVER:
    import importlib.util
    import sys as _sys
    # The `django-mcp-server` distribution installs the `mcp_server` module
    # (NOT `django_mcp_server`). Install it manually: `pip install django-mcp-server`.
    try:
        _mcp_available = importlib.util.find_spec('mcp_server') is not None
    except ValueError:
        # Module placed in sys.modules without a __spec__ (e.g. test stubs).
        _mcp_available = 'mcp_server' in _sys.modules
    if _mcp_available:
        INSTALLED_APPS += ['mcp_server']
    else:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "ENABLE_MCP_SERVER is set but the 'mcp_server' module is not installed; "
            "skipping app registration. Install it with `pip install django-mcp-server` "
            "(see docs/mcp_server_mode.md)."
        )

# Optional GitHub marketplace discovery (disabled by default)
ENABLE_GITHUB_MARKETPLACE = is_enable_github_marketplace()
GITHUB_TOKEN = get_github_token()  # optional, for higher rate limits

def _csv_env(name: str, default: str = '') -> list[str]:
    val = os.getenv(name, default)
    if not val:
        return []
    return [x.strip() for x in val.split(',') if x.strip()]

GITHUB_MARKETPLACE_TOPICS = _csv_env('GITHUB_MARKETPLACE_TOPICS', 'open-swarm-blueprint,open-swarm-mcp-template')
GITHUB_MARKETPLACE_ORG_ALLOWLIST = _csv_env('GITHUB_MARKETPLACE_ORG_ALLOWLIST', '')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Add custom middleware to handle async user loading after standard auth
    'swarm.middleware.AsyncAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'swarm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'swarm.wsgi.application'
ASGI_APPLICATION = 'swarm.asgi.application'

# Database — use Postgres (or any Django-supported backend) when DATABASE_URL is
# set, e.g. DATABASE_URL=postgres://user:pass@host:5432/dbname. Otherwise fall
# back to the zero-config SQLite default used for local/dev/tests.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL, conn_max_age=600, conn_health_checks=True
        ),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get('DJANGO_DB_NAME', '/tmp/db.sqlite3'),
            'TEST': {
                'NAME': os.environ.get('DJANGO_TEST_DB_NAME', '/tmp/test_db.sqlite3'),
                'OPTIONS': {
                    'timeout': 20,
                    'init_command': "PRAGMA journal_mode=WAL;",
                },
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR.parent / 'staticfiles'
STATICFILES_DIRS = [ 
    BASE_DIR / "swarm" / "static",
    BASE_DIR.parent / "staticfiles" / "webui" if (BASE_DIR.parent / "staticfiles" / "webui").exists() else None,
]
STATICFILES_DIRS = [d for d in STATICFILES_DIRS if d is not None]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'swarm.auth.StaticTokenAuthentication',
        'swarm.auth.CustomSessionAuthentication',
    ],
    # *** IMPORTANT: Add DEFAULT_PERMISSION_CLASSES ***
    # If ENABLE_API_AUTH is False, we might want to allow any access for testing.
    # If ENABLE_API_AUTH is True, we require HasValidTokenOrSession.
    # We need to set this dynamically based on ENABLE_API_AUTH.
    # A simple way is to set it here, but a cleaner way might involve middleware
    # or overriding get_permissions in views. For now, let's adjust this:
    'DEFAULT_PERMISSION_CLASSES': [
         # If auth is enabled, require our custom permission
         'swarm.permissions.HasValidTokenOrSession' if ENABLE_API_AUTH else
         # Otherwise, allow anyone (useful for dev when token isn't set)
         'rest_framework.permissions.AllowAny'
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Open Swarm API',
    'DESCRIPTION': 'API for managing autonomous agent swarms',
    'VERSION': '0.4.11',
    'SERVE_INCLUDE_SCHEMA': False,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': { 'format': '[{levelname}] {asctime} - {name}:{lineno} - {message}', 'style': '{', },
        'simple': { 'format': '[{levelname}] {message}', 'style': '{', },
    },
    'handlers': {
        'console': { 'class': 'logging.StreamHandler', 'formatter': 'verbose', },
    },
    'loggers': {
        'django': { 'handlers': ['console'], 'level': get_django_log_level(), 'propagate': False, },
        'swarm': { 'handlers': ['console'], 'level': get_swarm_log_level(), 'propagate': False, },
        'swarm.auth': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'swarm.views': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'swarm.extensions': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'blueprint_django_chat': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'print_debug': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
    },
    'root': { 'handlers': ['console'], 'level': 'WARNING', },
}

REDIS_HOST = get_redis_host()
REDIS_PORT = get_redis_port()

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
CSRF_TRUSTED_ORIGINS = get_django_csrf_trusted_origins()

# --- ComfyUI Configuration for Avatar Generation ---
COMFYUI_ENABLED = is_comfyui_enabled()
COMFYUI_HOST = get_comfyui_host()
COMFYUI_API_ENDPOINT = get_comfyui_api_endpoint()
COMFYUI_QUEUE_ENDPOINT = f"{COMFYUI_HOST}/queue"
COMFYUI_HISTORY_ENDPOINT = f"{COMFYUI_HOST}/history"

# Avatar generation settings
AVATAR_GENERATION_ENABLED = COMFYUI_ENABLED
AVATAR_STORAGE_PATH = BASE_DIR.parent / 'avatars'
AVATAR_URL_PREFIX = '/avatars/'

# Ensure avatar storage directory exists
AVATAR_STORAGE_PATH.mkdir(exist_ok=True)
