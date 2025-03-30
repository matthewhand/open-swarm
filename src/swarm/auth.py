import logging
from rest_framework.authentication import (
    TokenAuthentication, SessionAuthentication, HTTP_HEADER_ENCODING
)
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user, SESSION_KEY
from asgiref.sync import sync_to_async # Keep sync_to_async for DB calls

# Use a specific logger for auth related messages
logger = logging.getLogger('swarm.auth')

# --- Async Token Authentication ---

@sync_to_async
def get_token_from_db(model, key):
    logger.debug(f"[Auth][Token] Attempting DB lookup for key: {key[:6]}...")
    try:
        token = model.objects.select_related("user").get(key=key)
        logger.debug(f"[Auth][Token] DB lookup successful for key: {key[:6]}..., User: {token.user.username}")
        return token
    except model.DoesNotExist:
        logger.warning(f"[Auth][Token] DB lookup FAILED for key: {key[:6]}... Token does not exist.")
        return None
    except Exception as e:
        logger.error(f"[Auth][Token] DB lookup unexpected error for key {key[:6]}...: {e}", exc_info=True)
        return None

class AsyncTokenAuthentication(TokenAuthentication):
    """
    An async-aware version of TokenAuthentication.
    The authenticate method is async, suitable for async views/tests.
    """

    def get_authorization_header(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            auth = auth.encode(HTTP_HEADER_ENCODING)
        return auth

    # This method MUST be async when called from an async context (like AsyncClient)
    async def authenticate(self, request):
        logger.debug("[Auth][Token] AsyncTokenAuthentication.authenticate called.")
        auth = self.get_authorization_header(request).split()
        logger.debug(f"[Auth][Token] Authorization header parts: {auth}")

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            logger.debug(f"[Auth][Token] No auth header or incorrect keyword '{self.keyword}'. Expected: {self.keyword.lower().encode()}. Got: {auth[0].lower() if auth else 'N/A'}")
            return None

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            logger.warning(f"[Auth][Token] {msg}")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            logger.warning(f"[Auth][Token] {msg}")
            raise exceptions.AuthenticationFailed(msg)

        try:
            key = auth[1].decode()
            logger.debug(f"[Auth][Token] Extracted key: {key[:6]}...")
        except UnicodeError:
            msg = _("Invalid token header. Token string should not contain invalid characters.")
            logger.warning(f"[Auth][Token] {msg}")
            raise exceptions.AuthenticationFailed(msg)

        # Directly await the async credentials check
        try:
             logger.debug(f"[Auth][Token] Awaiting authenticate_credentials for key: {key[:6]}...")
             user_token_tuple = await self.authenticate_credentials(key)
             logger.debug(f"[Auth][Token] authenticate_credentials completed. Result: {user_token_tuple}")
             return user_token_tuple
        except exceptions.AuthenticationFailed as e:
             logger.warning(f"[Auth][Token] AuthenticationFailed raised during authenticate_credentials: {e.detail}")
             raise e # Re-raise auth exceptions
        except Exception as e:
             logger.error(f"[Auth][Token] Unexpected error during authenticate_credentials: {e}", exc_info=True)
             raise exceptions.AuthenticationFailed(_("Token authentication failed due to an internal error."))


    async def authenticate_credentials(self, key):
        logger.debug(f"[Auth][Token] authenticate_credentials started for key: {key[:6]}...")
        model = self.get_model()
        token = await get_token_from_db(model, key) # Await the async DB call

        if token is None:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            logger.warning(f"[Auth][Token] User '{token.user.username}' is inactive.")
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        logger.info(f"[Auth][Token] Authentication successful for user: {token.user.username}")
        return (token.user, token)

# --- Async Session Authentication ---

@sync_to_async
def get_user_from_session(request):
    """
    Synchronous helper to get user from session, wrapped for async context.
    This encapsulates the potentially blocking parts of Django's session/auth middleware logic.
    """
    user = getattr(request, '_cached_user', None)
    if user is not None:
        logger.debug("[Auth][Session] Using cached user from request.")
        return user

    # This mimics parts of AuthenticationMiddleware and get_user
    session_key = request.session.get(SESSION_KEY)
    if session_key is None:
        logger.debug("[Auth][Session] No session key found.")
        return None

    try:
        # The get_user function handles the DB lookup
        user = get_user(request)
        logger.debug(f"[Auth][Session] User retrieved from session: {user}")
        # Cache user for subsequent calls within the same request
        request._cached_user = user
        return user
    except Exception as e:
        # Catch potential errors during session/user loading
        logger.error(f"[Auth][Session] Error retrieving user from session: {e}", exc_info=True)
        return None


class AsyncSessionAuthentication(SessionAuthentication):
    """
    An async-aware version of SessionAuthentication.
    """
    async def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """
        logger.debug("[Auth][Session] AsyncSessionAuthentication.authenticate called.")
        # We use a helper function wrapped in sync_to_async to handle the sync parts
        # This still might cause issues if called during the wrong part of the loop
        user = await get_user_from_session(request)

        if user is None:
             logger.debug("[Auth][Session] No user retrieved from session helper.")
             return None

        # Standard SessionAuthentication checks (CSRF, active user)
        self.enforce_csrf(request)
        if not user.is_active:
            logger.warning(f"[Auth][Session] User '{user.username}' is inactive.")
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        logger.info(f"[Auth][Session] Authentication successful for user: {user.username}")
        return (user, None)

