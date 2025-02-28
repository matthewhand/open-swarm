from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os

from swarm import views
from swarm.views import HiddenSpectacularAPIView, ChatMessageViewSet
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

def favicon(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'assets', 'images', 'favicon.ico')
    with open(favicon_path, 'rb') as f:
        favicon_data = f.read()
    return HttpResponse(favicon_data, content_type="image/x-icon")

ENABLE_ADMIN = os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t")
ENABLE_WEBUI = os.getenv("ENABLE_WEBUI", "false").lower() in ("true", "1", "t")

router = DefaultRouter()
router.register(r'v1/chat/messages', ChatMessageViewSet, basename='chatmessage')

base_urlpatterns = [
    re_path(r'^health/?$', lambda request: HttpResponse("OK"), name='health_check'),
    re_path(r'^v1/chat/completions/?$', views.chat_completions, name='chat_completions'),
    re_path(r'^v1/models/?$', views.list_models, name='list_models'),
    path('v1/university/', include('blueprints.university.urls')),
    re_path(r'^schema/?$', HiddenSpectacularAPIView.as_view(), name='schema'),
    re_path(r'^swagger-ui/?$', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

admin_urlpatterns = []
if ENABLE_ADMIN:
    admin_urlpatterns = [path('admin/', admin.site.urls)]

webui_urlpatterns = []
if ENABLE_WEBUI:
    webui_urlpatterns = [
        path('', views.index, name='index'),
        path('favicon.ico', favicon, name='favicon'),
        path('config/swarm_config.json', views.serve_swarm_config, name='serve_swarm_config'),
        path('chatbot/', views.chatbot_view, name='chatbot'),
        path('messenger/', views.messenger, name='messenger'),
        path('<str:blueprint_name>', views.blueprint_webpage, name='blueprint_webpage'),
    ]
    webui_urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns = webui_urlpatterns + admin_urlpatterns + base_urlpatterns + router.urls
