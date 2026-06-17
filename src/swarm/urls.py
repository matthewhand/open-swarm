from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.http import HttpResponse, FileResponse
from django.views.static import serve
from pathlib import Path

from swarm.views.agent_creator_pro import agent_creator_pro_page
from swarm.views.agent_creator_views import (
    agent_creator_page,
    generate_agent_code,
    save_custom_agent,
    save_team_swarm,
    team_creator_page,
    validate_agent_code,
)
from swarm.views.api_views import (
    BlueprintsListView,
    BlueprintSourceView,
    CustomBlueprintDetailView,
    CustomBlueprintsView,
    MarketplaceGitHubBlueprintsView,
    MarketplaceGitHubMCPConfigsView,
)
from swarm.views.api_views import ModelsListView as OpenAIModelsView
from swarm.views.blueprint_library_views import (
    add_blueprint_to_library,
    blueprint_creator,
    blueprint_library,
    blueprint_requirements_status,
    check_comfyui_status,
    generate_avatar,
    my_blueprints,
    remove_blueprint_from_library,
)
from swarm.views.chat_views import ChatCompletionsView
from swarm.views.library_api import LibraryAPIView, LibraryDetailAPIView
from swarm.views.settings_views import (
    environment_variables,
    settings_api,
    settings_dashboard,
)
from swarm.views.teams_api import TeamDetailAPIView, TeamsAPIView
from swarm.views.web_views import (
    custom_login,
    index,
    profiles_page,
    team_admin,
    team_launcher,
    teams_export,
)
from swarm.views.webui import WebUIView

# Prefer the AllowAny variant if it's present in URL mappings elsewhere; for tests,
# wire the open variant to avoid auth blocking. If needed, switch to ProtectedModelsView.
urlpatterns = [
    path("", index, name="index"),  # Root path for web UI
    # Authentication. Two aliases for the same view:
    # - accounts/login/ matches Django's default LOGIN_URL ('/accounts/login/')
    #   and is the canonical 'login' name used by auth machinery.
    # - login/ matches this project's settings.LOGIN_URL ('/login/') and the
    #   'custom_login' name referenced by templates/account/login.html.
    path("accounts/login/", custom_login, name="login"),
    path("login/", custom_login, name="custom_login"),
    path("v1/models", OpenAIModelsView.as_view(), name="models-list-no-slash"),
    path("v1/models/", OpenAIModelsView.as_view(), name="models-list"),
    path("v1/blueprints", BlueprintsListView.as_view(), name="blueprints-list-no-slash"),
    path("v1/blueprints/", BlueprintsListView.as_view(), name="blueprints-list"),
    path("v1/blueprints/<str:blueprint_id>/source", BlueprintSourceView.as_view(), name="blueprint-source"),
    path("v1/blueprints/custom/", CustomBlueprintsView.as_view(), name="custom-blueprints"),
    path("v1/blueprints/custom/<str:blueprint_id>/", CustomBlueprintDetailView.as_view(), name="custom-blueprint-detail"),
    # GitHub-topics marketplace discovery (returns empty list if disabled)
    path("marketplace/github/blueprints/", MarketplaceGitHubBlueprintsView.as_view(), name="marketplace-github-blueprints"),
    path("marketplace/github/mcp-configs/", MarketplaceGitHubMCPConfigsView.as_view(), name="marketplace-github-mcp-configs"),
    path("v1/chat/completions", ChatCompletionsView.as_view(), name="chat_completions"),
    # JSON Teams API (REST counterpart to the server-rendered /teams/ page)
    path("v1/teams", TeamsAPIView.as_view(), name="teams-api-no-slash"),
    path("v1/teams/", TeamsAPIView.as_view(), name="teams-api"),
    path("v1/teams/<str:team_id>/", TeamDetailAPIView.as_view(), name="teams-api-detail"),
    # JSON Blueprint Library API (REST counterpart to /blueprint-library/)
    path("v1/library", LibraryAPIView.as_view(), name="library-api-no-slash"),
    path("v1/library/", LibraryAPIView.as_view(), name="library-api"),
    path("v1/library/<str:blueprint_name>/", LibraryDetailAPIView.as_view(), name="library-api-detail"),
    path("teams/launch", team_launcher, name="teams_launch_no_slash"),
    path("teams/launch/", team_launcher, name="teams_launch"),
    path("teams/", team_admin, name="teams_admin"),
    path("teams/export", teams_export, name="teams_export"),
    path("profiles/", profiles_page, name="profiles_page"),
    # Agent/Team Creator endpoints
    path("agent-creator/", agent_creator_page, name="agent_creator"),
    path("agent-creator/generate/", generate_agent_code, name="generate_agent_code"),
    path("agent-creator/validate/", validate_agent_code, name="validate_agent_code"),
    path("agent-creator/save/", save_custom_agent, name="save_custom_agent"),
    path("team-creator/", team_creator_page, name="team_creator"),
    path("team-creator/save/", save_team_swarm, name="save_team_swarm"),
    # Agent Creator Pro endpoints
    path("agent-creator-pro/", agent_creator_pro_page, name="agent_creator_pro"),
    # Settings Management endpoints
    path("settings/", settings_dashboard, name="settings_dashboard"),
    path("settings/api/", settings_api, name="settings_api"),
    path("settings/environment/", environment_variables, name="environment_variables"),
    # Blueprint Library endpoints
    path("blueprint-library/", blueprint_library, name="blueprint_library"),
    path("blueprint-library/creator/", blueprint_creator, name="blueprint_creator"),
    path("blueprint-library/my-blueprints/", my_blueprints, name="my_blueprints"),
    path("blueprint-library/requirements/", blueprint_requirements_status, name="blueprint_requirements_status"),
    path("blueprint-library/add/<str:blueprint_name>/", add_blueprint_to_library, name="add_blueprint_to_library"),
    path("blueprint-library/remove/<str:blueprint_name>/", remove_blueprint_from_library, name="remove_blueprint_from_library"),
    # Avatar generation endpoints
    path("blueprint-library/generate-avatar/<str:blueprint_name>/", generate_avatar, name="generate_avatar"),
    path("blueprint-library/comfyui-status/", check_comfyui_status, name="check_comfyui_status"),
    
    # Web UI endpoint
    path("webui/", WebUIView.as_view(), name="webui"),
]

# Serve avatar images in development
if settings.DEBUG:
    urlpatterns += static(settings.AVATAR_URL_PREFIX, document_root=settings.AVATAR_STORAGE_PATH)

# Optional MCP server (django-mcp-server) when enabled
import os

if os.getenv('ENABLE_MCP_SERVER', '').lower() in ('true', '1', 'yes'):
    try:
        from django.urls import include
        urlpatterns += [
            path('mcp/', include('django_mcp_server.urls')),
        ]
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "ENABLE_MCP_SERVER is set but the '/mcp/' mount was skipped: could not "
            "import 'django_mcp_server.urls' (%s). No installed package provides a "
            "'django_mcp_server' module; the PyPI distribution 'django-mcp-server' "
            "exposes 'mcp_server' instead and needs INSTALLED_APPS changes. "
            "See docs/mcp_server_mode.md for the supported options.",
            exc,
        )

# SPA Fallback for React Router - must be last
def _get_frontend_path():
    """Get the path to the built frontend assets."""
    frontend_path = Path("webui/frontend/dist")
    if not frontend_path.exists():
        frontend_path = Path("webui/frontend/build")
    return frontend_path if frontend_path.exists() else None

frontend_path = _get_frontend_path()
if frontend_path and frontend_path.exists():
    from django.views.static import serve
    from django.urls import re_path
    
    # Serve static assets
    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': str(frontend_path / 'assets')}),
    ]
    
    # SPA fallback - serve index.html for all non-API, non-admin, non-static routes
    # (the catch-all regex below has no capture group, so path must default)
    def spa_fallback(request, path=""):
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(open(index_file, 'rb'), content_type='text/html')
        return HttpResponse("Not Found", status=404)
    
    urlpatterns += [
        re_path(r'^(?!api/|admin/|static/|assets/|mcp/|marketplace/|v1/|teams/|blueprint-library/|agent-creator/|settings/|accounts/|login/).*$', spa_fallback),
    ]
