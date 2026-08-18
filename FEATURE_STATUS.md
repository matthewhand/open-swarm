# Feature Status Audit

> ⚠️ **Historical audit (2026-06-10).** Point-in-time evidence snapshot; it has
> drifted — the project has since shipped v0.4.x–**v0.5.1** on PyPI (CLI Agent
> Fusion, async `/v1/responses`, persona councils, recursion, community-blueprint
> discovery). For **current** status see [ROADMAP.md §0](./ROADMAP.md) and
> [CHANGELOG.md](./CHANGELOG.md). Rows below are lineage, not live state.

**Date:** 2026-06-10
**Baseline:** working tree on top of commit `720a08ae` ("fix(packaging): repair uv resolution…"), generated **during** the cleanup wave — 8 blueprint packages and legacy modules (`swarm/repl`, `swarm/agent`, `swarm/llm`, …) are deleted in the worktree but not yet committed. Re-verify before acting (see Regeneration at bottom).
**Test run (this audit):** 621 collected — **560 passed, 59 failed, 2 skipped** (`uv run pytest -q`). All 59 failures were in `tests/views/` + `tests/mcp/test_mcp_urls.py`, order-dependent, root-caused to the SPA-fallback bug in `src/swarm/urls.py:155`.
**Update (same day, post-audit):** the `urls.py` bug was fixed in `f1fa20b1` and the suite is green again — **673 passed, 2 skipped** as of `4c7e1b28` (includes salvaged archive tests and new memory-integration tests). Rows below referencing the urls.py failure are retained as audit history; the bug itself is FIXED.

Legend: ✅ working (verified) · 🟡 partial (caveat named) · 🔲 scaffolded (exists, not wired) · 📋 planned (flags/docs only) · ❌ broken/fake/dead

---

## 1. Core agent runtime — ✅ 3 · 🟡 1 · ❌ 1

| Feature | Status | Evidence |
|---|---|---|
| Blueprint discovery | ✅ | `src/swarm/core/blueprint_discovery.py` (247 lines); `tests/core/test_blueprint_discovery_behavior.py` and `test_blueprint_discovery_comprehensive.py` pass in full-suite run |
| Blueprint execution (`BlueprintBase.run`) | ✅ | `src/swarm/core/blueprint_base.py` (772 lines); `tests/core/test_blueprint_execution_comprehensive.py`, `test_blueprint_base.py`, `test_blueprint_model_override.py` all pass |
| openai-agents SDK integration | ✅ | `blueprint_base.py:39` `from agents import set_default_openai_client`; `:644-648` selects `OpenAIResponsesModel` vs `OpenAIChatCompletionsModel` per `api_mode`; agents created via `make_agent` (`:659-683`) |
| Test suite health | ✅ | 673 passed / 2 skipped as of `4c7e1b28`. (At audit time: 560/621 with 59 order-dependent failures from the `urls.py:155` import bug — fixed in `f1fa20b1`) |
| `swarm.extensions.blueprint` (legacy duplicate of core) | ❌ | Package does not import: `ImportError: cannot import name 'config_loader' … (circular import)` at `src/swarm/extensions/blueprint/__init__.py:12`; `extensions/blueprint/blueprint_base.py:7-8` still imports `from src.swarm.utils...` and `:18` `from swarm.core import Swarm` (class no longer exists). 562-line dead copy of `core/blueprint_base.py` |

## 2. CLI — ✅ 4

| Feature | Status | Evidence |
|---|---|---|
| `swarm-cli` | ✅ | Entry point `pyproject.toml [project.scripts]` → `swarm.core.swarm_cli:app`; `uv run swarm-cli --help` exits 0 (verified 2026-06-10) |
| `swarm-api` | ✅ | → `swarm.extensions.launchers.swarm_api:main`; `--help` exits 0; launcher tests `tests/cli/test_launchers.py` pass |
| `codey` | ✅ | → `swarm.blueprints.codey.codey_cli:main`; `--help` exits 0 |
| `suggestion` | ✅ | → `swarm.blueprints.suggestion.suggestion_cli:main`; `--help` exits 0 |

## 3. API — ✅ 5

| Feature | Status | Evidence |
|---|---|---|
| `/v1/chat/completions` (non-streaming) | ✅ | `src/swarm/views/chat_views.py:86` `_handle_non_streaming`; route `urls.py:67`; `tests/views/test_chat_views.py` (18 tests) pass in isolation |
| `/v1/chat/completions` SSE streaming | ✅ | `chat_views.py:128-162` `_handle_streaming` yields `text/event-stream` + `[DONE]`; `test_post_streaming_success` asserts Content-Type `text/event-stream` (`test_chat_views.py:214-241`) |
| `/v1/models` | ✅ | `urls.py:56-57` → `OpenAIModelsView`; `tests/views/test_api_views.py::TestModelsListView` (5 tests) pass in isolation |
| `/v1/blueprints` + custom CRUD | ✅ | `urls.py:58-61` (`BlueprintsListView`, `CustomBlueprintsView`, `CustomBlueprintDetailView`); 33 tests in `tests/views/test_api_views.py` incl. create/patch/delete custom blueprints |
| WebSocket chat consumer | ✅ | ROUTED 2026-06-11: `swarm/asgi.py` (ProtocolTypeRouter + AuthMiddlewareStack + origin validator) + `swarm/routing.py` (`ws/ai-demo/<id>/`); daphne+channels in INSTALLED_APPS; session-cookie auth only (Settings API bearer does **not** auth WS); anonymous accept-then-close **4401**; tests in `tests/test_asgi_routing.py` / `tests/test_consumers.py` |

## 4. Web UI — Django templates + HTMx (operator UI) — ✅ 6 · ❌ 2

Canonical day-to-day chrome is the **trailing-slash Django routes** below. `/` prefers the React SPA `dist/index.html` when built (`web_views.index`); bare `/teams` → `/teams/launch/`, `/blueprints` → `/blueprint-library/`, `/settings` → `/settings/`, `/agent-creator` → `/agent-creator/` (not the leftover SPA shells).

| Feature | Status | Evidence |
|---|---|---|
| Index/dashboard | ✅ | `web_views.index` serves SPA `dist/index.html` when present, else Django `index.html`; `tests/views/test_web_views.py::TestIndexView` |
| Teams (launch/admin/export) | ✅ | `urls.py` → `team_launcher`/`team_admin`/`teams_export` at `/teams/launch/`, `/teams/`, `/teams/export`; renders `teams_launch.html` (`web_views.py`), `teams_admin.html`. **Auth:** `team_admin` + `teams_export` are `@login_required`; `team_launcher` stays public |
| Blueprint library (+ my-blueprints) | ✅ | `views/blueprint_library_views.py` renders `blueprint_library.html`; routes under `/blueprint-library/`; `tests/views/test_blueprint_library_views.py`. **Auth:** browse + add/remove/creator/avatar mutators are `@login_required` (CSRF on POSTs) |
| Agent creator (+ pro) | ✅ | `/agent-creator/` + generate/validate/save in `views/agent_creator_views.py`; `agent_creator_pro.py`. **Auth:** GET page is public; generate/validate/save mutators are `@login_required` |
| Settings dashboard | ✅ | `/settings/` → `views/settings_views.py` renders `settings_dashboard.html` (`@login_required`) |
| Session Explorer | ✅ | `/sessions/` + `/sessions/<id>/` + `/api/sessions/` in `views/session_explorer.py` (`@login_required`). With `ENABLE_API_AUTH`, operator bridge also shows configured `token:<sha256-prefix>` sessions to the web login; foreign `user:…` hidden; REST IDOR unchanged (`explorer_owner_allows`) |
| `chat.html` / `simple_blueprint_page.html` | ❌ | Removed 0.5.2 (unrouted / never-rendered). Do not expect these templates on disk. |
| SPA fallback / asset serving | ✅ | FIXED in `f1fa20b1`: `urls.py:155` now `from django.urls import re_path` (was `django.conf.urls`, removed in Django 4.0 — broke whenever `webui/frontend/dist` existed). `tests/views` + `tests/mcp` green (169 passed) with dist present |

## 5. Web UI — React SPA (`webui/frontend`) — 🔲 1 · 🟡 2

| Feature | Status | Evidence |
|---|---|---|
| DaisyUI component library | 🔲 | 13 components built (`src/components/DaisyUI/*.tsx`: Alert, Badge, Button, Card, FormValidation, Input, Loading, Modal, Pagination, Select, Tabs, Textarea, Toast; 13 exports in `index.ts`); builds to `dist/`. Primary operator chrome is Django; SPA leftovers still import these. |
| TeamsPage | 🟡 | Live fetch from `/teams/export?format=json` (`TeamsPage.tsx` `loadTeams`); on error shows honest empty + alert (no demo rows). Launch links to SPA `/chat?blueprint=<team-id>`. Bare `/teams` redirects to Django Team Launcher — this page is a leftover SPA route, not the canonical UI. |
| BlueprintsPage | 🟡 | Live fetch from `/v1/blueprints` (`BlueprintsPage.tsx`); on error shows honest empty + alert (no demo rows). Launch links to SPA `/chat?blueprint=<id>` (session auth required). Bare `/blueprints` redirects to Django Blueprint Library. |
| API / auth / websocket integration | 🟡 | Typed api client (`src/lib/api.ts`), react-query on blueprints/models, ChatPage speaks the ws protocol via ASGI (`swarm/asgi.py` + `AuthMiddlewareStack`). Caveat: chat needs a Django **session cookie** (Settings API bearer token does **not** auth websockets). Anonymous sockets close with code **4401**; journey `spa-chat.png` shows **Connected** after login when ASGI is up (Unavailable is the unauthenticated / unreachable path). |

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
| MCP server mount (`ENABLE_MCP_SERVER`) | 📋 | `settings.py` adds `mcp_server` (the import name from the `django-mcp-server` dist) when the module is importable; docs in `docs/mcp_server_mode.md`. **Not** a declared `pyproject.toml` dependency (manual `pip install django-mcp-server`); flag without lockfile dep stays 📋. Blueprint→tool bridge still needs MCPToolset port (ROADMAP §3.3). |

## 8. Feature-flagged integrations — ✅ 1 · 🗑 2

| Feature | Status | Evidence |
|---|---|---|
| GitHub marketplace discovery | ✅ | `ENABLE_GITHUB_MARKETPLACE` in `settings.py` (topics/org allowlist envs); `src/swarm/services/github_topics_service.py` real GitHub API calls; `marketplace/github/*` routes in `urls.py`. Upstream failures raise `GitHubAPIError` → **429/502** JSON (not empty 200); library tab surfaces non-OK as error empty-state. Tests: `tests/services/test_github_topics_service.py`, `tests/views/test_api_views.py` |
| Wagtail marketplace CMS | 🗑 removed | Dropped 2026-06-11 (ROADMAP §3.4): `swarm/marketplace/` app, `ENABLE_WAGTAIL` flag/settings/urls, wagtail/taggit/modelcluster pins, and the Wagtail-backed `/marketplace/blueprints/` + `/marketplace/mcp-configs/` endpoints deleted. GitHub-topics discovery (row above) is the replacement |
| SAML IdP | 🗑 removed | Dropped 2026-06-11 (ROADMAP §3.4): `ENABLE_SAML_IDP` flag, `SAML_IDP_*` settings plumbing, `/idp/` mount, env getters, and `tests/unit/test_settings_saml.py` deleted; `djangosaml2idp` was never a declared dependency |

## 9. Blueprints (post-cleanup survivors) — ✅ 3 · 🟡 14 · ❌ 2

Import check: every module below imported successfully via `uv run python -c "import swarm.blueprints.<x>.<mod>"` on 2026-06-10 unless noted.

| Feature | Status | Evidence |
|---|---|---|
| codey | ✅ | CLI entry point verified (`codey --help`); command-injection fix `blueprint_codey.py:933-937` (`shlex.split`, commit `2e2ee426`). Caveat: its basic tests are excluded from CI — `pytest.ini addopts --ignore-glob tests/blueprints/test_codey_*.py` |
| suggestion | ✅ | CLI entry point verified (`suggestion --help`); `blueprint_suggestion.py` imports clean |
| rue_code | ✅ | Imports; dedicated collected tests `tests/unit/blueprints/rue_code/test_rue_code_tools.py` pass; has README + `rue_code_cli.py` |
| jeeves | 🟡 | Imports; README, CLI, MCP-aware agents (`blueprint_jeeves.py:226-245`); caveat: no dedicated collected tests; `SWARM_TEST_MODE` short-circuit at `:276` returns canned output |
| geese | 🟡 | Imports; richest structure (4 agent modules, prompts, memory objects, README); caveat: no dedicated collected tests; actively being modified in cleanup wave |
| zeus | 🟡 | Imports; `zeus_cli.py` + `apps.py`; no dedicated tests |
| django_chat | 🟡 | Imports only after `django.setup()` (verified) — unusable outside Django context; has views/urls/templates; no dedicated tests |
| flock | 🟡 | Imports; has `test_basic.py` — but **not collected**: it lives in `src/swarm/blueprints/flock/` while `pytest.ini testpaths = tests` |
| chucks_angels | 🟡 | Imports; same uncollected `test_basic.py` problem |
| digitalbutlers | 🟡 | Imports; same uncollected `test_basic.py` problem |
| whinge_surf | 🟡 | Imports; `llm_integration.py` backend added in commit `3f0ec3ea`; no dedicated tests |
| poets | 🟡 | Imports; `poets_cli.py`; no README, no tests |
| gawd | 🟡 | Imports; `apps.py`; no README, no tests |
| family_ties | 🟡 | Imports; single-file blueprint, no README/tests |
| dynamic_team | 🟡 | Imports; bare directory — no `__init__.py`, README, or tests |
| whiskeytango_foxtrot | 🟡 | Imports; no README/tests |
| stewie | 🟡 | Imports, has models/serializers/urls — but its blueprint module is literally named `blueprint_family_ties.py` (copy-paste from family_ties, never renamed): `src/swarm/blueprints/stewie/blueprint_family_ties.py` |
| chatbot, echocraft, mcp_demo, messenger, mission_improbable, monkai_magic, nebula_shellz, omniplex | ❌ | Removed in cleanup wave — `git status` shows `D src/swarm/blueprints/<each>/...` in the worktree at audit time; directories already gone from disk |
| `blueprint_audit_status.json` | ❌ | Stale/fake metadata: `src/swarm/blueprints/blueprint_audit_status.json` marks deleted blueprints (echocraft, mcp_demo, chatbot) "working" and lists blueprints that don't exist at all (dilbot, gaggle, gatcha, divine_code, shell_demo, unapologetic_press) |

## 10. Security — ✅ 8 · 🟡 2

| Feature | Status | Evidence |
|---|---|---|
| Codey command-injection fix | ✅ | `blueprint_codey.py:933-937` parses with `shlex.split` instead of shell string (commit `2e2ee426` "Fix Command Injection in Codey blueprint") |
| Sensitive-data redaction | ✅ | `swarm/utils/redact.py`; settings dashboard/API via `redact_settings_groups` + `json_script`; tests `tests/core/test_redact_sensitive_data.py`, `tests/unit/test_redact*.py` |
| API auth (static token / session) | 🟡 | `StaticTokenAuthentication` + multi-token (`API_AUTH_TOKEN`/`API_AUTH_TOKENS` / `SWARM_API_KEY(S)`); prod (`DEBUG=False`) refuses boot without a token unless `SWARM_ALLOW_NO_AUTH`. Caveat: with `DJANGO_DEBUG=true` and no token, `ENABLE_API_AUTH` is false (open API) and `SwarmConfig` logs a serve-time warning (`apps.py` `_warn_if_api_auth_disabled`) |
| Operator session gates (Django WebUI) | ✅ | `@login_required` on teams admin/export, blueprint library browse+mutators, settings, sessions, creator mutators; public without session: landing SPA, `/teams/launch/`, `/profiles/`, agent-creator GET, login form. CSRF required on `custom_login` POST + library mutators (not `@csrf_exempt`) |
| Session Explorer operator bridge | ✅ | With `ENABLE_API_AUTH`, logged-in Django users see `user:<name>` **and** configured Bearer `token:<sha256-prefix>` sessions (`auth.explorer_owner_allows`); foreign `user:…` / unowned stay hidden; REST `/v1/responses` IDOR stays strict same-principal |
| Login open-redirect hardening | ✅ | `web_views._safe_post_login_redirect`: relative rooted paths only + `url_has_allowed_host_and_scheme`; rejects `//evil`, `\\`, absolute/external, bare relatives; `tests/views/test_web_views_security.py` |
| Creator toast DOM XSS escapes | ✅ | `team_creator.html` / `agent_creator_pro.js` escape untrusted names/errors/paths before `innerHTML`; `tests/views/test_creator_toast_xss.py` |
| User-blueprint AST sandbox | ✅ | `blueprint_sandbox.py` (default on; opt out `SWARM_USER_BLUEPRINT_SANDBOX=false`); discovery opt-in `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY`; creator saves `@login_required` + banned-snippet/AST gate |
| ChatMessage tenancy + prod security headers | ✅ | `message_views.py` scopes list to `conversation__student=request.user` when `ENABLE_API_AUTH`; token-only → empty qs. Prod-only (`DEBUG=False`): secure cookies (`SWARM_SECURE_COOKIES`). Always-on (Django defaults + middleware, debug and prod): `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY` (prod block reasserts / `DJANGO_X_FRAME_OPTIONS`). **No CSP.** Browser honesty: `swarm.core.browser_tools` + TROUBLESHOOTING §7 (no fake playwright success). |
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

This doc decays fast (a cleanup wave was rewriting the tree while it was generated). Before acting on any row, re-verify:

1. **Tests:** `uv run pytest -q` (full counts) and re-run any failing file in isolation.
2. **Entry points:** `uv run swarm-cli --help && uv run swarm-api --help && uv run codey --help && uv run suggestion --help`.
3. **Imports:** `uv run python -c "import swarm.blueprints.<name>.blueprint_<name>"` per blueprint; `import swarm.extensions.blueprint` (expected to fail until removed/fixed).
4. **SPA leftovers:** `grep -rn "fetch\|mock\|simulated" webui/frontend/src/pages/` — Teams/Blueprints fetch live with honest empty/error (no demo fixtures); Launch routes to `/chat?blueprint=…`. Canonical operator UI is Django (bare SPA paths redirect).
5. **Flags vs deps:** `grep -n "django-mcp-server\\|mcp_server" pyproject.toml docs/mcp_server_mode.md` — flag without a declared lockfile dependency stays 📋.
6. **Resolved:** `urls.py` imports `re_path` from `django.urls` (Django 4+); the old `django.conf.urls` import bug is gone.
