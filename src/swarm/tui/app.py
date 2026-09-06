"""REQ-111 Wave 1a: interactive Textual chrome for ``swarm-cli tui``.

Renders the AGENTS rail on the left and a placeholder chat pane on the right.
Keyboard: ``j``/``k`` (or arrows) move, ``Enter`` selects, ``q`` quits. There is
no in-process agent runtime — the rail seats come from the same REST the WebUI
reads, and no messages are invented.

Textual stays an optional ``[tui]`` extra: this module is only imported from
the interactive branch of ``swarm.tui.cli``, so the Wave 0 ``--once`` ASCII
dump keeps working on a plain install.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import ListItem, ListView, Static

from swarm.tui.client import RailSeat

CHAT_BODY = (
    "Chat pane — Wave 1 loads and sends on the selected agent's session.\n"
    "This is a placeholder. No messages are invented."
)
EMPTY_RAIL = "No seats — API returned none (honest)."
FOOTER = " j/k or \u2191/\u2193 move \u00b7 Enter select \u00b7 q quit \u00b7 --once for the ASCII dump (CI)"


class _SeatItem(ListItem):
    """One rail row; keeps its ``RailSeat`` so selection maps back cleanly."""

    def __init__(self, seat: RailSeat, *, selected: bool = False) -> None:
        marker = "\u25cf" if selected else " "
        super().__init__(Static(f" {marker} {seat.name}", classes="seat-name"))
        self.seat = seat


class TuiApp(App[None]):
    """Herdr-like two-pane chrome: left agent rail, right placeholder chat."""

    TITLE = "Open Swarm TUI"
    SUB_TITLE = "REQ-111 Wave 1a chrome \u2014 list only, no send"
    CSS = """
    #chrome { height: 1fr; }
    #rail-box { width: 36; border-right: solid $primary; }
    #rail-title { text-style: bold; background: $primary; color: $text; }
    #rail-list { height: 1fr; }
    #chat-box { width: 1fr; }
    #chat-title { text-style: bold; background: $surface; color: $text; }
    #chat-body { padding: 1 2; }
    #footer { height: 1; color: $text-muted; }
    .seat-name { padding: 0 1; }
    """

    # ``q`` is app-wide today (no text input exists yet). Wave 2c adds a
    # composer — scope these bindings to the chrome then so typing never quits.
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(
        self,
        seats: list[RailSeat],
        *,
        base_url: str = "",
        selected_id: str | None = None,
    ) -> None:
        super().__init__()
        self._seats = list(seats)
        self._base_url = base_url
        self._selected_id = _initial_selected(self._seats, selected_id)
        self.selected_id = self._selected_id

    # -- composition ---------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Horizontal(id="chrome"):
            with Vertical(id="rail-box"):
                yield Static(" AGENTS", id="rail-title")
                yield self._rail_list()
            with Vertical(id="chat-box"):
                yield Static(self._chat_heading(), id="chat-title")
                yield Static(CHAT_BODY, id="chat-body")
        yield Static(FOOTER, id="footer")

    def _rail_list(self) -> ListView:
        items: list[ListItem] = []
        for seat in self._seats:
            items.append(_SeatItem(seat, selected=(seat.id == self._selected_id)))
        if not items:
            items.append(ListItem(Static(EMPTY_RAIL, classes="seat-name")))
        self._list_view = ListView(*items, id="rail-list")
        return self._list_view

    # -- keys ---------------------------------------------------------------
    def action_cursor_down(self) -> None:
        if self._seats:
            self.query_one("#rail-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._seats:
            self.query_one("#rail-list", ListView).action_cursor_up()

    # -- events -------------------------------------------------------------
    def on_mount(self) -> None:
        if self._seats:
            index = 0
            for i, seat in enumerate(self._seats):
                if seat.id == self._selected_id:
                    index = i
                    break
            self._list_view.index = index

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._seats:
            return
        index = event.list_view.index
        if index is None or not 0 <= index < len(self._seats):
            return
        seat = self._seats[index]
        self._selected_id = seat.id
        self.selected_id = seat.id
        self.query_one("#chat-title", Static).update(self._chat_heading(seat))
        self.query_one("#chat-body", Static).update(CHAT_BODY)

    # -- helpers ------------------------------------------------------------
    def _chat_heading(self, seat: RailSeat | None = None) -> str:
        seat = seat or _seat_by_id(self._seats, self._selected_id)
        if seat is None:
            return " Chat \u2014 none selected"
        return f" Chat \u2014 {seat.name} ({seat.kind} \u00b7 {seat.source})"


def _initial_selected(seats: list[RailSeat], selected_id: str | None) -> str | None:
    if not seats:
        return None
    if selected_id:
        for seat in seats:
            if seat.id == selected_id:
                return seat.id
    return seats[0].id


def _seat_by_id(seats: list[RailSeat], seat_id: str | None) -> RailSeat | None:
    if not seat_id:
        return None
    for seat in seats:
        if seat.id == seat_id:
            return seat
    return None


def run_tui_app(
    seats: list[RailSeat],
    *,
    base_url: str = "",
    selected_id: str | None = None,
) -> None:
    """Blocking entry point used by the interactive ``swarm-cli tui`` path."""
    TuiApp(seats, base_url=base_url, selected_id=selected_id).run()


__all__ = ["CHAT_BODY", "EMPTY_RAIL", "FOOTER", "TuiApp", "run_tui_app"]
