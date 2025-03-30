import logging
from rest_framework.authentication import (
    TokenAuthentication, SessionAuthentication, HTTP_HEADER_ENCODING
)
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
# We need async_to_sync to call async code from sync code
# We still need sync_to_async for the DB helper itself
from asgiref.sync import sync_to_async, async_to_sync
# Keep original helpers
from django.contrib.auth import get_user, SESSION_KEY

# Use a specific logger for auth related messages
logger = logging.getLogger('swarm.auth')

# --- Async DB Helper ---
# This remains async as it performs DB I/O
@sync_to_async
def get_token_from_db(model, key):
    logger.debug(f"[Auth][Token] Attempting DB lookup for key: {key[:6]}...")
    try:
        # Ensure user is selected to avoid N+1 in sync context
        token = model.objects.select_related("user").get(key=key)
        logger.debug(f"[Auth][Token] DB lookup successful for key: {key[:6]}..., User: {token.user.username}")
        return token
    except model.DoesNotExist:
        logger.warning(f"[Auth][Token] DB lookup FAILED for key: {key[:6]}... Token does not exist.")
        return None
    except Exception as e:
        logger.error(f"[Auth][Token] DB lookup unexpected error for key {key[:6]}...: {e}", exc_info=True)
        return None # Or re-raise depending on desired behavior

# --- Custom *Synchronous* Token Authentication ---
class CustomTokenAuthentication(TokenAuthentication):
    """
    Standard TokenAuthentication, but uses an async helper for the DB lookup.
    The main authenticate methods are synchronous to align with DRF's standard flow.
    """
    keyword = 'Bearer' # Or 'Token' depending on your desired header

    # Override get_authorization_header if needed (like DRF's does)
    def get_authorization_header(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            # Ensure encoding is handled correctly.
            auth = auth.encode(HTTP_HEADER_ENCODING)
        return auth

    # This method is synchronous as per DRF's standard APIView flow
    def authenticate(self, request):
        logger.debug("[Auth][Token] CustomTokenAuthentication.authenticate called.")
        auth = self.get_authorization_header(request).split()
        logger.debug(f"[Auth][Token] Authorization header parts: {auth}")

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            logger.debug(f"[Auth][Token] No auth header or incorrect keyword '{self.keyword}'.")
            return None # No credentials provided, DRF expects None here

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            logger.warning(f"[Auth][Token] {msg}")
            raise exceptions.AuthenticationFailed(msg) # Raise exception for invalid format
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            logger.warning(f"[Auth][Token] {msg}")
            raise exceptions.AuthenticationFailed(msg) # Raise exception for invalid format

        try:
            key = auth[1].decode()
            logger.debug(f"[Auth][Token] Extracted key: {key[:6]}...")
        except UnicodeError:
            msg = _("Invalid token header. Token string should not contain invalid characters.")
            logger.warning(f"[Auth][Token] {msg}")
            raise exceptions.AuthenticationFailed(msg) # Raise exception for invalid format

        # Call the synchronous credentials check
        # Exceptions raised within authenticate_credentials will propagate
        return self.authenticate_credentials(key)

    # This method remains synchronous
    def authenticate_credentials(self, key):
        logger.debug(f"[Auth][Token] authenticate_credentials started for key: {key[:6]}...")
        model = self.get_model()

        try:
            # *** Use async_to_sync to call the async DB helper ***
            token = async_to_sync(get_token_from_db)(model, key)
        except Exception as e:
             # Catch potential errors during async_to_sync execution if needed
             logger.error(f"[Auth][Token] Error calling async DB helper via async_to_sync: {e}", exc_info=True)
             raise exceptions.AuthenticationFailed(_("Internal error during token validation."))

        if token is None:
            logger.warning(f"[Auth][Token] Token lookup returned None for key {key[:6]}...")
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            logger.warning(f"[Auth][Token] User '{token.user.username}' is inactive.")
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        logger.info(f"[Auth][Token] Authentication successful for user: {token.user.username}")
        # Return the tuple expected by DRF
        return (token.user, token)

# --- Custom *Synchronous* Session Authentication ---
# Inherit directly from DRF's SessionAuthentication
class CustomSessionAuthentication(SessionAuthentication):
    """
    Standard SessionAuthentication. Django's session and user loading
    mechanisms called within are synchronous.
    """
    # No need to override authenticate unless adding custom logic.
    # DRF's default authenticate method will be called.
    # It internally accesses request.user, which triggers Django's
    # synchronous session/user loading middleware logic.
    pass # Inherit standard behavior

