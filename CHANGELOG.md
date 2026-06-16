# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

(nothing yet)

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
