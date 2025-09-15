from django.conf import settings
from django.conf import settings as dj_settings
from django.conf.urls.static import static
from django.urls import path

from swarm.views.agent_creator_pro import agent_creator_pro_page
from swarm.views.agent_creator_views import (
    agent_creator_page,
    generate_agent_code,
    save_custom_agent,
    team_creator_page,
    validate_agent_code,
)
from swarm.views.api_views import (
    BlueprintsListView,
    CustomBlueprintDetailView,
    CustomBlueprintsView,
    MarketplaceBlueprintsView,
    MarketplaceGitHubBlueprintsView,
    MarketplaceGitHubMCPConfigsView,
    MarketplaceMCPConfigsView,
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
from swarm.views.settings_views import (
    environment_variables,
    settings_api,
    settings_dashboard,
)
from swarm.views.web_views import profiles_page, team_admin, team_launcher, teams_export

# Prefer the AllowAny variant if it's present in URL mappings elsewhere; for tests,
# wire the open variant to avoid auth blocking. If needed, switch to ProtectedModelsView.
urlpatterns = [
    path("v1/models", OpenAIModelsView.as_view(), name="models-list-no-slash"),
    path("v1/models/", OpenAIModelsView.as_view(), name="models-list"),
    path("v1/blueprints", BlueprintsListView.as_view(), name="blueprints-list-no-slash"),
    path("v1/blueprints/", BlueprintsListView.as_view(), name="blueprints-list"),
    path("v1/blueprints/custom/", CustomBlueprintsView.as_view(), name="custom-blueprints"),
    path("v1/blueprints/custom/<str:blueprint_id>/", CustomBlueprintDetailView.as_view(), name="custom-blueprint-detail"),
    # Optional marketplace (Wagtail) headless endpoints (return empty list if disabled)
    path("marketplace/blueprints/", MarketplaceBlueprintsView.as_view(), name="marketplace-blueprints"),
    path("marketplace/mcp-configs/", MarketplaceMCPConfigsView.as_view(), name="marketplace-mcp-configs"),
    path("marketplace/github/blueprints/", MarketplaceGitHubBlueprintsView.as_view(), name="marketplace-github-blueprints"),
    path("marketplace/github/mcp-configs/", MarketplaceGitHubMCPConfigsView.as_view(), name="marketplace-github-mcp-configs"),
    path("v1/chat/completions", ChatCompletionsView.as_view(), name="chat_completions"),
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
]

# Serve avatar images in development
if settings.DEBUG:
    urlpatterns += static(settings.AVATAR_URL_PREFIX, document_root=settings.AVATAR_STORAGE_PATH)

# Optional Wagtail admin/site when enabled
if getattr(dj_settings, 'ENABLE_WAGTAIL', False):
    try:  # Import lazily to avoid hard dependency when disabled
        from django.urls import include
        from wagtail import urls as wagtail_urls
        from wagtail.admin import urls as wagtailadmin_urls
        from wagtail.documents import urls as wagtaildocs_urls

        urlpatterns += [
            path('cms/admin/', include(wagtailadmin_urls)),
            path('cms/documents/', include(wagtaildocs_urls)),
            path('cms/', include(wagtail_urls)),
        ]
    except Exception:
        pass

# Optional SAML IdP (djangosaml2idp) when enabled
if getattr(dj_settings, 'ENABLE_SAML_IDP', False):
    try:
        from django.urls import include
        urlpatterns += [
            path('idp/', include('djangosaml2idp.urls')),
        ]
    except Exception:
        # Package not installed or import failed; ignore if disabled in env
        pass

# Optional MCP server (django-mcp-server) when enabled
if getattr(dj_settings, 'ENABLE_MCP_SERVER', False):
    try:
        from django.urls import include
        urlpatterns += [
            path('mcp/', include('django_mcp_server.urls')),
        ]
    except Exception:
        pass
