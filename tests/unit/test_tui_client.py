"""REQ-111 Wave 0: TUI rail client talks HTTP REST only; honest degrade."""

from __future__ import annotations

import httpx
import pytest

from swarm.tui.client import (
    DEFAULT_BASE_URL,
    RAIL_KIND_SECTIONS,
    AgentThread,
    RailSeat,
    SwarmApiError,
    fetch_thread,
    is_rail_seat,
    list_rail_agents,
    rail_section,
    resolve_base_url,
    resolve_token,
    sectioned_seats,
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


def test_resolve_token_prefers_api_auth_token_over_swarm_api_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "primary-token")
    monkeypatch.setenv("SWARM_API_KEY", "legacy-token")
    assert resolve_token() == "primary-token"


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
        if url.endswith("/v1/team-rosters/"):
            return _response(
                200,
                {
                    "object": "list",
                    "data": [
                        {"id": "research", "name": "Research", "members": []},
                        {
                            "id": "office",
                            "name": "Office",
                            "members": [{"id": "research", "kind": "team"}],
                        },
                    ],
                },
            )
        if url.endswith("/v1/herdr-agents/"):
            return _response(
                200,
                {
                    "object": "list",
                    "data": [{"id": 7, "name": "workbox", "kind": "herdr"}],
                },
            )
        raise AssertionError(url)

    seats = list_rail_agents(base_url="http://127.0.0.1:8000", token="test-token", getter=getter)
    # research is a child team of office → only the root office roster surfaces.
    assert [s.id for s in seats] == ["support", "grok", "hermes", "team:office", "herdr:workbox"]
    assert seats[0] == RailSeat(id="support", name="Support", kind="api", source="blueprints")
    assert seats[2].kind == "remote"
    assert seats[3] == RailSeat(
        id="team:office", name="Office", kind="team", source="team-rosters"
    )
    assert seats[4] == RailSeat(
        id="herdr:workbox", name="workbox", kind="herdr", source="herdr-agents"
    )
    assert any("/v1/blueprints/" in u for u in calls)
    assert any("/v1/team-rosters/" in u for u in calls)
    assert any("/v1/herdr-agents/" in u for u in calls)
    assert "poets" not in {s.id for s in seats}
    assert "rakazo" not in {s.id for s in seats}
    assert "team:research" not in {s.id for s in seats}


def test_list_rail_agents_connection_error_is_honest():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(SwarmApiError, match="API unreachable"):
        list_rail_agents(base_url="http://127.0.0.1:8000", getter=getter)


def test_connection_error_names_base_env_hint():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(SwarmApiError) as exc:
        list_rail_agents(getter=getter)
    message = str(exc.value)
    assert "API unreachable" in message
    assert "SWARM_API_BASE" in message
    assert "127.0.0.1:8000" in message


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


def test_optional_catalog_rejected_token_is_fatal():
    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        if url.endswith("/v1/blueprints/"):
            return _response(200, {"object": "list", "data": []})
        return _response(401, {"detail": "nope"})

    with pytest.raises(SwarmApiError, match="not accepted"):
        list_rail_agents(getter=getter, token="wrong-key")


def test_optional_catalog_auth_required_without_token_is_fatal():
    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        if url.endswith("/v1/blueprints/"):
            return _response(200, {"object": "list", "data": []})
        return _response(403, {"detail": "nope"})

    with pytest.raises(SwarmApiError, match="auth required"):
        list_rail_agents(getter=getter)


# --- Wave 1c: named auth, missing vs rejected, never leaks a token ----------


def test_auth_required_401_without_token_names_env_vars(monkeypatch):
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("SWARM_API_KEY", raising=False)

    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _response(401, {"detail": "nope"})

    with pytest.raises(SwarmApiError) as exc:
        list_rail_agents(getter=getter)
    message = str(exc.value)
    assert "auth required (401)" in message
    assert "API_AUTH_TOKEN" in message
    assert "SWARM_API_KEY" in message


def test_auth_rejected_401_with_token_is_named_and_never_leaks():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _response(401, {"detail": "nope"})

    with pytest.raises(SwarmApiError) as exc:
        list_rail_agents(getter=getter, token="sk-live-secret-value")
    message = str(exc.value)
    assert "auth failed (401)" in message
    assert "not accepted" in message
    assert "sk-live-secret-value" not in message


def test_auth_403_is_named_and_never_leaks():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _response(403, {"detail": "nope"})

    with pytest.raises(SwarmApiError) as exc:
        list_rail_agents(getter=getter, token="wrong-key")
    message = str(exc.value)
    assert "auth failed (403)" in message
    assert "wrong-key" not in message


def test_no_authorization_header_when_no_token(monkeypatch):
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("SWARM_API_KEY", raising=False)
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, timeout: float):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, _url: str, headers: dict[str, str]):
            captured["headers"] = headers
            return _response(200, {"object": "list", "data": []})

    monkeypatch.setattr("swarm.tui.client.httpx.Client", FakeClient)
    assert list_rail_agents(base_url="http://127.0.0.1:8000", token=None) == []
    assert "Authorization" not in captured["headers"]
    assert captured["headers"] == {"Accept": "application/json"}


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
    assert any(str(u).endswith("/v1/team-rosters/") for u in captured["urls"])
    assert any(str(u).endswith("/v1/herdr-agents/") for u in captured["urls"])
    assert isinstance(captured["headers"], dict)


def test_missing_team_and_herdr_catalogs_are_optional():
    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        if url.endswith("/v1/blueprints/"):
            return _response(200, {"object": "list", "data": []})
        return _response(404, {"detail": "not found"})

    # Blueprints alone never fabricates teams / herdr members.
    assert list_rail_agents(getter=getter) == []


# --- Wave 1b: kind sections CLI / API / Blueprint / Remote -----------------


def test_rail_section_maps_kinds_to_four_sections():
    assert rail_section("cli") == "CLI"
    assert rail_section("api") == "API"
    assert rail_section("blueprint") == "Blueprint"
    assert rail_section("team") == "Blueprint"  # Team = Blueprint subtype
    assert rail_section("remote") == "Remote"
    assert rail_section("herdr") == "Remote"  # Herdr is a Remote implementation
    assert rail_section("") == "Blueprint"  # catalog rail rows default


def test_sectioned_seats_groups_and_omits_empty_sections():
    seats = [
        RailSeat(id="grok", name="Grok", kind="cli", source="cli-agents"),
        RailSeat(id="support", name="Support", kind="api", source="blueprints"),
        RailSeat(id="team:office", name="Office", kind="team", source="team-rosters"),
        RailSeat(id="night", name="Night", kind="remote", source="remotes"),
        RailSeat(id="herdr:workbox", name="workbox", kind="herdr", source="herdr-agents"),
    ]
    groups = sectioned_seats(seats)
    assert [label for label, _ in groups] == ["CLI", "API", "Blueprint", "Remote"]
    by_label = dict(groups)
    assert [s.id for s in by_label["CLI"]] == ["grok"]
    assert [s.id for s in by_label["API"]] == ["support"]
    assert [s.id for s in by_label["Blueprint"]] == ["team:office"]
    assert [s.id for s in by_label["Remote"]] == ["night", "herdr:workbox"]


def test_rail_kind_sections_are_the_four_user_facing_kinds():
    assert RAIL_KIND_SECTIONS == ("CLI", "API", "Blueprint", "Remote")


# --- Wave 2a: fetch_thread hydrate via GET /chat/thread/ --------------------

_THREAD_URL = "http://127.0.0.1:8000/chat/thread/?agent=grok"


def _thread_response(
    status: int,
    payload=None,
    *,
    content_type: str = "application/json",
    url: str = _THREAD_URL,
) -> httpx.Response:
    request = httpx.Request("GET", url)
    if content_type != "application/json":
        return httpx.Response(status, headers={"content-type": content_type}, request=request)
    return httpx.Response(status, json=payload if payload is not None else {}, request=request)


def test_fetch_thread_parses_messages_and_meta():
    payload = {
        "agent_id": "grok",
        "conversation_id": "agt-7-grok",
        "kind": "cli",
        "editable": False,
        "session_missing": False,
        "messages": [
            {"role": "user", "content": "hi", "ts": "2026-09-06T09:00:00Z"},
            {"role": "assistant", "content": "yo", "edited": True},
        ],
    }

    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _thread_response(200, payload)

    thread = fetch_thread(agent="grok", getter=getter)
    assert isinstance(thread, AgentThread)
    assert thread.conversation_id == "agt-7-grok"
    assert thread.kind == "cli"
    assert thread.editable is False
    assert [(m.role, m.content) for m in thread.messages] == [
        ("user", "hi"),
        ("assistant", "yo"),
    ]
    assert thread.messages[0].ts == "2026-09-06T09:00:00Z"
    assert thread.messages[1].edited is True


def test_fetch_thread_empty_transcript_is_honest_not_error():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _thread_response(200, {"conversation_id": "agt-7-grok", "messages": []})

    thread = fetch_thread(agent="grok", getter=getter)
    assert thread.messages == []


def test_fetch_thread_uses_default_thread_and_bearer():
    captured: list[str] = []
    headers_seen: dict[str, str] = {}

    def getter(url: str, headers: dict[str, str]) -> httpx.Response:
        captured.append(url)
        headers_seen.update(headers)
        return _thread_response(200, {"conversation_id": "c", "messages": []})

    fetch_thread(agent="grok", token="tok-123", getter=getter)
    # No session concept yet: no conversation_id is sent — server default wins.
    assert "conversation_id" not in captured[0]
    assert captured[0].startswith("http://127.0.0.1:8000/chat/thread/?agent=grok")
    assert headers_seen["Authorization"] == "Bearer tok-123"


def test_fetch_thread_session_gated_302_html_is_named():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _thread_response(302, content_type="text/html")

    with pytest.raises(SwarmApiError) as exc:
        fetch_thread(agent="grok", getter=getter)
    message = str(exc.value)
    assert "login-gated" in message
    assert "session cookie" in message
    assert "Wave 3b" in message


def test_fetch_thread_session_gated_401_is_named():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _thread_response(401, {"detail": "nope"})

    with pytest.raises(SwarmApiError, match="session cookie"):
        fetch_thread(agent="grok", getter=getter)


def test_fetch_thread_transport_error_is_honest():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(SwarmApiError, match="API unreachable"):
        fetch_thread(agent="grok", getter=getter)


def test_fetch_thread_http_error_is_named():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        return _thread_response(503, {"detail": "down"})

    with pytest.raises(SwarmApiError, match="503"):
        fetch_thread(agent="grok", getter=getter)
