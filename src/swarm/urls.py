from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.http import HttpResponse, FileResponse
from django.views.static import serve
from pathlib import Path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

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
    BlueprintToolsView,
    CliAgentsView,
    ConfigOptionsView,
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
from swarm.views.chat_views import ChatCompletionsView, HealthCheckView
from swarm.views.responses_views import ResponsesCancelView, ResponsesDetailView, ResponsesView
from swarm.views.session_explorer import session_detail, session_explorer, session_list_api
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
    # Lightweight liveness probe (no auth) — used by the Fly health check.
    path("health", HealthCheckView.as_view(), name="health"),
    path("health/", HealthCheckView.as_view()),
    # Session Explorer web UI (browse stateful /v1/responses sessions + delegation timelines)
    path("sessions/", session_explorer, name="session-explorer"),
    path("sessions/<str:response_id>/", session_detail, name="session-detail"),
    path("api/sessions/", session_list_api, name="session-list-api"),
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
    path("v1/blueprints/<str:blueprint_id>/tools", BlueprintToolsView.as_view(), name="blueprint-tools"),
    path("v1/cli-agents/", CliAgentsView.as_view(), name="cli-agents-api"),
    path("v1/config-options/", ConfigOptionsView.as_view(), name="config-options-api"),
    path("v1/blueprints/custom/", CustomBlueprintsView.as_view(), name="custom-blueprints"),
    path("v1/blueprints/custom/<str:blueprint_id>/", CustomBlueprintDetailView.as_view(), name="custom-blueprint-detail"),
    # GitHub-topics marketplace discovery (returns empty list if disabled)
    path("marketplace/github/blueprints/", MarketplaceGitHubBlueprintsView.as_view(), name="marketplace-github-blueprints"),
    path("marketplace/github/mcp-configs/", MarketplaceGitHubMCPConfigsView.as_view(), name="marketplace-github-mcp-configs"),
    path("v1/chat/completions", ChatCompletionsView.as_view(), name="chat_completions"),
    # OpenAI Responses API (MVP) — normalizes `input`/`instructions` to messages
    # and reuses the same blueprint-resolution + run path as chat completions.
    path("v1/responses", ResponsesView.as_view(), name="responses"),
    path("v1/responses/<str:response_id>/cancel", ResponsesCancelView.as_view(), name="responses-cancel"),
    path("v1/responses/<str:response_id>", ResponsesDetailView.as_view(), name="responses-detail"),
    # OpenAPI schema + interactive docs (drf-spectacular).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
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
            path('mcp/', include('mcp_server.urls')),
        ]
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "ENABLE_MCP_SERVER is set but the '/mcp/' mount was skipped: could not "
            "import 'mcp_server.urls' (%s). Install the MCP server package with "
            "`pip install django-mcp-server` (provides the 'mcp_server' module). "
            "See docs/mcp_server_mode.md.",
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
