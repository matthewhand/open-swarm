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
| WebSocket chat consumer | ✅ | ROUTED 2026-06-11: `swarm/asgi.py` (ProtocolTypeRouter + AuthMiddlewareStack + origin validator) + `swarm/routing.py` (`ws/ai-demo/<id>/`); daphne+channels in INSTALLED_APPS; 9 tests (`tests/test_asgi_routing.py`) incl. authenticated streamed round-trip; live 101 under daphne |

## 4. Web UI — Django templates + HTMx — ✅ 5 · ❌ 3

| Feature | Status | Evidence |
|---|---|---|
| Index/dashboard | ✅ | `views/core_views.py:34-36` renders `swarm/index.html`; covered by `tests/views/test_web_views.py::TestIndexView` (passes in isolation) |
| Teams (launch/admin/export) | ✅ | `urls.py:68-71` → `team_launcher`/`team_admin`/`teams_export`; renders `teams_launch.html` (`web_views.py:244`), `teams_admin.html` |
| Blueprint library (+ my-blueprints) | ✅ | `views/blueprint_library_views.py:186-242` renders `blueprint_library.html`, JSON persistence at `:155-183`; routes `urls.py:89`; `tests/views/test_blueprint_library_views.py` |
| Agent creator (+ pro) | ✅ | `urls.py:74-81` → generate/validate/save endpoints in `views/agent_creator_views.py`; `agent_creator_pro.py` |
| Settings dashboard | ✅ | `urls.py:83-85` → `views/settings_views.py:28-57` renders `settings_dashboard.html` |
| `chat.html` | ❌ | Dead template — zero references: `grep -rn "chat.html" src/swarm --include="*.py"` returns nothing (only `templates/chat.html` itself, which contains the repo's only htmx attrs) |
| `simple_blueprint_page.html` | ❌ | Only renderer is `web_views.py:121-140` `blueprint_webpage()`, which is **not routed** — `blueprint_webpage` absent from `urls.py`. Dead view + dead template |
| SPA fallback / asset serving | ✅ | FIXED in `f1fa20b1`: `urls.py:155` now `from django.urls import re_path` (was `django.conf.urls`, removed in Django 4.0 — broke whenever `webui/frontend/dist` existed). `tests/views` + `tests/mcp` green (169 passed) with dist present |

## 5. Web UI — React SPA (`webui/frontend`) — 🔲 1 · ❌ 3

| Feature | Status | Evidence |
|---|---|---|
| DaisyUI component library | 🔲 | 13 components built (`src/components/DaisyUI/*.tsx`: Alert, Badge, Button, Card, FormValidation, Input, Loading, Modal, Pagination, Select, Tabs, Textarea, Toast; 13 exports in `index.ts`); builds to `dist/`, but consumed only by mock pages below |
| TeamsPage | ❌ | Potemkin: hardcoded fixture only — `src/pages/TeamsPage.tsx:6` `const mockTeams = [...]`, `:48` `useState(mockTeams)`; zero `fetch`/`axios` calls in file |
| BlueprintsPage | ❌ | Potemkin: `src/pages/BlueprintsPage.tsx:6` `const mockBlueprints = [...]`, `:70` `useState(mockBlueprints)`; no network calls, no `useEffect` data load |
| API / auth / websocket integration | 🟡 | UPDATED 2026-06-11: typed api client (`src/lib/api.ts`), react-query on /v1/blueprints//models//teams/, token auth UX (SettingsPage + 401 banner), ChatPage speaking the ws protocol — ws blocked on missing backend ASGI routing (honest fallback shown) |

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
| MCP server provider (blueprints as tools) | 🟡 | `src/swarm/mcp/provider.py:84-137` `call_tool` now really instantiates and runs blueprints (starts/stops required MCP servers, `_run_blueprint_sync` at `:206`); tests `tests/mcp/test_provider_execute.py`, `test_provider.py`, `test_provider_edge_cases.py` pass. Caveat: docstring at `provider.py:38` still says real execution "is a TODO" (stale), and the provider is only reachable via the unshipped server below |
| MCP server mount (`ENABLE_MCP_SERVER`) | 📋 | `settings.py:165-171` appends `django_mcp_server` to INSTALLED_APPS, `urls.py:139` mounts `mcp/` — but `django_mcp_server` is **not declared anywhere in pyproject.toml** (grep: no match); `mcp/integration.py:20-23` import-guards it and returns 0 tools when absent. Flag without a dependency |

## 8. Feature-flagged integrations — ✅ 1 · 🗑 2

| Feature | Status | Evidence |
|---|---|---|
| GitHub marketplace discovery | ✅ | `ENABLE_GITHUB_MARKETPLACE` in `settings.py` (topics/org allowlist envs); `src/swarm/services/github_topics_service.py` real GitHub API calls; `marketplace/github/*` routes in `urls.py`; `tests/services/test_github_topics_service.py` passes |
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

## 10. Security — ✅ 2 · 🟡 2

| Feature | Status | Evidence |
|---|---|---|
| Codey command-injection fix | ✅ | `blueprint_codey.py:933-937` parses with `shlex.split` instead of shell string (commit `2e2ee426` "Fix Command Injection in Codey blueprint") |
| Sensitive-data redaction | ✅ | `swarm/utils/redact.py`; tests `tests/core/test_redact_sensitive_data.py`, `tests/unit/test_redact*.py` (3 files) pass; marketplace scrubs secrets via `SECRET_PATTERNS` (`marketplace/models.py:20-26`) |
| API auth (static token / session) | 🟡 | `auth.py:25` `StaticTokenAuthentication`, permission `auth.py:110-135`; `settings.py:40-45` `ENABLE_API_AUTH = bool(SWARM_API_KEY)`. Caveat: when `SWARM_API_KEY` is unset, DRF default permission falls back to `AllowAny` (`settings.py:261-268`) — API is open by default |
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

## Regeneration

This doc decays fast (a cleanup wave was rewriting the tree while it was generated). Before acting on any row, re-verify:

1. **Tests:** `uv run pytest -q` (full counts) and re-run any failing file in isolation to separate real breakage from the `urls.py:155` ordering bug.
2. **Entry points:** `uv run swarm-cli --help && uv run swarm-api --help && uv run codey --help && uv run suggestion --help`.
3. **Imports:** `uv run python -c "import swarm.blueprints.<name>.blueprint_<name>"` per blueprint; `import swarm.extensions.blueprint` (expected to fail until removed/fixed).
4. **Potemkin check (SPA):** `grep -rn "mock\|fetch\|axios" webui/frontend/src/pages/` — rows flip from ❌ only when real API calls replace the `mock*` constants.
5. **Flags vs deps:** `grep -n "django_mcp_server" pyproject.toml` — a flag without a declared dependency stays 📋.
6. **Known bug to re-check first:** `src/swarm/urls.py:155` (`from django.conf.urls import re_path` — invalid on Django ≥4.0; fix is `from django.urls import re_path`).
