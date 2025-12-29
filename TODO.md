# Swarm: Core Framework & Blueprint Management TODOs

## Phase 1: Core CLI & Blueprint Lifecycle Implementation

### 1.1. XDG Path Management & Utilities
- [x] Implement robust XDG path helper functions using `platformdirs`:
    - `get_user_data_dir_for_swarm()` -> `~/.local/share/OpenSwarm/swarm/`
    - `get_user_blueprints_dir()` -> `~/.local/share/OpenSwarm/swarm/blueprints/`
    - `get_user_bin_dir()` -> `~/.local/share/OpenSwarm/swarm/bin/`
    - `get_user_cache_dir_for_swarm()` -> `~/.cache/OpenSwarm/swarm/`
    - `get_user_config_dir_for_swarm()` -> `~/.config/OpenSwarm/swarm/`
- [x] Ensure all file operations (config, blueprint source, compiled binaries, cache) use these XDG paths.
- [x] Updated `core.config_loader` to use new path functions.

### 1.2. Blueprint Metadata Enhancements
- [ ] Add `abbreviation: Optional[str]` to `BlueprintBase` metadata.
    - Update `blueprint_discovery.py` to extract `abbreviation`.
    - Update a few example blueprints (e.g., `codey`, `chucks_angels`) with an `abbreviation`.
- [ ] Enhance blueprint metadata loader to fall back to class docstring for `description` if not explicitly set in metadata. (Already noted as implemented, verify and document).
- [ ] Remove legacy `metadata.json` files from all blueprints if they exist (now redundant).

### 1.3. `swarm-cli install <name_or_path>` Command
- [ ] Create `src/swarm/extensions/cli/commands/install_blueprint.py`.
- [ ] Implement logic to:
    - Identify if `<name_or_path>` is a prebuilt name, local file path (py, zip), or directory path. (URL support for later).
    - Determine/derive `blueprint_name`.
    - Create target directory: `get_user_blueprints_dir() / blueprint_name`.
    - Copy source file(s) / extract zip contents into this target directory.
    - Handle potential name conflicts or provide an `--overwrite` option.
- [ ] Register `install` command in `src/swarm/extensions/cli/main.py`.
- [ ] Add unit and integration tests for various installation sources and scenarios.

### 1.4. `swarm-cli list` Command (Installed & Available)
- [x] Modify `src/swarm/extensions/cli/commands/list_blueprints.py`.
- [x] **Default `list` (Installed Blueprints):**
    - [x] Scan subdirectories in `get_user_blueprints_dir()`.
    - [x] For each, dynamically load its main Python file to extract metadata (name, version, description, abbreviation).
        - [x] Use `importlib.util.spec_from_file_location` and `importlib.util.module_from_spec`.
    - [x] Check if `get_user_bin_dir() / <abbreviation_or_name>` exists to indicate "compiled status."
    - [x] Display information clearly.
- [x] **`list --available` (or `search`) (Prebuilt/Bundled Blueprints):**
    - [x] Use existing `discover_blueprints()` from `swarm.core.blueprint_discovery` (which scans `src/swarm/blueprints/` in the project).
    - [x] Ensure this discovery picks up the new `abbreviation` metadata.
- [x] Update command registration in `main.py`.
- [x] Add tests for listing installed and available blueprints.

### 1.5. `swarm-cli compile <blueprint_name>` Command
- [ ] Create `src/swarm/extensions/cli/commands/compile_blueprint.py`.
- [ ] Command takes `<blueprint_name>` (must be an *installed* blueprint, i.e., source exists in `get_user_blueprints_dir() / blueprint_name`).
- [ ] Logic:
    - Locate main Python file in `get_user_blueprints_dir() / blueprint_name`.
    - Load metadata (especially `abbreviation`) from this installed Python file.
    - Determine executable name (abbreviation or blueprint_name).
    - Use `PyInstaller.__main__.run([...])` (similar to `src/swarm/core/build_launchers.py`):
        - `script_name`: Path to the main `.py` file in the installed location.
        - `--name <executable_name>`
        - `--onefile`
        - `--distpath get_user_bin_dir()`
        - `--workpath get_user_cache_dir_for_swarm() / "build" / blueprint_name`
        - `--specpath get_user_cache_dir_for_swarm() / "specs" / blueprint_name`
        - `--noconfirm` or handle overwriting existing executables.
- [ ] Register `compile` command in `main.py`.
- [ ] Add tests for compiling blueprints, including checking output location and basic execution of the compiled binary.

### 1.6. `swarm-cli launch <blueprint_name>` Command
- [ ] Modify existing `launch` command (likely in `src/swarm/core/swarm_cli.py` or `src/swarm/extensions/cli/commands/`).
- [ ] It should now primarily look for and execute the *compiled binary* from `get_user_bin_dir() / <abbreviation_or_name>`.
- [ ] Retain support for `--pre`, `--listen`, `--post` hooks (these would also need to be compiled blueprints).
- [ ] If a compiled binary is not found, it could offer to run `swarm-cli compile <blueprint_name>` or fall back to running from installed source (less ideal for "launch").
- [ ] Update tests for launching compiled blueprints.

### 1.7. `swarm-cli delete/uninstall` Commands
- [ ] Review/Update `delete` and `uninstall` commands to correctly handle:
    - Removing blueprint source from `get_user_blueprints_dir()`.
    - Removing compiled binaries from `get_user_bin_dir()`.
    - Options to remove only source, only binary, or both.

### 1.8. CLI Command Test Coverage
- [ ] Ensure core CLI commands (`list`, `install`, `compile`, `launch`, `delete`) achieve at least 80% test coverage.
    - [ ] Identify gaps using `coverage report`.
    - [ ] Add missing unit and integration tests, particularly for edge cases and error handling.

## Phase 2: Documentation & Onboarding

### 2.1. Core Documentation Updates
- [x] **README.md:** Update Quickstart, Core Concepts, Building Standalone Executables, Installation, and CLI Reference to reflect the new `install` (source), `compile` (binary), `list --available` workflow. (Draft provided, pending review)
- [ ] **USERGUIDE.md:**
    - Detail the new XDG file locations.
    - Provide comprehensive usage instructions for `list`, `list --available`, `install`, `compile`, `launch`, `delete`, `uninstall`.
    - Include examples for each command and common troubleshooting tips (PATH issues, etc.).
- [ ] **DEVELOPMENT.md:**
    - Explain the internal architecture of the new blueprint management commands.
    - Detail how PyInstaller is invoked by `swarm-cli compile`.
    - Document the `abbreviation` metadata field and its use.
    - Explain XDG path management within the codebase.
    - Discuss implications for blueprint developers (e.g., ensuring their blueprints are PyInstaller-friendly if they have unusual dependencies).
- [ ] **CONFIGURATION.md:** Review for any impacts from the new CLI structure (likely minimal, but check).

### 2.2. CLI Onboarding & UX Polish
- [ ] Refactor CLI help output (`swarm-cli --help`, `swarm-cli <command> --help`) for S-tier onboarding:
    - Use color and emoji (if terminal supports).
    - Add a prominent "Quickstart" section at the top of main help.
    - List all commands with clear, one-line descriptions.
    - Add usage examples for every command.
    - Add a "What next?" section in main help.
- [ ] If `swarm-cli` is run with no arguments, show a welcome message and quickstart hints.
- [ ] If `swarm-cli run` (or `launch`) is run with no blueprint, suggest `swarm-cli list --available`.
- [ ] If `swarm-cli list` (default) is empty, suggest `swarm-cli list --available` and `swarm-cli install <name>`.
- [ ] Implement `swarm-cli onboarding` command to display UX-rich welcome, Quickstart, and blueprint discovery hints.
- [ ] Add command suggestions/typeahead/autocomplete for CLI (stretch goal).

### 2.3. Web UI — Team Launcher (High Priority)
- [ ] Add a minimal Web UI to launch multi‑agent teams from a simple dialog.
    - [ ] Page: `/teams/launch` with inputs: Team Blueprint (select), Task/Instruction (textarea), Model/Profile (select), Advanced (pre/listen/post hooks).
    - [ ] List available team blueprints via `/v1/models` (temporary) or a new `/v1/blueprints` endpoint.
    - [ ] Submit launches via OpenAI‑compatible `/v1/chat/completions` with `model=<blueprint>` and `messages=[...]`.
    - [ ] Streaming: render incremental output via SSE from `/v1/chat/completions` when `stream=true`.
    - [ ] Auth: respect `ENABLE_API_AUTH` (token header) and session login when enabled.
    - [ ] Toggle by `ENABLE_WEBUI=true` in env and Docker compose; default off.
- [ ] Add server routes to serve the Team Launcher and static assets (Django templates under `src/swarm/templates/`).
- [ ] API support (if needed for richer metadata):
    - [ ] `/v1/blueprints` returns id, description, tags (e.g., `team`), abbreviation, installed/compiled status.
    - [ ] Optional: `/v1/blueprints/<id>` for details and example prompts.
- [ ] Tests:
    - [ ] View renders with and without auth enabled.
    - [ ] Launch POST streams chunks and completes.
    - [ ] Blueprint list is populated and filtered by `team` tag where present.
- [ ] Docs: add a short “Web UI: Team Launcher” section to README + QUICKSTART.

## Phase 3: Advanced Features & Refinements

### 3.1. `swarm-wrapper` (Alternative Compilation Strategy - Re-evaluate)
- [ ] Re-evaluate the `swarm-wrapper` concept (`src/swarm/core/swarm_wrapper.py` and `build_swarm_wrapper.py`).
    - **Current Plan:** Focus on compiling individual blueprints directly using PyInstaller via `swarm-cli compile`.
    - **Alternative:** `swarm-wrapper` is a single PyInstaller-compiled binary that can run *any* installed blueprint source. `swarm-cli install <bp>` would then just create a symlink/shell script like `~/.local/bin/<bp> -> ~/bin/swarm-wrapper <bp>`.
    - **Decision:** Stick with direct blueprint compilation for now unless `swarm-wrapper` offers significant advantages not yet realized (e.g., much faster "installs" after initial `swarm-wrapper` build, smaller total disk footprint if many blueprints). The current plan provides more isolation.

### 3.2. Multi-Agent Orchestration (Zeus) Tasks
- [ ] Implement Zeus blueprint to read `TODO.md` via `read_file_tool` and parse tasks.
- [ ] Add planning step in Zeus using `blueprint_tool('suggestion')` to select the next task.
- [ ] Dispatch tasks to a worker blueprint (e.g., Codey) via `blueprint_tool('codey')` and capture results.
- [ ] Implement verification step using `blueprint_tool('suggestion')` to confirm task completion.
- [ ] Use `write_file_tool` in Zeus to update `TODO.md`, marking completed tasks.
- [ ] Write integration tests in `tests/blueprints/test_zeus_workflow.py` covering end-to-end orchestration.

### 3.3. API Enhancements
- [ ] Expose blueprint metadata (including installed/compiled status, tags) via a REST API endpoint for Web UI/discovery (`/v1/blueprints`).

### 3.4. Code Quality & Automation
- [ ] Add blueprint metadata linting as a required pre-commit hook (`swarm-cli blueprint lint` if such a command is created, or a custom script).
- [ ] Add script to auto-generate a blueprint metadata table for README.md from class metadata.
- [ ] Review codebase for stubs, TODOs, and placeholders; add actionable, specific items to this list for each.

## Phase 4: Testing & CI

### 4.1. Critical Missing Tests (from original TODO)
- [x] Test XDG config discovery and fallback order.
- [x] Test default config auto-generation when no config is found.
- [x] Test envvar/placeholder substitution in config loader.
- [ ] Test per-blueprint and per-agent model override logic.
- [ ] Test fallback to default model/profile with warning if requested is missing.
- [ ] Test MCP server config add/remove/parse.
- [ ] Test redaction of secrets in logs and config dumps.
- [x] Test Geese/Omniplex async generator mocking and execution flow.
- [x] Test Geese splash screen and operation box display.
- [x] Test WhingeSurf subprocess management and service integration.
- [x] Test WTF blueprint config loading and agent hierarchy.
- [x] Test Geese MCP assignment logic.
- [x] Test Jeeves progressive tool and spinner/box UX.
- [x] Fix `TypeError: Can't instantiate abstract class BlueprintUXImproved/BlueprintUX` in various blueprint tests.

### 4.2. New Tests for Blueprint Management
- [ ] Comprehensive tests for `swarm-cli install` with different source types.
- [ ] Tests for `swarm-cli compile`, checking for executable creation and basic functionality.
- [x] Tests for `swarm-cli list` (default and `--available`).
- [ ] Tests for `swarm-cli launch` with compiled blueprints.
- [ ] Tests for `swarm-cli delete/uninstall` ensuring correct removal of source/binaries.

## Phase 5: Existing UX & Feature Polish (from original TODO)

### 5.1. Unified UX Enhancements (Spinner, ANSI/Emoji Boxes)
- [x] Implement and verify enhanced ANSI/emoji operation boxes for search and analysis operations across all blueprints.
- [x] Implement spinner messages for Codey, Geese, Jeeves, RueCode, Zeus, WhingeSurf.
- [x] Codey CLI: Approval mode and github agent tests pass.
- [x] Codey CLI: Unified, visually rich ANSI/emoji box output.
- [x] Codey CLI: Progressive, live-updating search/analysis UX.
- [x] `output_utils`: `ansi_box` prints spinner state correctly.
- [x] GAWD CLI: Implement Shift-Tab toggle for auto-accept edits
- [x] GAWD CLI: Add light purple status bar for auto-accept mode
- [x] GAWD CLI: Show '? for shortcuts' in dark grey when auto-accept off
- [x] GAWD CLI: Implement terminal-width responsive input box
- [x] GAWD CLI: Add input history display in grey
- [x] GAWD CLI: Add response generation status line with timer and token count
- [x] GAWD CLI: Handle multi-line pasted content with line count display
  (shows first 4 lines + "... +X lines" indicator for longer outputs)
- [ ] GAWD CLI: Implement solid block input marker
- [ ] Extend unified output/UX to other blueprints (e.g., `django_chat`, `mcp_demo`, etc.) and ensure all use `ansi_box`/`print_operation_box`.
- [ ] GAWD CLI: Add tests for new input/output features
- [ ] Refactor spinner/operation progress so that live line/progress updates are available in real (non-test) mode.
- [ ] Add more result types, summaries, and param details to operation boxes.
- [ ] Add tests for output formatting and UX regressions.
- [ ] Implement command stdout rendering (styling, truncation).
- [ ] Refactor Codey CLI wrapper to use Rich Console for styled I/O.

### 5.2. Slash Commands & Hooks
- [ ] Document `--pre`, `--listen`, and `--post` flags comprehensively.
- [ ] Document slash-command REPL behavior.
- [ ] Extend interactive shell to support slash commands from config.
- [ ] Add support for per-hook message overrides (`--pre-msg`, etc.).
- [ ] Add integration tests for hook chaining.
- [ ] Add unit tests for `BlueprintFunctionTool` and `blueprint_tool()`.
- [ ] Add tests for slash-command REPL parsing.

### 5.3. Session Management
- [ ] Implement `swarm-cli session list` and `swarm-cli session show` to inspect past chat sessions from `~/.cache/swarm/sessions`.

### 5.4. Chatbot-Army Backlog Items (from original TODO)
- [x] Session Audit Trail (`--audit`).
- [x] Desktop Notifications.
- [x] Granular Approval Hooks.
- [ ] Write-Sandbox Enforcement.
- [ ] git-diff Summariser tool.
- [ ] Project Doc Loader for `--full-context`.
- [ ] Autogen PyInstaller Spec Files script.
- [ ] Flaky-Test Detector CI job.
- [ ] MCP Mock Server fixture.
- [ ] Multimodal Input Preview (`--image`).
- [ ] Streaming Token Output mode.
- [ ] WhingeSurf Async Subprocess UX (ensure LLM can yield control while process runs, add demo CLI).

### 5.5. Per-Blueprint QA & Packaging (from original TODO)
- [ ] For **each** blueprint:
    - [ ] Review docstring & README.
    - [ ] Document required env vars.
    - [ ] Run/update tests (aim for >=80% coverage).
    - [ ] Verify `swarm-cli launch <compiled_name> --instruction "ping"` works.
    - [ ] Confirm standalone run (direct execution of compiled binary) matches `swarm-cli launch`.
    - [ ] (Optional) Add GitHub Action job for standalone binary smoke-test.

## Phase 6: Advanced Agent Capabilities & Refinements

### 6.1. Agent Configuration Review
- [ ] **Investigate `AgentConfig` Redundancy:**
    - Review the usage of `src/swarm/core/agent_config.py`.
    - Evaluate if agent configuration within `open-swarm` can be simplified by aligning more closely with the `openai-agents` SDK's direct `Agent` class instantiation parameters (e.g., `instructions`, `model`, `model_settings`, `tools`) and its `context` mechanism.
    - Goal: Reduce potential redundancy and simplify agent configuration if feasible, potentially removing `AgentConfig` if SDK patterns are sufficient.

### 6.2. Implement Agent Feedback Loop via Hooks
- [ ] **Develop Agent Feedback Mechanism using Hooks:**
    - **Target Blueprint:** Start with `JeevesBlueprint`.
    - **Scenario:** Intercept the output of the `Mycroft` agent (web search tool) using an agent hook on `Jeeves`.
    - **Feedback Agent:**
        - Create a new, simple "CritiqueAgent" or "FeedbackAgent".
        - Its `instructions` will be to review provided input (original query + Mycroft's search results) and offer critical feedback (e.g., relevance, completeness, conciseness).
    - **Hook Implementation:**
        - The hook (e.g., `on_tool_result` for Mycroft, or `after_llm_call` if Jeeves processes Mycroft's raw output first) will:
            - Receive Mycroft's output.
            - Instantiate and run the `FeedbackAgent` with the original user query and Mycroft's results.
            - Capture the critique from the `FeedbackAgent`.
    - **Integration:**
        - Decide how Jeeves will use the critique:
            - Option A: Append the critique to Mycroft's results before Jeeves formulates its final response.
            - Option B: Allow Jeeves to use the critique to potentially re-query Mycroft or adjust its final synthesis.
    - **Goal:** Demonstrate how hooks can be used to introduce a review/feedback layer into an agent's workflow, potentially replacing or augmenting an "agent-as-tool" pattern with a more dynamic interaction.
    - Add tests for the hook and feedback agent interaction.

This revised TODO list prioritizes getting the new blueprint management lifecycle functional and documented.

---

## New: Web UI + API for Blueprint Requirements and CRUD

### A. MCP Compliance Visibility (Web UI)
- [x] Add endpoint GET /blueprint-library/requirements/ returning per-blueprint MCP compliance against active config (status, missing servers, unresolved env, etc.).
- [x] Extend discovery to pass through required_mcp_servers and env_vars metadata.
- [x] Add MCP status badges to blueprint library cards with quick link to settings.
- [x] Add unit test for the JSON endpoint.

### B. Simple Blueprints API (CRUD + Filtering)
- [x] GET /v1/blueprints/ supports search and required_mcp filters.
- [x] GET /v1/blueprints/custom/ lists custom blueprints with search, tag, category filters.
- [x] POST /v1/blueprints/custom/ creates a custom blueprint entry in JSON library.
- [x] GET /v1/blueprints/custom/<id>/ retrieves a custom blueprint entry.
- [x] PATCH|PUT /v1/blueprints/custom/<id>/ updates fields.
- [x] DELETE /v1/blueprints/custom/<id>/ removes entry.
- [ ] Tests for CRUD endpoints (create, read, update, delete, filters).
- [ ] Docs: Usage examples and filtering syntax.

Notes:
- Scope intentionally avoids DB migrations; uses JSON-backed library.
- Clients infer MCP requirements from blueprint contents and optional metadata.

---

## New: Authentication — SAML 2.0 IdP (djangosaml2idp)

### Milestone: Optional IdP at /idp (same host)
- [x] Feature flag `ENABLE_SAML_IDP` in settings; add `djangosaml2idp` to `INSTALLED_APPS` when enabled.
- [x] URLs: include `djangosaml2idp.urls` at `/idp/` when enabled.
- [x] Add docs (`docs/auth_saml_idp.md`) for enabling, endpoints, and configuration.
- [ ] Provide production‑ready SAML settings (signing/encryption, certs) via environment.
- [ ] Add admin or config loader to manage SP entries (SAML_IDP_SPCONFIG) securely.
- [ ] Verify integration against a sample Service Provider (SP) end‑to‑end.

### TDD: Tests
- [ ] URL inclusion test: with `ENABLE_SAML_IDP=true` and stubbed `djangosaml2idp.urls`, GET `/idp/metadata/` returns 200.
- [ ] Settings test: when enabled, `SAML_IDP_SPCONFIG` is present and dict‑typed.
- [ ] Security test: ensure no secrets/keys are committed; enforce env‑only provisioning in CI.

---

## New: MCP Server Integration — Host Blueprints via `django-mcp-server`

Research & Plan
- [ ] Review `omarbenhamid/django-mcp-server` README and examples.
- [ ] Determine adapter layer to expose blueprint execution as MCP tools:
  - Map blueprint `run()`/CLI to MCP tool calls (name, args schema, streaming?).
  - Define safe, templated MCP config (no secrets) for each blueprint.
- [ ] Hosting model:
  - Serve MCP over the same Django site (e.g., `/mcp/`), leveraging `django-mcp-server` routing.
  - AuthZ/AuthN integration with Open Swarm’s settings (optionally SAML IdP).
- [ ] Developer UX:
  - Document how to register blueprints as MCP tools.
  - CLI examples for discovery and invocation.
- [ ] Tests:
  - TDD minimal tool exposure for one example blueprint (e.g., `suggestion`).
  - E2E invocation via MCP client (mock) returning expected output.
  - Security: ensure no sensitive env leaks in tool schemas.
