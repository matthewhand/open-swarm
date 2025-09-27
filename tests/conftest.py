import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async

# --- Fixtures ---

def pytest_collection_modifyitems(config, items):
    """Optionally skip asyncio-marked tests in restricted environments.

    Set DISABLE_ASYNC_TESTS=1 to skip tests marked with @pytest.mark.asyncio.
    This is useful in sandboxes that prohibit socketpair(), which
    pytest-asyncio needs to create an event loop.
    """
    if os.getenv("DISABLE_ASYNC_TESTS", "").lower() in ("1", "true", "yes", "y"):
        skip_async = pytest.mark.skip(reason="Async tests disabled in restricted env (socketpair not permitted)")
        for item in items:
            if "asyncio" in item.keywords:
                item.add_marker(skip_async)

# Note: Avoid overriding pytest-django's internal django_db_setup fixture.
# Doing so can lead to subtle ordering/teardown issues in large test runs.
# If you need to perform session-wide DB tweaks, introduce a differently-named
# fixture and depend on pytest-django's built-in setup implicitly.


# Avoid forcing DB access on every single test by default — this can interfere
# with Django TestCase transaction management and increase flakiness. Tests
# that need the DB should request the `db` fixture or subclass Django's
# TestCase/TransactionTestCase explicitly.

@pytest.fixture
def mock_openai_client():
    from openai import AsyncOpenAI
    client = MagicMock(spec=AsyncOpenAI)
    client.chat.completions.create = AsyncMock()
    return client

@pytest.fixture
def mock_model_instance(mock_openai_client):
    try:
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        with patch('agents.models.openai_chatcompletions.AsyncOpenAI', return_value=mock_openai_client):
             model_mock = MagicMock(spec=OpenAIChatCompletionsModel)
             model_mock.call_model = AsyncMock(return_value=("Mock response", None, None))
             model_mock.get_token_count = MagicMock(return_value=10)
             yield model_mock
    except ImportError:
         pytest.skip("Skipping mock_model_instance fixture: openai-agents not fully available.")

# Removed @pytest.mark.django_db from fixture - keep it on the test classes/functions instead
@pytest.fixture
def test_user(db): # db fixture ensures DB is available *within* this fixture's scope
    """Creates a standard test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Use update_or_create for robustness
    user, created = User.objects.update_or_create(
        username='testuser',
        defaults={'is_staff': False, 'is_superuser': False}
    )
    if created:
        user.set_password('password')
        user.save()
    return user

@pytest.fixture
def api_client(db): # Request db fixture here too
     from rest_framework.test import APIClient
     return APIClient()

@pytest.fixture
def authenticated_client(api_client, test_user): # Relies on test_user, which relies on db
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
async def authenticated_async_client(async_client, test_user):
    await sync_to_async(async_client.force_login)(test_user)
    return async_client

@pytest.fixture
def mock_load_config():
    with patch('swarm.views.settings_manager.load_config') as mock:
        yield mock
