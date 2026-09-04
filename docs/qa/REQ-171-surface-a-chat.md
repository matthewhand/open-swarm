# REQ-171 Surface A — look-only audit

> Chat / composer / session / websocket / thread retention.
> **Look-only.** This file is a findings list for CoS triage. It does not
> change runtime product code, close [#596](https://github.com/matthewhand/open-swarm/issues/596),
> or implement fixes.

**As-of:** `origin/main` @ `f21d24ea` (`fix(webui): render CLI and API dropdowns with model selectors (REQ-133, Fixes #523) (#593)`).

**Umbrella:** [#596](https://github.com/matthewhand/open-swarm/issues/596) (REQ-171). This report is **audit partial** for surface A only. Surfaces B (rail/agents/blueprints) and C (CLI/API/remote harness) are out of scope here.

**Method:** static read of `webui/frontend/src/pages/ChatPage.tsx`, composer dock, `lib/chatWs.ts`, `lib/agentChat.ts`, `lib/chatStatus.ts`, `src/swarm/consumers.py`, `src/swarm/views/chat_persist_views.py`, `src/swarm/core/chat_store.py`, and the tests that claim to lock this surface. No host bounce. No Neon. No secrets. No live LAN URLs.

**How to read**

| Sev | Meaning here |
|-----|----------------|
| **HIGH** | Wrong behaviour a user can hit on `/chat` today: lost history, lost target, interleaved turns, or persist that silently drops. File a child Issue. |
| **MEDIUM** | Real hole, but bounded (missing affordance, double event, dead component, fallback path). Fix after HIGH waves. |
| **LOW** | Dead code, leftover protocol, or intentional silent-healthy chrome. Do not file unless a later REQ needs it. |

**Test column:** `missing` = no test would fail if the bug shipped. `weak` = a test exists but asserts a mock, a side-effect, or the buggy fallback itself.

**Do not treat this PR as Fixes #596.** Fixes belong on child Issues, queued in waves of 2–3.

---

## Skipped open Cursor surfaces

REQ-171 asked look-only agents not to fight in-flight Cursor PRs unless the defect is critical. On this snapshot:

| Open PR | Surface | This audit |
|---------|---------|------------|
| [#576](https://github.com/matthewhand/open-swarm/pull/576) | Desktop packaging ADR (REQ-151) | **Skip.** No chat-runtime overlap. |
| [#577](https://github.com/matthewhand/open-swarm/pull/577) | First-load keybinding tips under composer (#571) | **Skip.** Tips placement only. No critical chat defect found there. |
| [#579](https://github.com/matthewhand/open-swarm/pull/579) | Persist favourites / Hidden Bots / hostname prefs | **Skip.** Prefs, not thread retention. |
| [#582](https://github.com/matthewhand/open-swarm/pull/582) | ADR-004 virtualized infinite chat history (REQ-163 / #575) | **Note and skip product work.** Jump-to-bottom / `ChatComposerDock` (M1) will collide with virtualization; land the dock with or after that ADR, do not implement a second scroll model here. |

Related open product Issues (do **not** re-file as new product REQs):

- [#447](https://github.com/matthewhand/open-swarm/issues/447) — queue while the agent is working (UI). H3 is the **correctness** bug underneath, not the queue chrome.
- [#572](https://github.com/matthewhand/open-swarm/issues/572) — “Restored session” status for every agent kind. Adjacent to status-line honesty (M3, M6).
- [#469](https://github.com/matthewhand/open-swarm/issues/469) / [#468](https://github.com/matthewhand/open-swarm/issues/468) — Select / New session. Adjacent to H1 / H4.

---

## Surface map (what “chat” is today)

The live `/chat` surface is **`ChatPage.tsx` + an inline composer**. There is no mounted `ChatComposer` module.

| Piece | Role |
|-------|------|
| `webui/frontend/src/pages/ChatPage.tsx` | URL-driven agent/team/remote/session, in-memory `threads` map, WS lifecycle, streaming, header dropdowns, status lines, pin-to-bottom scroll (no dock). |
| `webui/frontend/src/lib/chatWs.ts` | Frame builders + HTMx/JSON parse. |
| `webui/frontend/src/lib/agentChat.ts` | REST `GET/POST/PATCH /chat/thread/` + localStorage conversation UUIDs. |
| `webui/frontend/src/lib/chatStatus.ts` | REQ-46 dropdown status copy. |
| `webui/frontend/src/components/ChatComposerDock.tsx` | Jump-to-bottom + working-avatar dock. **Unmounted.** |
| `src/swarm/consumers.py` | `DjangoChatConsumer` on `ws/ai-demo/<conversation_id>/`. |
| `src/swarm/views/chat_persist_views.py` | HTTP hydrate / append / edit. JSON disk is source of truth; Django rows are a mirror. |

Retention model:

```
URL (?blueprint / ?team / ?remote / ?session)
  → conversationId (localStorage UUID, team-* id, or ?session=)
  → GET /chat/thread/  (skipped for remotes)
  → in-memory threads[threadKey]
  → WS /ws/ai-demo/<conversationId>/ for live turns
  → persist: HTTP POST for dropdown status; consumer save on disconnect / status / edit
```

---

## HIGH findings

### H1 — Team-member dropdown does not write `?session=`; refresh resets target to All members

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `webui/frontend/src/pages/ChatPage.tsx` (member `useEffect`, Team members `<select>`); `webui/frontend/src/lib/sessionPicker.ts` (rail picker **does** write `?session=`) |
| **Evidence** | Header `onChange` calls `setMemberTarget(value)` and `recordDropdownChange` only. It does not `setSearchParams({ session })`. A later effect resets `memberTarget` from `sessionFromUrl`, or to `ALL_MEMBERS_TARGET` when `?session=` is absent. Reload after “All members → Codey” keeps the status line (if POST succeeded) but the combobox is **All members** again; the next Send uses `target: all`. Rail `SessionPicker` already encodes member as `?team=&session=`. |
| **Suggested fix Issue title** | Persist team-member dropdown target in `?session=` (REQ-171 / #596) |
| **Test** | **Weak.** `webui/frontend/e2e/dropdown-status.spec.ts` asserts the status line survives reload via an in-page mock store. It never asserts `getByRole('combobox', { name: 'Team members' })` is still `codey` after reload. Would pass with this bug. |

---

### H2 — Normal chat turns persist only on websocket disconnect

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `src/swarm/consumers.py` (`receive`, `respond_with_*`, `disconnect`, `save_conversation`) |
| **Evidence** | User + assistant rows are appended to `self.messages` during `receive` / `respond_with_*`. `save_conversation` (DB replace + `_save_agent_json`) runs from `disconnect`, `type: status`, or `edit` — **not** after a completed turn. Process kill, worker recycle, or a crash before `disconnect` drops the turn. Toast copy (“Message history is kept”) is only a client in-memory claim. |
| **Suggested fix Issue title** | Persist chat turns when the assistant finalises, not only on WS disconnect (REQ-171 / #596) |
| **Test** | **Weak / missing.** `tests/test_consumers.py` `test_disconnect_*` mock `save_conversation`. `test_save_creates_new_conversation_sync` / `test_save_updates_existing_conversation_sync` create ORM rows **by hand** and never call `save_conversation`. No test that a completed turn is on disk **before** disconnect. ASGI round-trips disconnect without asserting JSON/DB contents. |

---

### H3 — Send-while-streaming is allowed; consumer `receive` is not serialised

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `ChatPage.tsx` (`canSend` / `sendText`); `src/swarm/consumers.py` `receive` |
| **Evidence** | Send stays enabled while an assistant bubble has `streaming: true` (locked by “Send button honesty while streaming”). `sendText` does not queue or reject a second frame. Channels will run a second `receive` coroutine on the same consumer while the first `respond_with_*` is still awaiting. `self.messages` and outbound HTML can interleave; two assistant ids race; last `disconnect` wins on save. Product queue chrome is [#447](https://github.com/matthewhand/open-swarm/issues/447) — this finding is **corrupt transcript**, not the 1/3-height pane. |
| **Suggested fix Issue title** | Serialise overlapping chat turns on one websocket (REQ-171 / #596) |
| **Test** | **Weak / missing.** ChatPage test only asserts Send is not `aria-busy` and LoadingDots show. E2E `mockInference.ts` delivers start+final on one `send` and never overlaps two in-flight runs. No consumer test for concurrent `receive`. |

---

### H4 — Thread hydrate fails open (empty) on REST errors; remotes never hydrate

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `webui/frontend/src/lib/agentChat.ts` `fetchAgentThread`; `ChatPage.tsx` hydrate effect |
| **Evidence** | `fetchAgentThread` catch returns `{ messages: [], summaries: [] }` — comment: “empty on auth/network failure (chat still works).” Hydrate then does `if (thread.messages.length === 0) return`. On agent switch the target bucket was already cleared, so a 401/5xx/offline GET **wipes visible history** with no toast (unlike Compact / edit, which toast). Remote URL branch sets ids, optionally clears the bucket, and **returns without calling `fetchAgentThread`**. Refresh of `?remote=` is an empty transcript unless something else repopulates it. |
| **Suggested fix Issue title** | Hydrate chat threads honestly — do not fail-open empty; hydrate remotes (REQ-171 / #596) |
| **Test** | **Weak (fail-open locked in) + missing (remotes).** `agentChat.test.ts` “returns an empty thread when fetch fails” treats the silent empty as success. ChatPage rehydrate test mocks happy-path JSON per agent. No ChatPage test for REST 500/401. No remote hydrate test. |

---

### H5 — WS reconnect prefers stripped DB rows over JSON; HTTP is JSON-first

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `src/swarm/consumers.py` `fetch_conversation` / `_load_agent_json`; `src/swarm/views/chat_persist_views.py` `chat_thread` |
| **Evidence** | HTTP `GET /chat/thread/` loads **JSON disk first**, then DB backfill (and may write JSON). WS `fetch_conversation` is memory → **Django DB** → disk. DB projection is `{role: sender, content}` only — `ts` / `edited` / richer JSON fields drop. `_load_agent_json` also strips to role/content. Same user can see a richer HTTP hydrate after reload than a WS reconnect (or the reverse if DB exists and JSON is newer). `test_chat_thread_passes_through_stored_ts` locks HTTP `ts`; nothing locks WS reconnect to the same row. |
| **Suggested fix Issue title** | Align WS and HTTP thread load (JSON source of truth, keep ts/edited) (REQ-171 / #596) |
| **Test** | **Missing** for the mismatch. `test_fetch_from_database_sync` asserts ORM state and **never calls** `fetch_conversation`. No reconnect test comparing WS-loaded messages to `chat_store` JSON. |

---

## MEDIUM findings

### M1 — Jump-to-bottom dock exists but is not mounted; unpin has no recovery UI

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `webui/frontend/src/components/ChatComposerDock.tsx` (only definition); `ChatPage.tsx` `pinnedToBottomRef` + `onScroll` |
| **Evidence** | Auto-scroll runs only while `pinnedToBottomRef` is true (within 48px of bottom). Scrolling up unpins. `ChatComposerDock` implements jump chevron + “N new messages” pill + working avatars, but nothing imports it. Confirmed by `docs/GROK_KEYBINDING_PARITY.md`. During a long stream the user cannot re-pin except by manually scrolling to the floor. |
| **Suggested fix Issue title** | Mount ChatComposerDock jump-to-bottom (coordinate with #575 / #582) |
| **Test** | **Missing.** Zero tests reference `os-chat-dock` / `os-jump-btn` / `os-new-pill`. |

Coordinate with [#575](https://github.com/matthewhand/open-swarm/issues/575) / PR #582. Do not invent a second scroll model in the first HIGH wave.

---

### M2 — API-agent dropdown writes the status line onto the thread you are leaving

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `ChatPage.tsx` API `<select>` + `recordDropdownChange` |
| **Evidence** | `setSearchParams({ blueprint })` then `recordDropdownChange('api', …)` appends to the **current** `threadKey` (departing agent). The arriving thread never shows “API: Codey → Stewie”. Team/CLI/model dropdowns stay on the same thread, so those lines are visible. |
| **Suggested fix Issue title** | Record API dropdown status on the destination thread (or keep it on-screen across the switch) |
| **Test** | **Missing** for API-dropdown → visible status after navigation. CLI e2e covers same-thread only. |

---

### M3 — Dropdown status persist is fire-and-forget

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `ChatPage.tsx` `recordDropdownChange` → `appendAgentMessage(...).catch(() => {})` |
| **Evidence** | UI appends the line immediately. REST POST failure is swallowed. Reload then loses the line. Edit/Compact on the same page toast persist failures. |
| **Suggested fix Issue title** | Toast when a dropdown status line fails to persist |
| **Test** | **Weak.** Dropdown e2e mock always 200s the POST. No test of `.catch(() => {})`. |

---

### M4 — `notifyGenerationComplete` fires twice per finished turn

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `ChatPage.tsx` `handleWsEvent` (`assistant_final`) and the `streamingMessage` effect |
| **Evidence** | Final frame notifies the rail; dropping `streaming: true` notifies again. Rail bump / stacked-avatar animation can double-tick. |
| **Suggested fix Issue title** | Fire generation-complete once per assistant turn |
| **Test** | **Weak.** “notifies rail bump when a generation completes” sends **final without start**, so the streaming-flag path never runs. Asserts `completed === ['codey']` only. Does not assert the assistant text appeared. A start+final pair would double-fire and still be easy to miss. |

---

### M5 — Blueprint websocket path is batch, not token-stream

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `src/swarm/consumers.py` `respond_with_blueprint`; client `chatWs.ts` documents per-chunk streaming |
| **Evidence** | Default-model path sends OOB chunks per token. Blueprint path accumulates `final_message` and sends **one** OOB chunk + final partial. Almost all rail agents are blueprints. Composer footer still shows a stream elapsed timer against a first-and-only dump. |
| **Suggested fix Issue title** | Stream blueprint websocket chunks incrementally (parity with default-model path) |
| **Test** | **Weak.** `test_blueprint_reply_streams_chunk_and_final` yields spinner + one content chunk; asserts two frames. Would pass if incremental streaming were broken. E2E `mockInference.ts` emits start+final only — no chunks. |

---

### M6 — `interbot_hop` is parsed and then dropped

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `chatWs.ts` `parseChatWsMessage`; `ChatPage.tsx` `handleWsEvent`; `components/InterBotLine.tsx` (unused on this surface) |
| **Evidence** | Parser returns `interbot_hop`. Handler has no case; `next === current`. No producer under `src/` emits `os-interbot-hop`. Client protocol + unit tests lock a frame the live chat ignores. |
| **Suggested fix Issue title** | Render inter-bot hops on ChatPage or delete the unused protocol |
| **Test** | **Weak.** `chatWs.test.ts` parses hops. No ChatPage render test. |

---

### M7 — Compact-context exception fallback can leak status lines into the model

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `src/swarm/consumers.py` `_compacted_context` |
| **Evidence** | `chat_compact.context_for_conversation` skips `role == status` (REQ-70 / #407). The consumer wrapper’s `except` returns `list(messages or [])` **unfiltered**. DB/summary failures put dropdown/CLI notices into the next LLM call. |
| **Suggested fix Issue title** | Filter status roles in the compact-context fallback |
| **Test** | **Missing** for the exception path. Happy-path compact tests mock `_compacted_context`. |

---

### M8 — `assistant_chunk` / `assistant_final` no-op when start never landed

| Field | Value |
|-------|--------|
| **Severity** | MEDIUM |
| **File / area** | `ChatPage.tsx` `handleWsEvent` |
| **Evidence** | Both cases `map` existing messages by `event.id`. No matching start → silent drop of the reply. Consumer does send `system_message.html` first; a lost start (parse failure, mid-stream reconnect after a cleared bucket) still loses the answer. The rail-bump test uses final-without-start and does not assert text. |
| **Suggested fix Issue title** | Upsert assistant bubbles on chunk/final if start was missed |
| **Test** | **Missing** (would-fail-on-bug assert). |

---

## LOW findings (do not file unless a later REQ needs them)

| ID | Area | Why LOW |
|----|------|---------|
| L1 | `ChatPage.tsx` `composerPlaceholder` | Both branches are `'Message …'`. Disconnect uses toasts + sr-only `statusLabel` (REQ-8 silent-healthy). Dead ternary, not a user-facing hole. |
| L2 | `handleWsEvent` deps omit `selectedBlueprint` | Used for tool auto-allow. `threadKey` / `activeChatAgentId` usually change with the blueprint. Stale-closure risk is narrow. |
| L3 | `lib/agentChatSessions.ts`, `lib/chatLastRead.ts` | Persistence helpers with unit tests; **not** wired into `ChatPage`. Dead relative to this surface. |
| L4 | Preview-user mint failure keeps the socket open | Documented + tested (`test_connect_anonymous_preview_mint_failure_keeps_socket`). `receive` still 4401s. Odd half-open, not a transcript bug. |
| L5 | `IN_MEMORY_CONVERSATIONS` is process-local | Multi-worker daphne will miss the cache (DB/JSON still used). Deploy concern, not `/chat` single-worker default. |
| L6 | Two tabs, same `conversation_id` | Fetch returns a copy (good). Last disconnect wins. No integration test. Acceptable until H2 lands mid-turn save. |

---

## Test-quality cross-cut (surface A)

These are the asserts that would **not** catch the HIGH/MEDIUM bugs above. Use them when writing the child-Issue Success lists.

| Test | What it actually locks | Why it does not bite |
|------|------------------------|----------------------|
| `tests/test_consumers.py` `test_fetch_from_database_sync` | A `ChatConversation` row exists | Never invokes `fetch_conversation`. |
| `test_save_creates_new_conversation_sync` / `test_save_updates_existing_conversation_sync` | Manual `ChatMessage.objects.create` | Bypasses `save_conversation` (no JSON mirror, no idempotent replace). |
| `test_blueprint_reply_streams_chunk_and_final` | One content chunk → 2 frames | Encodes batch-at-end. Would pass without incremental streaming. |
| `test_disconnect_*` | `save_conversation` was **awaited** | Mocked; no disk/DB after a real turn. |
| `webui/frontend/src/lib/__tests__/agentChat.test.ts` empty-on-failure | `messages === []` on reject | Locks H4 fail-open as the contract. |
| `webui/frontend/e2e/dropdown-status.spec.ts` | Status text + mock POST store | Tests the mock, not Django persist; no combobox-after-reload (H1). CLI case has **no** reload. |
| `ChatPage.test.tsx` Send-while-streaming | `aria-busy` absent, LoadingDots present | Does not send a second prompt; no consumer overlap (H3). |
| `ChatPage.test.tsx` generation-complete | CustomEvent `codey` | Final without start; no double-notify; no “finished” text (M4/M8). |
| `e2e/helpers/mockInference.ts` | start + final, no chunks | SPA e2e never sees token streaming or overlapping turns. |
| `chatWs.test.ts` interbot_hop | Parser only | Handler drop (M6) stays green. |
| ChatPage unique-WS-per-agent | Two URLs differ | Unmount + remount, not in-page rail switch with live sockets. |

**Missing coverage (no test file claims it):**

- Jump-to-bottom / unpin / new-message pill (`ChatComposerDock`).
- Remote `?remote=` hydrate or refresh retention.
- REST hydrate 401/500 must not clear a known thread.
- Concurrent `receive` on one consumer.
- WS reconnect preserves `ts` / `edited` / status metadata vs HTTP GET.
- API dropdown status visible on the destination thread.
- `assistant_final` without start still renders text (or explicitly fails).
- Team combobox value after reload.

---

## Suggested first fix wave (2–3)

CoS queues implementers. Suggested order:

1. **H1** — team dropdown `?session=` (small, user-visible, e2e already nearby).
2. **H4** — hydrate honesty + remote GET (stops silent empty chats).
3. **H2** — persist on assistant final (stops crash loss).

Next wave: **H3** (serialise receive; do not wait for full #447 queue UI) + **H5** (one load order). Then M1 with #582.

---

## HIGH Issue drafts (for CoS to file)

`gh` on this agent is read-only. Copy each block into a new GitHub Issue. Do not close #596 from these.

### Issue 1 — Persist team-member dropdown target in `?session=`

**Intent:** The Team members header dropdown must share a source of truth with the rail session picker and survive reload, so Send keeps targeting the member the operator picked.

**Success:**

1. Changing Team members writes `?team=<id>&session=<memberId>` (All members clears `session` or writes the all-members sentinel already used by `SessionPicker`).
2. Reload restores the same combobox value and the next WS frame still has `params.target` equal to that member (or `all`).
3. Manage Team still does not write a status line or a session id.
4. Playwright asserts combobox value **and** `target` on the next send after reload — not only the centred status text.

**Constraints:** Look-only audit is #596 surface A. No Neon. Do not fight #576/#577/#579. Own-diff CI only. Keep REQ-46 bubble-less status chrome.

**Owner:** CoS assigns a Cursor implementer (wave 1).

**Parent:** #596 (REQ-171). Evidence: `docs/qa/REQ-171-surface-a-chat.md` H1.

---

### Issue 2 — Persist chat turns when the assistant finalises, not only on WS disconnect

**Intent:** A completed user/assistant turn must be on JSON (+ DB mirror) before the socket dies, so a crash, deploy, or killed worker cannot drop the last reply.

**Success:**

1. After `assistant_final` / blueprint final partial, `chat_store` (and Django rows) contain the new user + assistant messages **without** requiring `disconnect`.
2. Repeat save on disconnect stays idempotent (no duplicate rows).
3. Status and edit paths keep their immediate save.
4. A test completes a turn, inspects disk/DB, **then** disconnects — `test_save_*_sync` that bypass `save_conversation` do not count.

**Constraints:** No Neon. Do not change HTTP `/chat/thread/` contract except as needed for the same transcript. Coordinate with H5 if load order is touched.

**Owner:** CoS assigns (wave 1 or 2).

**Parent:** #596. Evidence: H2.

---

### Issue 3 — Serialise overlapping chat turns on one websocket

**Intent:** A second Send while a reply is in flight must not interleave `self.messages` or HTML frames on that socket.

**Success:**

1. Consumer processes one `respond_with_*` at a time per connection (queue or reject-with-status).
2. SPA either disables/queues the second send or shows a status line; it must not emit a second `{message}` that races the first handler.
3. A test fires two frames before the first `run()` completes and asserts one assistant body, ordered user rows, no mixed ids.
4. Do **not** require the full [#447](https://github.com/matthewhand/open-swarm/issues/447) queue pane in this Issue (link it).

**Constraints:** No Neon. Do not block #447. Own-diff CI only.

**Owner:** CoS assigns (wave 2).

**Parent:** #596. Evidence: H3.

---

### Issue 4 — Hydrate chat threads honestly — do not fail-open empty; hydrate remotes

**Intent:** Reload and agent switch must not silently replace a known transcript with an empty chat when REST fails, and remote threads must use the same hydrate path as API/team.

**Success:**

1. `fetchAgentThread` surfaces failure (throw or `{ ok: false }`); ChatPage toasts and **keeps** in-memory messages when the bucket was non-empty.
2. First load with no cache + failed GET shows an explicit empty/error state, not a fake blank new chat.
3. `?remote=` (and remote session) calls the thread endpoint (or a documented remote store) instead of returning early.
4. Tests: REST 500 after a switch does not wipe bubbles; remote refresh restores a seeded thread. Replace the “empty thread when fetch fails” contract test.

**Constraints:** No secrets in fixtures. No Neon. Remotes stay non-editable (existing 403 PATCH).

**Owner:** CoS assigns (wave 1).

**Parent:** #596. Evidence: H4.

---

### Issue 5 — Align WS and HTTP thread load (JSON source of truth, keep ts/edited)

**Intent:** Reload via `GET /chat/thread/` and reconnect via `fetch_conversation` must return the same transcript, including `ts` and `edited`.

**Success:**

1. One documented load order (JSON first, DB backfill) for both HTTP and WS.
2. WS fetch no longer drops `ts` / `edited` when JSON has them.
3. A test writes JSON with `ts` + `edited`, opens WS (or calls `fetch_conversation`), and asserts those fields; HTTP GET matches.
4. `test_fetch_from_database_sync` is rewritten to call `fetch_conversation` or deleted.

**Constraints:** Keep the cross-user cache key. Idempotent save stays. No Neon.

**Owner:** CoS assigns (wave 2, with or after H2).

**Parent:** #596. Evidence: H5.

---

## What this audit is not

- Not a chrome rewrite. Not a virtualizer. Not a keybinding-tips move.
- Not authority to merge product diffs in the same PR as this file.
- Not complete REQ-171 coverage (B and C still need disjoint reports).
