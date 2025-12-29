from unittest.mock import MagicMock

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from rest_framework import exceptions

from swarm.auth import (
    CustomSessionAuthentication,
    HasValidTokenOrSession,
    StaticTokenAuthentication,
)


class TestStaticTokenAuthentication:
    def setup_method(self):
        self.auth = StaticTokenAuthentication()
        self.factory = RequestFactory()

    def test_authenticate_no_token_in_settings(self):
        """Test authentication fails when SWARM_API_KEY is not set"""
        # Ensure SWARM_API_KEY is not set
        if hasattr(settings, 'SWARM_API_KEY'):
            delattr(settings, 'SWARM_API_KEY')

        request = self.factory.get('/api/test/')
        result = self.auth.authenticate(request)
        assert result is None

    def test_authenticate_no_token_in_request(self):
        """Test authentication returns None when no token provided"""
        settings.SWARM_API_KEY = 'test-key-123'
        request = self.factory.get('/api/test/')
        result = self.auth.authenticate(request)
        assert result is None

    def test_authenticate_valid_token_authorization_header(self):
        """Test successful authentication with Authorization header and comprehensive validation"""
        settings.SWARM_API_KEY = 'test-key-123'
        request = self.factory.get(
            '/api/test/',
            HTTP_AUTHORIZATION='Bearer test-key-123'
        )
        result = self.auth.authenticate(request)

        # Comprehensive authentication validation
        assert result is not None, "Authentication should succeed with valid token"
        assert len(result) == 2, "Authentication result should contain user and token"
        assert isinstance(result[0], AnonymousUser), "User should be AnonymousUser for token auth"
        assert result[1] == 'test-key-123', "Token should match the provided token"

        # Validate request state preservation
        assert request.META['HTTP_AUTHORIZATION'] == 'Bearer test-key-123', "Request should preserve auth header"
        assert request.method == 'GET', "Request method should be preserved"
        assert request.path == '/api/test/', "Request path should be preserved"

        # Validate settings interaction
        assert settings.SWARM_API_KEY == 'test-key-123', "Settings should contain the configured key"

    def test_authenticate_valid_token_x_api_key_header(self):
        """Test successful authentication with X-API-Key header"""
        settings.SWARM_API_KEY = 'test-key-456'
        request = self.factory.get(
            '/api/test/',
            HTTP_X_API_KEY='test-key-456'
        )
        result = self.auth.authenticate(request)
        assert result is not None
        assert isinstance(result[0], AnonymousUser)
        assert result[1] == 'test-key-456'

    def test_authenticate_invalid_token(self):
        """Test authentication fails with invalid token"""
        settings.SWARM_API_KEY = 'valid-key-123'
        request = self.factory.get(
            '/api/test/',
            HTTP_AUTHORIZATION='Bearer invalid-key-456'
        )

        with pytest.raises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_malformed_authorization_header(self):
        """Test authentication handles malformed Authorization header"""
        settings.SWARM_API_KEY = 'test-key-123'
        request = self.factory.get(
            '/api/test/',
            HTTP_AUTHORIZATION='Bearer'  # Missing token
        )
        result = self.auth.authenticate(request)
        assert result is None

    def test_authenticate_wrong_keyword_in_authorization_header(self):
        """Test authentication ignores wrong keyword in Authorization header"""
        settings.SWARM_API_KEY = 'test-key-123'
        request = self.factory.get(
            '/api/test/',
            HTTP_AUTHORIZATION='Token test-key-123'  # Wrong keyword
        )
        result = self.auth.authenticate(request)
        assert result is None


class TestCustomSessionAuthentication:
    def setup_method(self):
        self.auth = CustomSessionAuthentication()

    def test_custom_session_auth_inherits_from_session_auth(self):
        """Test that CustomSessionAuthentication inherits from SessionAuthentication"""
        from rest_framework.authentication import SessionAuthentication
        assert issubclass(CustomSessionAuthentication, SessionAuthentication)


class TestHasValidTokenOrSession:
    def setup_method(self):
        self.permission = HasValidTokenOrSession()
        self.factory = RequestFactory()

    def test_has_permission_with_valid_token(self):
        """Test permission granted with valid token"""
        request = self.factory.get('/api/test/')
        request.auth = 'valid-token-123'  # Simulate token auth success

        result = self.permission.has_permission(request, None)
        assert result is True

    def test_has_permission_with_authenticated_user(self):
        """Test permission granted with authenticated user"""
        request = self.factory.get('/api/test/')
        # Simulate authenticated user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        request.user = mock_user

        result = self.permission.has_permission(request, None)
        assert result is True

    def test_has_permission_no_auth(self):
        """Test permission denied with no authentication"""
        request = self.factory.get('/api/test/')
        # No auth token and no authenticated user
        request.auth = None
        request.user = None

        result = self.permission.has_permission(request, None)
        assert result is False

    def test_has_permission_unauthenticated_user(self):
        """Test permission denied with unauthenticated user"""
        request = self.factory.get('/api/test/')
        # Unauthenticated user
        mock_user = MagicMock()
        mock_user.is_authenticated = False
        request.user = mock_user
        request.auth = None

        result = self.permission.has_permission(request, None)
        assert result is False

    def test_has_permission_anonymous_user(self):
        """Test permission denied with anonymous user"""
        request = self.factory.get('/api/test/')
        # Anonymous user
        request.user = AnonymousUser()
        request.auth = None

        result = self.permission.has_permission(request, None)
        assert result is False
