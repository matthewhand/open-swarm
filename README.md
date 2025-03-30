# Open Swarm

<div align="center">
<img src="assets/images/openswarm-project-image.jpg" alt="Project Logo" width="70%"/>
</div>

**Open Swarm** is a Python framework for creating, managing, and deploying autonomous agent swarms. It leverages the `openai-agents` library for core agent functionality and provides a structured way to build complex, multi-agent workflows using **Blueprints**.

Open Swarm can be used in two primary ways:

1.  **As a CLI Utility (`swarm-cli`):** Manage, run, and install blueprints directly on your local machine. Ideal for personal use, testing, and creating standalone agent tools. (Recommended installation: PyPI)
2.  **As an API Service (`swarm-api`):** Deploy a web server that exposes your blueprints via an OpenAI-compatible REST API. Ideal for integrations, web UIs, and shared access. (Recommended deployment: Docker)

---

## Core Concepts

*   **Agents:** Individual AI units performing specific tasks, powered by LLMs (like GPT-4, Claude, etc.). Built using the `openai-agents` SDK.
*   **Blueprints:** Python classes (`BlueprintBase` subclasses) defining a swarm's structure, agents, coordination logic, and external dependencies (like required environment variables or MCP servers). They act as reusable templates for specific tasks (e.g., code generation, research, data analysis).
*   **MCP (Model Context Protocol) Servers:** Optional external processes providing specialized capabilities (tools) to agents, such as filesystem access, web browsing, database interaction, or interacting with specific APIs (Slack, Monday.com, etc.). Agents interact with MCP servers via a standardized communication protocol.
*   **Configuration (`swarm_config.json`):** A central JSON file defining available LLM profiles (API keys, models) and configurations for MCP servers. Typically managed via `swarm-cli` in `~/.config/swarm/`.
*   **`swarm-cli`:** A command-line tool for managing blueprints (adding, listing, running, installing) and the `swarm_config.json` file. Uses XDG directories for storing blueprints (`~/.local/share/swarm/blueprints/`) and configuration (`~/.config/swarm/`).
*   **`swarm-api`:** A launcher for the Django/DRF backend that exposes installed blueprints via an OpenAI-compatible REST API (`/v1/models`, `/v1/chat/completions`).

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

---

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or open an issue/pull request on the repository.

---

## License

Open Swarm is provided under the MIT License. Refer to the [LICENSE](LICENSE) file for full details.

---

## Acknowledgements

This project builds upon concepts and code from the `openai-agents` library and potentially other open-source projects. Specific acknowledgements can be found in `DEVELOPMENT.md` or individual source files.
