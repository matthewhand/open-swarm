"""REQ-111 Wave 2c: interactive Textual chrome — real transcript, composer, stream.

Left rail = AGENTS grouped under kind sections CLI / API / Blueprint / Remote
(Wave 1b). Selecting a seat hydrates its real thread via ``GET /chat/thread/``
(Wave 2a). Blueprint-backed seats can also send: the composer POSTs
``/v1/chat/completions`` with Bearer (Wave 2b) and assistant deltas render as
they arrive. CLI-tool / team / remote / Herdr rows are honestly not-sendable
over REST v1 (they use the SPA websocket path — Wave 3b).

Keyboard: ``j``/``k`` (or arrows) move between seats, ``Enter`` selects a seat
from the rail, typing goes to the composer and ``Enter`` sends, ``q`` quits
(typing never quits). Textual stays an optional ``[tui]`` extra; the Wave 0
``--once`` ASCII dump is unaffected.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import suppress

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, ListItem, ListView, Static

from swarm.tui.client import (
    GETTER,
    POSTER,
    AgentThread,
    RailSeat,
    SwarmApiError,
    ThreadMessage,
    fetch_thread,
    iter_assistant,
    sectioned_seats,
    sendable_model,
)

EMPTY_RAIL = "No seats — API returned none (honest)."
EMPTY_THREAD = " No messages yet for this seat — type below to send the first turn."
HYDRATE_LOADING = " Loading transcript…"
COMPOSER_SENDABLE = "Type a message — Enter sends"
COMPOSER_UNSENDABLE = "Not sendable over REST v1 (websocket path = Wave 3b)"
FOOTER = " j/k move \u00b7 Enter select \u00b7 type + Enter send \u00b7 q quit"

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
    """A rail ListView whose kind-section header rows are skipped by the cursor."""

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
        for i in range(len(self.children)):
            if not self._is_header_index(i):
                self.index = i
                return

    def action_cursor_end(self) -> None:
        for i in range(len(self.children) - 1, -1, -1):
            if not self._is_header_index(i):
                self.index = i
                return


class TuiApp(App[None]):
    """Two-pane chrome: rail + live transcript + composer with streaming replies."""

    TITLE = "Open Swarm TUI"
    SUB_TITLE = "REQ-111 Wave 2c \u2014 rail + transcript + REST SSE send"
    CSS = """
    #chrome { height: 1fr; }
    #rail-box { width: 36; border-right: solid $primary; }
    #rail-title { text-style: bold; background: $primary; color: $text; }
    #rail-list { height: 1fr; }
    #chat-box { width: 1fr; }
    #chat-title { text-style: bold; background: $surface; color: $text; }
    #chat-body { height: 1fr; padding: 1 2; }
    #composer { dock: bottom; }
    #footer { height: 1; color: $text-muted; }
    .seat-name { padding: 0 1; }
    .section-name { padding: 0 1; color: $text-muted; text-style: bold; }
    """

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
        poster: POSTER | None = None,
        token: str | None = None,
    ) -> None:
        super().__init__()
        self._seats = list(seats)
        self._base_url = base_url
        self._display_seats = [
            seat for _, group in sectioned_seats(self._seats) for seat in group
        ]
        self._selected_id = _initial_selected(self._display_seats, selected_id)
        self.selected_id = self._selected_id
        self._getter = getter
        self._poster = poster
        self._token = token
        self._cache: dict[str, AgentThread] = {}
        self._send_worker = None
        self._sending = False

    # -- composition ---------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Horizontal(id="chrome"):
            with Vertical(id="rail-box"):
                yield Static(" AGENTS", id="rail-title")
                yield self._rail_list()
            with Vertical(id="chat-box"):
                yield Static(self._chat_heading(), id="chat-title")
                yield Static(HYDRATE_LOADING, id="chat-body")
                initial = _seat_by_id(self._seats, self._selected_id)
                initial_sendable = bool(initial and sendable_model(initial))
                composer = Input(
                    placeholder=COMPOSER_SENDABLE if initial_sendable else COMPOSER_UNSENDABLE,
                    id="composer",
                )
                composer.disabled = not initial_sendable
                yield composer
        yield Static(FOOTER, id="footer")

    def _rail_list(self) -> _SectionListView:
        items: list[ListItem] = []
        for label, group in sectioned_seats(self._seats):
            items.append(_SectionHeaderItem(label))
            for seat in group:
                items.append(_SeatItem(seat, selected=(seat.id == self._selected_id)))
        if not self._seats:
            items.append(ListItem(Static(EMPTY_RAIL, classes="seat-name")))
        self._list_view = _SectionListView(*items, id="rail-list")
        return self._list_view

    def _selected_display_index(self) -> int | None:
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
        if self._seats and not self._input_focused():
            self._list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._seats and not self._input_focused():
            self._list_view.action_cursor_up()

    def action_quit(self) -> None:
        # Typing 'q' in the composer must not quit; the Input consumed it anyway,
        # but keep the guard so future global bindings never steal letters.
        if not self._input_focused():
            self.exit()

    def _input_focused(self) -> bool:
        return isinstance(getattr(self, "focused", None), Input)

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
            return
        self._cancel_send()
        self._selected_id = seat.id
        self.selected_id = seat.id
        self.query_one("#chat-title", Static).update(self._chat_heading(seat))
        self._update_composer(seat)
        self._hydrate(seat)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        seat = _seat_by_id(self._seats, self._selected_id)
        if seat is None or self._sending:
            event.input.value = ""
            return
        text = (event.value or "").strip()
        event.input.value = ""
        if not text:
            return
        model = sendable_model(seat)
        if not model:
            self._notice(seat, f"{seat.name} is not sendable over REST v1 — the websocket path is Wave 3b")
            return
        self._send(seat, model, text)

    # -- hydrate (Wave 2a) --------------------------------------------------
    def _hydrate(self, seat: RailSeat) -> None:
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
            return
        body = _render_messages(thread.messages, seat.name)
        if thread.session_missing:
            body += "\n\n [!] requested session is missing on the server"
        self._set_chat_body(body)

    def _fetch_thread(self, seat_id: str) -> AgentThread:
        return fetch_thread(
            agent=seat_id,
            base_url=self._base_url or None,
            token=self._token,
            getter=self._getter,
        )

    def _show_hydrate_failure(self, seat: RailSeat, exc: BaseException) -> None:
        if seat.id != self._selected_id:
            return
        cached = self._cache.get(seat.id)
        if cached is not None and cached.messages:
            body = _render_messages(cached.messages, seat.name)
            self._set_chat_body(f"{body}\n\n [!] offline cache shown — refresh failed: {exc}")
        elif cached is not None:
            self._set_chat_body(f"{EMPTY_THREAD}\n\n [!] refresh failed: {exc}")
        else:
            self._set_chat_body(f" [!] could not load {seat.name}'s thread: {exc}")

    # -- send + stream (Wave 2b/2c) ----------------------------------------
    def _send(self, seat: RailSeat, model: str, text: str) -> None:
        self._sending = True
        self._update_composer(seat, sending=True)
        base = self._cache.get(seat.id)
        history = list(base.messages) if base is not None else []
        user_msg = ThreadMessage(role="user", content=text)
        payload = [
            {"role": m.role, "content": m.content} for m in history
        ] + [{"role": "user", "content": text}]
        # Visible user echo immediately (honest even if the stream then fails).
        running = [*history, user_msg]
        self._set_chat_body(_render_messages(running, seat.name))
        self._send_worker = self.run_worker(
            self._send_coro(seat, model, payload, running),
            name=f"send-{seat.id}",
            group="send",
            exclusive=True,
        )

    def _send_iterator(self, model: str, payload: list[dict[str, str]]) -> Iterator[str]:
        return iter_assistant(
            model=model,
            messages=payload,
            base_url=self._base_url or None,
            token=self._token,
            poster=self._poster,
        )

    async def _next_delta(self, iterator: Iterator[str]) -> str | None:
        """Advance the SSE iterator in a thread; None = clean [DONE] end.

        ``StopIteration`` must not cross the ``await`` boundary (asyncio turns
        it into RuntimeError), so it is mapped to None inside the thread.
        """
        def _step() -> str | None:
            try:
                return next(iterator)
            except StopIteration:
                return None

        return await asyncio.to_thread(_step)

    async def _send_coro(
        self,
        seat: RailSeat,
        model: str,
        payload: list[dict[str, str]],
        running: list[ThreadMessage],
    ) -> None:
        buffer: list[str] = []
        iterator: Iterator[str] | None = None
        try:
            iterator = self._send_iterator(model, payload)
            while True:
                delta = await self._next_delta(iterator)
                if delta is None:
                    break
                buffer.append(delta)
                if seat.id == self._selected_id:
                    view = [*running, ThreadMessage(role="assistant", content="".join(buffer))]
                    self._set_chat_body(_render_messages(view, seat.name))
        except asyncio.CancelledError:
            raise  # seat switch — the finally block closes the stream
        except SwarmApiError as exc:
            self._sending = False
            self._send_worker = None
            if seat.id == self._selected_id:
                # Keep the user echo + any partial deltas (never lose the transcript).
                keep = [*running, *self._assistant_row(buffer)]
                self._store_thread(seat, keep)
                self._set_chat_body(
                    f"{_render_messages(keep, seat.name)}\n\n [!] send failed: {exc}"
                )
                self._update_composer(seat)
            return
        finally:
            if iterator is not None:
                with suppress(Exception):
                    iterator.close()  # never leak the open SSE response
        self._sending = False
        self._send_worker = None
        done = [*running, *self._assistant_row(buffer)]
        self._store_thread(seat, done)
        if seat.id == self._selected_id:
            self._set_chat_body(_render_messages(done, seat.name))
            self._update_composer(seat)

    @staticmethod
    def _assistant_row(buffer: list[str]) -> list[ThreadMessage]:
        """One assistant row from streamed deltas; none when the stream was empty."""
        if not buffer:
            return []
        return [ThreadMessage(role="assistant", content="".join(buffer))]

    def _store_thread(self, seat: RailSeat, messages: list[ThreadMessage]) -> None:
        """Persist a transcript for a seat, keeping the hydrated thread metadata."""
        base = self._cache.get(seat.id)
        self._cache[seat.id] = AgentThread(
            agent_id=(base.agent_id if base else seat.id),
            conversation_id=(base.conversation_id if base else ""),
            messages=list(messages),
            kind=(base.kind if base else ""),
            editable=True,
        )

    def _cancel_send(self) -> None:
        worker = self._send_worker
        self._send_worker = None
        self._sending = False
        if worker is not None:
            worker.cancel()

    # -- chrome helpers -----------------------------------------------------
    def _update_composer(self, seat: RailSeat | None, *, sending: bool = False) -> None:
        with suppress(Exception):
            composer = self.query_one("#composer", Input)
            sendable = seat is not None and sendable_model(seat) is not None
            composer.disabled = not sendable or sending
            composer.placeholder = (
                "Streaming…" if sending else COMPOSER_SENDABLE if sendable else COMPOSER_UNSENDABLE
            )

    def _notice(self, seat: RailSeat, text: str) -> None:
        if seat.id == self._selected_id:
            self._set_chat_body(f"{_render_messages(self._cache.get(seat.id).messages if self._cache.get(seat.id) else [], seat.name)}\n\n [!] {text}")

    def _chat_heading(self, seat: RailSeat | None = None) -> str:
        seat = seat or _seat_by_id(self._seats, self._selected_id)
        if seat is None:
            return " Chat \u2014 none selected"
        return f" Chat \u2014 {seat.name} ({seat.kind} \u00b7 {seat.source})"

    def _set_chat_body(self, text: str) -> None:
        with suppress(Exception):
            self.query_one("#chat-body", Static).update(text)


def _render_messages(messages: list[ThreadMessage], seat_name: str | None = None) -> str:
    """Plain-text transcript render (v1 — assistant label is the seat name)."""
    assistant = seat_name or "assistant"
    lines: list[str] = []
    for message in messages:
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
    poster: POSTER | None = None,
    token: str | None = None,
) -> None:
    """Blocking entry point used by the interactive ``swarm-cli tui`` path."""
    TuiApp(
        seats,
        base_url=base_url,
        selected_id=selected_id,
        getter=getter,
        poster=poster,
        token=token,
    ).run()


__all__ = [
    "COMPOSER_SENDABLE",
    "COMPOSER_UNSENDABLE",
    "EMPTY_RAIL",
    "EMPTY_THREAD",
    "FOOTER",
    "HYDRATE_LOADING",
    "TuiApp",
    "run_tui_app",
    "sectioned_seats",
]
