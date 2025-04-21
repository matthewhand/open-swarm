# 🚀 Open Swarm — S-Tier Onboarding

Welcome to Open Swarm! Orchestrate, manage, and run AI agent blueprints with S-tier onboarding and UX polish.

## Quickstart

1. List blueprints:
   ```bash
   swarm-cli list
   ```
2. Run the demo blueprint:
   ```bash
   swarm-cli run hello_world --instruction "Hello, world!"
   ```
3. Install as command:
   ```bash
   swarm-cli install hello_world
   ./hello_world "Hello, world!"
   ```

For advanced features, see below or run `swarm-cli help`.

# Open Swarm

<div align="center">
<img src="assets/images/openswarm-project-image.jpg" alt="Project Logo" width="70%"/>
</div>

**Open Swarm** is a Python framework for creating, managing, and deploying autonomous agent swarms. It leverages the `openai-agents` library for core agent functionality and provides a structured way to build complex, multi-agent workflows using **Blueprints**.

Open Swarm can be used in two primary ways:

1.  **As a CLI Utility (`swarm-cli`):** Manage, run, and install blueprints directly on your local machine. Ideal for personal use, testing, and creating standalone agent tools. (Recommended installation: PyPI)
2.  **As an API Service (`swarm-api`):** Deploy a web server that exposes your blueprints via an OpenAI-compatible REST API. Ideal for integrations, web UIs, and shared access. (Recommended deployment: Docker)

---

## Development Setup (Editable Install)

If you are working from a cloned repository or developing Open Swarm locally, you must install the package in editable mode before using the CLI or API tools:

```bash
pip install -e .
```

This ensures that the `swarm-cli` and `swarm-api` commands point to the latest source code and are available in your PATH. After running this, you can use the CLI commands as described below.

---

## Configuration & Quickstart

See [CONFIGURATION.md](./CONFIGURATION.md) for a full guide to Swarm configuration—including LLM setup, MCP server integration, per-blueprint overrides, pricing, and CLI vs manual workflows.

You can configure everything interactively using `swarm-cli configure` or by manually editing your config file (see guide for details and examples).

> **Note:** In development mode, some CLI commands or features may differ from the published PyPI version. If you encounter issues, ensure you have run `pip install -e .` and that your environment is activated.

---

## Core Framework TODO

- [x] Unified interactive approval mode for all blueprints (core, CLI/API flag, boxed UX)
- [x] Enhanced ANSI/emoji output for search, analysis, and file ops (core BlueprintUX)
- [x] Custom spinner/progress messages (core and per-blueprint personality)
- [x] Persistent session logging/audit trail (core, opt-in per blueprint)
- [x] Automatic context/project file injection for agent prompts
- [x] User feedback/correction loop for agent actions
- [x] API/CLI flag for enabling/disabling advanced UX features
  - [x] Support desktop notifications (`--notify`)
  - [x] Support attaching image inputs (`--image`, `-i`)
  - [x] Support inspecting past sessions via `--view`, `-v`)
  - [x] Support opening instructions file with `--config`, `-c`)
  - [x] Support whitelisting sandbox write roots (`--writable-root`, `-w`)
  - [x] Support disabling project docs (`--no-project-doc`)
  - [x] Support full stdout (`--full-stdout`)
  - [x] Support dangerous auto-approve (`--dangerously-auto-approve-everything`)
  - [x] Support shell completion subcommand (`completion <bash|zsh|fish>`)
  - [x] Support full-context mode (`--full-context`, `-f`)
- [x] Model selection overlay and CLI/agent-specific support
- [x] Session/history management and overlays
- [x] Full-context mode for large refactor/analysis
- [x] Writable root/sandboxing CLI/config support
- [x] Command suggestions/typeahead/autocomplete for CLI and slash commands
- [x] Help and onboarding overlays
- [x] Desktop notification support (optional)
- [x] Dangerous auto-approve flag/UX
- [x] Output formatting/full stdout option
- [x] Image input (CLI/UX, future-proof)
- [ ] Security review: command sanitization, safe execution wrappers
- [ ] Documentation: core feature usage, extension points, UX guidelines

---

## 🚀 Unified Blueprint Search & Analysis UX

Open Swarm blueprints now deliver a consistent, branded, and user-friendly experience for all search and analysis operations. Each blueprint leverages:

- **ANSI/emoji result boxes** summarizing search/analysis results, parameters, and counts
- **Progress spinners** ("Generating...", "Taking longer than expected") with live line/progress updates
- **Distinct emoji branding** for each blueprint (e.g., 🌳 Family Ties, 🪶 Unapologetic Poets, 🦢 Gaggle)
- **Clear feedback** for subprocess management and onboarding

<!-- BLUEPRINT_TABLE_START -->
<!-- The following table is auto-generated. Do not edit manually. Run scripts/gen_blueprint_table.py to update. -->

| Emoji | Name | Description | Example Commands | Branding |
|-------|------|-------------|------------------|----------|
|  | `ChatbotBlueprint` | A basic conversational agent that responds to user input. |  |  |
|  | `ZeusBlueprint` | Zeus leads a pantheon for software dev & sysadmin tasks, coordinating via agent-as-tool delegation. (DivineOpsBlueprint merged into this) |  |  |
|  | `FamilyTiesBlueprint` | Manages WordPress content using Peter (coordinator) and Brian (WP manager via MCP). |  |  |
|  | `JeevesBlueprint` | Provides private web search (DuckDuckGo) and home automation (Home Assistant) via specialized agents (Jeeves, Mycroft, Gutenberg). |  |  |
|  | `MCPDemoBlueprint` | A scalable agent (Sage) demonstrating interaction with filesystem and memory MCP servers, supporting horizontal scaling and viral file operations. |  |  |
|  | `MissionImprobableBlueprint` | A cheeky team led by JimFlimsy (coordinator), CinnamonToast (strategist/filesystem), and RollinFumble (operative/shell). Uses SQLite for instructions. |  |  |
|  | `MonkaiMagicBlueprint` | A *Monkai Magic*-inspired crew managing AWS, Fly.io, and Vercel with pre-authenticated CLI tools and agent-as-tool delegation. |  |  |
|  | `NebulaShellzzarBlueprint` | A multi-agent blueprint inspired by The Matrix for system administration and coding tasks. |  |  |
|  | `OmniplexBlueprint` | Dynamically delegates tasks to agents (Amazo:npx, Rogue:uvx, Sylar:other) based on the command type of available MCP servers. |  |  |
|  | `PoetsBlueprint` | A swarm of agents embodying legendary poets, using SQLite for instructions, agent-as-tool for collaboration, and MCPs for creative augmentation. |  |  |
|  | `RueCode` | Generates, executes code, and interacts with the file system. |  |  |
|  | `SuggestionBlueprint` | An agent that provides structured suggestions using Agent(output_type=...). |  |  |
|  | `UnapologeticPoetsBlueprint` | A swarm of agents embodying legendary poets, using SQLite for instructions, agent-as-tool for collaboration, and MCPs for creative augmentation. |  |  |
|  | `WhiskeyTangoFoxtrotBlueprint` | Tracks free online services with SQLite and web search using a multi-tiered agent hierarchy. |  |  |
| 🤖 | `codey` | Code and semantic code search/analysis. | swarm-cli codey /codesearch recursion . 5<br>swarm-cli codey /semanticsearch asyncio . 3 | Unified ANSI/emoji box UX, spinner, progress, summary |
| 🦢 | `gaggle` | Minimal test/demo search blueprint. | swarm-cli gaggle /search alpha . 5<br>swarm-cli gaggle /analyze beta . 2 | Unified ANSI/emoji box UX, spinner, progress, summary |
|  | `DivineOpsBlueprint` (historical, merged into ZeusBlueprint) |  |  |  |
|  | `divine_code` (historical, merged into ZeusBlueprint) |  |  |  |
<!-- BLUEPRINT_TABLE_END -->

- All commands support `/analyze` as well as `/search` (e.g., `/analyze beta . 5`).
- Try the commands above to see the new UX in action!

### Key Features
- **Result counts** and summaries in every result box
- **Live progress updates** during long-running operations
- **Custom spinner messages** for clear feedback
- **Fallback echo** for other commands, always in a result box

---

## 🚀 Unified Spinner and Result Output for Blueprints

All blueprints must use `print_search_progress_box` for spinner/progress/result output. See [`src/swarm/blueprints/blueprint_template.py`](src/swarm/blueprints/blueprint_template.py) for a canonical implementation.

- Distinguish between code and semantic search.
- Show spinner sequence: "Generating.", "Generating..", "Generating...", "Running...", and "Generating... Taking longer than expected".
- Update line numbers and result counts during progress.
- Always emit a summary/result box at the end.
- Pass all test suite checks for spinner/result output.

**Review Checklist:**
- [ ] Uses `print_search_progress_box` for all output
- [ ] Distinguishes code/semantic search
- [ ] Shows spinner sequence and “Taking longer than expected”
- [ ] Progress boxes update lines/results
- [ ] Passes all tests

---

## Blueprint UX Compliance & Test Mode

Open Swarm blueprints must provide a consistent, user-friendly CLI experience. All blueprints must:
- Display custom spinner messages: `Generating.`, `Generating..`, `Generating...`, `Running...`, and `Generating... Taking longer than expected` for long operations.
- Use ANSI/emoji boxes to summarize operations, results, and parameters (see `print_search_progress_box`).
- Clearly distinguish between code search, semantic search, and analysis operations in the output.
- In test mode (`SWARM_TEST_MODE=1`), output must be deterministic and include all spinner/box states for compliance tests.
- For more, see `docs/blueprint_standards.md` and `docs/blueprint_test_mode_ux.md`.

To check compliance or debug output, run:
```bash
uv run pytest -v tests/blueprints
```

For automated compliance checking, see `scripts/check_ux_compliance.py`.

---

## What to Try Next

- **Try Code Search:**
  - `swarm-cli codey /codesearch <keyword> <path> <max_results>`
  - Example: `swarm-cli codey /codesearch recursion . 5`
  - Try `/semanticsearch` for semantic code search with rich result boxes, result counts, and progressive spinner.

- **Try WhingeSurf Async UX:**
  - `swarm-cli whinge_surf !run sleep 2`
  - Then: `swarm-cli whinge_surf !status <process_id>`
  - Demonstrates async subprocess management and status polling.

- **Discover Blueprints:**
  - `swarm-cli info <blueprint>`
  - Shows blueprint description, usage, and onboarding tips.

- **Get Help:**
  - `swarm-cli --help` or `swarm-cli codey --help`
  - For onboarding, command list, and usage examples.

---

## Core Concepts

*   **Agents:** Individual AI units performing specific tasks, powered by LLMs (like GPT-4, Claude, etc.). Built using the `openai-agents` SDK.
*   **Blueprints:** Python classes (`BlueprintBase` subclasses) defining a swarm's structure, agents, coordination logic, and external dependencies (like required environment variables or MCP servers). They act as reusable templates for specific tasks (e.g., code generation, research, data analysis).
*   **MCP (Model Context Protocol) Servers:** Optional external processes providing specialized capabilities (tools) to agents, such as filesystem access, web browsing, database interaction, or interacting with specific APIs (Slack, Monday.com, etc.). Agents interact with MCP servers via a standardized communication protocol.
*   **Configuration (`swarm_config.json`):** A central JSON file defining available LLM profiles (API keys, models) and configurations for MCP servers. Typically managed via `swarm-cli` in `~/.config/swarm/`.
*   **`swarm-cli`:** A command-line tool for managing blueprints (adding, listing, running, installing) and the `swarm_config.json` file. Uses XDG directories for storing blueprints (`~/.local/share/swarm/blueprints/`) and configuration (`~/.config/swarm/`).
*   **`swarm-api`:** A launcher for the Django/DRF backend that exposes installed blueprints via an OpenAI-compatible REST API (`/v1/models`, `/v1/chat/completions`).

---

## Installation

### Option 1: Install from PyPI (Recommended for most users)

```bash
pip install open-swarm
```

This will install the `swarm-cli` and `swarm-api` command-line tools to your PATH (typically `~/.local/bin/` for user installs).

- Run `swarm-cli --help` or `swarm-api --help` to verify installation.

### Option 2: Install from Local Source (for development and testing)

Clone the repository and install in editable mode:

```bash
git clone https://github.com/matthewhand/open-swarm.git
cd open-swarm
pip install -e .
```

- This makes `swarm-cli` and `swarm-api` available from your local copy. Changes to the code are immediately reflected.
- You can now test your local changes before pushing to PyPI.

#### Local CLI Usage Example

```bash
swarm-cli --help
swarm-cli run hello_world --instruction "Hello from CLI!"
python src/swarm/blueprints/hello_world/blueprint_hello_world.py Hello from CLI!
./hello_world Hello from CLI!
swarm-api --help
```

If you do not see the commands in your PATH, ensure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Configuration Management & Secrets

Open Swarm uses a modern, XDG-compliant config structure:

- Main config: `~/.config/swarm/swarm_config.json`
- Secrets: `~/.config/swarm/.env`
- Example config: `swarm_config.json.example` (in project root)

### Deploying/Initializing Config

1.  **Copy the advanced example config:**
   ```bash
   cp ./swarm_config.json ~/.config/swarm/swarm_config.json
   ```
2.  **Copy your .env file:**
   ```bash
   cp .env ~/.config/swarm/.env
   ```

### Config Structure (Advanced Example)

Your `swarm_config.json` can include rich LLM profiles, MCP server definitions, and blueprint metadata. Example:

```json
{
  "llm": {
    "default": {
      "provider": "openai",
      "model": "${LITELLM_MODEL}",
      "base_url": "${LITELLM_BASE_URL}",
      "api_key": "${LITELLM_API_KEY}"
    },
    ...
  },
  "mcpServers": {
    "git": {
      "description": "Provides Git operations via Docker.",
      "command": "docker",
      "args": ["run", "--rm", ...]
    },
    ...
  },
  "blueprints": {
    "defaults": { "max_llm_calls": 10 },
    "MyBlueprint": { "llm_profile": "default" }
  }
}
```
- **Secrets** (like API keys) are always referenced as `${ENV_VAR}` in the config and stored in `.env`.

### Editing Config with `swarm-cli`

- Use `swarm-cli` to add/edit/remove/list:
  - LLMs
  - MCP servers
  - Blueprints
- When prompted for secrets, they are stored in `~/.config/swarm/.env`, not in the JSON.

---

## Environment Variables

Open Swarm and its blueprints use a variety of environment variables for configuration, security, and integration with external services. Set these in your shell, `.env` file, Docker environment, or deployment platform as appropriate.

### Core Framework Environment Variables

| Variable                 | Description                                                      | Default / Required         |
|--------------------------|------------------------------------------------------------------|----------------------------|
| `OPENAI_API_KEY`         | API key for OpenAI LLMs (used by agents and blueprints)           | Required for OpenAI usage  |
| `SWARM_API_KEY`          | API key for securing API endpoints (swarm-api)                   | Optional (recommended)     |
| `LITELLM_BASE_URL`       | Override base URL for LiteLLM/OpenAI-compatible endpoints        | Optional                   |
| `LITELLM_API_KEY`        | API key for LiteLLM endpoints                                    | Optional                   |
| `SWARM_CONFIG_PATH`      | Path to the main Swarm config file (`swarm_config.json`)          | `../swarm_config.json`     |
| `BLUEPRINT_DIRECTORY`    | Directory containing blueprint files                              | `src/swarm/blueprints`     |
| `DJANGO_SECRET_KEY`      | Django secret key (for API mode)                                 | Auto-generated/dev default |
| `DJANGO_DEBUG`           | Enable Django debug mode                                         | `True`                     |
| `DJANGO_ALLOWED_HOSTS`   | Comma-separated allowed hosts for Django API                      | `localhost,127.0.0.1`      |
| `API_AUTH_TOKEN`         | Token for authenticating API requests                            | Optional                   |
| `DJANGO_LOG_LEVEL`       | Log level for Django app                                         | `INFO`                     |
| `SWARM_LOG_LEVEL`        | Log level for Swarm app                                          | `DEBUG`                    |
| `REDIS_HOST`             | Host for Redis (if used)                                         | `localhost`                |
| `REDIS_PORT`             | Port for Redis (if used)                                         | `6379`                     |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF protection           | `http://localhost:8000,...`|
| `ENABLE_ADMIN`           | Enable admin web interface                                      | `false`                    |
| `ENABLE_API_AUTH`        | Require API authentication                                      | `true`                     |

#### Blueprint/Tool-Specific Variables
- Some blueprints and MCP tools may require additional env vars (e.g., Google API keys, Slack tokens, etc.).
- Refer to the blueprint's docstring or config for details.

#### Usage Example
```bash
export OPENAI_API_KEY="sk-..."
export SWARM_API_KEY="..."
export LITELLM_BASE_URL="https://open-litellm.fly.dev/v1"
# ... set other variables as needed
```

---

## Toolbox Functionality

Open Swarm ships with a growing toolbox of agent and blueprint utilities. All features listed below have robust, passing tests unless marked as **WIP** (Work In Progress).

### Task Scheduler Toolbox
- **Schedule jobs with `at`:**
  - Schedule a shell script or command to run at a specific time (uses the system `at` command).
  - **Test Status:** Passing
- **List scheduled `at` jobs:**
  - List all jobs currently scheduled with `at`.
  - **Test Status:** Passing
- **Remove `at` jobs:**
  - Remove a scheduled job by its job ID.
  - **Test Status:** Passing
- **Schedule jobs with `cron`:**
  - Schedule recurring jobs using cron expressions (uses the system `crontab`).
  - **Test Status:** Passing
- **List scheduled `cron` jobs:**
  - List all jobs currently scheduled with `crontab`.
  - **Test Status:** Passing
- **Remove `cron` jobs:**
  - Remove a scheduled cron job by its job ID.
  - **Test Status:** Passing

### Slash Command Framework
- **Global slash command registry:**
  - Blueprints can register and use slash commands (e.g., `/help`, `/agent`, `/model`).
  - Built-in demo commands: `/help`, `/agent`, `/model`.
  - **Test Status:** Passing
- **Blueprint Integration:**
  - Blueprints can access the global registry and add their own commands.
  - **Test Status:** Passing

#### Usage Example (Slash Commands)
```python
from swarm.extensions.blueprint.slash_commands import slash_command_registry

@slash_command_registry.register('/hello')
def hello_command(args):
    return f"Hello, {args}!"
```

#### Usage Example (Task Scheduler)
```python
from swarm.extensions.task_scheduler_toolbox import schedule_at_job, list_at_jobs, remove_at_job

job_id = schedule_at_job('/path/to/script.sh', run_time='now + 5 minutes')
jobs = list_at_jobs()
remove_at_job(job_id)
```

---

## CLI Reference

### swarm-cli Usage

```shell
Usage: swarm-cli [OPTIONS] COMMAND [ARGS]...

Swarm CLI tool for managing blueprints.

Options:
  --install-completion          Install completion for the current shell.
  --show-completion             Show completion for the current shell, to copy it or customize the installation.
  --help                        Show this message and exit.

Commands:
  install   Install a blueprint by creating a standalone executable using PyInstaller.
  launch    Launch a previously installed blueprint executable.
  list      Lists available blueprints (bundled and user-provided) and/or installed executables.
```

### swarm-api Usage

```shell
# (No standalone swarm-api binary was found in dist/; see Docker/API section below for usage.)
```

---

## Developer Notes
- System dependencies are mocked in tests for CI and portability.
- Any toolbox feature not listed as **Passing** above is considered **WIP** and may not be stable.
- Contributions and feedback are welcome!

---

## Blueprint Metadata: Developer Guide

All blueprints must define a class-level `metadata` property for onboarding, CLI discovery, and documentation automation. This property should be a Python dictionary and include the following keys:

- `name`: The blueprint's canonical name (string)
- `emoji`: The blueprint's emoji branding (string)
- `description`: Short description for CLI/docs (string)
- `examples`: List of CLI example commands (list of strings)
- `commands`: List of supported commands (list of strings)
- `branding`: Description of the UX/branding features (string)

**Example:**
```python
class FamilyTiesBlueprint(BlueprintBase):
    metadata = {
        "name": "family_ties",
        "emoji": "🌳",
        "description": "Genealogy/family data search and analysis.",
        "examples": [
            "swarm-cli family_ties /search Smith . 5",
            "swarm-cli family_ties /analyze Johnson . 3"
        ],
        "commands": ["/search", "/analyze"],
        "branding": "Unified ANSI/emoji box UX, spinner, progress, summary"
    }
```

This metadata is used by the CLI for `swarm-cli blueprint list` and `swarm-cli blueprint info <name>`, and for onboarding/documentation automation. **Always update the `metadata` property when adding or modifying a blueprint.**

---

## Test Database Setup (Django + SQLite)

- The Django test database is configured to use a file in `/tmp` to avoid permission issues:
  - Path: `/tmp/tmp.FwE9ucN97b/test_db.sqlite3`
- Journal mode is set to `DELETE` for maximum compatibility and to avoid WAL file locking issues in CI and local runs.
- Before running tests, the test DB file is deleted to prevent corruption or stale locks.
- **Automated cleanup:** Use `make test` or run `bash scripts/pretest_cleanup.sh` before tests to automatically remove any stale test DB files in `/tmp`.
- If you encounter `readonly database` or `disk I/O error` during tests:
  1. Delete the test DB file manually: `rm -f /tmp/tmp.FwE9ucN97b/test_db.sqlite3`
  2. Or use `make pretest-clean` to remove all test DBs.
  3. Re-run your tests.
- For CI, add a pre-test cleanup step to always remove the test DB file before running tests (see `scripts/pretest_cleanup.sh`).
- To prevent DB lock/readonly errors, ensure `/tmp` has free space and is not mounted read-only.

---

## Troubleshooting
- Ensure `/tmp` has free space and is not mounted read-only.
- If you see persistent DB errors, check for OS-level security restrictions or concurrent test runs.

---

## Security
- Never commit `.env` or sensitive config files to version control.
- Review environment variable usage for API keys and secrets.

---

## Acknowledgements

This project builds upon concepts and code from the `openai-agents` library and potentially other open-source projects. Specific acknowledgements can be found in `DEVELOPMENT.md` or individual source files.

---

## License

Open Swarm is provided under the MIT License. Refer to the [LICENSE](LICENSE) file for full details.

---

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or open an issue/pull request on the repository.

---

## Quickstart for Contributors

- **Run all tests and check UX compliance:**
  ```bash
  uv run pytest -v tests/blueprints
  python scripts/check_ux_compliance.py
  ```
- **Check code style (lint):**
  ```bash
  ruff check .
  ```
- **Check coverage:**
  ```bash
  uv run pytest --cov=src --cov-report=term-missing tests/blueprints
  ```
- **Add new blueprints:**
  - Follow the standards in `docs/blueprint_standards.md` and `docs/blueprint_test_mode_ux.md`.
  - Ensure spinner/box/emoji/summary output is present in test mode (`SWARM_TEST_MODE=1`).
  - Add or update tests in `tests/blueprints/`.
- **CI/CD:**
  - All PRs are checked for spinner/box/emoji/summary compliance, lint, and coverage.
  - Warnings are surfaced for missing UX elements in test mode, but do not block merges.

See the docs and scripts for more details on compliance and extending Open Swarm.

---

## Quickstart 1: Using `swarm-cli` Locally (via PyPI)

This is the recommended way to use `swarm-cli` for managing and running blueprints on your local machine.

**Prerequisites:**
*   Python 3.10+
*   `pip` (Python package installer)

**Steps:**

1.  **Install `open-swarm` from PyPI:**
    ```bash
    pip install open-swarm
    ```
    *(Using a virtual environment is recommended: `python -m venv .venv && source .venv/bin/activate`)*

2.  **Initial Configuration (First Run):**
    *   The first time you run a `swarm-cli` command that requires configuration (like `run` or `config`), it will automatically create a default `swarm_config.json` at `~/.config/swarm/swarm_config.json` if one doesn't exist.
    *   You **must** set the required environment variables (like `OPENAI_API_KEY`) in your shell for the configuration to work. Create a `.env` file in your working directory or export them:
        ```bash
        export OPENAI_API_KEY="sk-..."
        # Add other keys as needed (GROQ_API_KEY, etc.)
        ```
    *   You can customize the configuration further using `swarm-cli config` commands (see `USERGUIDE.md`).

3.  **Add a Blueprint:**
    *   Download or create a blueprint file (e.g., `my_blueprint.py`). Example blueprints are available in the [project repository](https://github.com/matthewhand/open-swarm/tree/main/src/swarm/blueprints).
    *   Add it using `swarm-cli`:
        ```bash
        # Example: Adding a downloaded blueprint file
        swarm-cli add ./path/to/downloaded/blueprint_hello_world.py

        # Example: Adding a directory containing a blueprint
        swarm-cli add ./my_custom_blueprints/agent_smith --name agent_smith
        ```

4.  **Run the Blueprint:**
    *   **Single Instruction (recommended):**
        ```bash
        swarm-cli run hello_world --instruction "Hello from CLI!"
        ```
    *   **Interactive Mode:**
        ```bash
        swarm-cli run hello_world
        # Now you can chat with the blueprint interactively
        ```
    *   **Direct Python or Binary Execution:**
        ```bash
        python src/swarm/blueprints/hello_world/blueprint_hello_world.py Hello from CLI!
        ./hello_world Hello from CLI!
        ```

5.  **(Optional) Install as Command:**
    ```bash
    swarm-cli install hello_world
    # Now run (ensure ~/.local/share/swarm/bin is in your PATH):
    ./hello_world Hello from CLI!
    ```

---

## Quickstart 2: Deploying `swarm-api` Service (via Docker)

This section covers deploying the API service using Docker.

### Option A: Docker Compose (Recommended for Flexibility)

This method uses `docker-compose.yaml` and is best if you need to customize volumes, environment variables easily, or manage related services (like Redis).

**Prerequisites:**
*   Docker ([Install Docker](https://docs.docker.com/engine/install/))
*   Docker Compose ([Install Docker Compose](https://docs.docker.com/compose/install/))
*   Git

**Steps:**

1.  **Clone the Repository:** (Needed for `docker-compose.yaml` and config files)
    ```bash
    git clone https://github.com/matthewhand/open-swarm.git
    cd open-swarm
    ```

2.  **Configure Environment:**
    *   Copy `cp .env.example .env` and edit `.env` with your API keys (e.g., `OPENAI_API_KEY`, `SWARM_API_KEY`).

3.  **Prepare Blueprints & Config:**
    *   Place blueprints in `./blueprints`.
    *   Ensure `./swarm_config.json` exists and is configured.

4.  **Configure Overrides (Optional):**
    *   Copy `cp docker-compose.override.yaml.example docker-compose.override.yaml`.
    *   Edit the override file to mount additional volumes, change ports, etc.

5.  **Start the Service:**
    ```bash
    docker compose up -d
    ```

6.  **Verify API:** (Default port 8000)
    *   Models: `curl http://localhost:8000/v1/models`
    *   Chat: `curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "hello_world", ...}'` (Add `-H "Authorization: Bearer <key>"` if needed).

### Option B: Direct `docker run` (Simpler for Single Container)

This method runs the pre-built image directly from Docker Hub. Good for quick tests or simple deployments without cloning the repo. Customization requires careful use of `-v` (volume) and `-e` (environment) flags.

**Prerequisites:**
*   Docker ([Install Docker](https://docs.docker.com/engine/install/))

**Steps:**

1.  **Prepare Local Files (If Customizing):**
    *   Create a directory for your blueprints (e.g., `~/my_swarm_blueprints`).
    *   Create your `swarm_config.json` file locally (e.g., `~/my_swarm_config.json`).
    *   Create a `.env` file locally (e.g., `~/swarm.env`) with your API keys (`OPENAI_API_KEY`, `SWARM_API_KEY`, etc.).

2.  **Run the Container:**
    ```bash
    docker run -d \
      --name open-swarm-api \
      -p 8000:8000 \
      --env-file ~/swarm.env \
      -v ~/my_swarm_blueprints:/app/blueprints:ro \
      -v ~/my_swarm_config.json:/app/swarm_config.json:ro \
      -v open_swarm_db:/app/db.sqlite3 \
      --restart unless-stopped \
      mhand79/open-swarm:latest
    ```
    *   `-d`: Run detached (in background).
    *   `--name`: Assign a name to the container.
    *   `-p 8000:8000`: Map host port 8000 to container port 8000 (adjust if needed).
    *   `--env-file`: Load environment variables from your local file.
    *   `-v ...:/app/blueprints:ro`: Mount your local blueprints directory (read-only). **Required** if you want to use custom blueprints.
    *   `-v ...:/app/swarm_config.json:ro`: Mount your local config file (read-only). **Required** for custom LLM/MCP settings.
    *   `-v open_swarm_db:/app/db.sqlite3`: Use a named Docker volume for the database to persist data.
    *   `--restart unless-stopped`: Automatically restart the container unless manually stopped.
    *   `mhand79/open-swarm:latest`: The image name on Docker Hub.

3.  **Verify API:** (Same as Docker Compose)
    *   Models: `curl http://localhost:8000/v1/models`
    *   Chat: `curl http://localhost:8000/v1/chat/completions ...` (Add `-H "Authorization: Bearer <key>"` if needed).

---

## Usage Modes Summary

*   **`swarm-api` (via Docker or `manage.py runserver`):** Exposes blueprints as an OpenAI-compatible REST API. Ideal for integrations. Requires `SWARM_API_KEY` for security in non-local deployments.
*   **`swarm-cli run` (via PyPI install):** Executes managed blueprints locally, either with a single instruction or in interactive chat mode. Good for testing and local tasks.
*   **`swarm-cli install` (via PyPI install):** Creates standalone command-line executables from managed blueprints.
*   **Direct Python Execution (via Git clone):** Running `uv run python <blueprint_file.py>` is mainly for development and testing individual files.

---

## Further Documentation

This README provides a high-level overview and quickstart guides. For more detailed information, please refer to:

*   **User Guide (`USERGUIDE.md`):** Detailed instructions on using `swarm-cli` commands for managing blueprints and configuration locally.
*   **Development Guide (`DEVELOPMENT.md`):** Information for contributors and developers, including architecture details, testing strategies, project layout, API details, and advanced topics.
*   **Example Blueprints (`src/swarm/blueprints/README.md`):** A list and description of the example blueprints included with the framework, showcasing various features and integration patterns.
*   **Blueprint Patterns and Configuration (`blueprints/README.md`):** Guidance on creating and configuring blueprints, including best practices and common pitfalls. **Start here for blueprint usage and extension.**
*   **User Experience Standards (`UX.md`):** Guidelines for creating a consistent and user-friendly experience across blueprints and the Swarm framework.
*   **User Experience Standards (`UX.md`)**: Guidelines for creating a consistent and user-friendly experience across blueprints and the Swarm framework.

---

## Acknowledgements

This project builds upon concepts and code from the `openai-agents` library and potentially other open-source projects. Specific acknowledgements can be found in `DEVELOPMENT.md` or individual source files.

---

## License

Open Swarm is provided under the MIT License. Refer to the [LICENSE](LICENSE) file for full details.

---

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or open an issue/pull request on the repository.

---

## Quickstart 1: Using `swarm-cli` Locally (via PyPI)

This is the recommended way to use `swarm-cli` for managing and running blueprints on your local machine.

**Prerequisites:**
*   Python 3.10+
*   `pip` (Python package installer)

**Steps:**

1.  **Install `open-swarm` from PyPI:**
    ```bash
    pip install open-swarm
    ```
    *(Using a virtual environment is recommended: `python -m venv .venv && source .venv/bin/activate`)*

2.  **Initial Configuration (First Run):**
    *   The first time you run a `swarm-cli` command that requires configuration (like `run` or `config`), it will automatically create a default `swarm_config.json` at `~/.config/swarm/swarm_config.json` if one doesn't exist.
    *   You **must** set the required environment variables (like `OPENAI_API_KEY`) in your shell for the configuration to work. Create a `.env` file in your working directory or export them:
        ```bash
        export OPENAI_API_KEY="sk-..."
        # Add other keys as needed (GROQ_API_KEY, etc.)
        ```
    *   You can customize the configuration further using `swarm-cli config` commands (see `USERGUIDE.md`).

3.  **Add a Blueprint:**
    *   Download or create a blueprint file (e.g., `my_blueprint.py`). Example blueprints are available in the [project repository](https://github.com/matthewhand/open-swarm/tree/main/src/swarm/blueprints).
    *   Add it using `swarm-cli`:
        ```bash
        # Example: Adding a downloaded blueprint file
        swarm-cli add ./path/to/downloaded/blueprint_hello_world.py

        # Example: Adding a directory containing a blueprint
        swarm-cli add ./my_custom_blueprints/agent_smith --name agent_smith
        ```

4.  **Run the Blueprint:**
    *   **Single Instruction (recommended):**
        ```bash
        swarm-cli run hello_world --instruction "Hello from CLI!"
        ```
    *   **Interactive Mode:**
        ```bash
        swarm-cli run hello_world
        # Now you can chat with the blueprint interactively
        ```
    *   **Direct Python or Binary Execution:**
        ```bash
        python src/swarm/blueprints/hello_world/blueprint_hello_world.py Hello from CLI!
        ./hello_world Hello from CLI!
        ```

5.  **(Optional) Install as Command:**
    ```bash
    swarm-cli install hello_world
    # Now run (ensure ~/.local/share/swarm/bin is in your PATH):
    ./hello_world Hello from CLI!
    ```

---

## Quickstart 2: Deploying `swarm-api` Service (via Docker)

This section covers deploying the API service using Docker.

### Option A: Docker Compose (Recommended for Flexibility)

This method uses `docker-compose.yaml` and is best if you need to customize volumes, environment variables easily, or manage related services (like Redis).

**Prerequisites:**
*   Docker ([Install Docker](https://docs.docker.com/engine/install/))
*   Docker Compose ([Install Docker Compose](https://docs.docker.com/compose/install/))
*   Git

**Steps:**

1.  **Clone the Repository:** (Needed for `docker-compose.yaml` and config files)
    ```bash
    git clone https://github.com/matthewhand/open-swarm.git
    cd open-swarm
    ```

2.  **Configure Environment:**
    *   Copy `cp .env.example .env` and edit `.env` with your API keys (e.g., `OPENAI_API_KEY`, `SWARM_API_KEY`).

3.  **Prepare Blueprints & Config:**
    *   Place blueprints in `./blueprints`.
    *   Ensure `./swarm_config.json` exists and is configured.

4.  **Configure Overrides (Optional):**
    *   Copy `cp docker-compose.override.yaml.example docker-compose.override.yaml`.
    *   Edit the override file to mount additional volumes, change ports, etc.

5.  **Start the Service:**
    ```bash
    docker compose up -d
    ```

6.  **Verify API:** (Default port 8000)
    *   Models: `curl http://localhost:8000/v1/models`
    *   Chat: `curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "hello_world", ...}'` (Add `-H "Authorization: Bearer <key>"` if needed).

### Option B: Direct `docker run` (Simpler for Single Container)

This method runs the pre-built image directly from Docker Hub. Good for quick tests or simple deployments without cloning the repo. Customization requires careful use of `-v` (volume) and `-e` (environment) flags.

**Prerequisites:**
*   Docker ([Install Docker](https://docs.docker.com/engine/install/))

**Steps:**

1.  **Prepare Local Files (If Customizing):**
    *   Create a directory for your blueprints (e.g., `~/my_swarm_blueprints`).
    *   Create your `swarm_config.json` file locally (e.g., `~/my_swarm_config.json`).
    *   Create a `.env` file locally (e.g., `~/swarm.env`) with your API keys (`OPENAI_API_KEY`, `SWARM_API_KEY`, etc.).

2.  **Run the Container:**
    ```bash
    docker run -d \
      --name open-swarm-api \
      -p 8000:8000 \
      --env-file ~/swarm.env \
      -v ~/my_swarm_blueprints:/app/blueprints:ro \
      -v ~/my_swarm_config.json:/app/swarm_config.json:ro \
      -v open_swarm_db:/app/db.sqlite3 \
      --restart unless-stopped \
      mhand79/open-swarm:latest
    ```
    *   `-d`: Run detached (in background).
    *   `--name`: Assign a name to the container.
    *   `-p 8000:8000`: Map host port 8000 to container port 8000 (adjust if needed).
    *   `--env-file`: Load environment variables from your local file.
    *   `-v ...:/app/blueprints:ro`: Mount your local blueprints directory (read-only). **Required** if you want to use custom blueprints.
    *   `-v ...:/app/swarm_config.json:ro`: Mount your local config file (read-only). **Required** for custom LLM/MCP settings.
    *   `-v open_swarm_db:/app/db.sqlite3`: Use a named Docker volume for the database to persist data.
    *   `--restart unless-stopped`: Automatically restart the container unless manually stopped.
    *   `mhand79/open-swarm:latest`: The image name on Docker Hub.

3.  **Verify API:** (Same as Docker Compose)
    *   Models: `curl http://localhost:8000/v1/models`
    *   Chat: `curl http://localhost:8000/v1/chat/completions ...` (Add `-H "Authorization: Bearer <key>"` if needed).

---

## Usage Modes Summary

*   **`swarm-api` (via Docker or `manage.py runserver`):** Exposes blueprints as an OpenAI-compatible REST API. Ideal for integrations. Requires `SWARM_API_KEY` for security in non-local deployments.
*   **`swarm-cli run` (via PyPI install):** Executes managed blueprints locally, either with a single instruction or in interactive chat mode. Good for testing and local tasks.
*   **`swarm-cli install` (via PyPI install):** Creates standalone command-line executables from managed blueprints.
*   **Direct Python Execution (via Git clone):** Running `uv run python <blueprint_file.py>` is mainly for development and testing individual files.

---

## Further Documentation

This README provides a high-level overview and quickstart guides. For more detailed information, please refer to:

*   **User Guide (`USERGUIDE.md`):** Detailed instructions on using `swarm-cli` commands for managing blueprints and configuration locally.
*   **Development Guide (`DEVELOPMENT.md`):** Information for contributors and developers, including architecture details, testing strategies, project layout, API details, and advanced topics.
*   **Example Blueprints (`src/swarm/blueprints/README.md`):** A list and description of the example blueprints included with the framework, showcasing various features and integration patterns.
*   **Blueprint Patterns and Configuration (`blueprints/README.md`):** Guidance on creating and configuring blueprints, including best practices and common pitfalls. **Start here for blueprint usage and extension.**
*   **User Experience Standards (`UX.md`):** Guidelines for creating a consistent and user-friendly experience across blueprints and the Swarm framework.
*   **User Experience Standards (`UX.md`)**: Guidelines for creating a consistent and user-friendly experience across blueprints and the Swarm framework.

---

## Acknowledgements

This project builds upon concepts and code from the `openai-agents` library and potentially other open-source projects. Specific acknowledgements can be found in `DEVELOPMENT.md` or individual source files.

---

## License

Open Swarm is provided under the MIT License. Refer to the [LICENSE](LICENSE) file for full details.

---

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or open an issue/pull request on the repository.

---
