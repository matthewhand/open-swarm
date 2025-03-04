from django.contrib import admin
from django.urls import path, re_path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os
import logging

from swarm import views
from swarm.views import HiddenSpectacularAPIView, ChatMessageViewSet
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

def favicon(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'assets', 'images', 'favicon.ico')
    with open(favicon_path, 'rb') as f:
        favicon_data = f.read()
    return HttpResponse(favicon_data, content_type="image/x-icon")

ENABLE_ADMIN = os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t")
ENABLE_WEBUI = os.getenv("ENABLE_WEBUI", "true").lower() in ("true", "1", "t")

logger.debug(f"ENABLE_WEBUI={'true' if ENABLE_WEBUI else 'false'}")
logger.debug(f"ENABLE_ADMIN={'true' if ENABLE_ADMIN else 'false'}")

router = DefaultRouter()
router.register(r'v1/chat/messages', ChatMessageViewSet, basename='chatmessage')

base_urlpatterns = [
    re_path(r'^health/?$', lambda request: HttpResponse("OK"), name='health_check'),
    re_path(r'^v1/chat/completions/?$', views.chat_completions, name='chat_completions'),
    re_path(r'^v1/models/?$', views.list_models, name='list_models'),
    re_path(r'^schema/?$', HiddenSpectacularAPIView.as_view(), name='schema'),
    re_path(r'^swagger-ui/?$', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

admin_urlpatterns = [path('admin/', admin.site.urls)] if ENABLE_ADMIN else []

webui_urlpatterns = []
if ENABLE_WEBUI:
    webui_urlpatterns = [
        path('', views.index, name='index'),
        path('favicon.ico', favicon, name='favicon'),
        path('config/swarm_config.json', views.serve_swarm_config, name='serve_swarm_config'),
        path('accounts/login/', views.custom_login, name='custom_login'),
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns = webui_urlpatterns + admin_urlpatterns + base_urlpatterns + router.urls
