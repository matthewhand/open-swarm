import logging
from rest_framework.permissions import BasePermission
from django.conf import settings
from swarm.auth import StaticTokenAuthentication # Import for type checking

logger = logging.getLogger(__name__)

class HasValidTokenOrSession(BasePermission):
    """
    Allows access if the user is authenticated via a valid session
    OR if a valid static API token was provided (indicated by request.auth).
    """

    def has_permission(self, request, view):
        # Check if standard Django user authentication succeeded (Session)
        # This user comes from AuthenticationMiddleware + CustomSessionAuthentication
        is_session_authenticated = request.user and request.user.is_authenticated
        if is_session_authenticated:
            logger.debug("[Permission] Access granted via authenticated session user.")
            return True

        # Check if StaticTokenAuthentication succeeded.
        # We modified StaticTokenAuthentication to return (AnonymousUser(), token)
        # DRF populates request.auth with the second element of the tuple (the token).
        # We also check the authenticator type for robustness.
        is_static_token_auth = (
            request.successful_authenticator and
            isinstance(request.successful_authenticator, StaticTokenAuthentication) and
            request.auth is not None # Check if request.auth (the token) was set
        )

        if is_static_token_auth:
             logger.debug("[Permission] Access granted via valid static API token.")
             return True

        logger.debug("[Permission] Access denied. No valid session or static token found.")
        return False

