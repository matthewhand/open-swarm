import pytest


@pytest.fixture(autouse=True, scope="function")
def _set_root_urlconf(settings):
    """
    Ensure API tests resolve /v1/models by wiring src.swarm.urls.
    """
    original = settings.ROOT_URLCONF
    settings.ROOT_URLCONF = "src.swarm.urls"
    yield settings
    settings.ROOT_URLCONF = original
