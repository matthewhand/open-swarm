"""
Main URL configuration for the swarm project.
"""
# *** ADDED logging import ***
import logging
from django.urls import path, include, re_path
from django.contrib import admin
from django.conf import settings
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Import views correctly
from swarm.views.chat_views import ChatCompletionsView, HealthCheckView
from swarm.views.model_views import ListModelsView
from swarm.views import message_views # Import the module

# Import web UI views if enabled
if getattr(settings, 'ENABLE_WEBUI', False):
    from swarm.views import chat_views as web_ui_views

# *** ADDED get logger instance ***
logger = logging.getLogger(__name__)

# Create a router and register viewsets
router = DefaultRouter()
if hasattr(message_views, 'ChatMessageViewSet'): # Check if viewset exists before registering
     router.register(r'chat/messages', message_views.ChatMessageViewSet, basename='chatmessage')

# Define explicit paths for other API views
api_urlpatterns = [
    path('health', HealthCheckView.as_view(), name='health_check'),
    path('chat/completions', ChatCompletionsView.as_view(), name='chat_completions'),
    path('models', ListModelsView.as_view(), name='list_models'),
    path('', include(router.urls)),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns = [
    # Default redirect logic
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False) if settings.DEBUG else RedirectView.as_view(url_name='login', permanent=False)),
    path('v1/', include(api_urlpatterns)), # API paths
]

# Conditionally add Admin URLs
if getattr(settings, 'ENABLE_ADMIN', settings.DEBUG):
    urlpatterns += [path('admin/', admin.site.urls)]
    logger.debug("ENABLE_ADMIN=true")
else:
    logger.debug("ENABLE_ADMIN=false")


# Conditionally add Web UI URLs
if getattr(settings, 'ENABLE_WEBUI', False):
    # Check if the alias was created successfully before using it
    if 'web_ui_views' in locals():
        logger.debug("ENABLE_WEBUI=true")
        from django.contrib.auth import views as auth_views
        urlpatterns += [
            path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
            path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
            path('dashboard/', web_ui_views.index, name='dashboard_index'),
        ]
        # Update root path redirect if necessary
        if not settings.DEBUG:
             urlpatterns[0] = path('', RedirectView.as_view(pattern_name='login', permanent=False))
    else:
        logger.warning("ENABLE_WEBUI is True but web UI views could not be imported.")

else:
     logger.debug("ENABLE_WEBUI=false")

