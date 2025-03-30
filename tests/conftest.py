import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import os
import django
from django.apps import apps

# --- Fixtures ---

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    # Option 1: Default behavior (usually creates in-memory :memory: sqlite db)
    # If settings.py DATABASES['default'] is already sqlite/:memory:, this is fine.
    # If settings.py DATABASES['default'] is Postgres, pytest-django *should*
    # create a test_yourdbname, but might fail due to permissions or config.
    print("Allowing Django DB access for session...")
    with django_db_blocker.unblock():
         # If needed, force override here, but let's see settings first
         # from django.conf import settings
         # settings.DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
         pass # Rely on pytest-django for now
    print("Django DB access allowed.")


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    # This fixture ensures that the database is available for any test
    # that implicitly depends on it via other fixtures like test_user or client.
    # The @pytest.mark.django_db on the test *class* or *function* is still
    # the primary way to trigger DB setup for that specific test item.
    pass

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

