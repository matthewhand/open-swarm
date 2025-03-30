# Blueprints Overview

This directory contains example blueprints for the Open Swarm framework, showcasing agent coordination, external data handling, database operations, and more via parody-themed agent teams. Each blueprint achieves a practical outcome while demonstrating specific framework capabilities. Blueprints are generally ordered by complexity.

## Refactored Blueprints (Using `BlueprintBase`)

These blueprints have been updated to use the `BlueprintBase` class, `openai-agents` library conventions (like `Agent`, `@function_tool`, agent-as-tool delegation), and standardized configuration loading.

| Blueprint Name                  | CLI (`uv run ...`) Example Instruction                | What it Demonstrates                                                           | Key Features                                                              | MCP Servers Used (Examples) |
|---------------------------------|-------------------------------------------------------|--------------------------------------------------------------------------------|---------------------------------------------------------------------------|-----------------------------|
| **EchoCraft**                   | `--instruction "Repeat this message"`                 | Simplest blueprint, direct input echo                                          | Basic `BlueprintBase` structure, Agent `process` override                 | None                        |
| **Suggestion**                  | `--instruction "Topic: AI Ethics"`                    | Generating structured JSON output                                              | Agent `output_type=TypedDict`, JSON mode                                  | None                        |
| **Chatbot**                     | `--instruction "Tell me a joke"`                      | Basic single-agent conversation                                                | Standard `Agent` interaction with LLM                                     | None                        |
| **BurntNoodles**                | `--instruction "Check git status"`                    | Coordinating Git & testing tasks via function tools & agent delegation       | `@function_tool` for CLI commands, Agent-as-tool delegation             | None                        |
| **RueCode**                     | `--instruction "Refactor this python code..."`        | Multi-agent code generation/refactoring workflow                             | Agent-as-tool delegation, specialized agent roles (Coordinator, Code, etc.) | memory                      |
| **NebulaShellzzar**             | `--instruction "List files in /tmp"`                  | Matrix-themed sysadmin/coding tasks with delegation                        | Agent-as-tool delegation, `@function_tool` for shell/code analysis    | memory                      |
| **DigitalButlers**              | `--instruction "Search for nearby restaurants"`       | Delegating tasks requiring specific MCPs (search, home automation)         | Agent-as-tool delegation, MCP usage by specialist agents                  | duckduckgo-search, home-assistant |
| **DilbotUniverse (SQLite)**     | `--instruction "Start the SDLC"`                      | Comedic SDLC simulation, instructions loaded from SQLite                     | Agent-as-tool delegation, SQLite integration for dynamic prompts          | sqlite                      |
| **FamilyTies**                  | `--instruction "Create WP post titled 'Hello'..."`    | Coordinating WordPress operations via MCP                                    | Agent-as-tool delegation, specialized agent using specific MCP (WP)     | server-wp-mcp               |
| **MissionImprobable (SQLite)**  | `--instruction "Use RollinFumble to run 'pwd'"`       | Spy-themed ops, instructions from SQLite, multi-level delegation             | Agent-as-tool delegation, SQLite integration, MCP usage (fs, shell, mem)  | memory, filesystem, mcp-shell |
| **WhiskeyTangoFoxtrot**       | `--instruction "Find free vector DBs"`                  | Hierarchical agents tracking services using DB & web search                | Multi-level agent delegation, SQLite, various search/scrape/doc MCPs    | sqlite, brave-search, mcp-npx-fetch, mcp-doc-forge, filesystem |
| **DivineOps**                   | `--instruction "Design user auth API"`                | Large-scale SW dev coordination (Design, Implement, DB, DevOps, Docs)      | Complex delegation, wide range of MCP usage (search, shell, db, fs...)  | memory, filesystem, mcp-shell, sqlite, sequential-thinking, brave-search |
| **Gaggle**                      | `--instruction "Write story: cat library"`            | Collaborative story writing (Planner, Writer, Editor)                        | Agent-as-tool delegation, function tools for writing steps                | None                        |
| **MonkaiMagic**                 | `--instruction "List AWS S3 buckets"`                 | Cloud operations (AWS, Fly, Vercel) via direct CLI function tools          | `@function_tool` for external CLIs, agent-as-tool delegation            | mcp-shell (for Sandy)       |
| **UnapologeticPress (SQLite)** | `--instruction "Write poem: city rain"`               | Collaborative poetry writing by distinct "poet" agents, SQLite instructions | Agent-as-tool (all-to-all), SQLite, broad MCP usage                       | Various (see blueprint)     |
| **Omniplex**                    | `--instruction "Use filesystem to read README.md"`    | Dynamically routes tasks based on MCP server type (npx, uvx, other)      | Dynamic agent/tool creation based on available MCPs                     | Dynamic (all available)     |

## WIP / Needs Refactoring

These blueprints still use older patterns or have known issues (e.g., UVX/NeMo dependencies) and need refactoring to the `BlueprintBase` standard.

| Blueprint Name          | CLI      | Description                                                  | Status          |
|-------------------------|----------|--------------------------------------------------------------|-----------------|
| chucks_angels           | chuck    | Manages transcripts, compute, Flowise (UVX/NeMo WIP)         | Needs Refactor  |
| django_chat             | djchat   | Django-integrated chatbot example                            | Needs Review    |
| flock                   | flock    | (Details TBC)                                                | Needs Refactor  |
| messenger               | msg      | (Details TBC)                                                | Needs Refactor  |

## Configuration (`swarm_config.json`)

The framework uses a central `swarm_config.json` file (usually in the project root) to define:

*   **`llm`**: Profiles for different language models (provider, model name, API keys via `${ENV_VAR}`, base URL, etc.).
*   **`mcpServers`**: Definitions for starting external MCP servers. Each entry includes:
    *   `command`: The command to run (e.g., `npx`, `uvx`, `python`, `docker`). Can be a string or list.
    *   `args`: A list of arguments for the command.
    *   `env`: A dictionary of environment variables to set for the server process.
    *   `cwd`: (Optional) Working directory for the server process.
    *   `description`: (Optional) A human-readable description of the server's function.
    *   `startup_timeout`: (Optional) Seconds to wait for the server to start and connect (default: 30).
*   **`blueprints`**: Optional section for blueprint-specific overrides (e.g., default profile, max calls).
*   **`defaults`**: Global default settings (e.g., `default_markdown_cli`).

## Environment Variables

Many blueprints or their required MCP servers depend on environment variables (e.g., API keys). These should ideally be set in a `.env` file in the project root. `BlueprintBase` will automatically load this file. See individual blueprint metadata (`env_vars`) or `swarm_config.json` for potentially required variables. The `BlueprintBase` will warn if variables listed in a blueprint's `metadata["env_vars"]` are not set.

## Running Blueprints (Development)

Use `uv run python <path_to_blueprint.py> --instruction "Your instruction"`

Common flags:
*   `--debug`: Enable detailed DEBUG logging.
*   `--quiet`: Suppress most logs, print only final output.
*   `--config-path`: Specify a different config file location.
*   `--profile`: Use a specific LLM profile from the config.
*   `--markdown` / `--no-markdown`: Force markdown rendering on/off.
