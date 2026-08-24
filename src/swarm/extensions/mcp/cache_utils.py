# cache_utils.py

from typing import Any


class DummyCache:
    """A dummy cache that performs no operations."""
    def get(self, key: str, default: Any = None) -> Any:
        return default

    def set(self, key: str, value: Any, timeout: int = None) -> None:
        pass

def get_cache():
    """
    Attempts to retrieve Django's cache. If Django isn't available or configured,
    returns a DummyCache instance.
    """
    try:
        from django.conf import settings
        from django.core.cache import cache as django_cache
        from django.core.exceptions import ImproperlyConfigured

        if not settings.configured:
            # Django settings are not configured; return DummyCache
            return DummyCache()

        return django_cache

    except (ImportError, ImproperlyConfigured):
        # Django is not installed or not properly configured; use DummyCache
        return DummyCache()
