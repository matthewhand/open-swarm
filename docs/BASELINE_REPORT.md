# Baseline Verification Report — Milestone 0
Goal: Verify README Quickstart paths are runnable using uv. Capture exact commands, observed results, and gaps to fix.

Generated: UTC 2025-08-03

---

## Environment
- uv: `uv 0.6.3`
- OS: Linux
- Repo: open-swarm (editable dev)
- Command runner: uv-managed venv

Setup executed:
- `uv sync --all-extras`
- `uv run pytest -q` (still running at time of report; long-duration)

---

## README Paths Verification

### CLI

1) Help
- Command:
  - `uv run swarm-cli --help`
- Result: PASS
  - Shows commands: `install-executable`, `launch`, `list`
- Notes:
  - README mentions variants like `swarm-cli blueprints list` and `swarm-cli run` which are NOT available. CLI surface is unified under top-level `install-executable | launch | list`.

2) List Blueprints
- Commands:
  - `uv run swarm-cli list`
- Result: PASS
  - Displays installed executables and bundled blueprints.

- Commands (README drift):
  - `uv run swarm-cli blueprints list`
- Result: FAIL (by design)
  - Error: No such command 'blueprints'.
- Action: Update README and docs to reflect real command set.

3) Install Executable (Codey)
- Command:
  - `uv run swarm-cli install-executable codey`
- Result: PASS
  - PyInstaller run succeeded; binary written to `~/.local/share/swarm/bin/codey`.

4) Launch Executable (Codey)
- Command:
  - `uv run swarm-cli launch codey --message "Hello from smoke"`
- Result: FAIL at runtime
  - Output shows Codey CLI banner and "Environment validation passed."
  - Crash from packaged binary:
    ```
    AttributeError: 'CodeyBlueprint' object has no attribute 'create_agents'
    [PYI-2793573:ERROR] Failed to execute script 'codey_cli' due to unhandled exception!
    ```
- Action:
  - Implement/create_agents or compatibility shim for CodeyBlueprint to work in packaged mode.
  - Add tests for packaged CLI path.

5) Minimal Hello World (README variant)
- Commands (README drift):
  - `swarm-cli run hello_world --instruction "Hello from CLI!"`
- Result: FAIL (by design)
  - No top-level `run` command.
- Action:
  - Provide correct CLI invocations or a mapped helper to run a blueprint in-process.
  - Update README examples accordingly.

### API via Docker

1) Docker Compose
- Command:
  - `docker compose up -d`
- Result: FAIL to launch
  - Warning about obsolete `version` in override.
  - Error: service "swarm" has neither an image nor a build context specified.
- Action:
  - Provide `image:` or `build:` for `swarm` service or update docs to specify correct override usage.
  - Add a minimal compose file that runs out of the box for API mode.

2) API Check
- Command:
  - `curl -sf http://localhost:8000/v1/models`
- Result: No response (service not running).

---

## Test Run Status

- `uv run pytest -q` long-running. Live log showed httpx SSL context debug and timeout markers exist in several tests:
  - tests/integration/test_cli_jeeves.py: @pytest.mark.timeout(15)
  - tests/integration/test_cli_geese.py: @pytest.mark.timeout(15)
  - tests/integration/test_cli_codey.py: @pytest.mark.timeout(15)
  - tests/blueprints/test_jeeves_progressive_tool.py: @pytest.mark.timeout(2)

At time of this report, the run had not completed. A gate is configured to stage commits only if pytest rc == 0.

---

## Summary of Gaps Blocking “Runs as in README”

1) CLI command drift
- README uses `swarm-cli blueprints list` and `swarm-cli run ...`
- Actual CLI uses: `install-executable | launch | list`
- Fix: Update README/QUICKSTART/DEVELOPER_GUIDE to reflect correct CLI and add equivalents for common tasks.

2) Packaged Codey executable runtime error
- AttributeError: missing `create_agents` in CodeyBlueprint during packaged run
- Fix: Implement/create_agents (or compatibility layer) and add integration tests that exercise packaged binary path.

3) Docker Compose API path not runnable
- Compose lacks image/build for service "swarm"
- Fix: Provide a working compose file and verified steps; add smoke test to validate `/v1/models` and `/v1/chat/completions`.

4) Hello World “run” example
- No top-level `run` command exists
- Fix: Replace with supported equivalent or add a thin “run” command that wraps current UX.

---

## Recommended Next Fixes (Milestone 1 candidates)

- CLI/docs reconciliation:
  - Replace invalid commands in README and docs.
  - Add a small wrapper or explicit examples using `install-executable` and `launch`.
- Codey CLI packaged fix:
  - Implement `create_agents` method or adjust Codey CLI entry to align with current Blueprint API.
  - Add test: install-executable + launch smoke returning rc=0, asserting UX boxes where applicable.
- Docker/API:
  - Provide `image:` or `build:` in compose.
  - Add API smoke test to CI to verify `/v1/models` returns 200.
- Add doctest-like script to verify README snippets (shell) offline when possible.

---

## Acceptance Criteria for Milestone 0
- Report produced with pass/fail per README command (this file).
- Blocking defects identified, with clear actions.
- Tests completion gate pending (automated). Commit will stage upon pytest rc=0.