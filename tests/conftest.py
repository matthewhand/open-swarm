import os
import pytest
import django
from django.conf import settings
from swarm.settings import append_blueprint_apps, BLUEPRINTS_DIR
import logging

logger = logging.getLogger(__name__)

def pytest_configure():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'swarm.settings'
    os.environ['SWARM_BLUEPRINTS'] = 'university'  # Force university blueprint
    logger.info(f"Set SWARM_BLUEPRINTS to: {os.environ['SWARM_BLUEPRINTS']}")
    if not settings.configured:
        django.setup()
    append_blueprint_apps()
    logger.info(f"INSTALLED_APPS after append: {settings.INSTALLED_APPS}")

@pytest.fixture(scope='session', autouse=True)
def django_db_setup(django_db_setup, django_db_blocker):
    from swarm.extensions.blueprint import discover_blueprints
    all_blueprints = discover_blueprints([str(BLUEPRINTS_DIR)])
    logger.info(f"Discovered blueprints: {list(all_blueprints.keys())}")
    assert 'university' in all_blueprints, f"University blueprint not found in {BLUEPRINTS_DIR}"
    assert 'blueprints.university' in settings.INSTALLED_APPS, "University blueprint not in INSTALLED_APPS"
    with django_db_blocker.unblock():
        yield
