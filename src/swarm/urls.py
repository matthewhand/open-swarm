from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

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
from swarm.views.herdr_api import (
    HerdrAgentDetailAPIView,
    HerdrAgentsAPIView,
    HerdrDiscoverAPIView,
)
from swarm.views.library_api import LibraryAPIView, LibraryDetailAPIView
from swarm.views.responses_views import (
    ResponsesCancelView,
    ResponsesDetailView,
    ResponsesView,
)
from swarm.views.session_explorer import (
    session_detail,
    session_explorer,
    session_list_api,
)
from swarm.views.chat_persist_views import chat_compact, chat_retention_action, chat_thread
from swarm.views.settings_views import (
    environment_variables,
    settings_api,
    settings_dashboard,
)
from swarm.views.remotes_api import (
    AgentTeamView,
    RemoteDetailView,
    RemoteHealthView,
    RemoteOperateView,
    RemotesListView,
)
from swarm.views.team_rosters_api import TeamRosterDetailAPIView, TeamRostersAPIView
from swarm.views.teams_api import TeamDetailAPIView, TeamsAPIView
from swarm.views.web_views import (
    asgi_file_response,
    custom_login,
    index,
    profiles_page,
    spa_chat,
    team_admin,
    team_launcher,
    team_rosters_json,
    teams_export,
)
from swarm.views.webui import WebUIView

# Prefer the AllowAny variant if it's present in URL mappings elsewhere; for tests,
# wire the open variant to avoid auth blocking. If needed, switch to ProtectedModelsView.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index, name="index"),  # Root path for web UI
    # First-class SPA Chat. Must stay /chat (composer + Connected), not /agents.
    path("chat", spa_chat, name="spa_chat"),
    path("chat/", spa_chat, name="spa_chat_slash"),
    path(
        "agents",
        RedirectView.as_view(url="/chat", permanent=False, query_string=True),
        name="spa_agents_to_chat",
    ),
    path(
        "agents/",
        RedirectView.as_view(url="/chat", permanent=False, query_string=True),
        name="spa_agents_slash_to_chat",
    ),
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
    # Slash + no-slash twins (same pattern as /v1/responses and /v1/chat/completions).
    path("v1/blueprints/<str:blueprint_id>/source", BlueprintSourceView.as_view(), name="blueprint-source"),
    path("v1/blueprints/<str:blueprint_id>/source/", BlueprintSourceView.as_view(), name="blueprint-source-slash"),
    path("v1/blueprints/<str:blueprint_id>/tools", BlueprintToolsView.as_view(), name="blueprint-tools"),
    path("v1/blueprints/<str:blueprint_id>/tools/", BlueprintToolsView.as_view(), name="blueprint-tools-slash"),
    path("v1/cli-agents", CliAgentsView.as_view(), name="cli-agents-api-no-slash"),
    path("v1/cli-agents/", CliAgentsView.as_view(), name="cli-agents-api"),
    path("v1/config-options", ConfigOptionsView.as_view(), name="config-options-api-no-slash"),
    path("v1/config-options/", ConfigOptionsView.as_view(), name="config-options-api"),
    path("v1/blueprints/custom/", CustomBlueprintsView.as_view(), name="custom-blueprints"),
    path("v1/blueprints/custom/<str:blueprint_id>/", CustomBlueprintDetailView.as_view(), name="custom-blueprint-detail"),
    # GitHub-topics marketplace discovery (returns empty list if disabled)
    path("marketplace/github/blueprints/", MarketplaceGitHubBlueprintsView.as_view(), name="marketplace-github-blueprints"),
    path("marketplace/github/mcp-configs/", MarketplaceGitHubMCPConfigsView.as_view(), name="marketplace-github-mcp-configs"),
    # Slash + no-slash twins (same pattern as /v1/responses and /v1/blueprints).
    path("v1/chat/completions", ChatCompletionsView.as_view(), name="chat_completions"),
    path("v1/chat/completions/", ChatCompletionsView.as_view(), name="chat_completions_slash"),
    # OpenAI Responses API (MVP) — normalizes `input`/`instructions` to messages
    # and reuses the same blueprint-resolution + run path as chat completions.
    # Slash + no-slash twins (same pattern as /v1/blueprints and /v1/teams).
    path("v1/responses", ResponsesView.as_view(), name="responses"),
    path("v1/responses/", ResponsesView.as_view(), name="responses-slash"),
    path("v1/responses/<str:response_id>/cancel", ResponsesCancelView.as_view(), name="responses-cancel"),
    path("v1/responses/<str:response_id>/cancel/", ResponsesCancelView.as_view(), name="responses-cancel-slash"),
    path("v1/responses/<str:response_id>", ResponsesDetailView.as_view(), name="responses-detail"),
    path("v1/responses/<str:response_id>/", ResponsesDetailView.as_view(), name="responses-detail-slash"),
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
    # Static roster file for the AGENTS sidepane (REQ-23). Composition CRUD is
    # /v1/team-rosters/ below — not LLM-alias /v1/teams/.
    path("team_rosters.json", team_rosters_json, name="team-rosters-json"),
    # JSON Teams API (REST counterpart to the server-rendered /teams/ page)
    path("v1/teams", TeamsAPIView.as_view(), name="teams-api-no-slash"),
    path("v1/teams/", TeamsAPIView.as_view(), name="teams-api"),
    path("v1/teams/<str:team_id>/", TeamDetailAPIView.as_view(), name="teams-api-detail"),
    # Composition rosters (REQ-20 / REQ-28). Not teams.json LLM aliases.
    path("v1/team-rosters", TeamRostersAPIView.as_view(), name="team-rosters-api-no-slash"),
    path("v1/team-rosters/", TeamRostersAPIView.as_view(), name="team-rosters-api"),
    path("v1/team-rosters/<str:roster_id>/", TeamRosterDetailAPIView.as_view(), name="team-rosters-api-detail"),
    # Remote harnesses (Hermes / OpenMausBot / Rakazo) — config + health + operate
    path("v1/remotes", RemotesListView.as_view(), name="remotes-list-no-slash"),
    path("v1/remotes/", RemotesListView.as_view(), name="remotes-list"),
    path("v1/remotes/<str:remote_id>", RemoteDetailView.as_view(), name="remotes-detail-no-slash"),
    path("v1/remotes/<str:remote_id>/", RemoteDetailView.as_view(), name="remotes-detail"),
    path("v1/remotes/<str:remote_id>/health", RemoteHealthView.as_view(), name="remotes-health-no-slash"),
    path("v1/remotes/<str:remote_id>/health/", RemoteHealthView.as_view(), name="remotes-health"),
    path("v1/remotes/<str:remote_id>/operate", RemoteOperateView.as_view(), name="remotes-operate-no-slash"),
    path("v1/remotes/<str:remote_id>/operate/", RemoteOperateView.as_view(), name="remotes-operate"),
    # Handoff Team (API/CLI/remote members) — not /v1/teams/ Profiles aliases.
    path("v1/agent-team", AgentTeamView.as_view(), name="agent-team-no-slash"),
    path("v1/agent-team/", AgentTeamView.as_view(), name="agent-team"),
    # JSON Blueprint Library API (REST counterpart to /blueprint-library/)
    path("v1/library", LibraryAPIView.as_view(), name="library-api-no-slash"),
    path("v1/library/", LibraryAPIView.as_view(), name="library-api"),
    path("v1/library/<str:blueprint_name>/", LibraryDetailAPIView.as_view(), name="library-api-detail"),
    # Herdr members (REQ-21): name + optional --remote. Empty remote = localhost.
    path("v1/herdr-agents", HerdrAgentsAPIView.as_view(), name="herdr-agents-api-no-slash"),
    path("v1/herdr-agents/", HerdrAgentsAPIView.as_view(), name="herdr-agents-api"),
    path("v1/herdr-agents/discover", HerdrDiscoverAPIView.as_view(), name="herdr-agents-discover-no-slash"),
    path("v1/herdr-agents/discover/", HerdrDiscoverAPIView.as_view(), name="herdr-agents-discover"),
    path("v1/herdr-agents/<str:agent_id>", HerdrAgentDetailAPIView.as_view(), name="herdr-agents-api-detail-no-slash"),
    path("v1/herdr-agents/<str:agent_id>/", HerdrAgentDetailAPIView.as_view(), name="herdr-agents-api-detail"),
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
    # Agent Creator Pro was unwired clickware (generate/validate/save 404).
    # Keep the path as a soft redirect to the canonical creator.
    path(
        "agent-creator-pro/",
        RedirectView.as_view(url="/agent-creator/", permanent=False, query_string=True),
        name="agent_creator_pro",
    ),
    # Settings Management endpoints
    path("settings/", settings_dashboard, name="settings_dashboard"),
    path("settings/api/", settings_api, name="settings_api"),
    path("settings/environment/", environment_variables, name="environment_variables"),
    path("settings/chats/action/", chat_retention_action, name="chat_retention_action"),
    # Per-agent chat restore (session cookie). Not shown in Chat chrome.
    path("chat/thread/", chat_thread, name="chat_thread"),
    # REQ-37: compact the backlog into a nested sqlite summary (raw JSON stays).
    path("chat/compact/", chat_compact, name="chat_compact"),
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

# Canonical product UI is Django (trailing-slash). Bare SPA-style paths that used
# to dual-mount the React shell now redirect so users never hit two different UIs
# for the same concept (e.g. /teams vs /teams/).
urlpatterns += [
    path(
        "teams",
        RedirectView.as_view(url="/teams/launch/", permanent=False, query_string=True),
        name="spa_teams_to_django",
    ),
    path(
        "blueprints",
        RedirectView.as_view(url="/blueprint-library/", permanent=False, query_string=True),
        name="spa_blueprints_to_django",
    ),
    path(
        "settings",
        RedirectView.as_view(url="/settings/", permanent=False, query_string=True),
        name="spa_settings_to_django",
    ),
    # Bare /agent-creator (no slash) used to hit an empty SPA shell; canonical
    # creator is Django at /agent-creator/.
    path(
        "agent-creator",
        RedirectView.as_view(url="/agent-creator/", permanent=False, query_string=True),
        name="spa_agent_creator_to_django",
    ),
]

# SPA Fallback for React Router - must be last (home `/` and experimental routes).
def _get_frontend_path():
    """Get the path to the built frontend assets."""
    frontend_path = Path("webui/frontend/dist")
    if not frontend_path.exists():
        frontend_path = Path("webui/frontend/build")
    return frontend_path if frontend_path.exists() else None

frontend_path = _get_frontend_path()
if frontend_path and frontend_path.exists():
    import mimetypes

    def spa_asset(request, path):
        root = (frontend_path / "assets").resolve()
        target = (root / path).resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            return HttpResponse("Not Found", status=404)
        ctype, _ = mimetypes.guess_type(str(target))
        return asgi_file_response(target, ctype or "application/octet-stream")

    # SPA fallback - serve index.html for all non-API, non-admin, non-static routes
    # (the catch-all regex below has no capture group, so path must default)
    def spa_fallback(request, path=""):
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return asgi_file_response(index_file, "text/html")
        return HttpResponse("Not Found", status=404)

    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', spa_asset),
        re_path(r'^(?!api/|admin/|static/|assets/|mcp/|marketplace/|v1/|teams/|blueprint-library/|agent-creator/|settings/|accounts/|login/|profiles/|sessions/|webui/|chat/|agents/).*$', spa_fallback),
    ]
