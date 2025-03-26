from django.contrib import admin
from django.urls import path, re_path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os
import logging

# Import specific views from their modules
from swarm.views.core_views import index as core_index_view, serve_swarm_config, custom_login
from swarm.views.chat_views import chat_completions
from swarm.views.model_views import list_models
from swarm.views.message_views import ChatMessageViewSet
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView as HiddenSpectacularAPIView
from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

def favicon(request):
    favicon_path = settings.BASE_DIR / 'assets' / 'images' / 'favicon.ico'
    try:
        with open(favicon_path, 'rb') as f:
            favicon_data = f.read()
        return HttpResponse(favicon_data, content_type="image/x-icon")
    except FileNotFoundError:
        logger.warning("Favicon not found.")
        return HttpResponse(status=404)

ENABLE_ADMIN = os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t")
ENABLE_WEBUI = os.getenv("ENABLE_WEBUI", "true").lower() in ("true", "1", "t")

logger.debug(f"ENABLE_WEBUI={'true' if ENABLE_WEBUI else 'false'}")
logger.debug(f"ENABLE_ADMIN={'true' if ENABLE_ADMIN else 'false'}")

router = DefaultRouter()
# Ensure ChatMessageViewSet is available before registering
if ChatMessageViewSet:
    router.register(r'v1/chat/messages', ChatMessageViewSet, basename='chatmessage')
else:
     logger.warning("ChatMessageViewSet not imported correctly, skipping API registration.")

# Base URL patterns required by Swarm core
# Use the imported view functions directly
base_urlpatterns = [
    re_path(r'^health/?$', lambda request: HttpResponse("OK"), name='health_check'),
    re_path(r'^v1/chat/completions/?$', chat_completions, name='chat_completions'),
    re_path(r'^v1/models/?$', list_models, name='list_models'),
    re_path(r'^schema/?$', HiddenSpectacularAPIView.as_view(), name='schema'),
    re_path(r'^swagger-ui/?$', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Optional Admin URLs
admin_urlpatterns = [path('admin/', admin.site.urls)] if ENABLE_ADMIN else []

# Optional Web UI URLs
webui_urlpatterns = []
if ENABLE_WEBUI:
    webui_urlpatterns = [
        path('', core_index_view, name='index'),
        path('favicon.ico', favicon, name='favicon'),
        path('config/swarm_config.json', serve_swarm_config, name='serve_swarm_config'),
        path('accounts/login/', custom_login, name='custom_login'),
    ]
    if settings.DEBUG:
         if settings.STATIC_URL and settings.STATIC_ROOT:
              webui_urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
         else:
              logger.warning("STATIC_URL or STATIC_ROOT not configured, static files may not serve correctly in DEBUG mode.")

# --- Blueprint URLs are now added dynamically via blueprint_base.py -> django_utils.py ---
blueprint_urlpatterns = [] # Start with empty list, populated by utils

# Combine all URL patterns
urlpatterns = webui_urlpatterns + admin_urlpatterns + base_urlpatterns + blueprint_urlpatterns + router.urls

# Log final URL patterns (consider moving this to where patterns are finalized if issues persist)
if settings.DEBUG:
    try:
        from django.urls import get_resolver
        # Note: get_resolver(None) might not reflect dynamically added URLs perfectly here.
        # Logging within django_utils might be more accurate for dynamic additions.
        final_patterns = get_resolver(None).url_patterns
        logger.debug(f"Initial resolved URL patterns ({len(final_patterns)} total):")
        # for pattern in final_patterns:
        #      try: pattern_repr = str(pattern)
        #      except: pattern_repr = f"[Pattern for {getattr(pattern, 'name', 'unnamed')}]"
        #      logger.debug(f"  {pattern_repr}")
    except Exception as e:
        logger.error(f"Could not log initial URL patterns: {e}")
