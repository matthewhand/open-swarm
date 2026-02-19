import json

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

try:
    from src.swarm.views.api_views import ModelsListView as TargetModelsView
except Exception:  # pragma: no cover - fallback path if module layout changes
    from src.swarm.views.model_views import (
        ListModelsView as TargetModelsView,  # type: ignore
    )


def _invoke_view(monkeypatch, replacement):
    """
    Monkeypatch get_available_blueprints and invoke the view synchronously.
    Returns a rendered DRF Response.
    """
    import src.swarm.views.api_views as api_views
    monkeypatch.setattr(api_views, "get_available_blueprints", replacement, raising=True)
    view = TargetModelsView.as_view()
    request = APIRequestFactory().get("/v1/models")
    response = view(request)
    if hasattr(response, "render"):
        response = response.render()
    return response


@pytest.mark.django_db
def test_models_positive_dict_source(monkeypatch):
    """
    When discovery returns a mapping, ensure response follows OpenAI models schema.
    """
    async def _ok():
        return {"alpha": {"metadata": {"name": "Alpha"}}}

    response = _invoke_view(monkeypatch, _ok)
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.content.decode("utf-8"))
    assert payload.get("object") == "list"
    data = payload.get("data")
    assert isinstance(data, list) and data
    item = {x["id"]: x for x in data}["alpha"]
    assert item["object"] == "model"
    assert item["owned_by"] == "open-swarm"
    assert isinstance(item["created"], int)


@pytest.mark.django_db
def test_models_positive_list_source(monkeypatch):
    """
    When discovery returns a list of blueprint ids, ensure they are projected correctly.
    """
    async def _ok():
        return ["alpha", "beta"]

    response = _invoke_view(monkeypatch, _ok)
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.content.decode("utf-8"))
    ids = sorted([x["id"] for x in payload.get("data", [])])
    assert ids == ["alpha", "beta"]

