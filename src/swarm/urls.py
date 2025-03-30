from django.contrib import admin
from django.urls import path, re_path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os
import logging

# Import views
from swarm.views.core_views import index as core_index_view, serve_swarm_config, custom_login
# Import the Class-Based View
from swarm.views.chat_views import ChatCompletionsView
from swarm.views.model_views import list_models
from swarm.views.message_views import ChatMessageViewSet
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView as HiddenSpectacularAPIView
from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

# favicon function remains the same...
def favicon(request):
    favicon_path = settings.BASE_DIR / 'assets' / 'images' / 'favicon.ico'
    try:
        with open(favicon_path, 'rb') as f: favicon_data = f.read()
        return HttpResponse(favicon_data, content_type="image/x-icon")
    except FileNotFoundError: logger.warning("Favicon not found."); return HttpResponse(status=404)

ENABLE_ADMIN = os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t")
ENABLE_WEBUI = os.getenv("ENABLE_WEBUI", "true").lower() in ("true", "1", "t")
logger.debug(f"ENABLE_WEBUI={'true' if ENABLE_WEBUI else 'false'}"); logger.debug(f"ENABLE_ADMIN={'true' if ENABLE_ADMIN else 'false'}")

router = DefaultRouter()
if ChatMessageViewSet: router.register(r'v1/chat/messages', ChatMessageViewSet, basename='chatmessage')
else: logger.warning("ChatMessageViewSet not imported correctly, skipping API registration.")

base_urlpatterns = [
    re_path(r'^health/?$', lambda request: HttpResponse("OK"), name='health_check'),
    # Use Class-Based View with .as_view()
    re_path(r'^v1/chat/completions/?$', ChatCompletionsView.as_view(), name='chat_completions'),
    re_path(r'^v1/models/?$', list_models, name='list_models'),
    re_path(r'^schema/?$', HiddenSpectacularAPIView.as_view(), name='schema'),
    re_path(r'^swagger-ui/?$', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

admin_urlpatterns = [path('admin/', admin.site.urls)] if ENABLE_ADMIN else []
webui_urlpatterns = []
if ENABLE_WEBUI:
    webui_urlpatterns = [ path('', core_index_view, name='index'), path('favicon.ico', favicon, name='favicon'), path('config/swarm_config.json', serve_swarm_config, name='serve_swarm_config'), path('accounts/login/', custom_login, name='custom_login'), ]
    if settings.DEBUG and settings.STATIC_URL and settings.STATIC_ROOT: webui_urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    elif settings.DEBUG: logger.warning("STATIC_URL or STATIC_ROOT not configured...")

blueprint_urlpatterns = [] # Populated dynamically elsewhere (if blueprints provide metadata)
urlpatterns = webui_urlpatterns + admin_urlpatterns + base_urlpatterns + blueprint_urlpatterns + router.urls

if settings.DEBUG:
    try: from django.urls import get_resolver; logger.debug(f"Initial resolved URL patterns ({len(get_resolver(None).url_patterns)} total):")
    except Exception as e: logger.error(f"Could not log initial URL patterns: {e}")

