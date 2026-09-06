"""REQ-111 Wave 1a: headless Textual chrome tests (rail + j/k/Enter/q).

Textual is an optional ``[tui]`` extra; these tests skip when it is not
installed so the core suite never hard-depends on it.
"""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import ListView, Static  # noqa: E402

from swarm.tui.app import EMPTY_RAIL, TuiApp  # noqa: E402
from swarm.tui.client import RailSeat  # noqa: E402


def _seats() -> list[RailSeat]:
    return [
        RailSeat(id="support", name="Support", kind="api", source="blueprints"),
        RailSeat(id="grok", name="Grok", kind="cli", source="cli-agents"),
        RailSeat(id="night", name="Night", kind="remote", source="remotes"),
    ]


def _static_text(app) -> str:
    return "\n".join(
        str(widget.renderable)
        for widget in app.query(Static)
        if widget.renderable is not None
    )


async def test_rail_lists_seats_and_chat_placeholder():
    async with TuiApp(_seats(), base_url="http://127.0.0.1:8000").run_test() as pilot:
        text = _static_text(pilot.app)
        for name in ("Support", "Grok", "Night"):
            assert name in text
        body = pilot.app.query_one("#chat-body", Static).renderable
        assert "placeholder" in str(body).lower()
        assert "no messages are invented" in str(body).lower()


async def test_jk_moves_and_enter_selects():
    async with TuiApp(_seats()).run_test() as pilot:
        rail = pilot.app.query_one("#rail-list", ListView)
        assert rail.index == 0  # Support selected first
        await pilot.press("j")
        assert rail.index == 1
        await pilot.press("k")
        assert rail.index == 0
        await pilot.press("down")
        assert rail.index == 1
        await pilot.press("enter")
        assert pilot.app.selected_id == "grok"
        heading = pilot.app.query_one("#chat-title", Static).renderable
        assert "Grok" in str(heading)
        assert "cli" in str(heading)


async def test_first_seat_is_pre_selected_heading():
    async with TuiApp(_seats()).run_test() as pilot:
        heading = pilot.app.query_one("#chat-title", Static).renderable
        assert "Support" in str(heading)


async def test_q_quits():
    app = TuiApp(_seats())
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
