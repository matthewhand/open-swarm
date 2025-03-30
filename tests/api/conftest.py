# --- Content for tests/api/conftest.py ---
import pytest
from django.test import AsyncClient
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async # Make sure this is imported

User = get_user_model()

@pytest.fixture(scope='function') # Use function scope if tests modify the user/db
def test_user(db):
    """Fixture to create a standard test user."""
    # Use get_or_create to avoid issues if user exists from other tests in session
    user, created = User.objects.get_or_create(username='testuser')
    if created:
        user.set_password('password')
        user.save()
    return user

@pytest.fixture()
async def async_client():
    """Provides a standard async client."""
    # Note: AsyncClient instances are generally stateful regarding cookies/sessions
    # If tests need isolation, consider function scope or manual cleanup.
    return AsyncClient()

@pytest.fixture()
async def authenticated_async_client(db, test_user):
    """Provides an async client logged in as test_user."""
    client = AsyncClient()
    # Explicitly wrap force_login with sync_to_async to handle potential sync issues
    await sync_to_async(client.force_login)(test_user)
    return client
