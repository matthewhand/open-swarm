import logging
import os
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework import exceptions
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# Import AnonymousUser
from django.contrib.auth.models import AnonymousUser
# Keep get_user_model if CustomSessionAuthentication needs it or for future user mapping
from django.contrib.auth import get_user_model

logger = logging.getLogger('swarm.auth')
User = get_user_model()

# --- Static Token Authentication ---
class StaticTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests based on a static API token passed in a header.
    Returns (AnonymousUser, token) on success to satisfy DRF's expectations
    while signaling that a specific user isn't associated.
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        logger.debug("[Auth][StaticToken] StaticTokenAuthentication.authenticate called.")
        expected_token = getattr(settings, 'SWARM_API_KEY', None)

        if not expected_token:
            logger.error("[Auth][StaticToken] SWARM_API_KEY is not set in Django settings. Cannot authenticate.")
            return None

        provided_token = None
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth_header) == 2 and auth_header[0].lower() == self.keyword.lower():
            provided_token = auth_header[1]
            logger.debug(f"[Auth][StaticToken] Found token in Authorization header: {provided_token[:6]}...")
        else:
            provided_token = request.META.get('HTTP_X_API_KEY')
            if provided_token:
                logger.debug(f"[Auth][StaticToken] Found token in X-API-Key header: {provided_token[:6]}...")

        if not provided_token:
            logger.debug("[Auth][StaticToken] No token found in headers.")
            return None

        # Use constant time comparison if possible in future?
        if provided_token == expected_token:
            logger.info("[Auth][StaticToken] Static token authentication successful.")
            # *** Return AnonymousUser and the token ***
            # This sets request.user to AnonymousUser and request.auth to the token.
            return (AnonymousUser(), provided_token)
        else:
            logger.warning(f"[Auth][StaticToken] Invalid token provided: {provided_token[:6]}...")
            raise exceptions.AuthenticationFailed(_("Invalid API Key."))

# --- Custom *Synchronous* Session Authentication ---
class CustomSessionAuthentication(SessionAuthentication):
    """ Standard SessionAuthentication """
    pass

