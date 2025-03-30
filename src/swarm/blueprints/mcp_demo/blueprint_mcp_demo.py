import logging
import os
import sys
from typing import Dict, Any, List, ClassVar, Optional

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in MCPDemoBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Instructions ---

sage_instructions_template = """
You are Sage, an agent demonstrating capabilities provided by MCP servers.
You have access to the following external capabilities via implicitly available MCP tools:
{mcp_tool_descriptions}

Your goal is to understand the user's request and utilize the appropriate MCP tool to fulfill it.
For example:
- To write to a file, use the 'filesystem' tool's 'write' function.
- To read from memory, use the 'memory' tool's 'get' function.
- To store in memory, use the 'memory' tool's 'set' function.
Explain what action you are taking via which tool and report the result.
"""

# --- Define the Blueprint ---
class MCPDemoBlueprint(BlueprintBase):
    """Demonstrates using filesystem and memory MCP servers."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "MCPDemoBlueprint",
        "title": "MCP Demo (Filesystem & Memory)",
        "description": "A simple agent (Sage) demonstrating interaction with filesystem and memory MCP servers.",
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["mcp", "filesystem", "memory", "demo"],
        "required_mcp_servers": ["filesystem", "memory"],
        "env_vars": ["ALLOWED_PATH"], # For filesystem MCP
    }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation is the same as in previous refactors) ...
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data: raise ValueError(f"Missing LLM profile '{profile_name}'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name: raise ValueError(f"Missing 'model' in profile '{profile_name}'.")
        if provider != "openai": raise ValueError(f"Unsupported provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM: {e}") from e

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Sage agent, dynamically adding MCP server descriptions to its prompt."""
        logger.debug("Creating MCP Demo agent (Sage)...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Sage.")
        model_instance = self._get_model_instance(default_profile_name)

        # Filter for required MCPs and get descriptions
        required_names = self.metadata["required_mcp_servers"]
        agent_mcps: List[MCPServer] = []
        mcp_descriptions = []
        for server in mcp_servers:
            if server.name in required_names:
                agent_mcps.append(server)
                description = self.get_mcp_server_description(server.name)
                mcp_descriptions.append(f"- {server.name}: {description or 'No description available.'}")

        if len(agent_mcps) != len(required_names):
            missing = set(required_names) - {s.name for s in agent_mcps}
            logger.warning(f"Sage agent created, but missing required MCP server(s): {', '.join(missing)}. Functionality will be limited.")
            # Continue with available servers

        # Format descriptions for the prompt
        mcp_tool_desc_str = "\n".join(mcp_descriptions) if mcp_descriptions else "No external tools available."
        sage_instructions = sage_instructions_template.format(mcp_tool_descriptions=mcp_tool_desc_str)
        logger.debug(f"Sage instructions generated:\n{sage_instructions}")

        # Instantiate Sage
        sage_agent = Agent(
            name="Sage",
            model=model_instance,
            instructions=sage_instructions,
            tools=[], # Tools come implicitly from assigned MCP servers
            mcp_servers=agent_mcps # Pass the list of *started* server objects
        )

        logger.debug("Sage agent created.")
        return sage_agent

# Standard Python entry point
if __name__ == "__main__":
    MCPDemoBlueprint.main()
