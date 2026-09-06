"""REQ-111 Wave 0: TUI rail client talks HTTP REST only; honest degrade."""

from __future__ import annotations

import httpx
import pytest

from swarm.tui.client import (
    DEFAULT_BASE_URL,
    RailSeat,
    SwarmApiError,
    is_rail_seat,
    list_rail_agents,
    resolve_base_url,
    resolve_token,
)


def _response(status: int, payload) -> httpx.Response:
    request = httpx.Request("GET", "http://127.0.0.1:8000/v1/blueprints/")
    return httpx.Response(status, json=payload, request=request)


def test_default_base_url_is_loopback_8000_not_8001():
    assert DEFAULT_BASE_URL == "http://127.0.0.1:8000"
    assert ":8001" not in DEFAULT_BASE_URL
    assert resolve_base_url(None) == DEFAULT_BASE_URL


def test_resolve_base_url_env_and_explicit(monkeypatch):
    monkeypatch.setenv("SWARM_API_BASE", "http://127.0.0.1:9/")
    assert resolve_base_url(None) == "http://127.0.0.1:9"
    assert resolve_base_url("http://example.test:8000/") == "http://example.test:8000"


def test_resolve_token_reads_env_names_only(monkeypatch):
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("SWARM_API_KEY", raising=False)
    assert resolve_token() is None
    monkeypatch.setenv("SWARM_API_KEY", "placeholder-not-a-secret")
    assert resolve_token() == "placeholder-not-a-secret"


def test_is_rail_seat_matches_spa_default_deny():
    assert is_rail_seat({"id": "poets", "rail": False}) is False
    assert is_rail_seat({"id": "support", "rail": True}) is True
    assert is_rail_seat({"id": "grok", "kind": "cli"}) is True
    assert is_rail_seat({"id": "herdr-1", "kind": "herdr"}) is True
    assert is_rail_seat({"id": "api-1", "kind": "api"}) is True


def test_list_rail_agents_merges_and_dedupes():
    calls: list[str] = []

    def getter(url: str, headers: dict[str, str]) -> httpx.Response:
        calls.append(url)
        assert headers["Authorization"] == "Bearer test-token"
        if url.endswith("/v1/blueprints/"):
            return _response(
                200,
                {
                    "object": "list",
                    "data": [
                        {"id": "poets", "name": "Poets", "rail": False},
                        {"id": "support", "name": "Support", "rail": True, "kind": "api"},
                    ],
                },
            )
        if url.endswith("/v1/cli-agents/"):
            return _response(
                200,
                {
                    "rail": [
                        {"id": "grok", "name": "Grok", "kind": "cli"},
                        {"id": "support", "name": "Support-cli", "kind": "cli"},
                    ]
                },
            )
        if url.endswith("/v1/remotes/"):
            return _response(
                200,
                {
                    "configured": [{"id": "hermes", "title": "Hermes"}],
                    "data": [{"id": "rakazo", "title": "Default Rakazo"}],
                },
            )
        raise AssertionError(url)

    seats = list_rail_agents(base_url="http://127.0.0.1:8000", token="test-token", getter=getter)
    assert [s.id for s in seats] == ["support", "grok", "hermes"]
    assert seats[0] == RailSeat(id="support", name="Support", kind="api", source="blueprints")
    assert seats[2].kind == "remote"
    assert any("/v1/blueprints/" in u for u in calls)
    assert "poets" not in {s.id for s in seats}
    assert "rakazo" not in {s.id for s in seats}


def test_list_rail_agents_connection_error_is_honest():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(SwarmApiError, match="API unreachable"):
        list_rail_agents(base_url="http://127.0.0.1:8000", getter=getter)


def test_list_rail_agents_http_error_is_honest():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _response(503, {"detail": "down"})

    with pytest.raises(SwarmApiError, match="503"):
        list_rail_agents(getter=getter)


def test_list_rail_agents_empty_catalog_is_not_faked():
    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        if url.endswith("/v1/blueprints/"):
            return _response(200, {"object": "list", "data": []})
        return _response(404, {"detail": "not found"})

    assert list_rail_agents(getter=getter) == []


def test_optional_catalog_auth_failure_is_fatal():
    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        if url.endswith("/v1/blueprints/"):
            return _response(200, {"object": "list", "data": []})
        return _response(401, {"detail": "nope"})

    with pytest.raises(SwarmApiError, match="auth failed"):
        list_rail_agents(getter=getter)


def test_list_rail_agents_uses_httpx_when_no_getter(monkeypatch):
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, timeout: float):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, headers: dict[str, str]):
            captured.setdefault("urls", []).append(url)
            captured["headers"] = headers
            return _response(200, {"object": "list", "data": []})

    monkeypatch.setattr("swarm.tui.client.httpx.Client", FakeClient)
    assert list_rail_agents(base_url="http://127.0.0.1:8000", token=None) == []
    assert captured["urls"][0] == "http://127.0.0.1:8000/v1/blueprints/"
    assert any(str(u).endswith("/v1/cli-agents/") for u in captured["urls"])
    assert any(str(u).endswith("/v1/remotes/") for u in captured["urls"])
    assert isinstance(captured["headers"], dict)
