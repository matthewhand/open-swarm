# Feature Status

> **Live status board** — per-feature evidence for what is shipped, partial, or
> planned. Last updated: **2026-08-18**. Nested checklist:
> [ROADMAP.md](./ROADMAP.md); release notes: [CHANGELOG.md](./CHANGELOG.md).
> Product direction + live-vs-intended honesty: [docs/VISION.md](./docs/VISION.md)
> (remotes and Grok-Bot chrome are **not** claimed here). The original 2026-06-10
> point-in-time audit is archived at
> [docs/archive/FEATURE_STATUS_2026-06-10.md](./docs/archive/FEATURE_STATUS_2026-06-10.md).

Legend: ✅ working (verified) · 🟡 partial (caveat named) · 🔲 scaffolded (exists, not wired) · 📋 planned (flags/docs only) · ❌ broken/fake/dead · 🗑 removed

---

## 1. Core agent runtime — ✅ 3 · 🟡 1 · ❌ 1

| Feature | Status | Evidence |
|---|---|---|
| Blueprint discovery | ✅ | `src/swarm/core/blueprint_discovery.py` (247 lines); `tests/core/test_blueprint_discovery_behavior.py` and `test_blueprint_discovery_comprehensive.py` pass in full-suite run |
| Blueprint execution (`BlueprintBase.run`) | ✅ | `src/swarm/core/blueprint_base.py` (772 lines); `tests/core/test_blueprint_execution_comprehensive.py`, `test_blueprint_base.py`, `test_blueprint_model_override.py` all pass |
| openai-agents SDK integration | ✅ | `blueprint_base.py:39` `from agents import set_default_openai_client`; `:644-648` selects `OpenAIResponsesModel` vs `OpenAIChatCompletionsModel` per `api_mode`; agents created via `make_agent` (`:659-683`) |
| Test suite health | ✅ | 673 passed / 2 skipped as of `4c7e1b28`. (At audit time: 560/621 with 59 order-dependent failures from the `urls.py:155` import bug — fixed in `f1fa20b1`) |
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
| `/v1/chat/completions` (non-streaming) | ✅ | `src/swarm/views/chat_views.py:86` `_handle_non_streaming`; route `urls.py:67`; `tests/views/test_chat_views.py` (18 tests) pass in isolation |
| `/v1/chat/completions` SSE streaming | ✅ | `chat_views.py:128-162` `_handle_streaming` yields `text/event-stream` + `[DONE]`; `test_post_streaming_success` asserts Content-Type `text/event-stream` (`test_chat_views.py:214-241`) |
| `/v1/models` | ✅ | `urls.py:56-57` → `OpenAIModelsView`; `tests/views/test_api_views.py::TestModelsListView` (5 tests) pass in isolation |
| `/v1/blueprints` + custom CRUD | ✅ | `urls.py:58-61` (`BlueprintsListView`, `CustomBlueprintsView`, `CustomBlueprintDetailView`); 33 tests in `tests/views/test_api_views.py` incl. create/patch/delete custom blueprints |
| `/v1/teams/` JSON Teams API | ✅ | `views/teams_api.py` list/create/delete over `teams.json`. **Live honesty:** each team is an LLM-profile alias (`id`/`description`/`llm_profile`) via `DynamicTeamBlueprint` — **not** inter-agent talk. **Intended** Team (wire API/CLI/remotes via handoff / `as_tool`) is in [VISION](./docs/VISION.md) / [GLOSSARY](./docs/GLOSSARY.md); Teams Admin does not do that. Tests: `tests/views/test_teams_api.py` |
| WebSocket chat consumer | ✅ | ROUTED 2026-06-11: `swarm/asgi.py` (ProtocolTypeRouter + AuthMiddlewareStack + origin validator) + `swarm/routing.py` (`ws/ai-demo/<id>/`); daphne+channels in INSTALLED_APPS; session-cookie auth only (Settings API bearer does **not** auth WS); anonymous accept-then-close **4401**; tests in `tests/test_asgi_routing.py` / `tests/test_consumers.py` |

## 4. Web UI — Django templates + HTMx (operator UI) — ✅ 6 · 🗑 2

Canonical day-to-day chrome is the **trailing-slash Django routes** below. `/` prefers the React SPA `dist/index.html` when built (`web_views.index`); SPA itself only mounts `/` + `/chat` ([ADR-001](docs/ADR-001-primary-ui.md)). Bare `/teams` → `/teams/launch/`, `/blueprints` → `/blueprint-library/`, `/settings` → `/settings/`, `/agent-creator` → `/agent-creator/` (deleted SPA operator pages are not remounted).

| Feature | Status | Evidence |
|---|---|---|
| Index/dashboard | ✅ | `web_views.index` serves SPA `dist/index.html` when present, else Django `index.html`; `tests/views/test_web_views.py::TestIndexView`. After pull: `make frontend`. Docker multi-stage Node bake; CI `frontend` job runs `scripts/build_frontend.sh` |
| Teams (launch/admin/export) | ✅ | `urls.py` → `team_launcher`/`team_admin`/`teams_export` at `/teams/launch/`, `/teams/`, `/teams/export`; same `teams.json` **LLM-profile alias** registry as `/v1/teams/`. **Not** inter-agent talk — that is Blueprints/MoA today; intended Team is [VISION](./docs/VISION.md). **Auth:** `team_admin` + `teams_export` are `@login_required`; `team_launcher` stays public |
| Blueprint library (+ my-blueprints) | ✅ | `views/blueprint_library_views.py` renders `blueprint_library.html`; routes under `/blueprint-library/`; `tests/views/test_blueprint_library_views.py`. **Auth:** browse + add/remove/creator/avatar mutators are `@login_required` (CSRF on POSTs). **Creator:** POST writes under `get_user_blueprints_dir()` (+ JSON catalog); discovery opt-in via `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY`. **Runner:** My Blueprints posts to `/v1/chat/completions` (+ links to `/chat?blueprint=` and `/teams/launch/`) |
| Agent creator | ✅ | `/agent-creator/` + generate/validate/save in `views/agent_creator_views.py`. **Auth:** GET page is public; generate/validate/save mutators are `@login_required`. **Codegen:** `AgentPersonaGenerator` emits `AsyncOpenAI` + `chat.completions.create(stream=True)` (same contract as library `generate_blueprint_code`; no `chat_completion_stream`) — `tests/unit/test_agent_creator_codegen.py` |
| Agent Creator Pro | 🗑 removed | **Deleted** (was unwired clickware). `/agent-creator-pro/` soft-redirects to `/agent-creator/` (query preserved). View/template/JS/CSS removed; redirect kept in `urls.py`. |
| Settings dashboard | ✅ | `/settings/` → `views/settings_views.py` renders `settings_dashboard.html` (`@login_required`). Export Settings / Refresh / Environment Variables work; Validate Config + env Export stay disabled “(not available)”; path-check buttons removed (were unwired). Compact credential checklist callout matches [docs/AUTH.md](./docs/AUTH.md) (session for Chat/WS; Bearer/session for `/v1/*`; Explorer operator bridge; link to repo AUTH.md — docs not served in-app) |
| Session Explorer | ✅ | `/sessions/` + `/sessions/<id>/` + `/api/sessions/` in `views/session_explorer.py` (`@login_required`). With `ENABLE_API_AUTH`, operator bridge also shows configured `token:<sha256-prefix>` sessions to the web login; foreign `user:…` hidden; REST IDOR unchanged (`explorer_owner_allows`). Golden path: `tests/api/test_auth_operator_golden_path.py` (create→own→list + IDOR; library create→run→sessions: AsyncOpenAI stream + My Blueprints chat POST + Explorer list/detail + owner stamps) |
| `chat.html` / `simple_blueprint_page.html` | 🗑 removed | Deleted 0.5.2 (unrouted / never-rendered). Do not expect these templates on disk. |
| SPA fallback / asset serving | ✅ | FIXED in `f1fa20b1`: `urls.py:155` now `from django.urls import re_path` (was `django.conf.urls`, removed in Django 4.0 — broke whenever `webui/frontend/dist` existed). `tests/views` + `tests/mcp` green (169 passed) with dist present |

## 5. Web UI — React SPA (`webui/frontend`) — 🔲 1 · 🟡 1 · 🗑 3

Per [ADR-001](docs/ADR-001-primary-ui.md): SPA mounts **only** `/` (dashboard) and `/chat`. Teams / Blueprints / Settings / Builder / AgentCreator SPA pages were **deleted** (not quarantined for remount). Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` continue to **redirect to Django** when served behind the app.

| Feature | Status | Evidence |
|---|---|---|
| DaisyUI component library | 🔲 | 13 components built (`src/components/DaisyUI/*.tsx`: Alert, Badge, Button, Card, FormValidation, Input, Loading, Modal, Pagination, Select, Tabs, Textarea, Toast; 13 exports in `index.ts`); builds to `dist/`. Primary operator chrome is Django; dashboard + chat still use these. |
| Dashboard (`/`) + Chat (`/chat`) | 🟡 | `App.tsx` routes only these two; desktop nav Home·Chat + Django hrefs (Blueprints·Teams·Sessions·Settings); **mobile five-tab dock** Home·Chat + Django hrefs (Blueprints·Teams·Sessions) — Settings is desktop top-nav/gear only (matches `mobile/*.png`). Home uses large chrome action cards (Launch Team / Browse Blueprints / Manage Teams / Settings). ChatPage WS via ASGI; needs Django **session cookie** (bearer does **not** auth websockets). Anonymous sockets close **4401**. Safe GFM markdown (`marked` + `htmlSafe`) + WS auto-reconnect (skips 4401). |
| Agent sidepane hide | ✅ | SPA `AgentSidebar` + Django `agent_sidebar.js` list `/v1/blueprints` agents; right-click **Hide from sidebar** moves an item into expandable Hidden; Unhide restores it. Persist `localStorage.swarm_hidden_agents` (no hide-all). Shared on Home, Chat, Blueprints, Teams, Sessions, Settings. |
| TeamsPage / BlueprintsPage / SettingsPage | 🗑 deleted | Deleted from the SPA tree (ADR-001). Canonical UI: `/teams/launch/`, `/blueprint-library/`, `/settings/`. Bare paths redirect to Django; SPA `*` → `/`. |
| BuilderPage / AgentCreatorPage | 🗑 deleted | Removed (same cut). Do not remount. Canonical creator UI is Django `/agent-creator/`. |
| Orphan Builder React panels | 🗑 deleted | Inference/Skills/Trait/ToolCapabilities/BlueprintToolsBadges/CodeViewer/ApiAccess/ConfigSnippet/InfoTip + unused AuthContext removed; `@uiw/react-codemirror` deps dropped. Pure helpers remain in `src/lib/{inferenceProfile,skills,toolCapabilities}.ts`. |
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
| Non-interactive smoke probe + `--smoke` | ✅ | `CliAdapter.smoke_check()` / `smoke_check_all()`; classifies ok/hang/error/not_installed (PR 6) |
| End-to-end API coverage | ✅ | `tests/api/test_cli_fusion_api.py`: real panel→synthesize and `params` selection over `/v1/chat/completions` (PR 7) |

Remaining v0.4.0 work (PRs 8–13): not yet specced; version bump + CHANGELOG + tag
deferred to the release PR.

---

## 12. MoA / consensus-then-team — ✅ (current shipped)

| Feature | Status | Evidence |
|---|---|---|
| Consensus → scripted team (Grok panel; no live Runner default) | ✅ | `run_moa_consensus` / `run_moa_then_team` / `TeamTask` in `swarm.core.moa.team`; live seats via `GrokParticipantBackend`; CLI `swarm-cli moa --team --workdir`; `moa_orchestrator` → `run_moa_agents_orchestrator` is scripted specialists by default — not a live openai-agents `Runner` (optional only via `build_moa_orchestrator_agents`). Soft `--team` failure still prints payload then exit 1 + `MoA team soft-fail:…` on stderr (`format_team_text` does not relabel as “consensus only”). Docs: `docs/MOA.md`. |

---

## Regeneration

Before treating a questionable row as authoritative, re-verify and update this file:

1. **Tests:** `uv run pytest -q` (full counts) and re-run any failing file in isolation.
2. **Entry points:** `uv run swarm-cli --help && uv run swarm-api --help && uv run codey --help && uv run suggestion --help`.
3. **Imports:** `uv run python -c "import swarm.blueprints.<name>.blueprint_<name>"` per blueprint; `import swarm.core.blueprint_base` (canonical). `swarm.extensions.blueprint` must raise `ModuleNotFoundError`.
4. **SPA scope:** `App.tsx` routes only `/` + `/chat`; leftover operator SPA pages deleted (ADR-001). Canonical operator UI is Django (bare SPA paths redirect).
5. **Flags vs deps:** `grep -n "django-mcp-server\\|mcp_server" pyproject.toml docs/mcp_server_mode.md` — flag without a declared lockfile dependency stays 📋.
6. **Resolved:** `urls.py` imports `re_path` from `django.urls` (Django 4+); the old `django.conf.urls` import bug is gone.
