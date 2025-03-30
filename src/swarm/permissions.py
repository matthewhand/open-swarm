import logging
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

class HasValidTokenOrSession(BasePermission):
    """
    Allows access only to authenticated users.

    Relies on DRF's authentication classes (e.g., SessionAuthentication,
    TokenAuthentication) having run first to populate request.user.
    """
    message = 'Authentication credentials were not provided or are invalid.'

    def has_permission(self, request, view):
        # Authentication backends run before permissions.
        # We just need to check if authentication was successful.
        is_authenticated = request.user and request.user.is_authenticated

        if is_authenticated:
            # logger.debug(f"Permission granted for authenticated user: {request.user}") # Optional: keep for debugging
            return True
        else:
            # logger.debug("Permission denied: User is not authenticated.") # Optional: keep for debugging
            # Let DRF handle returning 401/403 based on whether credentials were provided.
            return False

