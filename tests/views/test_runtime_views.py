"""GET /v1/runtime/ and /v1/browser-control/ — AllowAny, no secrets."""
import pytest
from rest_framework.test import APIClient

from swarm.core.runtime_mode import (
    ENV_RUNTIME_MODE,
    MODE_BARE_METAL,
    MODE_SANDBOX_HOME,
    MODE_SANDBOX_ISOLATED,
    MODE_UNKNOWN,
    TONE_INFO,
    TONE_UNKNOWN,
    TONE_WARNING,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.parametrize(
    ("value", "mode", "tone"),
    [
        ("bare-metal", MODE_BARE_METAL, TONE_WARNING),
        ("sandbox-home", MODE_SANDBOX_HOME, TONE_WARNING),
        ("sandbox-isolated", MODE_SANDBOX_ISOLATED, TONE_INFO),
        ("", MODE_UNKNOWN, TONE_UNKNOWN),
        (None, MODE_UNKNOWN, TONE_UNKNOWN),
        ("/home/ubuntu", MODE_UNKNOWN, TONE_UNKNOWN),
    ],
)
def test_runtime_modes(api_client, monkeypatch, value, mode, tone):
    if value is None:
        monkeypatch.delenv(ENV_RUNTIME_MODE, raising=False)
    else:
        monkeypatch.setenv(ENV_RUNTIME_MODE, value)

    response = api_client.get("/v1/runtime/")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == mode
    assert body["tone"] == tone
    if mode == MODE_SANDBOX_ISOLATED:
        assert body["tone"] == TONE_INFO
    else:
        assert body["tone"] != TONE_INFO or mode == MODE_SANDBOX_ISOLATED
    blob = str(body)
    assert "/home/ubuntu" not in blob
    assert "secret" not in blob.lower()


def test_runtime_unknown_never_green(api_client, monkeypatch):
    monkeypatch.delenv(ENV_RUNTIME_MODE, raising=False)
    body = api_client.get("/v1/runtime").json()
    assert body["mode"] == MODE_UNKNOWN
    assert body["known"] is False
    assert body["tone"] == TONE_UNKNOWN


def test_browser_control_catalog(api_client):
    response = api_client.get("/v1/browser-control/")
    assert response.status_code == 200
    body = response.json()
    assert body["default"] == "this_machine"
    ids = [row["id"] for row in body["targets"]]
    assert ids == ["this_machine", "sandbox", "saas"]
    assert body["targets"][0]["wired"] is True
    assert body["targets"][1]["todo"] is True
    assert body["targets"][2]["todo"] is True
