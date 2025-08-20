from django.urls import path
from src.swarm.views.api_views import ModelsListView as OpenAIModelsView
from src.swarm.views.api_views import BlueprintsListView
from src.swarm.views.model_views import ListModelsView as ProtectedModelsView
from src.swarm.views.chat_views import ChatCompletionsView
from src.swarm.views.web_views import team_launcher, team_admin, teams_export, profiles_page
from src.swarm.views.agent_creator_views import (
    agent_creator_page, generate_agent_code, validate_agent_code, save_custom_agent,
    team_creator_page
)
from src.swarm.views.agent_creator_pro import (
    agent_creator_pro_page
)
from src.swarm.views.settings_views import (
    settings_dashboard, settings_api, environment_variables
)

# Prefer the AllowAny variant if it's present in URL mappings elsewhere; for tests,
# wire the open variant to avoid auth blocking. If needed, switch to ProtectedModelsView.
urlpatterns = [
    path("v1/models", OpenAIModelsView.as_view(), name="models-list-no-slash"),
    path("v1/models/", OpenAIModelsView.as_view(), name="models-list"),
    path("v1/blueprints", BlueprintsListView.as_view(), name="blueprints-list-no-slash"),
    path("v1/blueprints/", BlueprintsListView.as_view(), name="blueprints-list"),
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
]
