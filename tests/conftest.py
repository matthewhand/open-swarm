import os
import pytest
import django
from django.conf import settings
# Import BLUEPRINTS_DIR if needed for discovery check
from swarm.settings import BLUEPRINTS_DIR # Removed append_blueprint_apps
import logging
from pathlib import Path
# Removed call_command import

logger = logging.getLogger(__name__)

def pytest_configure():
    """Configures Django settings before tests run."""
    os.environ['DJANGO_SETTINGS_MODULE'] = 'swarm.settings'
    # SWARM_BLUEPRINTS might still be needed if discovery logic uses it
    os.environ['SWARM_BLUEPRINTS'] = 'university'
    logger.info(f"pytest_configure: Set SWARM_BLUEPRINTS to: {os.environ['SWARM_BLUEPRINTS']}")

    # Ensure Django is set up ONLY ONCE
    if not settings.configured:
        # Settings should now load INSTALLED_APPS correctly *before* setup
        django.setup()
        logger.info("pytest_configure: Django setup completed.")
    else:
        logger.info("pytest_configure: Django already configured.")

    # Log INSTALLED_APPS *after* setup to see the final list
    logger.info(f"pytest_configure: Final INSTALLED_APPS: {settings.INSTALLED_APPS}")


@pytest.fixture(scope='session', autouse=True)
def django_db_setup_fixture(django_db_setup, django_db_blocker):
    """
    Ensures DB setup runs correctly. App verification is less critical now
    as settings.py handles adding the app during testing.
    """
    logger.info("django_db_setup_fixture: Running fixture.")

    # Optional: Verify blueprint discovery still works if needed
    # try:
    #     from swarm.extensions.blueprint import discover_blueprints
    #     bp_dir_path = Path(BLUEPRINTS_DIR) if isinstance(BLUEPRINTS_DIR, str) else BLUEPRINTS_DIR
    #     all_blueprints = discover_blueprints([str(bp_dir_path)])
    #     logger.info(f"django_db_setup_fixture: Discovered blueprints: {list(all_blueprints.keys())}")
    #     required_blueprint = os.environ.get('SWARM_BLUEPRINTS', 'university')
    #     assert required_blueprint in all_blueprints, f"{required_blueprint} blueprint not found in {BLUEPRINTS_DIR}"
    # except Exception as e:
    #     logger.warning(f"django_db_setup_fixture: Blueprint discovery check failed (non-fatal): {e}")

    # Check the actual Django app path in INSTALLED_APPS (still useful)
    required_blueprint = os.environ.get('SWARM_BLUEPRINTS', 'university')
    expected_app_path = f'blueprints.{required_blueprint}'
    assert expected_app_path in settings.INSTALLED_APPS, \
        f"{expected_app_path} blueprint app not in INSTALLED_APPS: {settings.INSTALLED_APPS}"

    logger.info(f"django_db_setup_fixture: App '{expected_app_path}' found in INSTALLED_APPS. Unblocking DB.")
    with django_db_blocker.unblock():
        yield # Let the tests run
    logger.info("django_db_setup_fixture: Fixture teardown complete.")

# Add Path import if not already present globally
from pathlib import Path
