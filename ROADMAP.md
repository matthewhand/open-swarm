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

Last updated: 2026-06-19 (v0.5.1 on PyPI; CLI Agent Fusion + async + persona councils + recursion shipped).

---

## 0. Current release — v0.5.1 (on PyPI)

The first tagged FOSS releases shipped: **v0.3.0 → v0.4.x → v0.5.0 → v0.5.1** are
live on PyPI (`pip install open-swarm`). Highlights since the 2026-06-11 snapshot:

- [x] **CLI Agent Fusion line** shipped & tagged (was §3.5b/§3.6 "publish pending"):
  `cli_agent`, `cli_fusion`, `cli_orchestrator`, `cli_map`, plus MAF-class
  `cli_pipeline`/`cli_roundtable`/`cli_planner`, and recursive `cli_recurse`.
- [x] **Canonical `swarm_*` names** for the orchestration patterns (`swarm_ensemble`,
  `swarm_recurse`, …); `cli_*` kept as aliases. `cli_fusion`→`cli_ensemble`.
- [x] **Async tasking** — `/v1/responses` + `/v1/chat/completions` `background:true`
  (queued→poll→cancel, restart-durable), `system_fingerprint` provenance.
- [x] **Persona councils** (`persona_council`) — diverse-lens consensus.
- [x] **Community-blueprint discovery foundation** — external roots + `SWARM_BLUEPRINT_PATHS`.
- [x] **Docker** — API-only base compose + opt-in CLI mapping override.
- [x] **First tagged release + PyPI publish** (was §3.6 open).
- [x] **Memory configuration documented** in CONFIGURATION.md §9 (mem0 default) (was §3.2 open).

Still open (see below + new items): SPA↔Django parity, MCP-server dependency,
letta/langmem backends, blueprint ecosystem curation, deprecation-shim sunset,
and **CLI command-registration cruft** (many `swarm-cli` aliases declared but
"not found or not callable" — only `list`/`wizard`/`install` work cleanly).

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

- [x] **Non-streaming `/v1/chat/completions` test-mode bug FIXED** — chunk normalizer consumes the whole generator and returns the final message (was: first spinner chunk). Per-blueprint API smoke matrix added (`tests/api/test_blueprint_api_smoke.py`): 13 blueprints verified answering on BOTH streaming and non-streaming surfaces (was: only zeus). Former xfail RESOLVED: `whiskeytango_foxtrot` now yields a canned `[TEST-MODE]` answer early in run() instead of hanging — all 14 blueprints pass the smoke matrix.

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
  - [x] Decide on a default backend and document configuration in CONFIGURATION.md — **DONE** (mem0 default, CONFIGURATION.md §9)

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

### 3.4b CLI command-registration cruft (NEW — found 2026-06-19)

`swarm-cli` discovery emits a wall of `Warning: Execute function for alias 'X'
not found or not callable. Skipping.` on every invocation (config, add, delete,
edit-config, validate-env, validate-envvars, …). Only `list`, `wizard`, and
`install` resolve cleanly; `swarm-cli config` errors `invalid choice`.

- [ ] Prune the dead alias registrations (or wire their `execute` functions)
- [ ] Silence the per-invocation warnings for unregistered aliases
- [ ] Reconcile docs to the commands that actually work

### 3.5b CLI Agent Fusion (v0.4.0 feature line)

Turns the agentic CLIs an operator already has installed (`claude`, `gemini`,
`codex`, `opencode`, …) into one-shot, OpenAI-API-addressable subagents, composed
four ways: single (`cli_agent`), consensus panel (`cli_fusion`), granular
consensus (`cli_orchestrator`), and decompose-and-distribute (`cli_map`). Full
design in [docs/CLI_FUSION.md](./docs/CLI_FUSION.md). Built as a PR series in the
commit log; version bumped to 0.4.0.

- [x] CLI Agent Fusion built for v0.4.0 (code complete; tag + PyPI publish pending)
  - [x] Foundation: `CliAdapter` one-shot layer + `cli_agent`/`cli_fusion` blueprints
  - [x] Install + auth autodiscovery: `swarm-cli cli-agents` (`--check-auth`/`--smoke`/`--suggest`/`--json`)
  - [x] Full-capability panelists (auto-approve) + per-panelist workdir isolation (git worktree / temp dir)
  - [x] Built-in adapter catalog with per-CLI gotchas baked in (gemini `--skip-trust`, opencode `--model`)
  - [x] Incremental streaming (`cli_agent`) + failover/graceful degradation
  - [x] Reusable `swarm.core.consensus` service (consensus-first synthesis) + `swarm.core.cli_tools` agent-tool layer (`as_tool()`)
  - [x] `cli_orchestrator` (granular consensus) + `cli_map` (decompose → distribute → reduce) blueprints
  - [x] End-to-end API coverage; verified live over claude+gemini+opencode
  - [ ] Tag `v0.4.0` + PyPI publish (manual release step — owner action)

### 3.6 Release engineering

- [x] First tagged FOSS release on PyPI — **DONE**: v0.3.0 → v0.5.1 all published
  - [x] Fix publish workflow: old workflows deleted (one published to REAL PyPI on every main push with timestamp versions!); new `publish.yml` is release/tag-driven with manual dispatch, version from pyproject
  - [x] CI tests Python 3.10/3.11/3.12 via uv, with `uv lock --check` guarding against phantom pins
  - [x] CONTRIBUTING.md added (honest: references only scripts that exist; lint scoped to touched files)
  - [x] License headers / NOTICE decision: **NOTICE file instead of per-file headers** (decided 2026-06-11). `NOTICE` covers the MIT grant, OpenAI Swarm/openai-agents attribution, and vendored static assets (marked.js, Tabler Icons, Font Awesome webfonts); linked from README's License section
  - [x] Cut the actual first release (tag, release notes from CHANGELOG) — through v0.5.1

---

## 4. Critique findings — multi-agent audit (2026-06-19)

A read-only fan-out audited the web UI, end-to-end workflows, code/repo
structure, and cruft. Findings below are prioritized; each cites `file:line`.
Bright spots confirmed: the `/v1/responses` async engine, the `swarm-cli
cli-agents --init/--check-auth/--suggest` flow, the OpenAPI-served REST surface,
USERGUIDE.md accuracy, and the `cli_*` family's test coverage.

### 4.1 Security (do first)
- [ ] **XSS / secret leak:** `templates/settings_dashboard.html:567`
  `let settingsData = {{ settings_groups|safe }}` injects server settings
  (incl. values flagged `sensitive`) unescaped into a `<script>`. Use
  `json_script` + server-side redaction.
- [ ] **Unauthed web save + unsandboxed exec:** `views/agent_creator_views.py`
  `save_custom_agent`/`save_team_swarm` are POST-only (no `login_required`); the
  generated blueprints (which can carry `execute_shell_command`/`write_file`)
  are `exec_module`'d by discovery unsandboxed.

### 4.2 Broken-but-shipped (erodes trust)
- [ ] **`django_chat` is a stub** — `blueprints/django_chat/blueprint_django_chat.py:200-221`
  never calls an LLM (`"[DjangoChat LLM] Would respond to: …"`). Implement or label demo.
- [ ] **Web create→run loop is broken** — `save_custom_agent`/`save_team_swarm`
  (`agent_creator_views.py:431-453,773-792`) and `blueprint_creator`
  (`blueprint_library_views.py:473-530`) save to a relative `user_blueprints/` /
  JSON catalog that discovery never scans (`views/utils.py`, XDG dir). Nothing
  built in the web UI is runnable. Point saves at `get_user_blueprints_dir()`.
- [ ] **Agent Creator Pro is non-functional clickware** — route exists
  (`urls.py:127`) but no generate/validate/save routes and the JS handlers are
  undefined (`agent_creator_pro.html`). Finish or hide behind a flag.
- [ ] **Fake buttons (Django UI):** `my_blueprints.html:445-463` "Run Blueprint"
  is a `setTimeout` simulation; `settings_dashboard.html:661-672`
  Validate/Check/Export only toast "coming soon"; `team_creator.html:341`
  validation is a no-op demo toast. Wire or remove.
- [ ] **SPA `loading` button shows no spinner (DaisyUI 5)** —
  `components/DaisyUI/Button.tsx:56` uses the bare `loading` class (removed in
  v5; needs a `loading-spinner` span). Every mutating action lacks feedback.
  Also dead `active`/`disabled` variants (`:8,38`).

### 4.3 Docs-vs-reality (breaks onboarding)
- [ ] **Docs instruct nonexistent CLI commands** — QUICKSTART (`swarm-cli llm add`,
  `config add`, `config validate`) and CONFIGURATION.md (`configure`,
  `list-config`, `set`, `config init`) reference commands the shipped
  `swarm.core.swarm_cli:app` (`list`/`wizard`/`install`/`cli-agents`/`skills`/…)
  does not have. The config loader's own error hints do too
  (`config_loader.py:113,144,157`). Rewrite docs to the real commands (or wire a
  `config`/`llm` group). [partially started: QUICKSTART §6/§7 fixed 2026-06-19]
- [ ] **`install` misdescribed** — QUICKSTART §2 says "downloads"; it actually
  runs PyInstaller to compile a binary (`swarm_cli.py` `install_executable`).
- [ ] **swarm-cli dead-alias warnings** — see 4.4 (orphaned `extensions/cli/main.py`).

### 4.4 Dead code / parallel trees
- [ ] **`extensions/` vs `core/` parallel CLI trees (~700 LOC)** — `swarm-cli`→`core`,
  `swarm-api`→`extensions.launchers` (opposite trees); two tests import the
  non-shipped `extensions.launchers.swarm_cli`. Pick `core/`, repoint `swarm-api`,
  delete `extensions/launchers` + `extensions/cli`.
- [ ] **`extensions/cli/main.py` orphaned** — unreferenced; source of the
  "Execute function for alias 'X' not found" warnings (8/11 aliases lack
  `execute`). Delete. (supersedes §3.4b)
- [ ] **Dead view+template:** `views/web_views.py:122` `blueprint_webpage` (no URL)
  + its only template `templates/simple_blueprint_page.html`. Delete both.
- [ ] **Unrendered `templates/chat.html`** (only a `routing.py:6` docstring) + ~8
  orphaned `templates/rest_mode/*` files. Delete.
- [ ] **`stewie` ships a broken nested Django app** — `blueprints/stewie/{settings,views,serializers,models}.py`
  import a nonexistent `blueprints.chc`. Fix paths or delete.

### 4.5 Structure
- [ ] **God-modules:** `blueprints/codey/blueprint_codey.py` (1021 lines),
  `core/blueprint_base.py` (919 lines, 35 methods — memory/approval/config all
  inlined). Extract `MemoryMixin`/`ApprovalMixin`/`ConfigResolver`; pull
  `CodeySpinner`/`DummyTool` into shared infra.
- [ ] **Spinner reimplemented ≥13×** and **`ansi_box` duplicated & divergent**
  (`utils/ansi_box.py` 23 lines vs `ux/ansi_box.py` 42). Consolidate to one `ux/`.
- [ ] **Blueprint metadata inconsistent** — `name`≠dirname in 9 blueprints;
  3 declaration styles (`ClassVar`, bare, `@property`); absent in `gawd`/`geese`/
  `whinge_surf`/`zeus`; no machine-readable `category`. Define a schema +
  discovery-time validator (CI-enforced).
- [ ] **`urls.py` REST inconsistency** — hand-duplicated slash/no-slash route
  pairs, mixed CBV/FBV, 4 auth styles. Adopt a DRF router for `v1/*` resources.
- [ ] **9 `cli_*` deliberation blueprints overlap** — a strategy family as 9
  top-level blueprints. Consider one blueprint + `strategy` param, or a shared base.

### 4.6 UX / SPA (medium)
- [ ] **Toast a11y + duplication** — `components/DaisyUI/Toast.tsx:98` no
  `aria-live` (primary feedback is SR-invisible); `ToastProvider` triple-nested
  (App + 3 pages).
- [ ] **Modal triple focus/dismiss** — native `<dialog>` + `focus-trap-react` +
  manual backdrop math (`Modal.tsx:84-105`); pick one.
- [ ] **ChatPage gaps** — no auto-reconnect (`:115`), single-line composer
  (`:324`), no markdown/code rendering (`:301`).
- [ ] **BuilderPage** titled "Builder" but read-only (no save); no list filter.
  **AgentCreator** code field is a plain textarea (no editor); custom cards offer
  only Delete (dead end).
- [ ] **Django legacy surface off-brand/broken** — Bootstrap CDN (offline breaks),
  `profiles.html` uses DaisyUI classes on a Bootstrap base (unstyled),
  `base.html` missing `title`/`head` blocks. Decide retire-vs-migrate.

### 4.7 API + tests
- [ ] **`/v1/responses` missing trailing-slash twin** (`urls.py:91`) — `…/responses/` 404s.
- [ ] **Silent model fallback** — unknown `default_model` silently uses `default`
  (`config_loader.py:303-304`, DEBUG-only log). Warn or 400.
- [ ] **`/v1/teams/` oversold** — only `{name, description, llm_profile}`, an LLM-
  profile alias, not a team builder (`teams_api.py:51-120`). Relabel or extend.
- [ ] **Zero test coverage:** `stewie`, `whinge_surf` (both have real `run()`).
