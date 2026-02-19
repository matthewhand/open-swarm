# src/swarm/wsgi.py

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Define the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / '.env')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swarm.settings')

application = get_wsgi_application()
