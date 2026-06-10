"""Shared fixtures for the async chat-completions API tests.

Ported from archive/local-main-2025-04.
"""
import os

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import AsyncClient

# Async views touch the ORM through sync_to_async wrappers; allow this in the
# test event loop when the suite is run directly via pytest (scripts/run_tests.py
# sets this too).
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(scope='function')  # Use function scope if tests modify the user/db
def test_user(db):
    """Fixture to create a standard test user."""
    User = get_user_model()
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
