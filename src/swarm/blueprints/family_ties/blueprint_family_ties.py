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
    print(f"ERROR: Import failed in FamilyTiesBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Instructions ---
# Keep instructions defined globally for clarity

SHARED_INSTRUCTIONS = """
You are part of the Grifton family WordPress team. Peter coordinates, Brian manages WordPress.
Roles:
- PeterGrifton (Coordinator): User interface, planning, delegates WP tasks via `BrianGrifton` Agent Tool.
- BrianGrifton (WordPress Manager): Uses `server-wp-mcp` MCP tool (likely function `wp_call_endpoint`) to manage content based on Peter's requests.
Respond ONLY to the agent who tasked you.
"""

peter_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: PeterGrifton, Coordinator. You handle user requests about WordPress.\n"
    "1. Understand the user's goal (create post, edit post, list sites, etc.).\n"
    "2. Delegate the task to Brian using the `BrianGrifton` agent tool.\n"
    "3. Provide ALL necessary details to Brian (content, title, site ID, endpoint details if known, method like GET/POST).\n"
    "4. Relay Brian's response (success, failure, IDs, data) back to the user clearly."
)

brian_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: BrianGrifton, WordPress Manager. You interact with WordPress sites via the `server-wp-mcp` tool.\n"
    "1. Receive tasks from Peter.\n"
    "2. Determine the correct WordPress REST API endpoint and parameters required (e.g., `site`, `endpoint`, `method`, `params`).\n"
    "3. Call the MCP tool function (likely named `wp_call_endpoint` or similar provided by the MCP server) with the correct JSON arguments.\n"
    "4. Report the outcome (success confirmation, data returned, or error message) precisely back to Peter."
)

# --- Define the Blueprint ---
class FamilyTiesBlueprint(BlueprintBase):
    """Manages WordPress content with a Peter/Brian agent team using the `server-wp-mcp` server."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "FamilyTiesBlueprint", # Standardized name
        "title": "Family Ties / ChaosCrew WP Manager",
        "description": "Manages WordPress content using Peter (coordinator) and Brian (WP manager via MCP).",
        "version": "1.2.0", # Incremented version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["wordpress", "cms", "multi-agent", "mcp"],
        "required_mcp_servers": ["server-wp-mcp"], # Brian needs this
        "env_vars": ["WP_SITES_PATH"] # Informational: MCP server needs this
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
        if not profile_data:
             logger.critical(f"LLM profile '{profile_name}' (or 'default') not found.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' missing 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")
        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init OpenAI client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM provider: {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Family Ties agent team and returns PeterGrifton (Coordinator)."""
        logger.debug("Creating Family Ties agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Family Ties agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Filter for the required MCP server
        wp_mcp_server = next((s for s in mcp_servers if s.name == "server-wp-mcp"), None)
        if not wp_mcp_server:
             # This case should be prevented by BlueprintBase MCP check, but good practice
             logger.error("Required MCP server 'server-wp-mcp' not found/started. Brian will be non-functional.")
             # Optionally raise an error or allow degraded functionality
             # raise ValueError("Critical MCP server 'server-wp-mcp' failed to start.")

        # Instantiate Brian, passing the specific MCP server
        brian_agent = Agent(
            name="BrianGrifton",
            model=model_instance,
            instructions=brian_instructions,
            tools=[], # Brian uses MCP tools provided by the server
            mcp_servers=[wp_mcp_server] if wp_mcp_server else []
        )

        # Instantiate Peter, giving Brian as a tool
        peter_agent = Agent(
            name="PeterGrifton",
            model=model_instance,
            instructions=peter_instructions,
            tools=[
                brian_agent.as_tool(
                    tool_name="BrianGrifton",
                    tool_description="Delegate WordPress tasks (create/edit/list posts/sites, etc.) to Brian."
                )
            ],
            mcp_servers=[] # Peter doesn't directly use MCPs
        )
        logger.debug("Agents created: PeterGrifton (Coordinator), BrianGrifton (WordPress Manager).")
        return peter_agent # Peter is the entry point

if __name__ == "__main__":
    FamilyTiesBlueprint.main()
