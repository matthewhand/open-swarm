import hmac
import logging

from django.conf import settings

# Keep get_user_model if CustomSessionAuthentication needs it or for future user mapping
from django.contrib.auth import get_user_model

# Import AnonymousUser
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, SessionAuthentication

# Import BasePermission for creating custom permissions
from rest_framework.permissions import AllowAny, BasePermission

logger = logging.getLogger('swarm.auth')
User = get_user_model()

# ==============================================================================
# Authentication Classes (Determine *who* the user is)
# ==============================================================================

# --- Static Token Authentication ---
class StaticTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests based on static API token(s) passed in a header
    (Authorization: Bearer <token> or X-API-Key: <token>).

    Accepts any token in ``settings.SWARM_API_KEYS`` (or the single
    ``settings.SWARM_API_KEY`` when the list is empty). On match returns
    ``(AnonymousUser(), provided_token)`` so ``request.auth`` is the presenting
    credential and ``request_principal`` can hash that specific token.
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        """
        Attempts to authenticate using a static token against all accepted keys.
        """
        logger.debug("[Auth][StaticToken] Attempting static token authentication.")
        # Preferred: multi-key list. Fall back to single SWARM_API_KEY.
        accepted = list(getattr(settings, 'SWARM_API_KEYS', None) or [])
        if not accepted:
            single = getattr(settings, 'SWARM_API_KEY', None)
            if single:
                accepted = [single]

        # If no tokens configured, this method cannot authenticate.
        if not accepted:
            logger.error(
                "[Auth][StaticToken] SWARM_API_KEY(S) not set in Django settings. "
                "Cannot use static token auth."
            )
            return None  # Indicate authentication method did not run or failed pre-check

        # Extract the provided token from standard Authorization header or
        # custom X-API-Key header.
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
            return None  # Indicate authentication method did not find credentials

        # Constant-time compare against each accepted token (small N).
        provided_str = str(provided_token)
        for expected in accepted:
            if hmac.compare_digest(provided_str, str(expected)):
                logger.info("[Auth][StaticToken] Static token authentication successful.")
                # Return AnonymousUser and the *provided* token as request.auth so
                # ownership principals differ per credential under multi-key setups.
                return (AnonymousUser(), provided_token)

        # Token was provided but did not match any accepted key.
        logger.warning("[Auth][StaticToken] Invalid static token provided.")
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
    message = (
        'Authentication credentials were not provided or are invalid '
        '(Requires valid API Key or active session).'
    )

    def has_permission(self, request, _view):
        """
        Checks if the request has valid authentication via token or session.
        """
        # Check if static token authentication was successful.
        # StaticTokenAuthentication returns (AnonymousUser, token), so
        # request.auth will be the token.
        has_valid_token = getattr(request, 'auth', None) is not None
        if has_valid_token:
            logger.debug(
                "[Perm][TokenOrSession] Access granted via static token "
                "(request.auth is set)."
            )
            return True

        # Check if session authentication was successful.
        # request.user should be populated by SessionAuthentication/AuthMiddleware.
        user = getattr(request, 'user', None)
        has_valid_session = user is not None and user.is_authenticated
        if has_valid_session:
            logger.debug(
                f"[Perm][TokenOrSession] Access granted via authenticated session user: {user}"
            )
            return True

        # If neither condition is met, deny permission.
        logger.debug("[Perm][TokenOrSession] Access denied: No valid token (request.auth=None) and no authenticated session user.")
        return False


def api_permission_classes():
    """Permission classes that respect ``ENABLE_API_AUTH``.

    Mutating / management API views should use this (or omit ``permission_classes``
    so DRF defaults apply) instead of hard-coding ``AllowAny``.
    """
    if getattr(settings, "ENABLE_API_AUTH", False):
        return [HasValidTokenOrSession]
    return [AllowAny]


def request_principal(request) -> str | None:
    """Stable principal id for the request (ownership stamps).

    - Session user → ``user:<username>``
    - Static API token (request.auth) → ``token:<sha256-prefix>`` of the
      presenting credential. With multi-key auth (``API_AUTH_TOKENS`` /
      ``SWARM_API_KEYS``), each accepted Bearer maps to a distinct principal
      because the hash is over the token that authenticated the request.
    - Unauthenticated → ``None``
    """
    import hashlib

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{user.get_username()}"

    auth = getattr(request, "auth", None)
    if auth is not None:
        # request.auth is the raw token string from StaticTokenAuthentication
        digest = hashlib.sha256(str(auth).encode("utf-8")).hexdigest()[:24]
        return f"token:{digest}"
    return None

