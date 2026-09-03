#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def main():
    # Define the base directory
    base_dir = Path(__file__).resolve().parent

    # XDG ~/.config/swarm/.env (primary) + checkout .env (fallback)
    try:
        # src/manage.py → project root is parent of src/
        from swarm.utils.dotenv_load import load_swarm_dotenv
        load_swarm_dotenv(project_root=base_dir.parent)
    except Exception:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=base_dir.parent / '.env')

    # Database health check: prevent crash-looping on quota-exceeded DB
    # Only run for server commands (runserver, uvicorn via daphne, etc.)
    # Skip for management commands like migrate, shell, etc.
    server_commands = {'runserver', 'daphne', 'grpcrunserver', 'runserver_plus'}
    if len(sys.argv) > 1 and sys.argv[1] in server_commands:
        from swarm.utils.db_health import enforce_database_health_on_startup
        enforce_database_health_on_startup()

    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swarm.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
