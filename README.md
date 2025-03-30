# Open Swarm

Open Swarm is a framework for creating, managing, and deploying autonomous agent swarms. It leverages the `openai-agents` library for core agent functionality and provides a structured way to build complex workflows using Blueprints.

## Core Concepts

*   **Agents:** Individual AI units performing specific tasks, powered by LLMs (like GPT-4, Claude, etc.). Built using the `openai-agents` SDK.
*   **Blueprints:** Python classes (`BlueprintBase` subclasses) defining a swarm's structure, agents, coordination logic, and external dependencies. They act as reusable templates for specific tasks (e.g., code generation, research, data analysis).
*   **MCP (Mission Control Platform) Servers:** External processes providing specialized capabilities (tools) to agents, such as filesystem access, web browsing, database interaction, or interacting with specific APIs (Slack, Monday.com, etc.). Agents interact with MCP servers via a standardized communication protocol.
*   **Configuration (`swarm_config.json`):** A central JSON file defining available LLM profiles (API keys, models) and configurations for MCP servers (command to run, environment variables, working directory).
*   **`swarm-cli`:** A command-line tool for managing blueprints (adding, listing, deleting), running them directly, installing them as standalone utilities, and managing the `swarm_config.json` file.

## Getting Started

1.  **Installation:**
    ```bash
    # Recommended: Use a virtual environment
    python -m venv .venv
    source .venv/bin/activate
    # Install using uv (faster pip alternative) or pip
    uv pip install -e .
    # Or: pip install -e .
    ```

2.  **Configuration:**
    *   The main configuration file is `swarm_config.json`. By default, `swarm-cli` looks for it in the XDG config directory: `~/.config/swarm/swarm_config.json`.
    *   Copy the example `swarm_config.json.example` from the project root to `~/.config/swarm/swarm_config.json` and populate it with your API keys (OpenAI, Brave Search, etc.) and any custom MCP server definitions.
    *   Create a `.env` file in the project root directory (where you run `swarm-cli` or your blueprint scripts from) for sensitive keys referenced in `swarm_config.json` (e.g., `${OPENAI_API_KEY}`).

3.  **Manage Blueprints with `swarm-cli`:**
    *   `swarm-cli` manages blueprint source code in the XDG data directory: `~/.local/share/swarm/blueprints/`.
    *   **Add a blueprint:**
        ```bash
        # Add from a directory
        swarm-cli add ./blueprints/echocraft --name echocraft
        # Add from a single file (name inferred)
        swarm-cli add ./my_blueprints/special_task.py
        ```
    *   **List blueprints:**
        ```bash
        swarm-cli list
        ```
    *   **Run a blueprint:**
        ```bash
        # Basic run
        swarm-cli run echocraft --instruction "Hello there!"

        # Run with a specific config profile and blueprint-specific args
        swarm-cli run my_complex_bp --profile cloud_llm --instruction "Analyze data in /data/input.csv" --output-file /results/output.json

        # Specify a different config file location for this run
        swarm-cli run my_complex_bp --config-path /alt/path/to/swarm_config.json --instruction "Do something"
        ```
        *(Note: Arguments after `--instruction` or other blueprint-defined arguments are passed directly to the blueprint's `main` method).*
    *   **Install as CLI command:** (Builds executable using PyInstaller)
        ```bash
        swarm-cli install echocraft
        # Now you can run: echocraft --instruction "This is easy!"
        # Executable is placed in ~/.local/bin/ (ensure this is in your PATH)
        ```
    *   **Delete a blueprint:**
        ```bash
        swarm-cli delete echocraft
        ```
    *   **Uninstall (blueprint source and/or CLI wrapper):**
        ```bash
        swarm-cli uninstall echocraft # Removes both source and wrapper
        swarm-cli uninstall echocraft --blueprint-only # Removes only source
        swarm-cli uninstall echocraft --wrapper-only # Removes only wrapper
        ```

4.  **Manage Configuration with `swarm-cli`:**
    *   Edits the default config file (`~/.config/swarm/swarm_config.json` unless overridden with `--config`).
    *   **List LLM profiles:**
        ```bash
        swarm-cli config list --section llm
        ```
    *   **Add/Update an LLM profile:**
        ```bash
        swarm-cli config add --section llm --name gpt-4o --json '{"provider": "openai", "model": "gpt-4o", "api_key": "${OPENAI_API_KEY}"}'
        ```
    *   **List MCP Servers:**
        ```bash
        swarm-cli config list --section mcpServers
        ```
    *   **Add/Update an MCP Server:**
        ```bash
        swarm-cli config add --section mcpServers --name my-custom-mcp --json '{"command": "/path/to/my/mcp/server.py", "args": ["--port", "9999"], "env": {"SPECIAL_FLAG": "true"}}'
        ```
    *   **Remove an entry:**
        ```bash
        swarm-cli config remove --section llm --name gpt-4o
        swarm-cli config remove --section mcpServers --name my-custom-mcp
        ```

## Directory Structure (XDG Compliance)

`swarm-cli` uses standard user directories:

*   **Configuration (`swarm_config.json`):**
    *   Linux/Unix: `$XDG_CONFIG_HOME/swarm/swarm_config.json` (Default: `~/.config/swarm/swarm_config.json`)
    *   macOS: `~/Library/Application Support/swarm/swarm_config.json` *(Note: Requires `platformdirs` integration)*
    *   Windows: `%APPDATA%\swarm\swarm\Config\swarm_config.json` *(Note: Requires `platformdirs` integration)*
*   **Managed Blueprint Sources:**
    *   Linux/Unix: `$XDG_DATA_HOME/swarm/blueprints/` (Default: `~/.local/share/swarm/blueprints/`)
    *   macOS: `~/Library/Application Support/swarm/blueprints/` *(Note: Requires `platformdirs` integration)*
    *   Windows: `%APPDATA%\swarm\swarm\Data\blueprints\` *(Note: Requires `platformdirs` integration)*
*   **Installed CLI Binaries:**
    *   Linux/Unix/macOS: `$HOME/.local/bin/`
    *   Windows: `%APPDATA%\Python\Scripts` or similar Python user script location. *(Ensure this is in your system PATH)*
*   **Build Cache (PyInstaller):**
    *   Linux/Unix: `$XDG_CACHE_HOME/swarm/build/` (Default: `~/.cache/swarm/build/`)
    *   macOS: `~/Library/Caches/swarm/build/` *(Note: Requires `platformdirs` integration)*
    *   Windows: `%LOCALAPPDATA%\swarm\swarm\Cache\build\` *(Note: Requires `platformdirs` integration)*

*(Note: Full cross-platform path support requires integrating the `platformdirs` library, which is a future enhancement.)*

## Development & Testing

*   **Setup:** Follow the installation steps using `-e .` for an editable install.
*   **Running Tests:**
    ```bash
    # Run unit tests (mostly framework logic)
    uv run pytest tests/unit/

    # Run blueprint integration tests (mocks externals like LLMs/MCPs)
    # Requires specific mocking setup or running relevant MCPs
    uv run pytest tests/blueprints/

    # Run specific tests
    uv run pytest tests/unit/test_config_loader.py

    # Run tests with specific markers (TODO: Implement markers)
    # uv run pytest -m llm # Example for LLM tests
    # uv run pytest -m mcp # Example for MCP tests
    ```
*   **Linting/Formatting:** (Assuming tools like ruff, black, isort are configured)
    ```bash
    uv run ruff check .
    uv run black .
    uv run isort .
    ```

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or open an issue/pull request on the repository.

