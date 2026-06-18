# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.5.1] — 2026-06-19

### Added — Docker
- API-only base `docker-compose.yml` (the gateway serving the REST surface; CLIs are host-bound and opt-in) plus a rewritten `docker-compose.override.example.yml` catalog of per-CLI mount blocks.

### Added — `cli_recurse` (recursive divide & conquer)
- New blueprint that breaks a problem down to **any depth**: each node decides to solve directly or split into sub-problems, and every sub-problem is handed to a **freshly-instantiated child of the same blueprint** — recursing until each leaf is atomic, then synthesizing back up. Three limiters keep it finite: `max_depth`, `max_subproblems` (fan-out width), and `max_nodes` (a shared global budget; once spent, remaining nodes solve directly). Config block `cli_recurse` (decomposer/solver/synthesizer + limits), falls back to `cli_fusion`. The recursive generalization of `cli_map`'s single-level decompose.

### Changed — `cli_fusion` → `cli_ensemble` (canonical rename, alias kept)
- The multi-CLI deliberation blueprint is now published as **`cli_ensemble`** (ML-standard "ensemble" / Mixture-of-Agents terminology). **`cli_fusion` still works** as a back-compat model alias with identical behavior, and the shared `cli_fusion` config block / `cli_fusion_support` internals are unchanged (used family-wide). Renamed to avoid colliding with OpenRouter's "Fusion" — which is a *tool a model invokes*, the inverse of ours (the panel *is* the endpoint).

### Added — Community blueprints (discovery foundation)
- Blueprint discovery now scans **external roots** in addition to the bundled set: the user data dir `$XDG_DATA_HOME/swarm/blueprints` (where community packs install) plus any paths in `SWARM_BLUEPRINT_PATHS`. External roots load under a synthetic module namespace so they can't shadow or collide with `swarm.blueprints`; the bundled set always wins on name collisions. New `merge_community_blueprints()` / `discover_all_blueprints()` in `swarm.core.blueprint_discovery`. This is the foundation for installing community blueprint packs from GitHub (explicit opt-in; running third-party blueprint code is a code-execution trust decision).

## [0.5.0] — 2026-06-19

### Removed — Dead code cleanup (pre-release)
- Deleted the non-functional `digitalbutlers` and `flock` blueprint stubs (empty placeholder classes, superseded by `jeeves`) and the orphaned `services/monitor.py` fixture, along with their trivial import/shell tests. No functional blueprint or production path referenced them.

### Added — Persona councils (diverse-lens consensus)
- **`persona_council`** blueprint: examine one question through a council of distinct **expert lenses** (each a system-prompt persona) in parallel, then a judge reconciles agreement, tensions, and a synthesized position. Consensus from *perspective diversity*, not redundant runs. Built-in councils — `ethics` (Utilitarian/Kantian/Virtue/Rawlsian/Care), `science`, `psych`, `decision`, `red_team` — work with zero config; select via `params.council`, pass an explicit `personas` roster, or define your own in a `persona_council` config block. The published persona names stay generic but the lens prompts **channel the actual thinkers** (Mill, Kant, Rawls, Feynman, Munger, Schneier, …) for sharper, more distinct voices. Verified live. The bundled persona blueprints are reframed as *examples* of this composition system.

### Added — Docs (deployment-ready)
- **[docs/EXAMPLES.md](docs/EXAMPLES.md)** — every recipe in two sections: **Team examples** (consensus blueprints + persona councils, curl for each) and **CLI + REST config** (wiring `cli_agents`, `llm` profiles, and the mix). README gains an **Architecture** section with two diagrams (the dispatch flow and the consensus-invocation spectrum) linking out to the examples + [ORCHESTRATION_PATTERNS.md](docs/ORCHESTRATION_PATTERNS.md).

### Added — Async tasking (`/v1/responses` background mode)
- Fire-and-forget for long-running agent work: `POST /v1/responses` with `"background": true` returns **202** immediately with a `resp_<id>` and `status: "queued"`; the blueprint runs in a daemon worker that updates the file-backed store `queued → in_progress → completed/failed` with `execution_ms`/`started_at`. Poll via `GET /v1/responses/{id}`; completed results carry `output_text`/`system_fingerprint`/`usage` and are chainable via `previous_response_id`. Sync behavior unchanged when `background` is absent. Also wired per-request `params` into `/v1/responses`. See **[docs/ASYNC_RESPONSES.md](docs/ASYNC_RESPONSES.md)**.
- **Cancellation:** `POST /v1/responses/{id}/cancel` — cooperative cancel, `status → cancelled` (idempotent on finished tasks).
- **Restart durability:** queued/in-progress tasks persist a spec and **resume** on server startup (at-least-once).
- **No-auth opt-out:** `SWARM_ALLOW_NO_AUTH=true` lets the server boot in production without `API_AUTH_TOKEN` (for when an external OAuth/gateway layer gates access) — warns loudly instead of refusing.
- **Fast-path sync vs queued (auto-escalation):** `max_wait_seconds` (per request) or `SWARM_RESPONSES_SYNC_TIMEOUT` (server default) make `/v1/responses` return the result inline if it beats the deadline, else a queued handle to poll — the task keeps running either way. No deadline = classic blocking sync.

### Added — Orchestration patterns (MAF-class, over CLIs)
- Three new orchestration blueprints complete the field-standard pattern set over heterogeneous agentic CLIs: **`cli_pipeline`** (sequential — each stage refines the prior stage's output, draft → review → polish), **`cli_roundtable`** (group-chat — debaters react to each other in a shared transcript across bounded rounds, a moderator concludes and synthesizes), and **`cli_planner`** (Magentic-One — a planner keeps a task ledger, delegates to workers, and re-plans on stall until the goal is met). All follow the existing `BlueprintBase` + `cli_fusion_support` conventions, degrade gracefully on a dead backend, and are auto-discovered at `/v1/models`. 20 new tests.
- New docs: **[docs/VISION.md](docs/VISION.md)** (front-and-centre vision + honest built-vs-remaining) and **[docs/ORCHESTRATION_PATTERNS.md](docs/ORCHESTRATION_PATTERNS.md)** (GitHub Mermaid sequence diagrams for all seven patterns). Live cross-CLI transcripts (consensus, routing, tool calling) under `docs/proofs/`.

### Added — Skills
- Reusable **skills**: `SKILL.md` directories (Anthropic [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) open standard) discoverable via `swarm-cli skills` (`--show`/`--json`) and applied to any CLI with the `cli_agent` `skill=<name>` param. Applying a skill prepends its instructions and stages any bundled assets into the workdir so a write-mode CLI can execute them.
- Bundled skills: `conventional-commit`, `reviewing-code`, `writing-changelog`, and `counting-lines` (ships an executable `count.py`).
- Verified live across gemini + `claude -p` + grok: skill portability (3/3) and bundled-asset tool calling (2/2). See `docs/examples/`.

### Added — Inference profiles (decouple blueprints from models)
- A blueprint can declare *what kind of thinking it wants* — `intelligence`, `speed`, `cost` as 0–1 targets (`inference_profile`) — instead of naming a CLI. Backends carry capability traits, **per-provider** (`cli_catalog.CLI_TRAITS`) and **per-model** (`MODEL_TRAITS`, overridable via a config `models` block); the closest backend is chosen by **distance-from-ideal** over only the axes the blueprint specifies. Opt-in `profile=` param resolving to a `cli` or `cli@model`; precedence: explicit `cli` > `default_cli` > `profile`. Live routing verified (deep-reasoning → claude, fast&cheap → gemini, balanced → opencode). See `docs/examples/inference-profile-routing.md`.

### Added — Tool capabilities endpoint + playwright-mcp
- `GET /v1/blueprints/<id>/tools` resolves a blueprint's `tool_requirements` to concrete MCP providers. Official **microsoft/playwright-mcp** added to the catalog (non-auth `browser`), auto-provisioned for blueprints needing it (jeeves, whiskeytango_foxtrot); verified live (23 browser tools).

### Added — Web UI Builder config panels
- The Builder gained four config panels bound to `GET /v1/config-options/`: **inference profile** (live resolve preview), **per-model trait editor**, **tool capabilities/MCP** (non-auth preferred), and a **skills picker** (with SKILL.md preview). Each snippet has Copy/Download; selected blueprints show a "resolved MCP" badge; accessible header tooltips. 0 axe violations; Playwright e2e. See `docs/examples/webui-config-panels.md`.

### Added — Tool capabilities (decouple blueprints from MCP providers)
- A blueprint can declare an abstract tool capability and whether it's mandatory/optional (`tool_requirements`) instead of naming a server. `swarm.core.tool_capabilities` resolves each capability to a configured MCP provider, **preferring non-auth providers**; unmet optional needs never block. `suggest_mcp_config()` emits a ready-to-paste, keyless `mcpServers` block (duckduckgo/fetch/filesystem/…). See `docs/examples/tool-capabilities.md`.

### Added — Docs
- Illustrated [Skills & Consensus walkthrough](docs/SKILLS_AND_CONSENSUS_WALKTHROUGH.md) with regenerable terminal screenshots; `docs/CLI_FUSION.md` Skills + Inference-profiles sections; README Core Concepts bullets.

## [0.4.11] - 2026-06-17

### Fixed — accessibility best-practice (web UI)
- A deeper axe pass with the **full** ruleset (not just WCAG2 A/AA) surfaced best-practice violations the scoped run missed, now all fixed:
  - `landmark-one-main` / `region`: page content is wrapped in a single `<main>` so every region sits inside a landmark.
  - `page-has-heading-one`: the Dashboard had no `<h1>` — added one.
  - `heading-order`: Blueprints/Teams card titles jumped from `<h1>` to `<h3>`; demoted to `<h2>`.
- Adds reusable `webui/frontend/scripts/a11y-audit.mjs` (full ruleset, 7 routes × light/dark × desktop/mobile). **0 violations across all 28 combinations.**

### Added — CLI permutation proof
- `scripts/prove_cli_permutations.py` exercises every installed CLI through every framework mode (cli_agent, cli_fusion panel, cli_orchestrator, cli_map, self-consensus ×2, native best-of-n). Verified live: **12/12 permutations PASS** across claude + gemini + grok + opencode.

## [0.4.10] - 2026-06-17

### Changed — Builder visual polish
- The source file-browser is shown only when a blueprint has more than one file; single-file blueprints get a full-width editor instead of a lonely 1-item list. Verified: tap targets all >=24px across pages; axe stays at 0 (mobile+desktop, light+dark).

## [0.4.9] - 2026-06-17

### Fixed — responsive / mobile (web UI)
- Builder: the blueprint list (a desktop sidebar) buried the config + editor on mobile; below `lg` it's now a compact blueprint **dropdown**, so the agent/model config and source editor are immediately reachable.
- Mobile a11y: the API Access snippet `<pre>` blocks and the chat message list became scrollable-region-focusable violations at narrow widths — made keyboard-focusable + labeled. **0 axe WCAG2 A/AA violations across mobile (light+dark) and desktop.**

## [0.4.8] - 2026-06-17

### Fixed — accessibility (web UI)
- Pedantic a11y pass (axe-core, WCAG 2 A/AA): **0 violations across all pages in both light and dark mode** (was several "serious"). Fixes: CodeMirror editor/scroller given an accessible name + keyboard focus (read-only, not editable=false); the config `<pre>` made focusable + labeled; the Settings icon-link labeled; `aria-current` on active list items; replaced fixed `text-gray-*`/low-opacity text with theme-adaptive `text-base-content` tokens (fixed dark-mode contrast); fixed a low-contrast stat color and the CodeMirror dark gutter.

## [0.4.7] - 2026-06-17

### Changed — Blueprint Builder polish
- Builder added to the mobile dock nav; agent/model config gains a **Download** button (client-side JSON); CodeMirror editor follows the app **dark/light theme**; dark mode verified across the page.

## [0.4.6] - 2026-06-17

### Added — Blueprint Builder web UI
- New **/builder** page (React + TanStack Query + DaisyUI): lists all blueprints, shows their source in a lazy-loaded **CodeMirror** editor with a file browser, and an **editable agent/model config builder** — pick a CLI + consensus mode (single / self-consensus N / native best-of-N / panel) + N and get a live, copy-pasteable `cli_agents` JSON block.
- Backend endpoints: `GET /v1/blueprints/<id>/source` (read-only source, path-traversal guarded) and `GET /v1/cli-agents/` (CLI catalog + `native_consensus` map). 4 API tests.

## [0.4.5] - 2026-06-17

### Added — more consensus modes
- **Self-consensus:** `consensus: N` (int) runs the **same persona N times** and synthesizes — self-consistency sampling. Verified live (grok ×3 → "operational/distributed complexity… no material disagreement on substance").
- **Call-time consensus flag:** a per-request `params.consensus` (bool/int/list/dict) overrides the agent's config designation; falsy forces a single call.
- **Native (built-in) consensus catalog:** `cli_catalog.NATIVE_CONSENSUS` records CLIs whose *own* flag fans out (grok `--best-of-n N`, verified live), with `has_native_consensus()` / `native_consensus_flags()` / `with_native_consensus()`. `swarm-cli cli-agents --json` now emits a `native_consensus` map so a UI can offer a "use this CLI's built-in consensus" toggle only where available. Framework and native consensus compose (N framework samples × M native candidates).

## [0.4.4] - 2026-06-16

### Added
- **Consensus agents:** designate any agent as a consensus agent via `consensus` in its `cli_agents` config — calling it runs a *panel* instead of a single inference. `true` => all available CLIs; a list => a preferred whitelist that falls back to all-available if it matches nothing; `{panel, judge}` => explicit. The default panel is real CLIs (other consensus *designations* are excluded). Verified live with grok (whitelist `[grok, claude]` and a no-match whitelist that fell back to the full panel — both returned "Tokyo").
- `docs/BLUEPRINT_LIBRARY.md` gains a **Consensus modes** taxonomy (single / agent-designated / self-consensus / call-time flag / orchestrated multi-persona) — a roadmap of permutations on the shared `run_consensus` engine.

## [0.4.3] - 2026-06-16

### Added — Blueprint library (permutation matrix)
- **`chatbot`** — minimal single-agent REST blueprint (the simplest template).
- **`hybrid_team`** / **`hybrid_swarm`** — the Mixed column: a REST coordinator/orchestrator that reaches for **grok CLI personas** and a **consensus panel** mid-run (`swarm.core.cli_tools`). REST half wired to a real openai-agents Agent that degrades gracefully without an LLM key; CLI half verified live with grok ("Rome", unanimous consensus).
- `docs/BLUEPRINT_LIBRARY.md` — a feature-tagged menu organized as an agents × backend matrix (1→many × REST/CLI/mixed); every cell now has a working, tested demonstrator.

### Changed
- **Laconic CLI:** `swarm-cli cli-agents` gains short flags (`-c/-a/-S/-s/-j/-i/-w`) and an `agents` alias, so `swarm-cli agents -iw` == `cli-agents --init --write`.

## [0.4.2] - 2026-06-16

### Added
- **grok** (xAI's CLI, also installed as `agent`) added to the catalog: `grok -p {prompt} --output-format json --always-approve` → `json:.text`. Verified live.
- `grok` is now the **preferred** single-agent CLI: `--init` (and the example config) make it the `cli_agent` default and the orchestrator router / map planner+reducer / fusion judge, while panels still include every installed CLI — so the other agents are only engaged for the multi-agent paths.

## [0.4.1] - 2026-06-16

### Added
- **One-command setup:** `swarm-cli cli-agents --init [--write]` autodiscovers the CLIs installed on the host and emits a complete, ready-to-run `swarm_config.json` wiring every mode (`cli_fusion` / `cli_orchestrator` / `cli_map`) over them, with per-CLI gotchas baked in. `--write` saves it (backing up any existing file).
- Example config now includes `cli_orchestrator` and `cli_map` blocks; docs gain a 60-second quick start.

### Fixed
- Removed a dead `[tool.hatch.version]` block in `pyproject.toml` (ignored, since the version is static).

## [0.4.0] - 2026-06-16

### Added — CLI Agent Fusion

Turn the agentic CLIs you already have installed (`claude`, `gemini`, `codex`,
`opencode`, …) into one-shot, OpenAI-API-addressable subagents — single
(`cli_agent`) or a parallel panel a judge synthesizes (`cli_fusion`). See
[docs/CLI_FUSION.md](docs/CLI_FUSION.md).

- `CliAdapter` one-shot layer + `cli_agent`/`cli_fusion` blueprints (panel → judge → synthesize, bounded master plan) (#116, #117)
- Autodiscovery: `swarm-cli cli-agents` reports install status; `--check-auth` probes each CLI's `auth_check`
- Full-capability (auto-approve) example adapters, replacing the read-only defaults
- Per-panelist workdir isolation (`cli_fusion.isolate_workdir` / per-request `isolate`): each write-capable panelist gets a throwaway `git worktree` (or temp dir) so parallel fan-out can't corrupt the source tree
- Built-in adapter catalog + `swarm-cli cli-agents --suggest`: paste-ready config for supported CLIs installed but not yet configured
- Catalog defaults encode known per-CLI gotchas so they run non-interactively out of the box: `gemini --skip-trust` (untrusted-dir gate), `opencode --model` (no usable built-in default) — verified live
- Non-interactive smoke probe + `swarm-cli cli-agents --smoke`: catches a misconfigured `cmd` that hangs instead of returning (ok/hang/error/not_installed)
- Machine-readable `swarm-cli cli-agents --json` (agents/smoke/suggestions) for CI and scripting
- `cli_agent` streams CLI stdout incrementally for `parse: "text"` adapters when `stream: true` (json-parse adapters fall back to one-shot)
- Failover & graceful degradation: `cli_agent` fails over down a candidate chain (`params.fallback`, or auto to other installed adapters; `failover: false` for strict) when a CLI is missing/broken/hung; `cli_fusion` drops failed panelists and reaches consensus from the survivors
- Reusable consensus service (`swarm.core.consensus.run_consensus`) extracted from the `cli_fusion` blueprint; consensus-first synthesis (no-judge fallback now picks the **most-corroborated** panel answer, not the longest)
- New `cli_orchestrator` blueprint — granular consensus: a cheap router CLI answers directly and escalates only high-stakes questions to a consensus panel (fusion as an on-demand tool, not a whole-request mode)
- Cleanup: removed dead `progress_text()` and `CliResult.as_dict()`
- Agent-tool layer (`swarm.core.cli_tools`): `cli_persona(adapter)` and `consensus_fn(panel, judge)` callables, `as_function_tool()` to hand either to an openai-agents `Agent` — so a real agent can call `consensus()` granularly mid-reasoning
- New `cli_map` blueprint — decompose → distribute → reduce: a planner CLI splits one task into subtasks, workers run them in parallel (round-robin), a reducer combines (complements `cli_fusion`'s consensus)
- Web UI **API Access** panel (Settings) — surfaces the live base URL, token, model list, and copy-paste snippets (curl / OpenAI SDK / Open WebUI) to plug any OpenAI client into the server
- End-to-end API coverage: real panel→synthesize and `params`-driven selection over `/v1/chat/completions`

## [0.3.3] - 2026-06-12

### Added
- Websocket chat honors blueprint selection (per-message field or ?blueprint= param); Teams page Launch buttons into preselected chat (#103)
- /v1/library/ API + SPA Add-to-Library / My Library filter (#104)
- Guided tour and all 26 screenshots refreshed to current UI

## [0.3.2] - 2026-06-11

### Fixed
- SPA shipped unstyled (Tailwind v4/v3 config mismatch emitted ~2kB CSS); DaisyUI 5 `card-bordered` removal made card borders invisible app-wide
- Django navbar dropdowns rendered as empty white boxes; duplicate element id
- Non-streaming `/v1/chat/completions` returned spinner text in test mode; all 14 blueprints now answer on both API surfaces (smoke matrix added)
- Mobile: SPA bottom nav never rendered (DaisyUI 4 class); viewport overflows fixed

### Added
- Guided tour + screenshot registry + README demo GIF; CI visual-regression workflow (golden journey, computed-style guards)
- SPA: agent-creator and settings pages, token auth UX, websocket ChatPage; theme-token dark mode toggle
- Mobile captures (13 pages); capture harness authenticates and migrates fresh DBs

### Changed
- Branding: project name is "Open Swarm" (dropped stale "MCP" suffix)

## [0.3.1] - 2026-06-11

### Added
- SPA: agent-creator and settings pages on live APIs (#80); websocket ChatPage + token auth UX
- ASGI routing — websocket chat now functional (channels/daphne wired)
- JSON Teams API (/v1/teams/); NOTICE file; opt-in mem0 e2e harness (#85)
- uv.lock tracked; CI lock-check now meaningful (#81)

### Changed
- vite 5 -> 8; npm audit clean (#84)
- Absorbed 18 community/agent branches (perf, security shlex hardening, UX, tests) (#83)

### Removed
- Wagtail marketplace and SAML IdP scaffolding (-716 lines; GitHub-topics discovery retained) (#82)

### Security / hygiene
- Hardened .dockerignore: image no longer ships .git history, dev database (auth_user hashes), .letta/.claude local state, pycache with local absolute paths, or test artifacts

## [0.3.0] - 2026-06-11

### Repository cleanup wave (June 2026)

- **Added** `ROADMAP.md` — nested-checkbox roadmap consolidating project status; `TODO.md` slimmed to point at it.
- **Removed** tracked `node_modules` from the repository (now untracked/ignored).
- **Removed** dead code identified during the sweep; deleted the automated `CODE_SWEEP_REPORT.md`; archived `IMPLEMENTATION_SUMMARY.md` to `docs/archive/`.
- **Security** hardened defaults: command/SQL injection fixes, open redirect fixes, removal of hardcoded passwords.
- **Fixed** packaging issues (`uv sync`, frontend lockfile regeneration).
- **Docs** README attribution section (OpenAI Swarm derivative, built on openai-agents SDK) and explicit prerequisites (Python >= 3.10, Node >= 22 for optional frontend); React web UI marked experimental with the Django UI as the supported interface.

### Added
- Comprehensive unit tests for low-coverage modules: `audit.py`, `progress.py`, `output_formatters.py`, and `ansi_box.py`
- Test coverage for `ChucksAngelsBlueprint` class
- Test coverage for `DiffFormatter` and `StatusFormatter` classes
- Test coverage for `ProgressRenderer` class
- Test coverage for `ansi_box` function with various parameters and edge cases

### Changed
- Improved test coverage from ~26% to ~30% for core modules
- Enhanced code quality with comprehensive test cases for utility functions
- Fixed test failures in `test_audit_logger_log_with_args` and `test_chucks_angels_blueprint_init`

### Fixed
- Syntax error in test file (async for outside async function)
- Incorrect assertion in audit logger test (format args mismatch)
- Incorrect assertion in ChucksAngelsBlueprint test (description content)

### Performance
- Identified performance bottleneck in blueprint creation (test currently disabled due to 5.4s > 2.0s limit)
- Added comprehensive performance test suite for future optimization work

## [0.1.0] - 2024-01-01

### Added
- Initial project structure
- Core blueprint architecture
- CLI interface
- Basic test suite

## Style Compliance

### Linting Issues Identified
- **C0301 (line-too-long)**: 126 occurrences - Lines exceeding 100 character limit
- **C0114 (missing-module-docstring)**: Multiple modules missing docstrings
- **C0115 (missing-class-docstring)**: Multiple classes missing docstrings
- **C0116 (missing-function-docstring)**: Multiple functions missing docstrings
- **W0611 (unused-import)**: Several unused imports detected

### Top Violations by Line Number
- Line 1: 126 occurrences (missing module docstrings)
- Line 24: 12 occurrences
- Line 8: 11 occurrences
- Line 7: 11 occurrences
- Line 60: 11 occurrences

### Recommendations
- Add module-level docstrings to all Python files
- Add class and function docstrings following Google or NumPy style
- Break long lines (>100 characters) into multiple lines
- Remove unused imports
- Consider increasing line length limit or reformatting long lines
