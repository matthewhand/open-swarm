"""REQ-111 Wave 2a: interactive Textual chrome with a real transcript pane.

Renders the AGENTS rail on the left (grouped under kind sections CLI / API /
Blueprint / Remote) and the selected seat's chat pane on the right. Selecting a
seat (Enter or the initial selection) hydrates that agent's real thread from
``GET /chat/thread/`` — the same endpoint the SPA reads (REQ-171A-4 / #604).
Hydrate failures are explicit (never a fake empty thread); a previously loaded
thread for the same seat is kept and shown as offline cache.

Keyboard: ``j``/``k`` (or arrows) move between seats, ``Enter`` selects, ``q``
quits. Kind-section headers are decoration only — cursor movement skips them
(Wave 1b). Wave 2b adds send (REST SSE) and Wave 2c the composer.

Textual stays an optional ``[tui]`` extra: this module is only imported from
the interactive branch of ``swarm.tui.cli``, so the Wave 0 ``--once`` ASCII
dump keeps working on a plain install.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import ListItem, ListView, Static

from swarm.tui.client import (
    GETTER,
    AgentThread,
    RailSeat,
    SwarmApiError,
    fetch_thread,
    sectioned_seats,
)

EMPTY_RAIL = "No seats — API returned none (honest)."
EMPTY_THREAD = " No messages yet for this seat — Wave 2b adds send (REST SSE)."
HYDRATE_LOADING = " Loading transcript…"
FOOTER = " j/k or \u2191/\u2193 move \u00b7 Enter select \u00b7 q quit \u00b7 --once for the ASCII dump (CI)"

_ROLE_LABELS = {"user": "you", "assistant": "assistant"}


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
    """Two-pane chrome: left rail grouped by kind section, right live thread."""

    TITLE = "Open Swarm TUI"
    SUB_TITLE = "REQ-111 Wave 2a hydrate \u2014 list + transcript, no send"
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
        getter: GETTER | None = None,
        token: str | None = None,
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
        # Wave 2a: hydrate uses the same client contract (env token); ``getter``
        # lets headless tests inject mocked HTTP responses.
        self._getter = getter
        self._token = token
        self._cache: dict[str, AgentThread] = {}

    # -- composition ---------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Horizontal(id="chrome"):
            with Vertical(id="rail-box"):
                yield Static(" AGENTS", id="rail-title")
                yield self._rail_list()
            with Vertical(id="chat-box"):
                yield Static(self._chat_heading(), id="chat-title")
                yield Static(HYDRATE_LOADING, id="chat-body")
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
        initial = _seat_by_id(self._seats, self._selected_id)
        if initial is not None:
            self._hydrate(initial)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._seats:
            return
        seat = getattr(event.item, "seat", None)
        if not isinstance(seat, RailSeat):
            return  # section header — keep the current selection
        self._selected_id = seat.id
        self.selected_id = seat.id
        self.query_one("#chat-title", Static).update(self._chat_heading(seat))
        self._hydrate(seat)

    # -- hydrate (Wave 2a) --------------------------------------------------
    def _hydrate(self, seat: RailSeat) -> None:
        """Kick an exclusive net worker; the newest selection wins races."""
        self._set_chat_body(HYDRATE_LOADING)
        self.run_worker(
            self._hydrate_coro(seat),
            name=f"hydrate-{seat.id}",
            group="net",
            exclusive=True,
        )

    async def _hydrate_coro(self, seat: RailSeat) -> None:
        try:
            thread = await asyncio.to_thread(self._fetch_thread, seat.id)
        except SwarmApiError as exc:
            self._show_hydrate_failure(seat, exc)
            return
        self._cache[seat.id] = thread
        if seat.id != self._selected_id:
            return  # a newer selection superseded this worker
        if thread.session_missing:
            self._set_chat_body(
                _render_thread(thread, seat.name)
                + "\n\n [!] requested session is missing on the server"
            )
        else:
            self._set_chat_body(_render_thread(thread, seat.name))

    def _fetch_thread(self, seat_id: str) -> AgentThread:
        return fetch_thread(
            agent=seat_id,
            base_url=self._base_url or None,
            token=self._token,
            getter=self._getter,
        )

    def _show_hydrate_failure(self, seat: RailSeat, exc: BaseException) -> None:
        """REST failure is explicit; a non-empty cache is kept (not fail-open)."""
        if seat.id != self._selected_id:
            return  # a newer selection superseded this worker
        cached = self._cache.get(seat.id)
        if cached is not None and cached.messages:
            self._set_chat_body(
                _render_thread(cached, seat.name)
                + f"\n\n [!] offline cache shown — refresh failed: {exc}"
            )
        elif cached is not None:
            self._set_chat_body(
                EMPTY_THREAD + f"\n\n [!] refresh failed: {exc}"
            )
        else:
            self._set_chat_body(f" [!] could not load {seat.name}'s thread: {exc}")

    def _set_chat_body(self, text: str) -> None:
        with suppress(Exception):  # widget not mounted yet — next hydrate overwrites
            self.query_one("#chat-body", Static).update(text)

    # -- helpers ------------------------------------------------------------
    def _chat_heading(self, seat: RailSeat | None = None) -> str:
        seat = seat or _seat_by_id(self._seats, self._selected_id)
        if seat is None:
            return " Chat \u2014 none selected"
        return f" Chat \u2014 {seat.name} ({seat.kind} \u00b7 {seat.source})"


def _render_thread(thread: AgentThread, seat_name: str | None = None) -> str:
    """Plain-text transcript render (v1 — Wave 2c adds inline streaming)."""
    assistant = seat_name or "assistant"
    lines: list[str] = []
    for message in thread.messages:
        label = _ROLE_LABELS.get(message.role, message.role or "note")
        if label == "assistant":
            label = assistant
        edited = " (edited)" if message.edited else ""
        text = message.content.replace("\r", "")
        if message.ts:
            lines.append(f" [{message.ts}] {label}{edited}: {text}")
        else:
            lines.append(f" {label}{edited}: {text}")
    body = "\n".join(lines)
    return body if body else EMPTY_THREAD


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
    getter: GETTER | None = None,
    token: str | None = None,
) -> None:
    """Blocking entry point used by the interactive ``swarm-cli tui`` path."""
    TuiApp(
        seats,
        base_url=base_url,
        selected_id=selected_id,
        getter=getter,
        token=token,
    ).run()


__all__ = [
    "EMPTY_RAIL",
    "EMPTY_THREAD",
    "FOOTER",
    "HYDRATE_LOADING",
    "TuiApp",
    "run_tui_app",
    "sectioned_seats",
]
