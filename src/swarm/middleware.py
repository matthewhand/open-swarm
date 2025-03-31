# src/swarm/middleware.py
import logging
import asyncio # Import asyncio
from asgiref.sync import sync_to_async
from django.utils.functional import SimpleLazyObject
from django.utils.decorators import sync_and_async_middleware
from django.contrib.auth.middleware import AuthenticationMiddleware

logger = logging.getLogger(__name__)

# Mark the middleware as compatible with both sync and async views
@sync_and_async_middleware
def AsyncAuthMiddleware(get_response):
    """
    Ensures request.user is loaded asynchronously before reaching async views,
    preventing SynchronousOnlyOperation errors during authentication checks
    that might involve database access (like session loading).

    This should be placed *after* Django's built-in AuthenticationMiddleware.
    """

    # One-time configuration and initialization.
    # (Not needed for this simple middleware)

    async def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Check if request.user is a SimpleLazyObject and hasn't been evaluated yet.
        # Django's AuthenticationMiddleware sets request.user to a SimpleLazyObject
        # wrapping the get_user function. Accessing request.user triggers evaluation.
        if isinstance(request.user, SimpleLazyObject):
            # Use sync_to_async to safely evaluate the lazy object (which calls
            # the synchronous get_user function) in an async context.
            # We don't need the result here, just to trigger the load.
            try:
                logger.debug("[AsyncAuthMiddleware] Attempting async user load...")
                _ = await sync_to_async(request.user._setup)() # Access internal _setup to force load
                is_auth = await sync_to_async(lambda: getattr(request.user, 'is_authenticated', False))()
                logger.debug(f"[AsyncAuthMiddleware] User loaded via SimpleLazyObject: {request.user}, Authenticated: {is_auth}")
            except Exception as e:
                # Log potential errors during user loading but don't block the request
                logger.error(f"[AsyncAuthMiddleware] Error during async user load: {e}", exc_info=True)
                # You might want to handle specific auth errors differently
        else:
            # If it's not a SimpleLazyObject, it might be already loaded or AnonymousUser
            is_auth = getattr(request.user, 'is_authenticated', False)
            logger.debug(f"[AsyncAuthMiddleware] User already loaded or not lazy: {request.user}, Authenticated: {is_auth}")


        response = await get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    # Return the correct function based on whether get_response is async or sync
    if asyncio.iscoroutinefunction(get_response):
        return middleware
    else:
        # If the next middleware/view is sync, we don't need our async wrapper
        # However, the decorator handles this, so we just return the async version.
        # For clarity, the decorator makes this middleware compatible either way.
        return middleware