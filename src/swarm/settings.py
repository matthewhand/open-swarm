import os
import sys
from django.db.backends.signals import connection_created
from django.dispatch import receiver
import logging
from pathlib import Path
from dotenv import load_dotenv

# Disable CORS in Django for development purposes, allowing all origins.
CORS_ALLOW_ALL_ORIGINS = True

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

logging.basicConfig(level=(logging.DEBUG if DEBUG else logging.INFO), format='%(levelname)s:%(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
CUSTOM_BASE_DIR = os.getenv("SWARM_BASE_DIR")
if CUSTOM_BASE_DIR:
    BASE_DIR = Path(CUSTOM_BASE_DIR)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    if not (BASE_DIR / 'manage.py').exists():  # Ensure we're in the project root (Docker fix)
        BASE_DIR = Path('/app')
logger.debug(f"BASE_DIR resolved to: {BASE_DIR}")

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / '.env')

# Define a logs directory within the base directory
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Add the project root and the app directory to the system path
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / 'src/swarm/'))
logger.debug(f"System path updated: {sys.path}")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("API_AUTH_KEY", 'django-insecure-your-secret-key')

# Blueprint discovery and configuration
blueprints_path_env = os.getenv("BLUEPRINTS_PATH", "").strip()
if blueprints_path_env:
    BLUEPRINTS_DIR = Path(blueprints_path_env)
elif (BASE_DIR / 'blueprints').exists():
    BLUEPRINTS_DIR = BASE_DIR / 'blueprints'
else:
    BLUEPRINTS_DIR = Path(os.path.expanduser("~/.swarm/blueprints"))
swarm_blueprints_env = os.getenv("SWARM_BLUEPRINTS", "").strip()
SWARM_BLUEPRINTS = [name.strip() for name in swarm_blueprints_env.split(',') if name.strip()] if swarm_blueprints_env else []
logger.info(f"Discovered SWARM_BLUEPRINTS env: {SWARM_BLUEPRINTS}")

ALLOWED_HOSTS = ['*']  # Adjust as needed in production

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'rest_framework',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drf_spectacular',
    'corsheaders',
    'channels',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'swarm',
    'swarm.extensions.blueprint.modes.rest_mode',
    'blueprints.university',
]

def append_blueprint_apps():
    """Dynamically append valid blueprint apps to INSTALLED_APPS with normalized labels."""
    if not os.path.exists(BLUEPRINTS_DIR):
        logger.warning(f"Blueprint directory {BLUEPRINTS_DIR} does not exist.")
        return
    for blueprint_name in os.listdir(BLUEPRINTS_DIR):
        app_path = os.path.join(BLUEPRINTS_DIR, blueprint_name)
        blueprint_file = os.path.join(app_path, f'blueprint_{blueprint_name}.py')
        if os.path.isdir(app_path) and os.path.exists(blueprint_file):
            # Normalize app label: replace hyphens with underscores
            normalized_name = blueprint_name.replace('-', '_')
            app_label = f"blueprints.{normalized_name}"
            if app_label not in INSTALLED_APPS:
                logger.debug(f"Adding {app_label} to INSTALLED_APPS")
                INSTALLED_APPS.append(app_label)
        else:
            logger.debug(f"Skipping {blueprint_name}: no valid blueprint file found.")

# Append blueprints at settings load time
append_blueprint_apps()

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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
        'DIRS': [BASE_DIR / 'src/swarm/templates'],
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

# Database
DJANGO_DATABASE = os.getenv("DJANGO_DATABASE", "sqlite").lower()
if DJANGO_DATABASE == "postgres":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv("POSTGRES_DB", "swarm"),
            'USER': os.getenv("POSTGRES_USER", "postgres"),
            'PASSWORD': os.getenv("POSTGRES_PASSWORD", ""),
            'HOST': os.getenv("POSTGRES_HOST", "localhost"),
            'PORT': os.getenv("POSTGRES_PORT", "5432"),
        }
    }
elif DJANGO_DATABASE == "sqlite":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    raise ValueError(f"Invalid value for DJANGO_DATABASE: {DJANGO_DATABASE}. Must be 'sqlite' or 'postgres'.")

if os.getenv("STATEFUL_CHAT_ID_PATH") and DJANGO_DATABASE != "postgres":
    logger.warning("⚠️ Stateful chat enabled with SQLite. Consider 'postgres' for scalability.")

@receiver(connection_created)
def set_sqlite_optimizations(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        cursor.execute('PRAGMA temp_store=MEMORY;')
        cursor.execute('PRAGMA mmap_size=30000000000;')
        cursor.execute('PRAGMA cache_size=-5000;')
        cursor.execute('PRAGMA busy_timeout=5000;')
        cursor.close()

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = False

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "src/swarm/static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file_rest_mode': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'rest_mode.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'open_swarm.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console', 'file_default'], 'level': 'INFO', 'propagate': True},
        'rest_mode': {'handlers': ['console', 'file_rest_mode'], 'level': 'DEBUG', 'propagate': False},
        '': {'handlers': ['console', 'file_default'], 'level': 'INFO'},
    },
}

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_SIGNUP_REDIRECT_URL = "/django_chat/"
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_REQUIRED = False

USE_DJANGO_CACHE = True
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

INSTALLED_APPS += ['rest_framework.authtoken']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['swarm.auth.EnvOrTokenAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Discover blueprint settings
if not os.getenv("SWARM_CLI"):
    config_path = BASE_DIR / "swarm_config.json"
    if config_path.exists():
        try:
            import json
            with open(config_path, "r") as f:
                config_data = json.load(f)
            static_blueprints = config_data.get("blueprints", {})
            for blueprint_name, blueprint_conf in static_blueprints.items():
                allowed = os.getenv("SWARM_BLUEPRINTS", "").strip()
                if allowed and blueprint_name not in [bp.strip() for bp in allowed.split(",")]:
                    continue
                bp_settings_path = Path(blueprint_conf["path"]) / "settings.py"
                if bp_settings_path.exists():
                    logger.info(f"Loading static settings for blueprint: {blueprint_name}")
                    with open(bp_settings_path, "r") as f:
                        code = compile(f.read(), str(bp_settings_path), "exec")
                        exec(code, globals())
                else:
                    logger.warning(f"Settings file not found for blueprint '{blueprint_name}' at {bp_settings_path}")
        except Exception as e:
            logger.error(f"Error loading blueprint config from swarm_config.json: {e}", exc_info=True)
    else:
        logger.info(f"swarm_config.json not found in BASE_DIR: {BASE_DIR}, skipping blueprint settings loading")
else:
    logger.info("CLI mode detected; skipping blueprint settings loading")

if 'pytest' in sys.argv[0]:
    MIGRATION_MODULES = {'swarm': None}

logger.debug(f"Final INSTALLED_APPS: {INSTALLED_APPS}")
