# Technical Guide: BlueprintBase with openai-agents

This document outlines the structure and usage of the `BlueprintBase` class designed to work with the `openai-agents` framework within the Open Swarm project.

## Core Concept

`BlueprintBase` provides a standardized way to define, configure, and run multi-agent systems (or single agents) built using the `openai-agents` library. It handles common tasks like configuration loading, agent creation, MCP server management, logging setup, and command-line execution.

## Key Components

### 1. `BlueprintBase` (Abstract Base Class)

Located in `src/swarm/extensions/blueprint/blueprint_base.py`.

-   **Inheritance:** Your specific blueprint class **must** inherit from `BlueprintBase`.
-   **Abstract Methods:** Implement `metadata(self)` and `create_agents(self)`. Decorator order: `@property` then `@abstractmethod`.
-   **`__init__(cli_args, cli_config_override)`:** Initializes config, loads profiles, creates agents, determines starting agent. Merges config. Sets `self.max_llm_calls`, `self.use_markdown`.
-   **`_determine_starting_agent()`:** Selects the first agent created as the default starting agent.
-   **`get_llm_profile(profile_name)`:** Retrieves LLM profile from `"llm"` config section. Handles API key injection and `${VAR}` substitution.
-   **`_start_required_mcp_servers(...)`:** Starts MCP servers listed in metadata. Reads config from `swarm_config.json["mcpServers"]` and substitutes `${VAR}`. Requires env vars in `.env`.
-   **`_run_non_interactive(instruction)`:** Core execution logic. Calls `await agents.Runner.run(starting_agent=..., input=...)`.
-   **`main()` (Class Method):** CLI entry point. Loads `.env`, parses args, sets up logging, instantiates blueprint, runs it.

### 2. Configuration Loading (`swarm_config.json`)

-   **`.env` File:** For secrets (`OPENAI_API_KEY`, `BRAVE_API_KEY`, etc.).
-   **`swarm_config.json` (or `--config-path`):** Contains `"llm"`, `"blueprints"`, and `"mcpServers"` sections.
-   **CLI Arguments:** `--profile`, `--config`, `--markdown`/`--no-markdown` provide overrides.

### 3. Agent & Tool Definition

-   **Model Agnosticism:** Use profile names in `Agent(model=...)`. Map names in `swarm_config.json["llm"]`. Omit `model` for default.
-   **Instructions:** Be detailed, include team roles/tools for delegation.
-   **Tools:** Use `@agents.function_tool` and `Agent.as_tool()`.
-   **Structured Output:** Use `output_type=YourTypedDict` in `Agent.__init__`.
-   **`env_vars` in Metadata:** List only env vars needed *directly* by blueprint tools (rare). Keys for LLMs/MCP servers belong in `.env`.

### 4. Running a Blueprint

-   `uv run python blueprints/<...>/<...>.py --instruction "..." [...]`

## Current Status & Known Issues

-   **Pytest:** Broken via `uv` (environment mismatch). **IGNORE PYTEST.**
-   **Direct Execution:** `echocraft`, `suggestion` run. `rue_code`, `stewie`, `gaggle`, `omniplex` refactored.
-   **`Runner.run` Hang:** May occur on complex tasks.
-   **`RunConfig`:** Unused by `Runner.run`.
-   **MCP Servers:** Env var substitution fixed. Startup requires keys/paths in `.env`. Dynamic lookup from config implemented.
-   **Markdown Rendering:** Flag exists but logic not implemented.
-   **`max_llm_calls`:** Loaded but not enforced.
-   **Unit Tests:** Old tests removed. New basic test `test_blueprint_base_new.py` added. Needs expansion.
