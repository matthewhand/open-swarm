"""
Django settings for swarm project.
"""

import os
import sys
from pathlib import Path
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BLUEPRINTS_DIR = PROJECT_ROOT / 'blueprints'

# --- Determine if running under pytest ---
TESTING = 'pytest' in sys.modules

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-YOUR_FALLBACK_KEY_HERE_CHANGE_ME')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    # Local apps
    'swarm.apps.SwarmConfig',
]

# --- Conditionally add blueprint apps for TESTING ---
# This ensures the app is known *before* django.setup() is called by pytest-django
if TESTING:
    # Add specific apps needed for testing
    # We know 'university' is needed based on SWARM_BLUEPRINTS in conftest
    _test_apps_to_add = ['blueprints.university'] # Hardcoding for University tests specifically
    for app in _test_apps_to_add:
        if app not in INSTALLED_APPS:
            # Use insert for potentially better ordering if it matters, otherwise append is fine
            INSTALLED_APPS.insert(0, app) # Or INSTALLED_APPS.append(app)
            logging.info(f"Settings [TESTING]: Added '{app}' to INSTALLED_APPS.")
    # Ensure SWARM_BLUEPRINTS is set if your conftest or other logic relies on it
    # Note: Setting it here might be redundant if conftest sets it too.
    if 'SWARM_BLUEPRINTS' not in os.environ:
         os.environ['SWARM_BLUEPRINTS'] = 'university'
         logging.info(f"Settings [TESTING]: Set SWARM_BLUEPRINTS='university'")

else:
    # --- Dynamic App Loading for Production/Development ---
    _INITIAL_BLUEPRINT_APPS = []
    _swarm_blueprints_env = os.getenv('SWARM_BLUEPRINTS')
    _log_source = "Not Set"
    if _swarm_blueprints_env:
        _blueprint_names = [name.strip() for name in _swarm_blueprints_env.split(',') if name.strip()]
        _INITIAL_BLUEPRINT_APPS = [f'blueprints.{name}' for name in _blueprint_names if name.replace('_', '').isidentifier()]
        _log_source = "SWARM_BLUEPRINTS env var"
        logging.info(f"Settings: Found blueprints from env var: {_INITIAL_BLUEPRINT_APPS}")
    else:
        _log_source = "directory scan"
        try:
            if BLUEPRINTS_DIR.is_dir():
                 for item in BLUEPRINTS_DIR.iterdir():
                     if item.is_dir() and (item / '__init__.py').exists():
                         if item.name.replace('_', '').isidentifier():
                             _INITIAL_BLUEPRINT_APPS.append(f'blueprints.{item.name}')
            logging.info(f"Settings: Found blueprints from directory scan: {_INITIAL_BLUEPRINT_APPS}")
        except Exception as e:
            logging.error(f"Settings: Error discovering blueprint apps during initial load: {e}")

    # Add dynamically discovered apps for non-testing scenarios
    for app in _INITIAL_BLUEPRINT_APPS:
         if app not in INSTALLED_APPS:
              INSTALLED_APPS.append(app)
              logging.info(f"Settings [{_log_source}]: Added '{app}' to INSTALLED_APPS.")
# --- End App Loading Logic ---

# Ensure INSTALLED_APPS is a list for compatibility
if isinstance(INSTALLED_APPS, tuple):
    INSTALLED_APPS = list(INSTALLED_APPS)

logging.info(f"Settings: Final INSTALLED_APPS = {INSTALLED_APPS}")


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'swarm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

# Database
SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', BASE_DIR / 'db.sqlite3')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SQLITE_DB_PATH,
    }
}
DJANGO_DATABASE = DATABASES['default']


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'assets',
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'swarm.auth.EnvOrTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
       'rest_framework.permissions.IsAuthenticated',
    )
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Open Swarm API',
    'DESCRIPTION': 'API for the Open Swarm multi-agent collaboration framework.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
         'standard': {
            'format': '[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False, },
        'django.request': { 'handlers': ['console'], 'level': 'WARNING', 'propagate': False, },
        'swarm': { 'handlers': ['console'], 'level': 'DEBUG' if DEBUG else 'INFO', 'propagate': False, },
        'swarm.extensions': { 'handlers': ['console'], 'level': 'DEBUG' if DEBUG else 'INFO', 'propagate': False, },
        'blueprints': { 'handlers': ['console'], 'level': 'DEBUG' if DEBUG else 'INFO', 'propagate': False, },
    },
}

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Login URL
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/chatbot/'

# Redis settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Adjust DB for testing if TESTING flag is set
if TESTING:
     print("Pytest detected: Adjusting settings for testing.")
     DATABASES['default']['NAME'] = ':memory:'
