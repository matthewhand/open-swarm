"""REQ-111 Wave 1a/1b: headless Textual chrome tests (kind sections + keys).

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


def _row_texts(app) -> list[str]:
    """All #rail-list ListItem static texts (headers + seats), in order."""
    from textual.widgets import ListItem

    rows: list[str] = []
    for item in app.query_one("#rail-list", ListView).query(ListItem):
        for child in item.children:
            if isinstance(child, Static):
                rows.append(str(child.renderable))
    return rows


async def test_rail_lists_seats_and_chat_placeholder():
    async with TuiApp(_seats(), base_url="http://127.0.0.1:8000").run_test() as pilot:
        text = _static_text(pilot.app)
        for name in ("Support", "Grok", "Night"):
            assert name in text
        body = pilot.app.query_one("#chat-body", Static).renderable
        assert "placeholder" in str(body).lower()
        assert "no messages are invented" in str(body).lower()


async def test_kind_section_headers_group_seats():
    async with TuiApp(_seats()).run_test() as pilot:
        rows = _row_texts(pilot.app)
        # Wave 1b: section headers appear before their seats; no empty section.
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
    async with TuiApp(_seats()).run_test() as pilot:
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


async def test_enter_selects_seat_and_updates_heading():
    async with TuiApp(_seats()).run_test() as pilot:
        await pilot.press("j")  # grok -> support
        await pilot.press("enter")
        assert pilot.app.selected_id == "support"
        heading = pilot.app.query_one("#chat-title", Static).renderable
        assert "Support" in str(heading)
        assert "api" in str(heading)


async def test_first_displayed_seat_is_pre_selected_heading():
    async with TuiApp(_seats()).run_test() as pilot:
        heading = pilot.app.query_one("#chat-title", Static).renderable
        # Rail display order starts with the CLI section (grok), not api support.
        assert "Grok" in str(heading)


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
