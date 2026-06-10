# Open Swarm Roadmap

Open Swarm is an agent framework — a derivative of OpenAI's experimental
[Swarm](https://github.com/openai/swarm) concept, since migrated to the
[openai-agents SDK](https://github.com/openai/openai-agents-python) — providing
blueprints (reusable multi-agent workflows), a Django REST API
(OpenAI-compatible `/v1/chat/completions`), CLI launchers, MCP integration, and
a web UI.

This roadmap is the single source of truth for project status. It supersedes
the older phase-based `TODO.md`. Per-feature evidence lives in
[FEATURE_STATUS.md](./FEATURE_STATUS.md) (re-verify rows before acting — it
goes stale fast).

## Status legend

| Mark | Meaning |
|------|---------|
| `[x]` | Done and shipped |
| `[ ]` | Not done / planned — partially-done parents stay unchecked, with checked sub-items showing progress |

Last updated: 2026-06-11 (post PR waves #80–#85; origin reduced to main; Docker-verified).

---

## 1. Done / Shipped

- [x] Core blueprint system (`src/swarm/core/`, `BlueprintBase`, discovery, config)
- [x] Django REST API with OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`)
- [x] Django templates/HTMx web UI — **this is the live, supported production UI**
  - ⚠️ Correction (2026-06-11): the websocket chat *consumer* exists but is **unroutable** — `settings.py` references `swarm.asgi.application` which does not exist, and `channels` is not in `INSTALLED_APPS`. See §2 ASGI item.
- [x] CLI entry points all working: `swarm-cli`, `swarm-api`, `codey`, `suggestion`
- [x] Test suite green: 857 passed / 2 skipped / 0 failed
- [x] Security hardening sprint (June 2026): command/SQL injection, open redirect, hardcoded passwords
- [x] **FOSS cleanup wave (2026-06-10):**
  - [x] `node_modules` (8,356 files / 69 MB) and `.letta/` untracked from git
  - [x] Packaging repaired: `uv sync`/`uv lock` work; phantom `langmem`/`papr` pins removed; `mem0` → `mem0ai`; entry-point typo; real URLs
  - [x] README rewritten as honest FOSS-product doc (only verified features documented)
  - [x] Dead code removed: 8 orphaned blueprints + `repl/`, `agent/`, `llm/`, `cli/`, duplicate builders
  - [x] Consolidation: 5 spinners → 1, 2 config loaders → 1, ANSI boxes → 1, import-broken `extensions/blueprint` → deprecation shims (see §2.1 sunset)
  - [x] Production-safe defaults: `SECRET_KEY` required outside debug, `DEBUG` off by default, `ALLOWED_HOSTS` required in prod
  - [x] Auth bypass elimination: `testuser`/`testpass` auto-login removed (now `ALLOW_TESTUSER_AUTOLOGIN` + debug only, random password); API auth required to boot in production; `runserver` auth-on by default; CSRF restored on mutating endpoints; `.env.example` fully documented
  - [x] Security branches merged: open-redirect validation, `secure_subprocess` wrapper, CSRF agent/team creator
  - [x] Frontend repaired: lockfile in sync (`npm ci` works), type-check green (36 TS errors fixed), build green
  - [x] React SPA wired to real APIs: BlueprintsPage on `/v1/blueprints/`, dashboard on live counts, zero mock data remains
  - [x] Memory wired into the agent loop (opt-in `MemoryBackend` protocol, mem0 backend, graceful degradation, 11 tests)
  - [x] Bug fixes found en route: Django-4 `re_path` import (broke 59 tests when frontend built), SPA fallback `TypeError` on every non-root route, Pagination duplicate key / undefined `totalPages`
  - [x] Docs: ROADMAP.md, FEATURE_STATUS.md (58 evidence rows), USER_JOURNEY.md (7 Playwright screenshots + regeneration script), CHANGELOG entry
  - [x] Tests: 616 → 713 (archive salvage ports, auth-hardening guards, shim identity locks, memory integration)

---

## 2. Nearly Done — finish-first list

- [ ] **Remote branch hygiene (needs repo-owner action on GitHub)**
  - [x] Triage all 84 unmerged branches (44 superseded/duplicate → delete; ~28 still merge-worthy; 12 stale-diverged)
  - [x] Merge top 3 security branches
  - [x] Delete superseded/duplicate branches on origin (all done — origin now has only main)
  - [x] Merge the remaining merge-worthy branches — 16 merged (test-coverage set + GitHubClient/models-package refactor); session-poisoning sys.modules mocks in three of them rewritten
  - [x] Review `refactor-wip` (368 commits): verdict — nothing worth salvaging (2 nice-to-haves documented in the review: GitHub CLI discovery, compile_blueprint command); safe to archive/delete on origin
  - [x] Push the local cleanup-wave commits to origin (squashed; granular log in docs/archive/)
- [x] **Login routing** (found while capturing USER_JOURNEY screenshots)
  - [x] `custom_login` view exists (`src/swarm/views/web_views.py`) but has **no URL pattern** — `/accounts/login/` 404s; routed `accounts/login/` (name `login`, Django default) and `login/` (name `custom_login`, matches `settings.LOGIN_URL`); locked by `tests/views/test_login_routing.py`
  - [x] `/webui/` route 500s (`TemplateDoesNotExist: webui/index.html`) — `WebUIView` now redirects to `/` (kept for backward compat; the old `webui/index.html` template no longer exists)
- [x] **Finish archive salvage**: async API tests ported (`tests/api/`, 22 tests)
- [x] **Blueprint test collection**: in-tree `test_basic.py` files moved to `tests/blueprints/` and fixed (flock, chucks_angels, digitalbutlers — now collected and green)
- [x] **Naming/metadata debt**
  - [x] stewie module renamed `blueprint_family_ties.py` → `blueprint_stewie.py` (rename also FIXED discovery — stewie was invisible to the blueprint scanner); `family_ties/` forwarder deleted
  - [x] `blueprint_audit_status.json` deleted (fake metadata, zero consumers)

- [x] **ASGI routing for websocket chat** — `swarm/asgi.py` + `routing.py` created; daphne/channels registered (they were declared core deps all along, never wired); 9 full-stack tests; live-verified 101 upgrade with session auth, 403 anonymous/bad-origin (`docs/websocket_chat.md`)

### 2.1 Deprecation shim sunset

The consolidation left 7 import shims emitting `DeprecationWarning`
(`extensions/blueprint/{__init__,spinner,slash_commands}`,
`extensions/config/config_loader`, `blueprints/common/spinner`, `ux/spinner`,
`utils/ansi_box`). Locked by `tests/unit/test_deprecation_shims.py`.

- [x] Migrate remaining internal callers off shim paths (`views/settings_manager.py` → core config_loader; also fixed a broken `extensions.blueprint.discovery` import in `core_views.py`)
- [ ] Remove the shims in the release **after** the first tagged FOSS release

---

## 3. Far From Done — documented as roadmap, not current state

### 3.1 React/DaisyUI SPA (`webui/frontend`)

Status: build/type-check green, real API data, no mock data — but feature
coverage is thin. The Django templates/HTMx UI remains the supported UI until
parity is reached.

- [ ] React SPA reaches functional parity with Django UI
  - [x] Component library (13 DaisyUI/React components)
  - [x] Vite + TypeScript + Tailwind/DaisyUI build setup; lockfile in sync
  - [x] BlueprintsPage wired to `/v1/blueprints/` (react-query; loading/error/empty states)
  - [x] Dashboard on live blueprint/model counts; fabricated stats removed
  - [x] TeamsPage honestly reports the missing Teams API (no mock data)
  - [x] **JSON Teams API** — `/v1/teams/` list/create/delete endpoints (`views/teams_api.py`, tested) and TeamsPage wired via react-query
  - [x] Auth flow: token entry in Settings, localStorage persistence, 401/403 banner — no login wall on auth-disabled deployments
  - [x] ChatPage built (blueprint selector, streaming UI, parser for the server's HTMx ws partials) — **blocked on backend ASGI routing** (see §2); shows an honest 'unavailable' state until then
  - [x] Agent-creator and settings pages (PR #80: generate/validate/save flow, custom-blueprint CRUD, server-settings/env panels with masking)
  - [ ] Replace Django template pages page-by-page once each SPA page is wired
  - [x] Resolved npm audit advisories: vite 5 → 8 (PR #84), 0 vulnerabilities

### 3.2 Memory integration (mem0 / letta / langmem)

- [ ] Memory production-ready
  - [x] Backends scaffolded as optional extras (`mem0ai` resolves and installs)
  - [x] Wired into the agent loop: opt-in per-blueprint `memory` config block; retrieval injected pre-run, conversation stored post-run; no-op when unconfigured
  - [x] End-to-end validation against a real mem0 instance: opt-in `tests/integration/test_memory_mem0_e2e.py` (skips unless `RUN_MEM0_E2E=1` + `OPENAI_API_KEY`; local qdrant + sqlite under tmp_path). 2026-06-11 real run: mem0ai 2.0.4 initialized and the store cycle reached OpenAI embeddings, but the repo `.env` key is revoked (401) — full green pass pending a valid key
  - [ ] letta/langmem backends (placeholder modules raising clear errors today)
  - [ ] Decide on a default backend and document configuration in CONFIGURATION.md

### 3.3 MCP server mode (`ENABLE_MCP_SERVER`)

- [ ] Functional MCP server hosting blueprints as tools
  - [x] URL routing behind the flag
  - [x] `provider.py` executes blueprints with passing tests (stale TODO docstring corrected)
  - [ ] Declare the `django_mcp_server` dependency (not in `pyproject.toml` — the mount is dead on a clean install)
  - [ ] Auth story for MCP clients (token-based)

### 3.4 Marketplace/Wagtail (`ENABLE_WAGTAIL`) and SAML IdP (`ENABLE_SAML_IDP`) — REMOVED

- [x] **DECISION MADE (2026-06-11): drop both — executed 2026-06-11.** Removed `swarm/marketplace/` (Wagtail app), Wagtail/SAML blocks in settings.py + urls.py, wagtail/taggit/modelcluster pins from pyproject, the Wagtail-backed `MarketplaceBlueprintsView`/`MarketplaceMCPConfigsView` + routes, SAML env getters and `tests/unit/test_settings_saml.py`, and the wagtail/saml docs
  - [x] GitHub-topics discovery kept: service moved to `swarm/services/github_topics_service.py`; `Marketplace*GitHub*` endpoints and `ENABLE_GITHUB_MARKETPLACE` flag unchanged (`docs/github_marketplace.md`)
  - [x] Stewie blueprint reviewed: no Wagtail coupling; works as a normal blueprint (its optional Django-app self-registration in `blueprints/stewie/settings.py` is independent of Wagtail)

### 3.5 Blueprint ecosystem rationalization (17 remaining blueprints)

- [x] Delete the 8 orphaned blueprints (done 2026-06-10)
- [ ] Curate a flagship set — candidates: `codey`, `geese`, `jeeves`, `zeus`, `suggestion`, `whinge_surf`, `rue_code`, `poets`
- [ ] Test coverage for retained blueprints (most still lack collected tests; see §2 blueprint-test-collection item)
- [ ] Demote or archive non-flagship blueprints to an examples/contrib area
- [ ] Restore or formally drop legacy CLI commands old docs reference (`wizard`, `config`, `add`)

### 3.6 Release engineering

- [ ] First tagged FOSS release on PyPI
  - [x] Fix publish workflow: old workflows deleted (one published to REAL PyPI on every main push with timestamp versions!); new `publish.yml` is release/tag-driven with manual dispatch, version from pyproject
  - [x] CI tests Python 3.10/3.11/3.12 via uv, with `uv lock --check` guarding against phantom pins
  - [x] CONTRIBUTING.md added (honest: references only scripts that exist; lint scoped to touched files)
  - [x] License headers / NOTICE decision: **NOTICE file instead of per-file headers** (decided 2026-06-11). `NOTICE` covers the MIT grant, OpenAI Swarm/openai-agents attribution, and vendored static assets (marked.js, Tabler Icons, Font Awesome webfonts); linked from README's License section
  - [ ] Cut the actual first release (tag, release notes from CHANGELOG)
