# Open Swarm

<div align="center">
<img src="assets/images/openswarm-project-image.jpg" alt="Project Logo" width="70%"/>
</div>

**Open Swarm** is a Python framework for creating, managing, and deploying autonomous agent swarms. It leverages the `openai-agents` library for core agent functionality and provides a structured way to build complex, multi-agent workflows using **Blueprints**.

Open Swarm can be used in two primary ways:

1.  **As a CLI Utility (`swarm-cli`):** Manage, run, and install blueprints directly on your local machine. Ideal for personal use, testing, and creating standalone agent tools. (Recommended installation: PyPI)
2.  **As an API Service (`swarm-api`):** Deploy a web server that exposes your blueprints via an OpenAI-compatible REST API. Ideal for integrations, web UIs, and shared access. (Recommended deployment: Docker)

---

## Configuration & Quickstart

See [CONFIGURATION.md](./CONFIGURATION.md) for a full guide to Swarm configuration—including LLM setup, MCP server integration, per-blueprint overrides, pricing, and CLI vs manual workflows.

You can configure everything interactively using `swarm-cli configure` or by manually editing your config file (see guide for details and examples).

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

## New in Geese: Notifier Abstraction & Reflection

- The Geese blueprint now uses a Notifier abstraction for all user-facing output (operation boxes, errors, info), enabling easy redirection to different UIs or for testing.
- Plan reflection and operation transparency: After every agent operation, the current plan, all tool outputs, and any errors are displayed directly to the user, not just logged.
- The Notifier can be extended or swapped for custom UX and is available to all blueprints for unified output handling.

See `src/swarm/blueprints/geese/README.md` for usage and extension details.

---

## Codex CLI Feature Parity Checklist

This project aims to provide full feature parity with the OpenAI Codex CLI. Below is a checklist of Codex features and their current status in Open Swarm/codey:

### ✅ Already Implemented
- Rich output/emoji/spinner UX (unified for search, analysis, file ops)
- Modular blueprint/agent system
- Basic interactive CLI mode
- Basic approval mode for some agent actions
- Syntax-highlighted code output
- Session/history management and overlays
- Full-context mode for large refactor/analysis
- Writable root/sandboxing CLI/config support
- Command suggestions/typeahead/autocomplete for CLI and slash commands
- Help and onboarding overlays
- Desktop notification support (optional)
- Dangerous auto-approve flag/UX
- Output formatting/full stdout option
- Image input (CLI/UX, future-proof)

### ⚠️ Partially Implemented
- Approval modes (full-auto, interactive, granular gating) for all actions
- Directory sandboxing (not enforced everywhere, no network controls)
- CLI/config file support (not unified or live-reloadable)
- Version control integration (git ops for suggest mode only)
- Slash commands: `/help`, `/model`, `/approval`, `/history`, `/ls`, `/cat`, `/edit`, `/compact` (some available)
- Project-level instructions auto-loading

### ❌ Not Yet Implemented
- Auto dependency install for generated code
- Automatic context/project file injection
- Plan/changelog file maintenance
- User feedback/correction loop
- Persistent session logging/audit trail
- Streaming token-by-token CLI output
- Non-interactive/CI/headless mode
- Multimodal input (screenshots/diagrams)
- Atomic commit/rollback for all agent actions
- Safety/ZDR org restrictions

---

**See the codey blueprint README for blueprint-specific feature status and TODOs.**

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
        swarm-cli add ./path/to/downloaded/blueprint_echocraft.py

        # Example: Adding a directory containing a blueprint
        swarm-cli add ./my_custom_blueprints/agent_smith --name agent_smith
        ```

4.  **Run the Blueprint:**
    *   **Single Instruction:**
        ```bash
        swarm-cli run echocraft --instruction "Hello from CLI!"
        ```
    *   **Interactive Mode:**
        ```bash
        swarm-cli run echocraft
        # Now you can chat with the blueprint interactively
        ```

5.  **(Optional) Install as Command:**
    ```bash
    swarm-cli install echocraft
    # Now run (ensure ~/.local/share/swarm/bin is in your PATH):
    echocraft --instruction "I am a command now!"
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
    *   Chat: `curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "echocraft", ...}'` (Add `-H "Authorization: Bearer <key>"` if needed).

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

---

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or open an issue/pull request on the repository.

---

## License

Open Swarm is provided under the MIT License. Refer to the [LICENSE](LICENSE) file for full details.

---

## Acknowledgements

This project builds upon concepts and code from the `openai-agents` library and potentially other open-source projects. Specific acknowledgements can be found in `DEVELOPMENT.md` or individual source files.
