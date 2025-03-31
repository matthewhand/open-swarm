"""
Django settings for swarm project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

BASE_DIR = Path(__file__).resolve().parent.parent # Points to src/

# --- Load .env file ---
dotenv_path = BASE_DIR.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)
print(f"[Settings] Attempted to load .env from: {dotenv_path}")
# ---

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 't')
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# --- Custom Swarm Settings ---
# Load the token from environment
_raw_api_token = os.getenv('API_AUTH_TOKEN')

# *** Only enable API auth if the token is actually set ***
ENABLE_API_AUTH = bool(_raw_api_token)
SWARM_API_KEY = _raw_api_token # Assign the loaded token (or None)

if ENABLE_API_AUTH:
    # Add assertion to satisfy type checkers within this block
    assert SWARM_API_KEY is not None, "SWARM_API_KEY cannot be None when ENABLE_API_AUTH is True"
    print(f"[Settings] SWARM_API_KEY loaded: {SWARM_API_KEY[:4]}...{SWARM_API_KEY[-4:]}")
    print("[Settings] ENABLE_API_AUTH is True.")
else:
    print("[Settings] API_AUTH_TOKEN env var not set. SWARM_API_KEY is None.")
    print("[Settings] ENABLE_API_AUTH is False.")


SWARM_CONFIG_PATH = os.getenv('SWARM_CONFIG_PATH', str(BASE_DIR.parent / 'swarm_config.json'))
BLUEPRINT_DIRECTORY = os.getenv('BLUEPRINT_DIRECTORY', str(BASE_DIR / 'swarm' / 'blueprints'))
# --- End Custom Swarm Settings ---

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'swarm',
]

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'db.sqlite3',
        'TEST': {
            'NAME': BASE_DIR.parent / 'test_db.sqlite3',
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
STATICFILES_DIRS = [ BASE_DIR / "swarm" / "static", ]

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
    'VERSION': '0.2.0',
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
        'django': { 'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), 'propagate': False, },
        'swarm': { 'handlers': ['console'], 'level': os.getenv('SWARM_LOG_LEVEL', 'DEBUG'), 'propagate': False, },
        'swarm.auth': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'swarm.views': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'swarm.extensions': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'blueprint_django_chat': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
        'print_debug': { 'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, },
    },
    'root': { 'handlers': ['console'], 'level': 'WARNING', },
}

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
CSRF_TRUSTED_ORIGINS = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')

