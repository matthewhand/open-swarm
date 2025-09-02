import json
import pytest
from rest_framework.test import APIRequestFactory
from rest_framework import status

# Target the open (AllowAny) blueprints list view
from src.swarm.views.api_views import BlueprintsListView as TargetBlueprintsView


@pytest.fixture(scope="module")
def factory():
    return APIRequestFactory()


def _invoke_view(monkeypatch, replacement):
    """
    Monkeypatch get_available_blueprints and invoke the view synchronously.
    Returns a rendered DRF Response.
    """
    import src.swarm.views.api_views as api_views
    monkeypatch.setattr(api_views, "get_available_blueprints", replacement, raising=True)
    view = TargetBlueprintsView.as_view()
    request = APIRequestFactory().get("/v1/blueprints")
    response = view(request)
    if hasattr(response, "render"):
        response = response.render()
    return response


@pytest.mark.django_db
def test_blueprints_unexpected_type_logs_error_and_returns_200(monkeypatch, caplog):
    async def _weird():
        return 3.14159

    with caplog.at_level("ERROR"):
        response = _invoke_view(monkeypatch, _weird)
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.content.decode("utf-8"))
    assert payload.get("object") == "list"
    assert isinstance(payload.get("data"), list)
    # Ensure we recorded an error about unexpected type
    assert any("Unexpected type from get_available_blueprints" in rec.getMessage() for rec in caplog.records)


@pytest.mark.django_db
def test_blueprints_exception_returns_500(monkeypatch, caplog):
    async def boom():
        raise RuntimeError("boom")

    with caplog.at_level("ERROR"):
        response = _invoke_view(monkeypatch, boom)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    payload = json.loads(response.content.decode("utf-8"))
    assert "error" in payload
    # Exception path should log with stacktrace
    assert any("Error retrieving blueprints list." in rec.getMessage() for rec in caplog.records)


@pytest.mark.django_db
def test_blueprints_metadata_projection(monkeypatch):
    async def _ok():
        return {
            "alpha": {"metadata": {"name": "Alpha", "description": "First", "abbreviation": "A"}},
            "beta": {},  # Missing metadata should not crash
        }

    response = _invoke_view(monkeypatch, _ok)
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.content.decode("utf-8"))
    items = {item["id"]: item for item in payload.get("data", [])}
    assert items["alpha"]["name"] == "Alpha"
    assert items["alpha"]["description"] == "First"
    assert items["alpha"]["abbreviation"] == "A"
    # Defaults
    assert items["beta"]["name"] == "beta"
    assert items["beta"]["object"] == "blueprint"

