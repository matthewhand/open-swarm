# Swarm Configuration & System TODOs

## Multi-Agent Orchestration (Zeus) Tasks
- [ ] Implement Zeus blueprint to read `TODO.md` via `read_file_tool` and parse tasks.
- [ ] Add planning step in Zeus using `blueprint_tool('suggestion')` to select the next task.
- [ ] Dispatch tasks to a worker blueprint (e.g., Codey) via `blueprint_tool('codey')` and capture results.
- [ ] Implement verification step using `blueprint_tool('suggestion')` to confirm task completion.
- [ ] Use `write_file_tool` in Zeus to update `TODO.md`, marking completed tasks.
- [ ] Write integration tests in `tests/blueprints/test_zeus_workflow.py` covering end-to-end orchestration.

## Critical Missing Tests
- [x] Test XDG config discovery and fallback order.
- [x] Test default config auto-generation when no config is found.
- [x] Test envvar/placeholder substitution in config loader.
- [ ] Test per-blueprint and per-agent model override logic.
- [ ] Test fallback to default model/profile with warning if requested is missing.
- [ ] Test MCP server config add/remove/parse.
- [ ] Test redaction of secrets in logs and config dumps.

## Unified UX Enhancements (Spinner, ANSI/Emoji Boxes)
- [ ] Implement and verify enhanced ANSI/emoji operation boxes for search and analysis operations across all blueprints. Boxes should:
    - Summarize search/analysis results (e.g., 'Searched filesystem', 'Analyzed ...')
    - Include result counts and display search parameters
    - Update line numbers/progress during long operations
    - Distinguish between code/semantic search output
    - Use emojis and box formatting for clarity
- [x] Implement spinner messages: 'Generating.', 'Generating..', 'Generating...', 'Running...', and 'Generating... Taking longer than expected' for Codey, Geese, RueCode. (Zeus, WhingeSurf not found in repo as of 2025-04-20)
    - [x] Codey
    - [x] Geese
    - [x] Jeeves (migrated from DigitalButlers; all code, tests, and CLI updated)
    - [x] RueCode
    - [x] Zeus (implemented as DivineOpsBlueprint in divine_code; spinner/UX standardized)
    - [ ] WhingeSurf (no implementation yet; pending scaffold)
- [x] Codey CLI: Approval mode and github agent tests pass in all environments (test-mode exit code/output, simulated shell/git, robust sys import)
- [x] Codey CLI: Unified, visually rich ANSI/emoji box output for code/semantic search and analysis (test-mode and real)
- [x] Codey CLI: Progressive, live-updating search/analysis UX (matches, progress, spinner, slow-op feedback)
- [x] output_utils: ansi_box prints spinner state in yellow when 'Generating... Taking longer than expected', cyan otherwise
- [ ] [NEXT] Extend unified output/UX to other blueprints (e.g. divine_code, stewie, echocraft) and ensure all use ansi_box/print_operation_box for search/analysis
- [ ] [NEXT] Refactor spinner/operation progress so that live line/progress updates are available in real (non-test) mode
- [ ] [NEXT] Add more result types, summaries, and param details to operation boxes (e.g. for file ops, chat, creative, etc.)
- [ ] [NEXT] Add tests for output formatting and UX regressions (search/analysis, spinner, slow-op, etc.)
- [ ] Add system/integration tests that objectively verify the above UX features in CLI output (spinner, boxes, progressive updates, emojis, etc.)
- [ ] Enhance DivineCode and FamilyTies blueprints to display spinner state and "Taking longer than expected" in the output box using `print_operation_box`.
- [ ] Ensure all blueprints pass spinner state/progress to `print_operation_box` (messages: Generating., Generating.., Generating..., Running..., Generating... Taking longer than expected).
- [ ] Refactor shared spinner logic if needed for easier blueprint adoption.
- [ ] Add/expand tests for spinner state and output UX in all blueprints.
 - [ ] Implement command stdout rendering:
   - Style stdout headings in pink and content in dull grey.
   - Truncate long outputs: show only the first 4 lines followed by "... (<n> more lines)".
   - Fallback to generic message "[Output truncated: too many lines or bytes]" for large content.
   - Add helper in `swarm.core.output_utils` and update CLI wrappers (e.g., `codey_cli.py`) to use it.
 - [ ] Document unified UX pattern and next blueprints to enhance in `docs/UX.md` or similar.
  - [ ] Refactor Codey CLI wrapper to use Rich Console for ANSI detection and styled I/O:
   - Bordered box for user input with blue `user:` label.
   - Indented, pink `codey:` label for AI responses with inline stats `(code:<exit>, duration:<secs>)`.
   - Default grey `Done!` if no stdout, with codeblock highlighting via Rich `Syntax`.
  - [ ] Add CLI flags to override hook messages separately (`--pre-msg`, `--listen-msg`, `--post-msg`).
## Documentation Updates
- [ ] Document `--pre`, `--listen`, and `--post` flags in USERGUIDE.md and README.md with comprehensive examples and edge cases. (# Investigation/Implementation)
- [ ] Document slash-command REPL behavior in USERGUIDE.md and README.md; specify how `/compact` and other slash commands map to config entries. (# Investigation/Spec)
- [ ] Document Rich-styled Codey CLI UX in Developer docs: ANSI detection, boxed user input, styled AI responses, inline stats, and codeblock highlighting via Rich. (# Spec/Implementation)
- [ ] Document blueprint-as-tool pattern in USERGUIDE.md as an advanced recipe; include sample code. (# Confirm)
- [ ] Add publishing instructions for TestPyPI and PyPI in README.md, including secrets setup (`TEST_PYPI_API_TOKEN`). (# Confirm)
## CLI Enhancements
- [ ] Port legacy LLM/MCP config subcommands (`config add/read/update/delete`) from click script into Typer-based `swarm-cli config`. (# Investigation/Implementation)
- [ ] Extend interactive shell (`src/swarm/extensions/cli/interactive_shell.py`) to support slash commands:
    - Parse lines starting with `/` and lookup `slashCommands` in config
    - Render `promptTemplate` and dispatch to blueprint via `blueprint_tool()` (# Spec/Implementation)
- [ ] Add support for per-hook message overrides in `swarm-cli launch` via `--pre-msg`, `--listen-msg`, and `--post-msg` flags. (# Spec/Implementation)
- [ ] Implement `swarm-cli session list` and `swarm-cli session show` to inspect past chat sessions from `~/.cache/swarm/sessions`. (# Spec/Implementation)
- [ ] Create `swarm-cli onboarding` command to display UX-rich welcome, Quickstart, and blueprint discovery hints. (# Spec/Implementation)
## Testing & Verification
- [ ] Add integration tests under `tests/cli/` for hook chaining (`--pre`, `--listen`, `--post`), verifying correct order and outputs. (# Implementation)
- [ ] Add system/integration tests that exercise Rich-styled CLI (ANSI vs no-ANSI modes) using `pytest capfd` to capture styled output. (# Implementation)
- [ ] Add unit tests for `BlueprintFunctionTool` and `blueprint_tool()` in `tests/unit/test_blueprint_tools.py`. (# Implementation)
- [ ] Add tests for slash-command REPL parsing in `tests/cli/test_slash_commands.py`. (# Implementation)
- [ ] Add tests for publishing workflows (TestPyPI / PyPI) via dry-run flags. (# Spec)

## CLI & Onboarding S-Tier Polish (2025-04-20)
- [ ] Refactor CLI help output for S-tier onboarding:
    - Use color and emoji for visual clarity (if terminal supports)
    - Add a prominent "Quickstart" section at the top
    - List all commands with clear, one-line descriptions
    - Add usage examples for every command
    - Add a "What next?" section: how to see all blueprints, run advanced ones, and where to get help
    - If the user runs `swarm-cli` with no arguments, show a beautiful welcome and the quickstart
    - If they run `swarm-cli run` with no blueprint, suggest hello_world
    - If they run `swarm-cli list`, show the demo blueprint and a tip to try it
- [ ] Ensure all CLI commands are obvious, memorable, and functional
- [ ] Add or stub `configure` and `info` commands if not present
 - [ ] Port legacy `config` subcommands (LLM and MCP server management) into the Typer-based `swarm-cli config` group
 - [ ] Add slash-command support in the interactive shell:
   - Parse inputs starting with `/`, map to `slashCommands` in config
   - Render `promptTemplate` (e.g., `"Compact: {{ history }}"`) and invoke blueprint via `blueprint_tool()`
- [ ] README and CLI help should always match actual CLI usage
- [ ] After first five minutes, user should be able to:
    - Instantly understand what Open Swarm is and does
    - See all available commands and what they do
    - Run a demo blueprint without reading the docs
    - Discover and try advanced features with confidence
- [ ] Simulate and document the first five minutes as a new developer/user
- [ ] Add onboarding messages and usage examples to CLI
- [ ] Polish onboarding further based on real user feedback

## Open Swarm UX Unification Progress (2025-04-20)

### Blueprints with Standardized Spinner/Progress and ANSI/Emoji Output
- [x] DivineCode
- [x] FamilyTies
- [x] Suggestion
- [x] Jeeves
- [x] Codey
- [x] MissionImprobable
- [x] EchoCraft
- [x] Geese

### Blueprints Skipped or Deferred (Minimal/Stub, No Output Logic)
- [ ] Gaggle (stub)

### Remaining Blueprints To Review
- [ ] django_chat
- [ ] mcp_demo
- [ ] monkai_magic
- [ ] nebula_shellz
- [ ] omniplex
- [ ] poets
- [ ] rue_code
- [ ] unapologetic_poets
- [ ] whinge_surf
- [ ] whiskeytango_foxtrot

> All major agent blueprints now use unified spinner/progress and result/error boxes for operation output. Continue reviewing and enhancing remaining blueprints as needed for full UX parity.

## Code Fixes
- [x] Add XDG path (`~/.config/swarm/swarm_config.json`) as the first search location in config discovery. (Already implemented)
- [ ] Revise and update `blueprints/README.md` to reflect current blueprints, configuration, UX expectations, and modular/provider-agnostic patterns. Ensure it is discoverable and referenced from the main README.
- [x] Implement async CLI input handler for all blueprints: allow user to continue typing while previous response streams. If Enter is pressed once, warn: "Press Enter again to interrupt and send a new message." If Enter is pressed twice, interrupt the current operation and submit the new prompt. (Framework-wide, inspired by whinge_surf request) [Implemented: see async_input.py, Codey, Poets]
- [ ] [NEW] Add blueprint metadata linting as a required pre-commit hook for all contributors (run `swarm-cli blueprint lint` before merge).
- [ ] [NEW] Enhance blueprint metadata loader to fallback to class docstring for description (implemented, document in README and TODO).
- [ ] [NEW] Remove legacy metadata.json files from blueprints (now redundant).
- [ ] [NEW] Add script to auto-generate a blueprint metadata table for the README from class metadata.
- [ ] [NEW] Expose blueprint metadata via a REST API endpoint for web UI/discovery.
- [ ] [NEW] Implement interactive CLI onboarding (`swarm-cli onboarding`) for blueprint discovery and quickstart.
- [ ] [NEW] Review codebase for stubs, TODOs, and placeholders; add actionable, specific items to this list for each.

---

## 🛠️ Chatbot‑Army Backlog (Next 2 Weeks)

> These items are phrased so an autonomous blueprint/agent can pick them up, create a branch, and open a PR. Every task **must ship with tests** and be guarded behind a feature‑flag that defaults to `false` (unless marked *docs only*).

### 1 — Observable UX & Telemetry

- [x] **Session Audit Trail** – Persist a timeline (`.jsonl`) of every agent action, tool call, completion, and error. Add CLI flag `--audit` to enable. Unit test: file created; entries appended in order. (2025-04-20)
- [x] **Desktop Notifications** – Implement a notifier backend that uses `notify-send` (Linux) or `osascript` (macOS). Trigger on >30 s operations and failures. (2025-04-20)

### 2 — Safety & Approval Modes

- [x] **Granular Approval Hooks** – Allow per‑tool approval policies via blueprint config (`approval_policy: {tool.fs.write: "ask", tool.shell.exec: "deny"}`). (2025-04-20)
- [ ] **Write‑Sandbox Enforcement** – Abort with clear error if an agent writes outside the configured writable root. Integration test attempts `../../etc/passwd`.

### 3 — Automatic Context Injection

- [ ] **git‑diff Summariser** – Toolbox util that summarises current diff (vs `origin/main`) in ≤50 words and injects into system prompt. Expose via MCP server.
- [ ] **Project Doc Loader** – When `--full-context` is set and `README.md` >500 lines, chunk first 1 000 tokens into the prompt.

### 4 — Documentation & Developer DX

- [ ] **Revamp `docs/QUICKSTART.md`** (*docs only*) – Separate sections for CLI, API, extending blueprints; provide verified copy‑paste commands.
- [ ] **Autogen Spec Files** – Script (`tools/generate_specs.py`) that emits deterministic PyInstaller spec files for every blueprint directory.

### 5 — Reliability & Test Coverage

- [ ] **Flaky‑Test Detector** – Nightly CI job that runs the suite 10× and flags tests that fail ≥2 times.
- [ ] **MCP Mock Server** – Reusable fixture that imitates success/failure paths for FS and shell MCP calls; replace ad‑hoc mocks.

### 6 — Stretch Goals (Optional, Reward ++💰)

- [ ] **Multimodal Input Preview** – Pass `--image` attachments to models that support `image/*`.
- [ ] **Streaming Token Output** – Optional raw token stream mode; flush tokens to stdout as they arrive.

### 7 — WhingeSurf Async Subprocess UX

- [ ] **WhingeSurf Async Subprocess UX:**
    - Implement subprocesses that can run in the background (async).
    - Blueprint yields control back to LLM while process runs.
    - Provide a function for LLM to query/check progress, exit status, and output of running subprocesses.
    - Show spinner messages: 'Generating.', 'Generating..', 'Generating...', 'Running...', and update to 'Taking longer than expected' if needed.
    - Rich ANSI/emoji boxes for progress and result reporting.
    - Add demo/test CLI command for users to try this feature.

---

Let’s build 🚀

### 1 — Observable UX & Telemetry

- [x] **Session Audit Trail** – Persist a timeline (`.jsonl`) of every agent action, tool call, completion, and error. Add CLI flag `--audit` to enable. Unit test: file created; entries appended in order. (2025-04-20)
- [x] **Desktop Notifications** – Implement a notifier backend that uses `notify-send` (Linux) or `osascript` (macOS). Trigger on >30 s operations and failures. (2025-04-20)

### 2 — Safety & Approval Modes

- [x] **Granular Approval Hooks** – Allow per‑tool approval policies via blueprint config (`approval_policy: {tool.fs.write: "ask", tool.shell.exec: "deny"}`). (2025-04-20)
- [ ] **Write‑Sandbox Enforcement** – Abort with clear error if an agent writes outside the configured writable root. Integration test attempts `../../etc/passwd`.

### 3 — Automatic Context Injection

- [ ] **git‑diff Summariser** – Toolbox util that summarises current diff (vs `origin/main`) in ≤50 words and injects into system prompt. Expose via MCP server.
- [ ] **Project Doc Loader** – When `--full-context` is set and `README.md` >500 lines, chunk first 1 000 tokens into the prompt.

### 4 — Documentation & Developer DX

- [ ] **Revamp `docs/QUICKSTART.md`** (*docs only*) – Separate sections for CLI, API, extending blueprints; provide verified copy‑paste commands.
- [ ] **Autogen Spec Files** – Script (`tools/generate_specs.py`) that emits deterministic PyInstaller spec files for every blueprint directory.

### 5 — Reliability & Test Coverage

- [ ] **Flaky‑Test Detector** – Nightly CI job that runs the suite 10× and flags tests that fail ≥2 times.
- [ ] **MCP Mock Server** – Reusable fixture that imitates success/failure paths for FS and shell MCP calls; replace ad‑hoc mocks.

### 6 — Stretch Goals (Optional, Reward ++💰)

- [ ] **Multimodal Input Preview** – Pass `--image` attachments to models that support `image/*`.
- [ ] **Streaming Token Output** – Optional raw token stream mode; flush tokens to stdout as they arrive.

### 7 — WhingeSurf Async Subprocess UX

- [ ] **WhingeSurf Async Subprocess UX:**
    - Implement subprocesses that can run in the background (async).
    - Blueprint yields control back to LLM while process runs.
    - Provide a function for LLM to query/check progress, exit status, and output of running subprocesses.
    - Show spinner messages: 'Generating.', 'Generating..', 'Generating...', 'Running...', and update to 'Taking longer than expected' if needed.
    - Rich ANSI/emoji boxes for progress and result reporting.
    - Add demo/test CLI command for users to try this feature.

---

Let’s build 🚀

### 1 — Observable UX & Telemetry

- [x] **Session Audit Trail** – Persist a timeline (`.jsonl`) of every agent action, tool call, completion, and error. Add CLI flag `--audit` to enable. Unit test: file created; entries appended in order. (2025-04-20)
- [x] **Desktop Notifications** – Implement a notifier backend that uses `notify-send` (Linux) or `osascript` (macOS). Trigger on >30 s operations and failures. (2025-04-20)

### 2 — Safety & Approval Modes

- [x] **Granular Approval Hooks** – Allow per‑tool approval policies via blueprint config (`approval_policy: {tool.fs.write: "ask", tool.shell.exec: "deny"}`). (2025-04-20)
- [ ] **Write‑Sandbox Enforcement** – Abort with clear error if an agent writes outside the configured writable root. Integration test attempts `../../etc/passwd`.

### 3 — Automatic Context Injection

- [ ] **git‑diff Summariser** – Toolbox util that summarises current diff (vs `origin/main`) in ≤50 words and injects into system prompt. Expose via MCP server.
- [ ] **Project Doc Loader** – When `--full-context` is set and `README.md` >500 lines, chunk first 1 000 tokens into the prompt.

### 4 — Documentation & Developer DX

- [ ] **Revamp `docs/QUICKSTART.md`** (*docs only*) – Separate sections for CLI, API, extending blueprints; provide verified copy‑paste commands.
- [ ] **Autogen Spec Files** – Script (`tools/generate_specs.py`) that emits deterministic PyInstaller spec files for every blueprint directory.

### 5 — Reliability & Test Coverage

- [ ] **Flaky‑Test Detector** – Nightly CI job that runs the suite 10× and flags tests that fail ≥2 times.
- [ ] **MCP Mock Server** – Reusable fixture that imitates success/failure paths for FS and shell MCP calls; replace ad‑hoc mocks.

### 6 — Stretch Goals (Optional, Reward ++💰)

- [ ] **Multimodal Input Preview** – Pass `--image` attachments to models that support `image/*`.
- [ ] **Streaming Token Output** – Optional raw token stream mode; flush tokens to stdout as they arrive.

### 7 — WhingeSurf Async Subprocess UX

- [ ] **WhingeSurf Async Subprocess UX:**
    - Implement subprocesses that can run in the background (async).
    - Blueprint yields control back to LLM while process runs.
    - Provide a function for LLM to query/check progress, exit status, and output of running subprocesses.
    - Show spinner messages: 'Generating.', 'Generating..', 'Generating...', 'Running...', and update to 'Taking longer than expected' if needed.
    - Rich ANSI/emoji boxes for progress and result reporting.
    - Add demo/test CLI command for users to try this feature.

---

Let’s build 🚀

## 📑 Per‑Blueprint QA & Packaging

For **each** blueprint listed under `src/swarm/blueprints/*/` (excluding `common/`):

```text
- [ ] <blueprint‑name>/  
    - [ ] Read docstring & README – update if stale (docs only).
    - [ ] Ensure all required env vars are documented in `README.md`.
    - [ ] Run existing tests; note current coverage.
    - [ ] Add or update tests to reach ≥80 % coverage.
    - [ ] Verify blueprint works via `swarm-cli run <name> --instruction "ping"`.
    - [ ] Build standalone binary with `swarm-cli install` (PyInstaller) and run `--help`.
    - [ ] Confirm standalone run creates identical output to CLI run.
    - [ ] Add GitHub Action job `<name>-standalone-test` that builds + smoke‑tests binary.
```

Generate a **separate PR per blueprint** following the standard claiming procedure (branch `task/qa-<blueprint>`).

---

Let’s build 🚀
