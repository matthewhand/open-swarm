"""REQ-111 Wave 1a/1b: interactive Textual chrome for ``swarm-cli tui``.

Renders the AGENTS rail on the left (grouped under kind sections CLI / API /
Blueprint / Remote) and a placeholder chat pane on the right. Keyboard:
``j``/``k`` (or arrows) move between seats, ``Enter`` selects, ``q`` quits.
Kind-section headers are decoration only — cursor movement skips them so the
selection always rests on a real seat (Wave 1b).

Textual stays an optional ``[tui]`` extra: this module is only imported from
the interactive branch of ``swarm.tui.cli``, so the Wave 0 ``--once`` ASCII
dump keeps working on a plain install.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import ListItem, ListView, Static

from swarm.tui.client import RailSeat, sectioned_seats

CHAT_BODY = (
    "Chat pane — Wave 1 loads and sends on the selected agent's session.\n"
    "This is a placeholder. No messages are invented."
)
EMPTY_RAIL = "No seats — API returned none (honest)."
FOOTER = " j/k or \u2191/\u2193 move \u00b7 Enter select \u00b7 q quit \u00b7 --once for the ASCII dump (CI)"


class _SeatItem(ListItem):
    """One selectable rail row; keeps its ``RailSeat`` for clean selection."""

    def __init__(self, seat: RailSeat, *, selected: bool = False) -> None:
        marker = "\u25cf" if selected else " "
        super().__init__(Static(f"  {marker} {seat.name}", classes="seat-name"))
        self.seat = seat


class _SectionHeaderItem(ListItem):
    """Non-selectable kind-section header (Wave 1b). Cursor skips it."""

    def __init__(self, label: str) -> None:
        super().__init__(Static(f"  {label}", classes="section-name"))
        self.seat = None


class _SectionListView(ListView):
    """A rail ListView whose kind-section header rows are skipped by the cursor.

    j/k and the arrow keys all end up in ``action_cursor_down`` /
    ``action_cursor_up`` (ListView natively binds the arrows; the app reuses
    the same actions for j/k). Home / End are also overridden so the highlight
    always rests on a real seat, never on a header row.
    """

    def _is_header_index(self, index: int | None) -> bool:
        if index is None:
            return True
        children = list(self.children)
        if not 0 <= index < len(children):
            return True
        return getattr(children[index], "seat", "header") is None

    def action_cursor_down(self) -> None:
        nxt = (self.index if self.index is not None else -1) + 1
        while nxt < len(self.children) and self._is_header_index(nxt):
            nxt += 1
        if nxt < len(self.children):
            self.index = nxt

    def action_cursor_up(self) -> None:
        nxt = (self.index if self.index is not None else len(self.children)) - 1
        while nxt >= 0 and self._is_header_index(nxt):
            nxt -= 1
        if nxt >= 0:
            self.index = nxt

    def action_cursor_home(self) -> None:
        """Home parks on the first real seat, never a section header."""
        for i in range(len(self.children)):
            if not self._is_header_index(i):
                self.index = i
                return

    def action_cursor_end(self) -> None:
        """End parks on the last real seat, never a section header."""
        for i in range(len(self.children) - 1, -1, -1):
            if not self._is_header_index(i):
                self.index = i
                return


class TuiApp(App[None]):
    """Two-pane chrome: left rail grouped by kind section, right placeholder."""

    TITLE = "Open Swarm TUI"
    SUB_TITLE = "REQ-111 Wave 1b rail parity \u2014 list only, no send"
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
    .section-name { padding: 0 1; color: $text-muted; text-style: bold; }
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
        # Display order is the kind-section order (CLI, API, Blueprint, Remote).
        self._display_seats = [
            seat for _, group in sectioned_seats(self._seats) for seat in group
        ]
        self._selected_id = _initial_selected(self._display_seats, selected_id)
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

    def _rail_list(self) -> _SectionListView:
        items: list[ListItem] = []
        # Wave 1b: seat rows grouped under kind-section header rows.
        for label, group in sectioned_seats(self._seats):
            items.append(_SectionHeaderItem(label))
            for seat in group:
                items.append(_SeatItem(seat, selected=(seat.id == self._selected_id)))
        if not self._seats:
            items.append(ListItem(Static(EMPTY_RAIL, classes="seat-name")))
        self._list_view = _SectionListView(*items, id="rail-list")
        return self._list_view

    def _selected_display_index(self) -> int | None:
        """Child index of the current selection in the grouped rail, else first seat."""
        found = None
        for i, child in enumerate(self._list_view.children):
            seat = getattr(child, "seat", None)
            if seat is None:
                continue
            if found is None:
                found = i
            if seat.id == self._selected_id:
                return i
        return found

    # -- keys ---------------------------------------------------------------
    def action_cursor_down(self) -> None:
        if self._seats:
            self._list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._seats:
            self._list_view.action_cursor_up()

    # -- events -------------------------------------------------------------
    def on_mount(self) -> None:
        target = self._selected_display_index() if self._seats else None
        if target is not None:
            self._list_view.index = target

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._seats:
            return
        seat = getattr(event.item, "seat", None)
        if not isinstance(seat, RailSeat):
            return  # section header — keep the current selection
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


__all__ = [
    "CHAT_BODY",
    "EMPTY_RAIL",
    "FOOTER",
    "TuiApp",
    "run_tui_app",
    "sectioned_seats",
]
