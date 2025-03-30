import logging
import secrets # For secure comparison
from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

class HasValidTokenOrSession(BasePermission):
    """
    Custom permission to allow access based on:
    1. Valid API Token (if settings.ENABLE_API_AUTH is True and settings.SWARM_API_KEY is set).
    2. Active Django session (if API token is not provided, or if auth is disabled/no key set).
    """
    keyword = 'Bearer'
    auth_header_name = 'HTTP_AUTHORIZATION' # Standard header name in Django request.META

    def has_permission(self, request, view):
        # --- Check Settings ---
        auth_enabled = getattr(settings, 'ENABLE_API_AUTH', False)
        configured_key = getattr(settings, 'SWARM_API_KEY', None)

        # --- Check for API Token in Header ---
        auth_header = request.META.get(self.auth_header_name, '').split()
        token_provided = len(auth_header) == 2 and auth_header[0] == self.keyword

        if token_provided:
            token = auth_header[1]
            # If auth is enabled AND a key is configured, validate the token
            if auth_enabled and configured_key:
                if secrets.compare_digest(token, configured_key):
                    logger.debug("API Key authentication successful.")
                    # Set request.user to an anonymous user or a specific API user if needed
                    # request.user = AnonymousUser() # Or fetch/create a dedicated API user
                    # request.auth = token # Set auth token if needed by other parts
                    return True
                else:
                    logger.warning("Invalid API Key provided.")
                    # Fail immediately if an invalid token was provided when one was expected
                    raise AuthenticationFailed("Invalid API token.")
            elif auth_enabled and not configured_key:
                # Auth enabled, but no key set - token provided but ignored
                logger.warning("API Auth enabled but no SWARM_API_KEY set. Ignoring provided token, falling back to session auth.")
                # Fall through to session check
            else: # Auth disabled - token provided but ignored
                logger.debug("API Auth disabled. Ignoring provided token, falling back to session auth.")
                # Fall through to session check
        else:
            # --- No Token Provided ---
            # If auth is enabled AND a key is configured, token is REQUIRED
            if auth_enabled and configured_key:
                logger.warning("API Key authentication required but no token provided.")
                raise AuthenticationFailed("API token required.")
            # Otherwise (auth disabled OR no key configured), fall through to session check

        # --- Fallback to Session Authentication ---
        # This check runs if:
        # - No token was provided AND (auth is disabled OR no key is configured)
        # - Token was provided BUT (auth is disabled OR no key is configured)
        is_authenticated_by_session = request.user and request.user.is_authenticated
        if is_authenticated_by_session:
             logger.debug("Session authentication successful.")
        else:
             logger.debug("No valid API token or session found.")
        return is_authenticated_by_session

