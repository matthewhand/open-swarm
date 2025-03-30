# Open Swarm

<div align="center">
<img src="assets/images/openswarm-project-image.jpg" alt="Project Logo" width="70%"/>
</div>

**Open Swarm** is a Python framework for creating, managing, and deploying autonomous agent swarms. It leverages the `openai-agents` library for core agent functionality and provides a structured way to build complex, multi-agent workflows using **Blueprints**.

---

## Core Concepts

*   **Agents:** Individual AI units performing specific tasks, powered by LLMs (like GPT-4, Claude, etc.). Built using the `openai-agents` SDK.
*   **Blueprints:** Python classes (`BlueprintBase` subclasses) defining a swarm's structure, agents, coordination logic, and external dependencies (like required environment variables or MCP servers). They act as reusable templates for specific tasks (e.g., code generation, research, data analysis).
*   **MCP (Mission Control Platform) Servers:** Optional external processes providing specialized capabilities (tools) to agents, such as filesystem access, web browsing, database interaction, or interacting with specific APIs (Slack, Monday.com, etc.). Agents interact with MCP servers via a standardized communication protocol.
*   **Configuration (`swarm_config.json`):** A central JSON file defining available LLM profiles (API keys, models) and configurations for MCP servers. Typically managed via `swarm-cli` in `~/.config/swarm/`.
*   **`swarm-cli`:** A command-line tool for managing blueprints (adding, listing, running, installing) and the `swarm_config.json` file. Uses XDG directories for storing blueprints (`~/.local/share/swarm/blueprints/`) and configuration (`~/.config/swarm/`).
*   **`swarm-api`:** A launcher for the Django/DRF backend that exposes installed blueprints via an OpenAI-compatible REST API (`/v1/models`, `/v1/chat/completions`).

---

## Quickstart (Docker - Recommended)

This is the easiest and recommended way to get started, especially for deploying the API service.

**Prerequisites:**
*   Docker ([Install Docker](https://docs.docker.com/engine/install/))
*   Docker Compose ([Install Docker Compose](https://docs.docker.com/compose/install/))

**Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/matthewhand/open-swarm.git
    cd open-swarm
    ```

2.  **Configure Environment:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit `.env` and add your necessary API keys (e.g., `OPENAI_API_KEY`).

3.  **Configure Docker Compose Overrides (Optional but Recommended):**
    *   Copy the override example:
        ```bash
        cp docker-compose.override.yaml.example docker-compose.override.yaml
        ```
    *   Edit `docker-compose.override.yaml` to:
        *   Mount any local directories containing custom blueprints you want the API server to access (e.g., uncomment and adjust the `./my_custom_blueprints:/app/custom_blueprints:ro` line).
        *   Make any other necessary adjustments (ports, environment variables, etc.).

4.  **Start the Service:**
    ```bash
    docker compose up -d
    ```
    This will build the image (if not already pulled/built) and start the `open-swarm` service, exposing the API on port 8000 (or the port specified in your `.env`/override).

5.  **Verify API:**
    *   Check the available models (blueprints):
        ```bash
        curl http://localhost:8000/v1/models
        ```
    *   Send a chat completion request:
        ```bash
        curl http://localhost:8000/v1/chat/completions \
          -H "Content-Type: application/json" \
          -d '{
                "model": "echocraft",
                "messages": [{"role": "user", "content": "Hello Docker!"}]
              }'
        ```
        *(Replace `echocraft` with a blueprint name available in your mounted volumes or the base image).*

---

## Usage Modes

Open Swarm offers several ways to interact with your blueprints:

1.  **Run via `swarm-api` (OpenAI-Compatible REST API):**
    *   **How:** Start the Django server (`uv run python manage.py runserver` or via Docker as shown above).
    *   **What:** Exposes blueprints listed in `settings.BLUEPRINT_DIRECTORY` (within the Docker container, this typically includes `/app/blueprints` and any volumes mounted in the override file) via `/v1/models` and `/v1/chat/completions`.
    *   **Auth:** If `SWARM_API_KEY` is set in `.env`, requests require an `Authorization: Bearer <your_key>` header. Otherwise, access is anonymous.
    *   **Security:** **Warning:** Running with anonymous access, especially when bound to `0.0.0.0`, can be insecure if blueprints have access to sensitive operations (filesystem, shell commands). **Setting `SWARM_API_KEY` is highly recommended for non-local deployments.**
    *   **(TODO) Web UI:** A future mode will integrate a simple web chat interface with the API server.

2.  **Run via `swarm-cli run`:**
    *   **How:** `swarm-cli run <blueprint_name> --instruction "Your single instruction"`
    *   **What:** Executes a blueprint managed by `swarm-cli` (located in `~/.local/share/swarm/blueprints/`) directly in the terminal. Uses configuration from `~/.config/swarm/swarm_config.json`.
    *   **Interactive Mode:** If you omit the `--instruction` argument (`swarm-cli run <blueprint_name>`), it will enter an interactive chat mode in the terminal.
    *   **Use Case:** Good for testing, debugging, interactive sessions, or running specific tasks locally without the API overhead.

3.  **Run via `swarm-cli install`:**
    *   **How:** `swarm-cli install <blueprint_name>`, then run `<blueprint_name> --instruction "..."`
    *   **What:** Creates a standalone executable for a managed blueprint using PyInstaller and places it in the user's binary directory (e.g., `~/.local/bin/` or similar, ensure it's in your `PATH`).
    *   **Use Case:** Convenient for frequently used blueprints that act like regular command-line tools.

4.  **Direct Python Execution:**
    *   **How:** `uv run python /path/to/your/blueprint_file.py --instruction "..."`
    *   **What:** Runs a specific blueprint Python file directly. Requires manual handling of configuration loading and dependencies.
    *   **Use Case:** Primarily for development and testing of a single blueprint file outside the managed environment.

---

## Further Documentation

This README provides a high-level overview and quickstart. For more detailed information, please refer to:

*   **User Guide (`USERGUIDE.md`):** Detailed instructions on using `swarm-cli` commands for managing blueprints and configuration.
*   **Development Guide (`DEVELOPMENT.md`):** Information for contributors and developers, including architecture details, testing strategies, project layout, and advanced topics like XDG paths and blueprint creation.
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
