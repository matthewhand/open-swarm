"""
Swarm URL Configuration
"""
import logging
from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from swarm.views.chat_views import ChatCompletionsView, HealthCheckView
# *** Uncomment and correct the import path ***
from swarm.views.api_views import ModelsListView
# from swarm.views.webui_views import index as webui_index # Rename to avoid conflict

logger = logging.getLogger(__name__)

# ==============================================================================
# API URL Patterns (v1)
# ==============================================================================
api_urlpatterns = [
    path('chat/completions', ChatCompletionsView.as_view(), name='chat_completions'),
    # *** Uncomment this URL pattern ***
    path('models', ModelsListView.as_view(), name='list_models'),
    path('health', HealthCheckView.as_view(), name='health_check'),
    # Add other v1 API endpoints here
]

# ==============================================================================
# Schema URL Patterns
# ==============================================================================
schema_urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# ==============================================================================
# Main URL Patterns
# ==============================================================================
urlpatterns = [
    # Redirect root based on DEBUG setting
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False) if settings.DEBUG else RedirectView.as_view(pattern_name='login', permanent=False)),

    # API v1 endpoints
    path('v1/', include(api_urlpatterns)),

    # Schema endpoints
    path('api/', include(schema_urlpatterns)),

    # Django Admin (Optional)
    path('admin/', admin.site.urls) if getattr(settings, 'ENABLE_ADMIN', False) else path('admin/', RedirectView.as_view(url=reverse_lazy('login'))),

    # Authentication Views (Django Built-in)
    path('login/', auth_views.LoginView.as_view(template_name='swarm/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),

    # Web UI (Optional) - Conditionally include based on settings
    # *** Ensure this line remains commented out or removed if webui_index is not defined ***
    # path('webui/', webui_index, name='webui_index') if getattr(settings, 'ENABLE_WEBUI', False) else path('webui/', RedirectView.as_view(url=reverse_lazy('login'))),
]

# Debug logging (optional)
logger.debug(f"ENABLE_ADMIN={getattr(settings, 'ENABLE_ADMIN', False)}")
logger.debug(f"ENABLE_WEBUI={getattr(settings, 'ENABLE_WEBUI', False)}")

# Example of how to conditionally add URLs based on settings
# if getattr(settings, 'ENABLE_SOMETHING', False):
#     urlpatterns.append(path('something/', include('something.urls')))

