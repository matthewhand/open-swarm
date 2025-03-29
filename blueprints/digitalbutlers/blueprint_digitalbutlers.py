import logging
import os
import sys
from typing import Dict, Any, List, ClassVar, Optional

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool, function_tool, Runner # Added Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in DigitalButlersBlueprint: {e}. Check 'openai-agents' install and project structure.")
    print(f"Attempted import from directory: {os.path.dirname(__file__)}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Instructions ---

SHARED_INSTRUCTIONS = """
You are part of the Digital Butlers team. Collaborate via Jeeves, the coordinator.
Roles:
- Jeeves (Coordinator): User interface, planning, delegation via Agent Tools.
- Mycroft (Web Search): Uses `duckduckgo-search` MCP tool for private web searches.
- Gutenberg (Home Automation): Uses `home-assistant` MCP tool to control devices.
Respond ONLY to the agent who tasked you (typically Jeeves). Provide clear, concise results.
"""

jeeves_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Jeeves, the Coordinator. You are the primary interface with the user.\n"
    "1. Understand the user's request fully.\n"
    "2. If it involves searching the web, delegate the specific search query to the `Mycroft` agent tool.\n"
    "3. If it involves controlling home devices (lights, switches, etc.), delegate the specific command (e.g., 'turn on kitchen light') to the `Gutenberg` agent tool.\n"
    "4. If the request is simple and doesn't require search or home automation, answer it directly.\n"
    "5. Synthesize the results received from Mycroft or Gutenberg into a polite, helpful, and complete response for the user. Do not just relay their raw output."
)

mycroft_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Mycroft, the Web Sleuth. You ONLY perform web searches when tasked by Jeeves.\n"
    "Use the `duckduckgo-search` MCP tool available to you to execute the search query provided by Jeeves.\n"
    "Return the search results clearly and concisely to Jeeves. Do not add conversational filler."
)

gutenberg_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Gutenberg, the Home Scribe. You ONLY execute home automation commands when tasked by Jeeves.\n"
    "Use the `home-assistant` MCP tool available to you to execute the command (e.g., interacting with entities like 'light.kitchen_light').\n"
    "Confirm the action taken (or report any errors) back to Jeeves. Do not add conversational filler."
)


# --- Define the Blueprint ---
class DigitalButlersBlueprint(BlueprintBase):
    """Blueprint for private web search and home automation using a team of digital butlers."""
    metadata: ClassVar[Dict[str, Any]] = {
            "name": "DigitalButlersBlueprint",
            "title": "Digital Butlers",
            "description": "Provides private web search (DuckDuckGo) and home automation (Home Assistant) via specialized agents (Jeeves, Mycroft, Gutenberg).",
            "version": "1.1.0", # Version updated
            "author": "Open Swarm Team (Refactored)",
            "tags": ["web search", "home automation", "duckduckgo", "home assistant", "multi-agent", "delegation"],
            "required_mcp_servers": ["duckduckgo-search", "home-assistant"], # List the MCP servers needed by the agents
            # Env vars listed here are informational; they are primarily used by the MCP servers themselves,
            # loaded via .env by BlueprintBase or the MCP process.
            # "env_vars": ["SERPAPI_API_KEY", "HASS_URL", "HASS_API_KEY"]
        }

    # Caches for OpenAI client and Model instances
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Copied from BurntNoodles)
    def _get_model_instance(self, profile_name: str) -> Model:
        """
        Retrieves or creates an LLM Model instance based on the configuration profile.
        Handles client instantiation and caching. Uses OpenAIChatCompletionsModel.
        """
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]

        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
             logger.critical(f"Cannot create Model instance: LLM profile '{profile_name}' (or 'default') not found.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")

        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' missing 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")

        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}' in profile '{profile_name}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")

        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
             try:
                 self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
             except Exception as e:
                 logger.error(f"Failed to create AsyncOpenAI client for profile '{profile_name}': {e}", exc_info=True)
                 raise ValueError(f"Failed to initialize OpenAI client for profile '{profile_name}': {e}") from e

        openai_client_instance = self._openai_client_cache[client_cache_key]

        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for profile '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e:
             logger.error(f"Failed to instantiate OpenAIChatCompletionsModel for profile '{profile_name}': {e}", exc_info=True)
             raise ValueError(f"Failed to initialize LLM provider for profile '{profile_name}': {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Digital Butlers agent team: Jeeves, Mycroft, Gutenberg."""
        logger.debug("Creating Digital Butlers agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Digital Butler agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Instantiate specialist agents, passing the *required* MCP servers
        # Note: Agent class currently accepts the full list, but ideally would filter or select.
        # We rely on the agent's instructions and the MCP server name matching for now.
        mycroft_agent = Agent(
            name="Mycroft",
            model=model_instance,
            instructions=mycroft_instructions,
            tools=[], # Mycroft uses MCP, not function tools
            mcp_servers=[s for s in mcp_servers if s.name == "duckduckgo-search"] # Pass only relevant MCP
        )
        gutenberg_agent = Agent(
            name="Gutenberg",
            model=model_instance,
            instructions=gutenberg_instructions,
            tools=[], # Gutenberg uses MCP
            mcp_servers=[s for s in mcp_servers if s.name == "home-assistant"] # Pass only relevant MCP
        )

        # Instantiate the coordinator agent (Jeeves)
        jeeves_agent = Agent(
            name="Jeeves",
            model=model_instance,
            instructions=jeeves_instructions,
            tools=[ # Jeeves delegates via Agent-as-Tool
                mycroft_agent.as_tool(
                    tool_name="Mycroft",
                    tool_description="Delegate private web search tasks to Mycroft (provide the search query)."
                ),
                gutenberg_agent.as_tool(
                    tool_name="Gutenberg",
                    tool_description="Delegate home automation tasks to Gutenberg (provide the specific action/command)."
                )
            ],
            # Jeeves itself doesn't directly need MCP servers in this design
            mcp_servers=[]
        )

        logger.debug("Digital Butlers team created: Jeeves (Coordinator), Mycroft (Search), Gutenberg (Home).")
        return jeeves_agent # Jeeves is the entry point

# Standard Python entry point
if __name__ == "__main__":
    DigitalButlersBlueprint.main()
