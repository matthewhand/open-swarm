import logging
import os
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
# Import BasePermission for creating custom permissions
from rest_framework.permissions import BasePermission
from rest_framework import exceptions
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# Import AnonymousUser
from django.contrib.auth.models import AnonymousUser
# Keep get_user_model if CustomSessionAuthentication needs it or for future user mapping
from django.contrib.auth import get_user_model

logger = logging.getLogger('swarm.auth')
User = get_user_model()

# ==============================================================================
# Authentication Classes (Determine *who* the user is)
# ==============================================================================

# --- Static Token Authentication ---
class StaticTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests based on a static API token passed in a header
    (Authorization: Bearer <token> or X-API-Key: <token>).

    Returns (AnonymousUser, token) on success. This allows permission classes
    to check request.auth to see if token authentication succeeded, even though
    no specific user model is associated with the token.
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        """
        Attempts to authenticate using a static token.
        """
        logger.debug("[Auth][StaticToken] Attempting static token authentication.")
        # Retrieve the expected token from settings.
        expected_token = getattr(settings, 'SWARM_API_KEY', None)

        # If no token is configured in settings, this method cannot authenticate.
        if not expected_token:
            logger.error("[Auth][StaticToken] SWARM_API_KEY is not set in Django settings. Cannot use static token auth.")
            return None # Indicate authentication method did not run or failed pre-check

        # Extract the provided token from standard Authorization header or custom X-API-Key header.
        provided_token = None
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth_header) == 2 and auth_header[0].lower() == self.keyword.lower():
            provided_token = auth_header[1]
            logger.debug("[Auth][StaticToken] Found token in Authorization header.")
        else:
            provided_token = request.META.get('HTTP_X_API_KEY')
            if provided_token:
                logger.debug("[Auth][StaticToken] Found token in X-API-Key header.")

        # If no token was found in either header, authentication fails for this method.
        if not provided_token:
            logger.debug("[Auth][StaticToken] No token found in relevant headers.")
            return None # Indicate authentication method did not find credentials

        # Compare the provided token with the expected token.
        # NOTE: For production, consider using a constant-time comparison function
        #       to mitigate timing attacks if the token is highly sensitive.
        if provided_token == expected_token:
            logger.info("[Auth][StaticToken] Static token authentication successful.")
            # Return AnonymousUser and the token itself as request.auth.
            # This signals successful authentication via token without linking to a specific User model.
            return (AnonymousUser(), provided_token)
        else:
            # Token was provided but did not match. Raise AuthenticationFailed.
            logger.warning(f"[Auth][StaticToken] Invalid static token provided.")
            raise exceptions.AuthenticationFailed(_("Invalid API Key."))

# --- Custom *Synchronous* Session Authentication ---
class CustomSessionAuthentication(SessionAuthentication):
    """
    Standard Django Session Authentication provided by DRF.
    Relies on Django's session middleware to populate request.user.
    This class itself is synchronous, but the underlying session loading
    needs to be handled correctly in async views (e.g., via middleware or wrappers).
    """
    # No override needed unless customizing session behavior.
    pass


# ==============================================================================
# Permission Classes (Determine *if* access is allowed)
# ==============================================================================

class HasValidTokenOrSession(BasePermission):
    """
    Allows access if EITHER:
    1. Static token authentication succeeded (request.auth is not None).
    2. Session authentication succeeded (request.user is authenticated).
    """
    message = 'Authentication credentials were not provided or are invalid (Requires valid API Key or active session).'

    def has_permission(self, request, view):
        """
        Checks if the request has valid authentication via token or session.
        """
        # Check if static token authentication was successful.
        # StaticTokenAuthentication returns (AnonymousUser, token), so request.auth will be the token.
        has_valid_token = getattr(request, 'auth', None) is not None
        if has_valid_token:
            logger.debug("[Perm][TokenOrSession] Access granted via static token (request.auth is set).")
            return True

        # Check if session authentication was successful.
        # request.user should be populated by SessionAuthentication/AuthMiddleware.
        user = getattr(request, 'user', None)
        has_valid_session = user is not None and user.is_authenticated
        if has_valid_session:
            logger.debug(f"[Perm][TokenOrSession] Access granted via authenticated session user: {user}")
            return True

        # If neither condition is met, deny permission.
        logger.debug("[Perm][TokenOrSession] Access denied: No valid token (request.auth=None) and no authenticated session user.")
        return False

