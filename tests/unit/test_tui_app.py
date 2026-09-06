"""REQ-111 Wave 1a/1b/2a: headless Textual chrome tests (kind sections, keys,
hydrate via mocked GET /chat/thread/).

Textual is an optional ``[tui]`` extra; these tests skip when it is not
installed so the core suite never hard-depends on it.
"""

from __future__ import annotations

import httpx
import pytest

textual = pytest.importorskip("textual")

from textual.widgets import ListItem, ListView, Static  # noqa: E402

from swarm.tui.app import EMPTY_RAIL, EMPTY_THREAD, TuiApp  # noqa: E402
from swarm.tui.client import RailSeat  # noqa: E402


def _seats() -> list[RailSeat]:
    return [
        RailSeat(id="support", name="Support", kind="api", source="blueprints"),
        RailSeat(id="grok", name="Grok", kind="cli", source="cli-agents"),
        RailSeat(id="night", name="Night", kind="remote", source="remotes"),
    ]


def _thread_response(
    messages: list[dict],
    *,
    agent: str = "support",
    conversation_id: str = "agt-1-support",
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request(
        "GET", f"http://127.0.0.1:8000/chat/thread/?agent={agent}"
    )
    if status != 200:
        return httpx.Response(status, headers=headers or {}, request=request)
    return httpx.Response(
        status,
        json={
            "agent_id": agent,
            "conversation_id": conversation_id,
            "kind": "api" if not agent.startswith("cli") else "cli",
            "editable": True,
            "session_missing": False,
            "messages": messages,
        },
        request=request,
    )


def _ok_getter(messages: list[dict] | None = None) -> callable:
    rows = messages if messages is not None else []

    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        assert "chat/thread/" in url
        agent = url.split("agent=", 1)[1]
        return _thread_response(rows, agent=agent)

    return getter


def _static_text(app) -> str:
    return "\n".join(
        str(widget.renderable)
        for widget in app.query(Static)
        if widget.renderable is not None
    )


def _row_texts(app) -> list[str]:
    """All #rail-list ListItem static texts (headers + seats), in order."""
    rows: list[str] = []
    for item in app.query_one("#rail-list", ListView).query(ListItem):
        for child in item.children:
            if isinstance(child, Static):
                rows.append(str(child.renderable))
    return rows


async def _pump_until(pilot, app, needle: str, *, attempts: int = 60) -> str:
    for _ in range(attempts):
        text = _static_text(app)
        if needle in text:
            return text
        await pilot.pause(0.02)
    raise AssertionError(f"never saw {needle!r} in chat body")


# --- Wave 1a/1b chrome (hydrate mocked to empty threads) --------------------


async def test_rail_lists_seats_and_empty_thread_is_honest():
    async with TuiApp(_seats(), getter=_ok_getter()).run_test() as pilot:
        text = _static_text(pilot.app)
        for name in ("Support", "Grok", "Night"):
            assert name in text
        body = await _pump_until(pilot, pilot.app, EMPTY_THREAD)
        # A real (empty) hydrate replaces the Wave 1 placeholder copy.
        assert "No messages yet" in body
        assert "placeholder" not in body.lower()
        assert "invented" not in body.lower()


async def test_kind_section_headers_group_seats():
    async with TuiApp(_seats(), getter=_ok_getter()).run_test() as pilot:
        rows = _row_texts(pilot.app)
        assert any(" CLI" in row for row in rows)
        assert any(" API" in row for row in rows)
        assert any(" Remote" in row for row in rows)
        assert not any(" Blueprint" in row for row in rows)
        cli_at = next(i for i, row in enumerate(rows) if " CLI" in row)
        api_at = next(i for i, row in enumerate(rows) if " API" in row)
        remote_at = next(i for i, row in enumerate(rows) if " Remote" in row)
        grok_at = next(i for i, row in enumerate(rows) if "Grok" in row)
        support_at = next(i for i, row in enumerate(rows) if "Support" in row)
        night_at = next(i for i, row in enumerate(rows) if "Night" in row)
        assert cli_at < grok_at
        assert api_at < support_at
        assert remote_at < night_at


async def test_jk_and_arrows_skip_section_headers():
    async with TuiApp(_seats(), getter=_ok_getter()).run_test() as pilot:
        rail = pilot.app.query_one("#rail-list", ListView)
        # Seats are selected in rail order: grok (CLI) → support (API) → night.
        assert rail.index == 1  # first real seat under the CLI header
        await pilot.press("j")
        assert rail.index == 3  # API header at 2 is skipped
        await pilot.press("j")
        assert rail.index == 5  # Remote header at 4 is skipped
        await pilot.press("down")
        assert rail.index == 5  # clamped at the last seat
        await pilot.press("k")
        assert rail.index == 3
        await pilot.press("k")
        assert rail.index == 1
        await pilot.press("up")
        assert rail.index == 1  # clamped at the first seat


async def test_first_displayed_seat_is_pre_selected_heading():
    async with TuiApp(_seats(), getter=_ok_getter()).run_test() as pilot:
        heading = pilot.app.query_one("#chat-title", Static).renderable
        # Rail display order starts with the CLI section (grok), not api support.
        assert "Grok" in str(heading)


async def test_q_quits():
    app = TuiApp(_seats(), getter=_ok_getter())
    async with app.run_test() as pilot:
        await pilot.press("q")
        assert app.is_running is False


async def test_empty_rail_is_honest_and_keys_are_safe():
    async with TuiApp([]).run_test() as pilot:
        assert EMPTY_RAIL in _static_text(pilot.app)
        await pilot.press("j")
        await pilot.press("k")
        await pilot.press("down")
        await pilot.press("enter")
        assert pilot.app.selected_id is None


# --- Wave 2a: hydrate shows the real transcript / honest states -------------


async def test_mount_hydrates_selected_seat_thread():
    messages = [
        {"role": "user", "content": "first hello", "ts": "2026-09-06T09:00:00Z"},
        {"role": "assistant", "content": "hi from grok", "ts": "2026-09-06T09:00:01Z"},
    ]
    async with TuiApp(_seats(), getter=_ok_getter(messages)).run_test() as pilot:
        body = await _pump_until(pilot, pilot.app, "hi from grok")
        assert "first hello" in body
        assert "you:" in body
        # assistant label is the seat's display name
        assert "Grok:" in body


async def test_selecting_seat_hydrates_that_seat_thread():
    messages = [{"role": "user", "content": "support only message"}]

    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        agent = url.split("agent=", 1)[1]
        if agent.startswith("support"):
            return _thread_response(messages, agent=agent)
        return _thread_response([], agent=agent)

    async with TuiApp(_seats(), getter=getter).run_test() as pilot:
        # Initial (grok) hydrate is empty; move to support and Enter.
        await pilot.press("j")  # grok -> support (skips the API header)
        await pilot.press("enter")
        await _pump_until(pilot, pilot.app, "support only message")
        heading = pilot.app.query_one("#chat-title", Static).renderable
        assert "Support" in str(heading)


async def test_hydrate_transport_failure_first_miss_is_error_state():
    def getter(_url: str, _headers: dict[str, str]) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    async with TuiApp(_seats(), getter=getter).run_test() as pilot:
        body = await _pump_until(pilot, pilot.app, "could not load")
        assert "API unreachable" in body
        # No fail-open empty: the error is explicit.
        assert "No messages yet" not in body


async def test_hydrate_session_gated_error_is_named():
    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        agent = url.split("agent=", 1)[1]
        return _thread_response([], agent=agent, status=302, headers={"content-type": "text/html"})

    async with TuiApp(_seats(), getter=getter).run_test() as pilot:
        body = await _pump_until(pilot, pilot.app, "login-gated")
        assert "session cookie" in body


async def test_hydrate_failure_keeps_non_empty_cache():
    """Second hydrate of the same seat fails but the loaded thread stays visible."""
    hits = {"grok": 0}

    def getter(url: str, _headers: dict[str, str]) -> httpx.Response:
        agent = url.split("agent=", 1)[1]
        if agent.startswith("grok"):
            hits["grok"] += 1
            if hits["grok"] > 1:
                raise httpx.ConnectError("connection refused")
            return _thread_response(
                [{"role": "assistant", "content": "grok cached answer"}],
                agent=agent,
            )
        return _thread_response([], agent=agent)

    async with TuiApp(_seats(), getter=getter).run_test() as pilot:
        await _pump_until(pilot, pilot.app, "grok cached answer")
        await pilot.press("j")  # grok -> support (API header skipped)
        await pilot.press("enter")
        await _pump_until(pilot, pilot.app, "No messages yet")
        await pilot.press("k")  # back to grok
        await pilot.press("enter")
        body = await _pump_until(pilot, pilot.app, "offline cache")
        assert "grok cached answer" in body
        assert "refresh failed" in body
