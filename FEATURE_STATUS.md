# Feature Status

> **Live status board** — per-feature evidence for what is shipped, partial, or
> planned. Last updated: **2026-09-05**. Nested checklist:
> [ROADMAP.md](./ROADMAP.md); release notes: [CHANGELOG.md](./CHANGELOG.md).
> The original 2026-06-10 point-in-time audit is archived at
> [docs/archive/FEATURE_STATUS_2026-06-10.md](./docs/archive/FEATURE_STATUS_2026-06-10.md).

Legend: ✅ working (verified) · 🟡 partial (caveat named) · 🔲 scaffolded (exists, not wired) · 📋 planned (flags/docs only) · ❌ broken/fake/dead · 🗑 removed

---

## 1. Core agent runtime — ✅ 5 · 🟡 1 · ❌ 1

| Feature | Status | Evidence |
|---|---|---|
| Blueprint discovery | ✅ | `src/swarm/core/blueprint_discovery.py` (247 lines); `tests/core/test_blueprint_discovery_behavior.py` and `test_blueprint_discovery_comprehensive.py` pass in full-suite run |
| Blueprint execution (`BlueprintBase.run`) | ✅ | `src/swarm/core/blueprint_base.py` (772 lines); `tests/core/test_blueprint_execution_comprehensive.py`, `test_blueprint_base.py`, `test_blueprint_model_override.py` all pass |
| openai-agents SDK integration | ✅ | `blueprint_base.py:39` `from agents import set_default_openai_client`; `:644-648` selects `OpenAIResponsesModel` vs `OpenAIChatCompletionsModel` per `api_mode`; agents created via `make_agent` (`:659-683`) |
| Handoff graphs + harness types (REQ-156) | ✅ | Docs + example pack + `sdlc_handoff` blueprint. Forced BA→Engineer→Tester and circular skeptic; API-only graph (CLI/remote native); cross-type Demo Bridge roster. Tests lock live edges: `tests/core/test_handoff_graph.py`, `tests/blueprints/test_sdlc_handoff.py`. `:8001` seed: `scripts/seed_req156_demo.py` (no secrets). Fixes #564. |
| Kind bases API/CLI/remote (REQ-159) | ✅ | ADR-005 + stubs `swarm.core.kind_bases`. Support / `BLUEPRINT_AGENT_BRIEF` prefer kind templates. Creator validator accepts them. Cross-link from README Why openai-agents (ADR-006: user-facing kinds are CLI \| API \| Blueprint \| Remote). Wizard/library still emit `BlueprintBase` (follow-up). Fixes #570. |
| Test suite health | ✅ | Goal is green `main` `Python Tests` (3.10/3.11/3.12). Own-diff triage still applies on a red PR, but a collection `ImportError` on tip of `main` is a must-fix (REQ-134 / #524). Intentional HOLD: `golden-journey` skipped (`visual-regression.yml` `if: false`, REQ-89 #446) until screenshot/tour recapture — not a pytest waiver. |
| Consolidation deprecation shims | 🗑 removed | `extensions.blueprint`, `extensions.config.config_loader`, `blueprints.common.spinner`, `ux.spinner`, `utils.ansi_box`, `extensions.launchers.swarm_api` deleted. Use `swarm.core.*` / `swarm.ux.ansi_box`. Locked gone by `tests/unit/test_deprecation_shims.py` (ROADMAP §2.1). |

## 2. CLI — ✅ 4

| Feature | Status | Evidence |
|---|---|---|
| `swarm-cli` | ✅ | Entry point `pyproject.toml [project.scripts]` → `swarm.core.swarm_cli:app`; `uv run swarm-cli --help` exits 0. Orphan argparse trees `extensions/cli` + `core/cli` deleted (ROADMAP §3.4b / §4.4). |
| `swarm-api` | ✅ | → `swarm.core.swarm_api:main` (pyproject); former `extensions.launchers.swarm_api` `-m` shim removed; launcher tests `tests/cli/test_launchers.py` pass |
| `codey` | ✅ | → `swarm.blueprints.codey.codey_cli:main`; `--help` exits 0 |
| `suggestion` | ✅ | → `swarm.blueprints.suggestion.suggestion_cli:main`; `--help` exits 0 |

## 3. API — ✅ 5

| Feature | Status | Evidence |
|---|---|---|
| `/v1/chat/attachments/` (REQ-38) | ✅ | `ChatAttachment` on `swarm.models` + `chat_attachment_upload`; sqlite metadata, bytes on disk (`SWARM_ATTACHMENTS_DIR`). Tests: `tests/views/test_chat_attachments.py`, `tests/core/test_chat_attachments.py`. Restored after tip-of-main `ImportError` (REQ-134 / #524). |
| `/v1/chat/completions` (non-streaming) | ✅ | `src/swarm/views/chat_views.py:86` `_handle_non_streaming`; route `urls.py:67`; `tests/views/test_chat_views.py` (18 tests) pass in isolation |
| `/v1/chat/completions` SSE streaming | ✅ | `chat_views.py:128-162` `_handle_streaming` yields `text/event-stream` + `[DONE]`; `test_post_streaming_success` asserts Content-Type `text/event-stream` (`test_chat_views.py:214-241`) |
| `/v1/models` | ✅ | `urls.py:56-57` → `OpenAIModelsView`; `tests/views/test_api_views.py::TestModelsListView` (5 tests) pass in isolation |
| `/v1/blueprints` + custom CRUD | ✅ | `urls.py:58-61` (`BlueprintsListView`, `CustomBlueprintsView`, `CustomBlueprintDetailView`); 33 tests in `tests/views/test_api_views.py` incl. create/patch/delete custom blueprints |
| `/v1/preferences/` (REQ-144 / REQ-168) | ✅ | First-party `UserPreference` JSON bag keyed by User / token / guest session. Favourites + Hidden Bots + hostname override. SPA import-once from localStorage when empty. Tests: `tests/views/test_preferences_api.py`. No Neon / no secrets. |
| `/v1/teams/` JSON Teams API | ✅ | `views/teams_api.py` list/create/delete over `teams.json`. **Honesty:** prefer **Profiles** — each entry is an LLM-profile alias (`id`/`description`/`llm_profile`) via `DynamicTeamBlueprint`, **not** a REQ-11 Team. Handoff Team is `/v1/agent-team/`. `/teams/` admin banner documents the collision. Tests: `tests/views/test_teams_api.py` |
| Team rosters + CoS isolation (REQ-28) | 🟡 | Composition store `team_rosters.json` + `/v1/team-rosters/` (`kind` includes `team` / `herdr`). Role `chief_of_staff` (`cos`/`chief`) ice-steel rail badge. Isolation: no cross-team handoff/`as_tool` unless nested child team (send-to-all as one member) or CoS. **Honesty:** Django `/teams/` stays aliases. Tests: `tests/core/test_team_isolation.py`, `test_agent_roles.py`, `test_team_rosters.py` |
| WebSocket chat consumer | ✅ | ROUTED 2026-06-11: `swarm/asgi.py` (ProtocolTypeRouter + AuthMiddlewareStack + origin validator) + `swarm/routing.py` (`ws/ai-demo/<id>/`); daphne+channels in INSTALLED_APPS; session-cookie auth only (Settings API bearer does **not** auth WS); anonymous accept-then-close **4401**; tests in `tests/test_asgi_routing.py` / `tests/test_consumers.py` |

## 4. Web UI — Django templates + HTMx (operator UI) — ✅ 6 · 🗑 2

Canonical day-to-day chrome is the **trailing-slash Django routes** below. `/` prefers the React SPA `dist/index.html` when built (`web_views.index`); SPA itself only mounts `/` + `/chat` ([ADR-001](docs/ADR-001-primary-ui.md)). Bare `/teams` → `/teams/launch/`, `/blueprints` → `/blueprint-library/`, `/settings` → `/settings/`, `/agent-creator` → `/agent-creator/` (deleted SPA operator pages are not remounted).

| Feature | Status | Evidence |
|---|---|---|
| Index/dashboard | ✅ | `web_views.index` serves SPA `dist/index.html` when present, else Django `index.html`; `tests/views/test_web_views.py::TestIndexView`. After pull: `make frontend`. Docker multi-stage Node bake; CI `frontend` job runs `scripts/build_frontend.sh` |
| Teams (launch/admin/export) | ✅ | `urls.py` → `team_launcher`/`team_admin`/`teams_export` at `/teams/launch/`, `/teams/`, `/teams/export`; same `teams.json` LLM-profile alias registry as `/v1/teams/` (not a multi-agent builder — [GLOSSARY](./docs/GLOSSARY.md)). **Auth:** `team_admin` + `teams_export` are `@login_required`; `team_launcher` stays public |
| Blueprint library (+ my-blueprints) | ✅ | `views/blueprint_library_views.py` renders `blueprint_library.html`; routes under `/blueprint-library/`; `tests/views/test_blueprint_library_views.py`. **Auth:** browse + add/remove/creator/avatar mutators are `@login_required` (CSRF on POSTs). **Creator:** POST writes under `get_user_blueprints_dir()` (+ JSON catalog); discovery opt-in via `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY`. **Runner:** My Blueprints posts to `/v1/chat/completions` (+ links to `/chat?blueprint=` and `/teams/launch/`) |
| Agent creator | ✅ | `/agent-creator/` + generate/validate/save in `views/agent_creator_views.py`. **Auth:** GET page is public; generate/validate/save mutators are `@login_required`. **Codegen:** `AgentPersonaGenerator` emits `AsyncOpenAI` + `chat.completions.create(stream=True)` (same contract as library `generate_blueprint_code`; no `chat_completion_stream`) — `tests/unit/test_agent_creator_codegen.py` |
| Agent Creator Pro | 🗑 removed | **Deleted** (was unwired clickware). `/agent-creator-pro/` soft-redirects to `/agent-creator/` (query preserved). View/template/JS/CSS removed; redirect kept in `urls.py`. |
| Settings dashboard | ✅ | `/settings/` → `views/settings_views.py` renders `settings_dashboard.html` (`@login_required`). Export Settings / Refresh / Environment Variables work; Validate Config + env Export stay disabled “(not available)”; path-check buttons removed (were unwired). Compact credential checklist callout matches [docs/AUTH.md](./docs/AUTH.md) (session for Chat/WS; Bearer/session for `/v1/*`; Explorer operator bridge; link to repo AUTH.md — docs not served in-app) |
| Session Explorer | ✅ | `/sessions/` + `/sessions/<id>/` + `/api/sessions/` in `views/session_explorer.py` (`@login_required`). With `ENABLE_API_AUTH`, operator bridge also shows configured `token:<sha256-prefix>` sessions to the web login; foreign `user:…` hidden; REST IDOR unchanged (`explorer_owner_allows`). Golden path: `tests/api/test_auth_operator_golden_path.py` (create→own→list + IDOR; library create→run→sessions: AsyncOpenAI stream + My Blueprints chat POST + Explorer list/detail + owner stamps) |
| `chat.html` / `simple_blueprint_page.html` | 🗑 removed | Deleted 0.5.2 (unrouted / never-rendered). Do not expect these templates on disk. |
| SPA fallback / asset serving | ✅ | FIXED in `f1fa20b1`: `urls.py:155` now `from django.urls import re_path` (was `django.conf.urls`, removed in Django 4.0 — broke whenever `webui/frontend/dist` existed). `tests/views` + `tests/mcp` green (169 passed) with dist present |
| Bee brand mark (REQ-106 / #768) | ✅ | Three #537 tasters by surface: `favicon-minimal.svg` (tab/PWA/Pinokio), `webui-geometric.svg` (operator navbar, login, Settings), `marketing-cyber-swarm.svg` (website fanfare). ICO 16/32/48 + Apple/PWA 180/192/512 from minimal. #487 clipart in `assets/brand/retired/`. Tests: `tests/unit/test_req106_brand_mark.py` |

## 5. Web UI — React SPA (`webui/frontend`) — 🔲 2 · 🟡 1 · 📋 1 · 🗑 3

Per [ADR-001](docs/ADR-001-primary-ui.md): SPA mounts `/` + `/chat` as Grok-Bot (selected agent's chat) and **`/agents` as Agent Router** (own chrome). Teams / Blueprints / Settings / Builder / AgentCreator SPA pages were **deleted** (not quarantined for remount). Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` continue to **redirect to Django** when served behind the app. Django operator pages are reached from the composer **+** menu, not a top tab bar.

| Feature | Status | Evidence |
|---|---|---|
| DaisyUI component library | 🔲 | 13 components built (`src/components/DaisyUI/*.tsx`: Alert, Badge, Button, Card, FormValidation, Input, Loading, Modal, Pagination, Select, Tabs, Textarea, Toast; 13 exports in `index.ts`); builds to `dist/`. Primary operator chrome is Django; SPA chat chrome uses these. |
| Grok-Bot chrome (`/` + `/chat`) | 🟡 | Left rail + chat-only main (no Home/Chat/Blueprints/Teams/Settings top nav; no mobile five-tab dock). Rail: Search command palette, unlabeled favourite tiles, Support-first conversations, hidden-agents popup (Unhide, no hide-all), Plugins, editable hostname. Narrow (`<lg`) tucks the rail after an agent pick; left-edge swipe or header control restores it; first-concealment swipe hint persists dismissed. Header is agent name + icon tools (theme is an icon, not a Light text button; header **Edit** is a pencil icon, REQ-120). Gear (`Open settings`) opens a DaisyUI `modal` + `modal-end` settings sheet (Remotes / Retention / Hostname / LLM profiles / System) — Settings is not a top-nav or dock eject to Django. System is read-only local-database size + path + conversation/message counts (REQ-56). Django `/settings/` remains the operator dump (REQ-14 chat count / disk / trash). Composer pill `[+] [ Message … ] [mic]`. Footer is tokens / who+how-long. Errors toast; no standing Connected. Per-agent websocket threads persist as JSON (`SWARM_CHAT_DIR`); Chat silently restores on reload / agent switch. Retention (counts, disk, trash, `SWARM_CHAT_MAX_AGE_DAYS`) is **Settings-only**. ChatPage WS via ASGI; needs Django **session cookie** (bearer does **not** auth websockets). Anonymous sockets close **4401**. Safe GFM markdown (`marked` + `htmlSafe`) + WS auto-reconnect (skips 4401). |
| Virtualized infinite chat history (REQ-163) | 📋 | Phase 0 ADR only — [ADR-004](docs/adr/004-virtualized-chat-history.md). **Primary `@tanstack/react-virtual` ≥ 3.14** (headless; `anchorTo: 'end'` / `followOnAppend` / `scrollToEnd`). Fallback MIT `react-virtuoso` `Virtuoso`. Reject `react-window` and commercial `@virtuoso.dev/message-list`. `@tanstack/react-query` already fetches catalogs; it does **not** window the DOM. ChatPage still maps every `displayItems` row; `GET /chat/thread/` has no cursor. Phase 1–2 implement Issues are outlined in the ADR (not filed from this look-only PR). |
| Settings default LLM + per-task override (REQ-43) | ✅ | SPA Settings → LLM profiles lists configured CLI/API/remote ids and a Default picker persisted as `settings.default_llm_profile` (`GET/PATCH /v1/llm-profiles/`). Auto-pick consumes REQ-44 `{cli, models}` when `swarm.core.cli_models` is present; otherwise stubs on `/v1/models` + fixtures (no `--help` scrape). Override-per-task routes summary → auxiliary and design → delegation; missing slug warns and uses Default. Chat `respond_with_default_model` honours that default when env is unset. #356 hook: `resolve_summary_model()`. Tests: `tests/core/test_llm_task_routing.py`, `tests/core/test_llm_list_models.py`, `tests/views/test_llm_profiles_api.py`, `SettingsSheet.test.tsx`. |
| WebUI config Full coverage (#776) | ✅ | ADR-002 hybrid: Settings writes every non-secret product section (`llm` CRUD, `settings.*`, `mcpServers`, `remotes`, `cli_agents`, `agent_team`; advanced `PATCH /v1/config/sections/` for fusion/moa/slash/blueprints/memory). Secrets env-only (refused as plaintext). `GET /v1/config-ownership/` inventory. Env honesty badges + `SWARM_CONFIG_FORCE_ENV`. Example `swarm_config.example.json`. Tests: `tests/core/test_config_ownership.py`, `tests/views/test_config_ownership_api.py`, `EnvOverrideBadge.test.tsx`. |
| Scale-out rail + session picker (REQ-66) | ✅ | One rail row per agent. Session count > 1 → stacked avatars (max 3 + remainder), every face animated with `startedAt` stagger. Click opens search-palette overlay of running + finished sessions; row click sets `?session=` on still-mounted Chat. Empty copy “no sessions yet”. Shared widget: `AvatarStack` + `lib/avatarStack.ts` (REQ-68 / #398 should import; this PR does not stack teams/remotes). Tests: `avatarStack.test.ts`, `AvatarStack.test.tsx`, `scaleOutSessions.test.ts`, `StackedAvatars.test.tsx`, `SessionPicker.test.tsx`, AgentSidebar / ChatPage. |
| Agent Router (`/agents`) | 🟡 | Own chrome (typed Support/CLI/API/Remote starters, REST `/v1/agents/`). Not aliased to `/chat`. Nested inside the same App shell as the Grok rail today (possible double rail until a later split). |
| Nested compact / summaries (REQ-37) | ✅ | `ConversationSummary` on local Django sqlite (`span`, `parent_summary_id`, `body`). `POST /chat/compact/` + `GET /chat/thread/` summaries. Consumer walks the summary tree for model context; raw JSON / `ChatMessage` stay. SPA `+` Compact; `.chat-summary` bordered blocks nest. Tests: `tests/core/test_chat_compact.py`, `chatCompact.test.ts`, ChatPage compact menu. No Neon. |
| Role hover-edit → agent editor (REQ-25 + REQ-58) | ✅ | Rail rows with role `support` / `gate` / `skeptic` reveal a focusable pencil on hover (default-role rows stay clean). Enter/click opens an agent-scoped DaisyUI overlay (`#os-agent-editor`): name, role, blueprint picker, optional LLM override. No Remotes / System / CLI catalog in that pane. Picker assigns a catalog blueprint to the seat (`localStorage.swarm_agent_edits`). **Edit blueprint…** opens Settings → Blueprints (list, assigned item selected). Settings Remotes stay global. Tests: `AgentEditor.test.tsx`, `AgentSidebar.test.tsx`, `SettingsSheet.test.tsx`, `e2e/chrome.spec.ts`. |
| Settings → Blueprints list (REQ-58) | ✅ | Settings sheet nav item **Blueprints** is a catalog listbox (same ids as the agent-editor picker). Selecting an item inspects that recipe (`#os-blueprint-editor`). Gear still opens Remotes / Retention / Hostname / LLM profiles. |
| New chat per task (REQ-65) | ✅ | Agent-scoped DaisyUI editor (`#os-agent-editor`, no Remotes/System). Toggle **New chat per task** default off. On: mint empty session per task; concurrent chats allowed; API `/v1/agents/<id>/sessions/` creates; CLI/remote skip stored resume ids. Tests: `test_session_policy.py`, `AgentEditorSheet.test.tsx`, `agentChat.test.ts`. |
| Select / New session (REQ-105) | ✅ | Django `ChatConversation` is agent-scoped (title/snippet/labels/`cli_session_id`). `GET/POST /v1/agents/<id>/sessions/` lists and mints empty sessions (`{"new": true}`). Shared `RailContextMenu` **Select session** / **New session** on API and CLI rows (teams/remotes omit). API opens `SessionPicker` (relative time + New). CLI Select stays on REQ-104 `CliSessionPicker`; CLI New posts `start_new` (fresh id on next send). Chat `?session=` replaces transcript + compact tree; status “Switched to session …”. Tests: `test_agent_sessions.py`, `test_agent_settings_api.py`, `test_req105_session_chrome.py`, `agentSessions.test.ts`, `SessionPicker.test.tsx`, `AgentSidebar.test.tsx`. |
| Rail Terminate CLI process (REQ-114) | ✅ | CLI row right-click **Terminate** (idle disabled: “Nothing running”). Kills only the swarm-spawned CLI process group (SIGTERM→SIGKILL). API/team/remote omit. Agent row and transcript stay; toast “Process stopped.” + **Terminated**. Tests: `test_cli_run_registry.py`, `test_cli_runs_api.py`, `RailContextMenuReq114.test.tsx`. Fixes #495. |
| Role chrome is the badge only (REQ-67) | ✅ | Rail / Django sidepane agent rows share ordinary row chrome. No `os-agent-row--*` / `os-agent-role-*` fill or left-border on the row; accent dots use mark-index colours. Support / gate / skeptic / CoS colour stays on `.os-agent-role-badge`. Selected / hover / dragging / team-kind chrome unchanged. Badge click (#356) not touched. Tests: `AgentSidebar.test.tsx`, `tests/unit/test_req67_role_badge_chrome.py`, `e2e/req67-role-badge.spec.ts`. |
| Computer control chrome stub (REQ-27b / REQ-93) | 🔲 | SPA Grok chat header **Chat tools** toolbar (top-right): Monitor **icon only** (`aria-label` / tooltip **Computer control**, no adjacent label) opens a DaisyUI WIP modal (OpenMousBot/Rakazo remote later). Icon may look muted; stays clickable. No driver/E2B/CUA/xdotool/CDP; not attached to agent tools; no enable-that-drives-a-machine. Settings / Search overlay uses a separate pane (Playwright default; sandbox/SaaS greyed). Adaptation plan: [ADR-007](docs/adr/007-local-computer-control.md) (REQ-189 / #645). `webui/frontend/src/components/ComputerControlStub.tsx`; tests in `ComputerControlStub.test.tsx`, `ChatPage.test.tsx`, `e2e/chrome.spec.ts`. |
| Per-agent notifications (REQ-98) | ✅ | Rail context menu **Notifications: On / Off** (default Off) persists `localStorage.swarm_notify_agents` by agent / `team:` / `remote:` row id — same family as hide/pin, not Neon. First enable calls `Notification.requestPermission()` once; denied shows a quiet site-settings hint. Popups fire on assistant-final (and mid-stream fail) when the tab is hidden or another row is selected; title is the display name (OpenMousBot, not OMB) plus a short redacted snippet. Click focuses and selects that chat. Tests: `agentNotifications.test.ts`, `AgentNotifications.test.tsx`, `test_req98_agent_notifications.py`. Fixes #459. |
| Agent sidepane hide | ✅ | SPA `AgentSidebar` lists `/v1/blueprints` agents (Support first); first load seeds Hidden with gate + skeptic catalog ids (REQ-26) unless `localStorage.swarm_hidden_agents` already exists. No “drop here to hide” text. Empty footer Hidden Bots slot stays blank; drag-over lightly reveals a drop target; drop or right-click **Hide from sidebar** hides and shows ghost **Hidden Bots N** (hover swaps count for `>`; click opens Unhide). Drag onto that row also hides. Persist `localStorage.swarm_hidden_agents` as a cache; REQ-144 also writes Hidden + favourites to `GET/PATCH /v1/preferences/` (per-user Django bag; import-once when the server is empty, then server wins). Hide conceals the list row and visible favourite tile; the pin stays in `swarm_pinned_agents` so Unhide restores the same favourite slot. |
| User preferences API (REQ-144 / REQ-168) | ✅ | First-party `UserPreference` (FK/OneToOne to User + `principal`, JSON `values` bag). `GET/PATCH /v1/preferences/` for ordered favourites + Hidden Bots + hostname override. Logged-in → `user:<name>`; Bearer → `token:<hash>`; guest → Django session. No django-dynamic-preferences dep; no secrets; no Neon. Tests: `tests/views/test_preferences_api.py`, `tests/core/test_user_preferences.py`, `userPrefs.test.ts`. |
| Teams in AGENTS sidepane (REQ-23) | ✅ | Team rows mix with agents after Support (Users icon + Team badge). Click opens `/chat?team=<id>` as that team's thread. Unlabeled dropdown: **All members**, then `name (kind/role)`, last **Manage Teams**. Send params `{team, target: "all"\|memberId}`; consumer stubs the runtime. Data from `team_rosters.json` / `GET /v1/team-rosters/` — **not** Django LLM-alias `/v1/teams/`. Empty/missing → one demo-team stub. |
| Stacked team/remote avatars (REQ-68) | ✅ | Shared `AvatarStack` + `SessionPicker` (`webui/frontend/src/components/AvatarStack.tsx`). Team and configured-remote rows show max 3 most-recent faces + remainder; every stacked face is animated with `started_at` stagger. OpenMousBot label, not OMB. Single-agent remote is one avatar. Click opens a search-palette picker filtered to that group. GET `/v1/remotes/` list only (no health/operate / live LAN). #394 should reuse the widget. Tests: `avatarStack.test.ts`, `AgentSidebar.test.tsx`. |
| TeamsPage / BlueprintsPage / SettingsPage | 🗑 deleted | Deleted from the SPA tree (ADR-001). Canonical UI: `/teams/launch/`, `/blueprint-library/`, `/settings/`. Bare paths redirect to Django; SPA `*` → `/`. |
| BuilderPage / AgentCreatorPage | 🗑 deleted | Removed (same cut). Do not remount. Canonical creator UI is Django `/agent-creator/`. |
| Orphan Builder React panels | 🗑 deleted | Inference/Skills/Trait/ToolCapabilities/BlueprintToolsBadges/CodeViewer/ApiAccess/ConfigSnippet/InfoTip + unused AuthContext removed; `@uiw/react-codemirror` deps dropped. Unrouted `Dashboard.tsx` and leftover `inferenceProfile.ts` / `toolCapabilities.ts` mirrors deleted; `skills.ts` stays (Support `buildSkillRequest`). |
| API / auth / websocket integration | 🟡 | Typed api client (`src/lib/api.ts`), react-query on blueprints/models, ChatPage speaks the ws protocol via ASGI (`swarm/asgi.py` + `AuthMiddlewareStack`). Journey `spa-chat.png` shows **Connected** after login when ASGI is up. |

## 6. Memory — 🔲 1 · 📋 2

| Feature | Status | Evidence |
|---|---|---|
| mem0ai backend | 🟡 | WIRED in `4c7e1b28` (post-audit): `MemoryBackend` protocol + `get_memory_backend()` factory in `swarm/memory/__init__.py`; `BlueprintBase` injects retrieved memories into run context pre-run and stores the conversation post-run, opt-in via blueprint config `memory` block, strict no-op otherwise; 11 tests in `tests/unit/test_memory_integration.py`. Caveat: not yet exercised against a real mem0 instance end-to-end (tests use a fake backend) |
| langmem backend | 📋 | `src/swarm/memory/langmem_memory.py:13-16` — real import commented out (`# import langmem`), all methods `pass`; dep commented out in `pyproject.toml` ("incomplete placeholders") |
| papr backend | 📋 | `src/swarm/memory/papr_memory.py` — same placeholder pattern; dep commented out in `pyproject.toml` |

## 7. MCP — ✅ 1 · 🟡 1 · 📋 1

| Feature | Status | Evidence |
|---|---|---|
| MCP client (agents consume MCP servers) | ✅ | `src/swarm/extensions/mcp/mcp_client.py:23` `MCPClient` (list_tools/call/resources) imports cleanly; blueprints pass `mcp_servers` into SDK agents — e.g. `blueprints/jeeves/blueprint_jeeves.py:61,226-245` filters `duckduckgo-search`/`home-assistant` servers per sub-agent; `required_mcp_servers` metadata at `:182` |
| MCP server provider (blueprints as tools) | 🟡 | `src/swarm/mcp/provider.py` `call_tool` instantiates and runs blueprints for real (docstring + tests `tests/mcp/test_provider_execute.py`, `test_provider.py`, `test_provider_edge_cases.py`). Caveat: reachable mainly via MCP server mount below (still optional/unshipped on clean install). |
| MCP server mount (`ENABLE_MCP_SERVER`) | 📋 | Flag mounts **`/mcp/`** when `mcp_server` is importable (`settings.py` / `urls.py`); docs in `docs/mcp_server_mode.md`. **Not** a declared `pyproject.toml` dependency (manual `pip install django-mcp-server`); flag without lockfile dep stays 📋. **Blueprints are NOT MCP tools** until the bridge is ported: `register_blueprints_with_mcp()` is a no-op on `mcp_server` ≥0.5 (flat `registry.register_tool` gone → MCPToolset) and now logs **`logger.error`** (ROADMAP §3.3). |

## 8. Feature-flagged integrations — ✅ 1 · 🗑 2

| Feature | Status | Evidence |
|---|---|---|
| GitHub marketplace discovery | ✅ | `ENABLE_GITHUB_MARKETPLACE` in `settings.py` (topics/org allowlist envs); `src/swarm/services/github_topics_service.py` real GitHub API calls; `marketplace/github/*` routes in `urls.py`. Client `org`/`topic` must match non-empty allowlists else **400**; empty org allowlist is intentionally unscoped. Upstream failures raise `GitHubAPIError` → **429/502** JSON (not empty 200); library tab surfaces non-OK as error empty-state. Tests: `tests/services/test_github_topics_service.py`, `tests/views/test_api_views.py` |
| Wagtail marketplace CMS | 🗑 removed | Dropped 2026-06-11 (ROADMAP §3.4): `swarm/marketplace/` app, `ENABLE_WAGTAIL` flag/settings/urls, wagtail/taggit/modelcluster pins, and the Wagtail-backed `/marketplace/blueprints/` + `/marketplace/mcp-configs/` endpoints deleted. GitHub-topics discovery (row above) is the replacement |
| SAML IdP | 🗑 removed | Dropped 2026-06-11 (ROADMAP §3.4): `ENABLE_SAML_IDP` flag, `SAML_IDP_*` settings plumbing, `/idp/` mount, env getters, and `tests/unit/test_settings_saml.py` deleted; `djangosaml2idp` was never a declared dependency |

## 9. Blueprints (discoverable) — ✅ 5 · 🟡 many · 🗑 husks gone

Re-verified 2026-08-18: `discover_blueprints('src/swarm/blueprints')` registers
**38** model ids (canonical dirs + aliases). Prefer [docs/GLOSSARY.md](./docs/GLOSSARY.md)
names (Blueprint vs `/v1/teams` LLM-profile alias). Empty husk dirs (no
`blueprint_*.py`) were deleted this pulse — do not restore.

| Feature | Status | Evidence |
|---|---|---|
| codey | ✅ | CLI (`codey --help`); command-injection fix `blueprint_codey.py` (`shlex.split`). `tests/blueprints/test_codey_basic.py` re-enabled (SWARM_TEST_MODE) |
| suggestion | ✅ | CLI (`suggestion --help`); discoverable |
| rue_code | ✅ | Discoverable; `tests/unit/blueprints/rue_code/test_rue_code_tools.py`; README + `rue_code_cli.py` |
| stewie | ✅ | Discoverable; `tests/blueprints/test_stewie.py` + gap smoke; nested Django leftovers gone |
| chatbot | ✅ | Discoverable (`blueprint_chatbot.py`); `tests/blueprints/test_chatbot.py` — **not** removed (prior ❌ row was stale) |
| jeeves | 🟡 | Discoverable; README + CLI + MCP-aware agents; `SWARM_TEST_MODE` short-circuit; spinner/box tests |
| geese / zeus / poets / gawd / whiskeytango_foxtrot / chucks_angels / dynamic_team | 🟡 | Discoverable; thin or no dedicated collected coverage (zeus has CLI; dynamic_team backs `/v1/teams` aliases) |
| django_chat | 🟡 | Discoverable only after Django setup; views/urls/templates; config tests |
| MoA / hybrid / persona / CLI-fusion family | 🟡 | Discoverable: `moa`, `moa_orchestrator`, `hybrid_moa`, `hybrid_team`, `hybrid_swarm`, `persona_council`, `cli_*`, `fs_introspect` — see FEATURE_STATUS / ROADMAP MoA rows + `tests/blueprints/test_cli_*.py` |
| Empty husks | 🗑 removed | Deleted dirs with no `blueprint_*.py`: `flock`, `digitalbutlers`, `echocraft`, `mcp_demo`, `mission_improbable`, `monkai_magic`, `nebula_shellz`, `omniplex` (plus earlier `whinge_surf` / `family_ties` / `messenger`). API tests that named `echocraft` as a mocked model id are unaffected. |
| `blueprint_audit_status.json` | 🗑 gone | Deleted earlier; do not restore. Status lives here + per-blueprint READMEs / tests. |

## 10. Security — ✅ 8 · 🟡 2

Coherent operator map: **[docs/AUTH.md](./docs/AUTH.md)** (Bearer `token:` principals + REST IDOR, Django session / WS 4401, Explorer bridge, workdir confinement, user-blueprint AST sandbox, CSRF / prod CSP).

| Feature | Status | Evidence |
|---|---|---|
| Codey command-injection fix | ✅ | `blueprint_codey.py:933-937` parses with `shlex.split` instead of shell string (commit `2e2ee426` "Fix Command Injection in Codey blueprint") |
| Sensitive-data redaction | ✅ | `swarm/utils/redact.py`; settings dashboard/API via `redact_settings_groups` + `json_script`; tests `tests/core/test_redact_sensitive_data.py`, `tests/unit/test_redact*.py` |
| API auth (static token / session) | 🟡 | `StaticTokenAuthentication` + multi-token (`API_AUTH_TOKEN`/`API_AUTH_TOKENS` / `SWARM_API_KEY(S)`); prod (`DEBUG=False`) refuses boot without a token unless `SWARM_ALLOW_NO_AUTH`. Caveat: with `DJANGO_DEBUG=true` and no token, `ENABLE_API_AUTH` is false (open API) and `SwarmConfig` logs a serve-time warning (`apps.py` `_warn_if_api_auth_disabled`) |
| Operator session gates (Django WebUI) | ✅ | `@login_required` on teams admin/export, blueprint library browse+mutators, settings, sessions, creator mutators; public without session: landing SPA, `/teams/launch/`, `/profiles/`, agent-creator GET, login form. CSRF required on `custom_login` POST + library mutators (not `@csrf_exempt`) |
| Session Explorer operator bridge | ✅ | With `ENABLE_API_AUTH`, logged-in Django users see `user:<name>` **and** configured Bearer `token:<sha256-prefix>` sessions (`auth.explorer_owner_allows`); foreign `user:…` / unowned stay hidden; REST `/v1/responses` IDOR stays strict same-principal. Locked by `tests/api/test_auth_operator_golden_path.py` (incl. library create→run→sessions via chat completions + Explorer feed) |
| Login open-redirect hardening | ✅ | `web_views._safe_post_login_redirect`: relative rooted paths only + `url_has_allowed_host_and_scheme`; rejects `//evil`, `\\`, absolute/external, bare relatives; `tests/views/test_web_views_security.py` |
| Creator toast DOM XSS escapes | ✅ | Live `team_creator.html` / `agent_creator.html` escape untrusted names/errors/paths before `innerHTML`; `tests/views/test_creator_toast_xss.py` (Pro JS deleted with the clickware surface) |
| User-blueprint AST sandbox | ✅ | `blueprint_sandbox.py` (default on; opt out `SWARM_USER_BLUEPRINT_SANDBOX=false`); discovery opt-in `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY`; creator saves `@login_required` + banned-snippet/AST gate |
| ChatMessage tenancy + prod security headers | ✅ | `message_views.py` scopes list to `conversation__student=request.user` when `ENABLE_API_AUTH`; token-only → empty qs. Prod-only (`DEBUG=False`): secure cookies (`SWARM_SECURE_COOKIES`); CSP via `ContentSecurityPolicyMiddleware` (`SWARM_CSP=false` to opt out; `script-src 'self'`, `style-src 'self'` — AUTH.md §7). Always-on (Django defaults + middleware, debug and prod): `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY` (prod block reasserts / `DJANGO_X_FRAME_OPTIONS`). Operator UI assets self-hosted under `static/contrib/`. Browser honesty: `swarm.core.browser_tools` + TROUBLESHOOTING §7 (no fake playwright success). |
| `SWARM_TEST_MODE` | 🟡 | Works as designed for tests (dummy LLM paths e.g. `blueprint_jeeves.py:276`; `swarm_cli.py:97` installs a bash shim instead of a PyInstaller binary). Caveat: a single env var globally swaps real behavior for canned output — if leaked into prod, responses are fake with no warning |

---

## 11. CLI Agent Fusion — ✅ 8 (v0.4.0 line, in progress)

Turns installed agentic CLIs (`claude`, `gemini`, `codex`, `opencode`, …) into
one-shot, API-addressable subagents. See `docs/CLI_FUSION.md`.

| Feature | Status | Evidence |
|---|---|---|
| CliAdapter one-shot layer | ✅ | `src/swarm/core/cli_adapter.py`; argv/stdin prompt modes, text/`json:<path>` parse, process-group timeout kill; `tests/core/test_cli_adapter.py` |
| `cli_agent` / `cli_fusion` blueprints | ✅ | `src/swarm/blueprints/cli_{agent,fusion}/`; panel→judge→synthesize + bounded master plan; `tests/blueprints/test_cli_{agent,fusion}.py` |
| Install autodiscovery | ✅ | `CliAdapterRegistry.discover()` + `swarm-cli cli-agents` (PR 2) |
| Auth autodiscovery | ✅ | `CliAgentConfig.auth_check` + `discover_auth()` + `--check-auth` (PR 3) |
| Full-capability panelists + workdir isolation | ✅ | Yolo-flag example adapters; `cli_fusion.isolate_workdir` git-worktree/temp-dir isolation (PR 4); isolation tests incl. real-git end-to-end |
| Built-in adapter catalog + `--suggest` | ✅ | `src/swarm/core/cli_catalog.py`; `swarm-cli cli-agents --suggest`; `tests/core/test_cli_catalog.py` (PR 5) |
| List-models probe (REQ-44) | ✅ | `cli_catalog.LIST_MODELS` + `swarm.core.cli_models`; `swarm-cli list-models` / `--list-models`; `GET /v1/cli-agents/<cli>/models`; fixtures in `tests/core/test_cli_models.py` |
| CLI session resume (REQ-52) | ✅ | Per-CLI `--resume` / `--session` / `exec resume` in `cli_catalog.SESSION`; id stored on the chat thread (`cli_sessions`); honest new-session line; `tests/core/test_cli_sessions.py`, fixture two-turn resume in `tests/blueprints/test_cli_agent.py` |
| CLI Select session (REQ-104) | ✅ | Rail right-click **Select session** (CLI only). Overlay picker (`CliSessionPicker`) + `GET/POST /v1/cli-sessions/`. Design A: new Django/chat-store conversation bound to the chosen CLI id; differing prior chat → expandable Prior history pill (never deleted). Catalog CLIs: no list argv — paste-id + swarm-touch recents; activity SoT `provider` if `can_list` else `swarm`. Shared `RailContextMenu` for #435. Tests: `test_cli_session_select.py`, `test_cli_sessions_api.py`, `cliSessions.test.ts`, `CliSessionPicker.test.tsx`. Fixes #468. |
| Rail Terminate CLI process (REQ-114) | ✅ | CLI rail right-click **Terminate** (disabled when idle: “Nothing running”). `POST /v1/cli-agents/runs/terminate/` kills the registered `start_new_session` process group (SIGTERM then SIGKILL). API/team/remote omit. Transcript and session id stay; toast “Process stopped.” + status **Terminated**. Tests: `test_cli_run_registry.py`, `test_cli_runs_api.py`, `railContextMenu.test.ts`, `RailContextMenuReq114.test.tsx`. Fixes #495. |
| Non-interactive smoke probe + `--smoke` | ✅ | `CliAdapter.smoke_check()` / `smoke_check_all()`; classifies ok/hang/error/not_installed (PR 6) |
| End-to-end API coverage | ✅ | `tests/api/test_cli_fusion_api.py`: real panel→synthesize and `params` selection over `/v1/chat/completions` (PR 7) |

Remaining v0.4.0 work (PRs 8–13): not yet specced; version bump + CHANGELOG + tag
deferred to the release PR.

---

## 11b. Remote harnesses (Hermes / OMB / Rakazo / swarm) — ✅ config+health · 🟡 operate

Open Swarm as a harness **for** other harnesses. Not a Grok-Bot chrome claim; not a concurrent Grok/OMB/Rakazo seat clone. Catalog is **opt-in** (REQ-59/61): Settings shows no kind cards until + Add remote.

| Feature | Status | Evidence |
|---|---|---|
| Opt-in catalog | ✅ | `load_added_remotes`; `GET /v1/remotes/` `data: []` until add; Settings empty + **Add remote**; unused kinds are not default cards |
| Persist base URL + api-key-env name | ✅ | `add_remote` / `persist_remote`; `POST /v1/remotes/`; `swarm-cli remotes set --api-key-env`; never persist a live token |
| Health/version per remote | ✅ | `check_health` — TCP + HTTP, one shot, honest DOWN; `POST /v1/remotes/<id>/health/` never crash-loops; missing remote is 404 / not probed |
| Hermes kind complete (REQ-61) | ✅ | After add, Settings health / list / send. List: `GET /v1/models`, `GET /api/sessions`, `GET /api/jobs`. Send: `POST /v1/runs` `{"input":…}` |
| OMB operate | ✅ | `GET /api/health`, `GET /api/bots`, `POST /api/bots/{id}/messages` (HTTP only; no OMB source clone) |
| Rakazo operate | 🟡 | `GET /health` public; `POST /rpc/bots/list` + `/rpc/threads/send` need Better Auth session — honest 401 + gap flag |
| Nested swarm operate (REQ-57) | ✅ | Catalog id `swarm` (alias `open-swarm`). List `GET /v1/blueprints/`; send `POST /v1/chat/completions/`. Default stub `http://127.0.0.1:9`. `persist_remote` refuses this process listen URL. Not auto-placed. |
| Agent-as-tool Team members | ✅ | Remotes are Team members (`consult_hermes`/`consult_omb`/`consult_rakazo`/`consult_swarm`) that see/talk via as_tool — **not** `/teams/` LLM-profile aliases. `GET /v1/remotes/` returns `vocabulary` + `team_members` |
| Place remotes in a Team | ✅ | Persist `agent_team.members`; `swarm-cli remotes team\|place\|unplace`; `GET/PATCH /v1/agent-team/`; `remote_harness` attaches `as_tool` only for **placed** members |
| Herdr remotes kind (REQ-64) | ✅ | Opt-in `kind=herdr` — add base URL + api-key-env; appears in Settings Remotes after add. No baked LAN host. CLI `--remote` uses configured base (localhost omits flag only when user set loopback). Health `GET /health` + list `GET /agents` stubbed in tests. Missing config is a clear error. |

---

## 12. MoA / consensus-then-team — ✅ (current shipped)

| Feature | Status | Evidence |
|---|---|---|
| Consensus → scripted team (Grok panel; no live Runner default) | ✅ | `run_moa_consensus` / `run_moa_then_team` / `TeamTask` in `swarm.core.moa.team`; live seats via `GrokParticipantBackend`; CLI `swarm-cli moa --team --workdir`; `moa_orchestrator` → `run_moa_agents_orchestrator` is scripted specialists by default — not a live openai-agents `Runner` (optional only via `build_moa_orchestrator_agents`). Soft `--team` failure still prints payload then exit 1 + `MoA team soft-fail:…` on stderr (`format_team_text` does not relabel as “consensus only”). Docs: `docs/MOA.md`. |

---

## 13. Herdr connectivity (REQ-21) — ✅

| Feature | Status | Evidence |
|---|---|---|
| `herdr` CLI wrapper | ✅ | `src/swarm/herdr/client.py` — workspace/agent list, agent read, `agent prompt TARGET TEXT` (one argv), wait-until idle\|working\|blocked\|done. Empty remote omits `--remote`. Tests mock the binary: `tests/herdr/test_herdr_client.py` (includes spaces in TEXT + proven `w3:p1` / `HERDR_PING_OK` → `agent_prompted`) |
| Persisted members `kind=herdr` | ✅ | `HerdrAgent` model + migration `0012`; DRF `/v1/herdr-agents/` list/add/remove; discover from live `agent list` / `workspace list`. Settings + Teams + Django admin + SPA sidepane. SQLite default (no DATABASE_URL / Neon) |
| Honesty | ✅ | [docs/HERDR.md](./docs/HERDR.md) — not Hermes/OMB/Rakazo; same-host default; `--remote` for other machines; blocked reject / `--wait` may finish an in-flight turn; CI must mock `herdr` |
| Remotes kind + CLI `--remote` (REQ-64) | ✅ | `remotes.herdr` persist; Settings + Add; `HerdrClient.from_remote_config()`; stub HTTP health/list in `tests/core/test_herdr_remote.py` |

## 14. Desktop package (REQ-151) — 📋 planned

| Feature | Status | Evidence |
|---|---|---|
| Windows desktop zip (local server + window) | 📋 | [ADR-003](docs/adr/003-desktop-packaging.md) (Phase 0). **Pick:** OpenMausBot *shape* (loopback ASGI + owned window); **pywebview + PyInstaller onedir**, not Electron. No installer in the ADR PR. Pinokio/Docker stays the container path. Native `grok`/`agy`/… stay on the host. Fixes #554 when the ADR merges; Phase 1–2 are split Issues. |

## Regeneration

Before treating a questionable row as authoritative, re-verify and update this file:

1. **Tests:** `uv run pytest -q` (full counts) and re-run any failing file in isolation.
2. **Entry points:** `uv run swarm-cli --help && uv run swarm-api --help && uv run codey --help && uv run suggestion --help`.
3. **Imports:** `uv run python -c "import swarm.blueprints.<name>.blueprint_<name>"` per blueprint; `import swarm.core.blueprint_base` (canonical). `swarm.extensions.blueprint` must raise `ModuleNotFoundError`.
4. **SPA scope:** `App.tsx` routes only `/` + `/chat`; leftover operator SPA pages deleted (ADR-001). Canonical operator UI is Django (bare SPA paths redirect).
5. **Flags vs deps:** `grep -n "django-mcp-server\\|mcp_server" pyproject.toml docs/mcp_server_mode.md` — flag without a declared lockfile dependency stays 📋.
6. **Resolved:** `urls.py` imports `re_path` from `django.urls` (Django 4+); the old `django.conf.urls` import bug is gone.
