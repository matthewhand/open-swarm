# Open-Swarm - Agentic Blueprint Framework

**Version:** 0.2.9-quiet (Core)

**Status:** Actively Refactored - Utilizing `openai-agents`

## Overview

Open-Swarm has been refactored to leverage the official `openai-agents` library (previously known as Swarm). It provides a framework for building, configuring, and running multi-agent systems ("Blueprints").

Key focus areas:

1.  **Blueprints (`BlueprintBase`)**:
    *   Define multi-agent teams, their tools (functions or other agents), and instructions.
    *   Implement a standard interface for agent creation (`create_starting_agent`).
    *   Handle configuration loading (LLM profiles, MCP servers) with inheritance and overrides.
    *   Can be executed directly via CLI for development and testing.
2.  **Configuration (`swarm_config.json`)**:
    *   Centralized JSON configuration for LLM providers/models, MCP server commands, default settings, profiles, and blueprint-specific overrides.
    *   Supports environment variable substitution (`${VAR_NAME}`).
3.  **Execution Modes**:
    *   **Direct CLI**: Run blueprints using `uv run python blueprints/<name>/blueprint_<name>.py --instruction "..."`. Supports `--debug`, `--quiet`, `--config`, `--profile` flags.
    *   **(Planned/Future)** `swarm-api`: Serve blueprints as OpenAI-compatible API endpoints.
    *   **(Planned/Future)** `swarm-cli`: Package, install, and manage blueprints as standalone CLI tools.

## Refactoring Pattern (`BlueprintBase`)

The core refactoring uses the `src.swarm.extensions.blueprint.blueprint_base.BlueprintBase` abstract class. New blueprints should follow this pattern:

1.  **Inherit `BlueprintBase`**:
    ````python
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
    from agents import Agent, function_tool, Model, MCPServer # etc.
    from typing import Dict, Any, List, ClassVar

    class MyNewBlueprint(BlueprintBase):
        # ...
    ````

2.  **Define `metadata` (Class Variable)**:
    ````python
    class MyNewBlueprint(BlueprintBase):
        metadata: ClassVar[Dict[str, Any]] = {
            "name": "MyNewBlueprint", # Typically the class name
            "title": "My Awesome Agent Team",
            "description": "A brief description of what this blueprint does.",
            "version": "1.0.0",
            "author": "Your Name",
            "tags": ["example", "custom", "multi-agent"],
            "required_mcp_servers": ["optional-mcp-name-if-needed"], # List MCP server keys from config
        }
        # ...
    ````

3.  **Implement `create_starting_agent`**:
    ````python
    from agents import Agent
    from agents.models.interface import Model
    from agents.mcp import MCPServer
    from typing import List

    class MyNewBlueprint(BlueprintBase):
        # ... metadata ...
        _openai_client_cache: Dict[str, Any] = {} # Cache example
        _model_instance_cache: Dict[str, Model] = {} # Cache example

        # Optional: Helper to get model instances (adapt from existing blueprints)
        def _get_model_instance(self, profile_name: str) -> Model:
            # ... (Implementation like in BurntNoodlesBlueprint) ...
            pass

        def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
            """Creates the agent team and returns the entry-point agent."""
            logger.debug("Creating MyAwesome agent team...")
            self._model_instance_cache.clear() # Clear cache for this run if needed
            self._openai_client_cache.clear()

            default_profile = self.config.get("llm_profile", "default")
            model_instance = self._get_model_instance(default_profile) # Use helper

            # Define tools (functions)
            @function_tool
            def my_tool(param: str) -> str:
                """My custom tool."""
                logger.info(f"Executing my_tool with '{param}'")
                return f"Tool executed with {param}"

            # Create subordinate agents if needed
            sub_agent = Agent(
                name="SubAgent",
                model=model_instance,
                instructions="I perform sub-tasks.",
                tools=[] # Sub-agent might have its own tools
            )

            # Create the main/starting agent
            main_agent = Agent(
                name="MainAgent",
                model=model_instance,
                instructions="I am the main agent. I coordinate and use tools.",
                tools=[
                    my_tool,
                    sub_agent.as_tool(tool_name="SubAgentDelegator", tool_description="Delegate tasks to SubAgent.")
                ],
                mcp_servers=mcp_servers # Pass MCP servers if the agent needs them directly
            )
            logger.debug("Agent team created. MainAgent is starting agent.")
            return main_agent # Return the agent that Runner should start with
    ````

4.  **Add `if __name__ == "__main__":`**:
    ````python
    if __name__ == "__main__":
        MyNewBlueprint.main() # Use the base class main method
    ````

## Development Usage

1.  **Clone**: `git clone https://github.com/matthewhand/open-swarm.git`
2.  **Navigate**: `cd open-swarm`
3.  **Install Deps**: `uv pip install -r requirements.txt -e .` (Uses `uv` for speed, install with `pip install uv`)
4.  **Configure**: Create or update `swarm_config.json` in the project root. Add LLM API keys (or set environment variables like `OPENAI_API_KEY`). Define LLM profiles and any MCP servers needed.
    *Example `swarm_config.json`:*
    ````json
    {
      "llm": {
        "default": {
          "provider": "openai",
          "model": "gpt-4o-mini",
          "api_key": "${OPENAI_API_KEY}",
          "base_url": "${OPENAI_BASE_URL}"
        },
        "code-large": {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "${OPENAI_API_KEY}",
            "base_url": "${OPENAI_BASE_URL}"
        }
      },
      "mcpServers": {
         "memory": {
             "command": ["uv", "run", "python", "-m", "agents.mcp.servers.memory"],
             "args": [],
             "env": {}
         },
         "filesystem": {
             "command": ["uv", "run", "python", "-m", "agents.mcp.servers.filesystem"],
             "args": ["--root", "./agent_fs"],
             "env": {},
             "cwd": "${PROJECT_ROOT}"
         }
         # Add other MCP server definitions here
      }
    }
    ````
5.  **Run a Blueprint**:
    *   **Normal**: `uv run python blueprints/burnt_noodles/blueprint_burnt_noodles.py --instruction "Check git status."`
    *   **Debug**: `uv run python blueprints/burnt_noodles/blueprint_burnt_noodles.py --instruction "Check git status." --debug`
    *   **Quiet**: `uv run python blueprints/burnt_noodles/blueprint_burnt_noodles.py --instruction "Check git status." --quiet` (Outputs only the final result string)
    *   **With Config**: `uv run python blueprints/my_blueprint.py --instruction "Do something" --config-path /path/to/custom_config.json`
    *   **With Profile**: `uv run python blueprints/rue_code/blueprint_rue_code.py --instruction "Refactor this code..." --profile code-large`

## Testing

*   Run tests using `pytest`: `uv run pytest -vv`
*   Run specific tests: `uv run pytest -k test_burnt_noodles_agent_creation`

## Examples

*   **`burnt_noodles`**: Demonstrates multi-agent collaboration for Git and testing tasks using the new `BlueprintBase` pattern.
*   **`rue_code`**: Refactored to use `BlueprintBase`. Focuses on coding tasks with multiple agents.
*   **`nebula_shellz`**: Refactored to use `BlueprintBase`. Matrix-themed multi-agent system for shell commands and coding.
*   **`mcp_demo`**: (Needs Refactoring) Demonstrates MCP usage with filesystem and memory servers.
*   *(Other blueprints)*: Need refactoring to the `BlueprintBase` pattern.

## Future Work / Planned Features

*   Implement `swarm-api` for serving blueprints as REST endpoints.
*   Implement `swarm-cli` for packaging and installation.
*   Refactor remaining blueprints (`gaggle`, `echocraft`, `mcp_demo`, etc.).
*   Improve test coverage, especially for CLI, agent-as-tool, and MCP interactions.
*   Explore further modularization of `BlueprintBase` (e.g., config loading, MCP startup).
*   Add support for more LLM providers via `litellm` integration within `BlueprintBase` or helper functions.
