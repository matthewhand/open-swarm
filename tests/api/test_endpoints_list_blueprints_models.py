import pytest
from rest_framework.test import APIRequestFactory

from src.swarm.views.utils import register_dynamic_team, deregister_dynamic_team
from src.swarm.views.api_views import ModelsListView, BlueprintsListView


@pytest.mark.django_db(transaction=True)
def test_models_and_blueprints_endpoints_include_dynamic_team(settings):
    settings.ENABLE_WEBUI = True

    # Ensure clean state and register a team
    deregister_dynamic_team("demo-api-team")
    register_dynamic_team("demo-api-team", description="API Demo", llm_profile="default")

    factory = APIRequestFactory()

    # /v1/models via view instance
    request = factory.get("/v1/models")
    response = ModelsListView.as_view()(request)
    assert response.status_code == 200
    data = response.data if hasattr(response, "data") else response.json()
    ids = {m.get("id") for m in data.get("data", [])}
    assert "demo-api-team" in ids

    # /v1/blueprints via view instance
    request = factory.get("/v1/blueprints")
    response = BlueprintsListView.as_view()(request)
    assert response.status_code == 200
    data = response.data if hasattr(response, "data") else response.json()
    ids = {m.get("id") for m in data.get("data", [])}
    assert "demo-api-team" in ids

    # Cleanup
    deregister_dynamic_team("demo-api-team")
