# Open Swarm TODO (Prioritized Roadmap to “It runs as in the README” + Test Coverage)

This roadmap prioritizes making the application run as described in the README (CLI and API paths), then raises automated test coverage to enforce and keep that promise. Milestone-based with explicit acceptance criteria, commands, and coverage targets.

---

## Milestone 0 — Baseline: Reconcile README vs Reality

- [x] Verify all README Quickstart paths are runnable locally
  - [x] PyPI path: `pip install open-swarm` then `swarm-cli --help`
  - [x] Dev path: `pip install -e .[all-extras]` then `swarm-cli --help`
  - [x] Minimal “hello_world” run: `swarm-cli run hello_world --instruction "Hello from CLI!"`
  - [x] Blueprint install/launch: `swarm-cli install codey` and `swarm-cli launch codey --message "Hello"`
  - [x] Docker API: `docker compose up -d` then `curl http://localhost:8000/v1/models`
- [x] Identify all breakages and doc drifts; create issues per delta with repro/owner/ETA
- [x] Freeze scope for Milestone 1/2 based on this reconciliation report
- Acceptance criteria:
  - [x] A short baseline report exists in docs/BASELINE_REPORT.md with pass/fail per README command set
  - [x] Blocking defects are filed and referenced from this TODO

---

## Milestone 1 — Make Core Flows Work End-to-End

Focus: ensure “README Quickstart” works verbatim.

### CLI (swarm-cli)
- [x] Ensure `swarm-cli list` and `swarm-cli blueprints list` show bundled blueprints
- [x] Ensure `swarm-cli install <bp>` produces a runnable binary to user bin dir
- [x] Ensure `swarm-cli launch <bp> --message "..."`
- [x] Ensure “pre/listen/post” hook chain works (README example)
- [x] Add robust error messages for missing config/keys

### API (swarm-api via Docker)
- [x] Compose up starts server without manual fix-ups
- [x] `/v1/models` returns installed models/blueprints
- [x] `/v1/chat/completions` accepts blueprint name and returns a response
- [x] API auth behavior documented and enforced when enabled

### Config and Secrets
- [x] `swarm-cli config add` flows: llm, mcpServers, blueprint metadata
- [x] Keys are stored in `~/.config/swarm/.env` not JSON
- [x] Respect `${ENV_VAR}` expansion in config JSON

Acceptance criteria:
- [x] All README commands in “Quickstart”, “Using Blueprints as Tools”, “Installation”, “Quickstart 1/2” run cleanly on Linux
- [x] Clear error for missing OPENAI_API_KEY and optional keys

---

## Milestone 1.5 — Web UI: Team Launcher (High Priority)

Goal: a minimal, reliable browser UI that launches an agent team from a user dialog and streams results.

- [ ] Add `/teams/launch` page (behind `ENABLE_WEBUI=true`)
  - [ ] Inputs: Team Blueprint (select), Task/Instruction (textarea), Model/Profile (select), Advanced (pre/listen/post)
  - [ ] Populate options from API: initially `/v1/models`; prefer `/v1/blueprints` when available
  - [ ] Submit to `/v1/chat/completions` with `stream=true`; render SSE
  - [ ] Auth: API token header or session login per settings
- [ ] API support for richer metadata
  - [ ] `/v1/blueprints` returns id, description, abbreviation, tags, installed/compiled
  - [ ] Optional: `/v1/blueprints/<id>` detail
- [ ] Tests
  - [ ] Page renders with and without auth
  - [ ] Launch streams incremental tokens and completes cleanly
  - [ ] Fallback to non‑streaming when `stream=false`
- [ ] Docs
  - [ ] README “Web UI: Team Launcher” quickstart
  - [ ] QUICKSTART/Docker: set `ENABLE_WEBUI=true` and navigate to `/teams/launch`

Acceptance criteria:
- [ ] User can select a team blueprint, enter a task, click Launch, and see streaming output end‑to‑end.
- [ ] Works with token auth on/off; behaves consistently in Docker compose.
- [ ] Covered by basic view + API tests; documented in README/QUICKSTART.

---

## Milestone 2 — UX Compliance and Blueprint Readiness

Focus: guarantee UX standards and minimum functionality across bundled blueprints.

- [x] All active blueprints pass spinner/result box compliance
  - [x] Uses `print_search_progress_box` everywhere
  - [x] Shows spinner sequence and “Taking longer than expected”
  - [x] Distinguishes code vs semantic search
- [x] Metadata completeness for all blueprints
  - [x] name, emoji, description, examples, commands, branding present and meaningful
- [x] Update the auto-generated blueprint table in README via `scripts/gen_blueprint_table.py`
- [x] Fix flagged blueprints from TODO comments
  - [x] Unapologetic Poets: interactive/multi-turn behavior required
  - [x] Unapologetic Poets: respect debug flag over [SWARM_CONFIG_DEBUG]

Acceptance criteria:
- [x] `python scripts/check_ux_compliance.py` passes
- [x] Generated table matches current metadata
- [x] Known blueprint functional defects from docs/TODO are resolved or explicitly skipped with justification

---

## Milestone 3 — Test Coverage: Lock the Behavior

Target: ≥85% coverage for CLI/UX-critical surfaces, with focus on README-paths.

### CLI Tests
- [x] Unit: command parsing, help text, error paths
- [x] Integration: `list`, `install`, `launch`, hooks, minimal blueprint run
- [x] Config ops: `config add/list/edit` store secrets in .env and not JSON
- [x] Secret input: stdin/env/file mutual exclusivity

### API Tests
- [x] Start with `manage.py` test server fixture; test `/v1/models`, `/v1/chat/completions`
- [x] Auth on/off matrix; bad/expired token
- [x] JSON schema validation for common error returns

### Blueprint Tests
- [x] Codey: `/codesearch` and `/semanticsearch` spinner/results compliance
- [x] Gaggle: basic `/search` and `/analyze` compliance
- [x] Hello World: smoke test used by README
- [x] Poets/Unapologetic Poets fixes covered

### Tooling
- [x] Add coverage defaults in `pytest.ini`:
  - [x] `--cov=src --cov-report=term-missing` (or document local command variant)
- [ ] CI job for tests + compliance + coverage threshold
  - [ ] Fail below threshold; allow opt-in temporary waivers per-path
- [x] Fast path markers
  - [x] `-m "not integration"` suite for quick local checks
  - [x] Timeouts for flaky network calls with retries/mocks

Acceptance criteria:
- [ ] `uv run pytest --cov=src --cov-report=term-missing` ≥ 85% project-wide
- [x] All CLI/API paths used in README have stable, green tests
- [ ] CI enforces threshold

---

## Milestone 4 — Documentation Truthfulness and Hardening

- [x] Ensure README command blocks are verified by tests or script
  - [x] Add a “doctest-like” runner for shell blocks: `scripts/verify_readme_snippets.py`
- [ ] QUICKSTART/DEVELOPER_GUIDE/SWARM_CONFIG alignment
  - [ ] Remove drifts; replace placeholders with exact working examples
- [ ] Troubleshooting: add common test/CI issues (e.g., SQLite locks, missing PATH, Docker perms)
- [ ] Troubleshooting: document restricted sandbox behavior for asyncio/socketpair (see generated blueprints)
- [ ] Security notes:
  - [ ] Document secure key handling: stdin/env/file with explicit examples
  - [ ] Call out API auth defaults and recommended flags

Acceptance criteria:
- [ ] One script can verify prominent README shell blocks without network keys (mock where needed)
- [ ] Docs mention exact commands that our tests execute

---

## Milestone 5 — Reliability and Developer Experience

- [x] Pre-test cleanup and stable fixtures for DB and temp dirs
  - [x] Keep `/tmp` cleanup script wired into test runner
- [ ] Flake: identify and deflake any intermittent tests (add retries or mark/skip-with-justification)
- [x] Developer helpers
  - [x] `make test` with common flags
  - [x] `make fast` for non-integration suite
  - [x] `make compliance` for UX/metadata checks
- [x] Local smoke script
  - [x] `scripts/smoke_readme_paths.sh` to run all README flows headless and report summary

Acceptance criteria:
- [x] Single command for developers to validate: `make all` → lint, tests, coverage, compliance, smoke

---

## Security & Secrets Improvements (Cross-Milestone)

- [x] Implement mutually exclusive API key input for CLI:
  - [x] `--api-key-stdin`
  - [x] `--api-key-env`
  - [x] `--api-key-file`
  - [x] Clear precedence/error messages; no accidental echo in logs
- [x] Tests: explicit mocks asserting no secrets leak to stdout/stderr/logs
- [ ] Docs: examples for each secure path; discourage inline key flags

---

## MCP Provider Improvements

Focus: Enhance MCP integration for better tool discovery, security, and scalability.

- [ ] Improve MCP server auto-discovery in config (e.g., scan for common servers like filesystem, git)
- [ ] Add validation for MCP tool schemas in provider.py to prevent malformed tools
- [ ] Implement secure token passing for MCP servers (integrate with SAML/OAuth for local IdP)
- [ ] Support horizontal scaling for MCP servers (e.g., multiple instances for load balancing)
- [ ] Add tests for MCP execution edge cases (e.g., failed spawns, timeouts)
- [ ] Document MCP setup in QUICKSTART with examples for common servers (filesystem, weather)

Acceptance criteria:
- [ ] `swarm-cli config add --section mcpServers` supports validation and auto-fill for known servers
- [ ] All MCP interactions pass security audits (no plaintext secrets in comms)

---

## Marketplace Organization

Focus: Structure GitHub-based marketplace for blueprints and MCP templates.

- [x] Define GitHub topics: `open-swarm-blueprint`, `open-swarm-mcp-template`
- [ ] Create central discovery repo with search UI (e.g., GitHub Pages or Wagtail integration)
- [ ] Standardize manifest.json format for blueprints/MCP (no secrets, use ${VAR} placeholders)
- [ ] Add API endpoint `/v1/marketplace` to query GitHub topics and fetch manifests
- [ ] Implement import flow: `swarm-cli import-from-github <repo> <blueprint>`
- [ ] Editorial curation: Flag verified/high-quality blueprints in Web UI

Acceptance criteria:
- [ ] Users can discover/install from GitHub topics via CLI/Web UI
- [ ] Marketplace search returns metadata without fetching full repos

---

## Concrete Test Backlog (Additions/Improvements)

- [x] CLI: install → launch binary round-trip using temporary HOME/xdg paths
- [x] CLI: pre/listen/post workflow traces are visible and ordered
- [ ] CLI: slash commands minimal e2e in chat mode with `/compact` demo
- [x] API: OpenAI-compatible chat payload happy path and common errors
- [x] Config: env expansion `${ENV_VAR}` in nested objects and arrays
- [ ] MCP: filesystem server tool smoke with mocked command spawn
- [x] UX: spinner “Taking longer than expected” threshold triggers deterministically in tests
- [ ] Coverage: blueprint template path to guard regressions

---

## Existing Items Reconciled (from previous TODO)

- [x] Add tests for `swarm-cli llm create/update` with:
  - [x] `--api-key-file`
  - [x] `--api-key-env`
  - [x] `--api-key-stdin`
  - [x] Exclusivity logic
- [x] Update documentation in QUICKSTART/DEVELOPER_GUIDE/help strings for secure API key usage
- [x] Automate CLI script generation for blueprints with `cli_name` metadata
- [ ] Team Wizard: richer templates (multi-agent coordination patterns, streaming output)
- [ ] Team Wizard: more robust validation and dry-run diff output
- [ ] Team Wizard: optional test scaffold alongside generated blueprint
- [x] Expand tests for all new CLI features
- [x] Highlight security best practices in user-facing docs
- [x] Fix: Unapologetic Poets interactive behavior and debug flag adherence
- [x] Blueprint patch review for init/config across: RueCode/Chatbot/Omniplex/Poets/MonkaiMagic/MissionImprobable/NebulaShellzzar/WhiskeyTangoFoxtrot

---

## Other Outstanding Items

- [ ] Integrate MCP with marketplace: Allow blueprints to declare required MCP servers from templates
- [ ] Performance: Benchmark MCP spawn times and optimize for cold starts
- [ ] Accessibility: Ensure Web UI team launcher supports screen readers and keyboard nav
- [ ] CI/CD: Add auto-merge PRs for non-breaking changes (quality >=3)
- [ ] Release: Prepare v0.2.0 with updated CHANGELOG and PyPI upload

---

## Metrics and Gates

- [ ] Coverage gate: ≥85% by Milestone 3, target ≥90% by Milestone 5
- [x] README command verification script must pass in CI
- [x] Compliance scripts must pass in CI
- [x] No plaintext secrets in logs; redaction tests enforced

---

## Execution Order Summary

1) Milestone 0: Baseline report and gaps
2) Milestone 1: Fix CLI/API paths to match README
3) Milestone 2: Enforce UX + blueprint readiness
4) Milestone 3: Coverage to 85% with CI gate
5) Milestone 4: Docs become truth, verified automatically
6) Milestone 5: Reliability polish and DX
7) MCP/Marketplace sections
8) Other outstanding items

---

(See also: [docs/QUICKSTART.md](docs/QUICKSTART.md), [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md), [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md), [README.md](README.md))
