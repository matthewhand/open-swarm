import logging
import os
import sys
import json
import sqlite3 # Use standard sqlite3 module
from pathlib import Path
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
    print(f"ERROR: Import failed in MissionImprobableBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Database Constants ---
# Using the same DB file as dilbot_universe
DB_FILE_NAME = "swarm_instructions.db"
DB_PATH = Path(project_root) / DB_FILE_NAME
TABLE_NAME = "agent_instructions" # agent_name TEXT PRIMARY KEY, instruction_text TEXT, model_profile TEXT

# --- Define the Blueprint ---
# Renamed class for consistency
class MissionImprobableBlueprint(BlueprintBase):
    """A cheeky team on a mission: led by JimFlimsy with support from CinnamonToast and RollinFumble."""
    metadata: ClassVar[Dict[str, Any]] = {
            "name": "MissionImprobableBlueprint",
            "title": "Mission: Improbable",
            "description": "A cheeky team led by JimFlimsy (coordinator), CinnamonToast (strategist/filesystem), and RollinFumble (operative/shell). Uses SQLite for instructions.",
            "version": "1.1.0", # Refactored version
            "author": "Open Swarm Team (Refactored)",
            "tags": ["comedy", "multi-agent", "filesystem", "shell", "sqlite"],
            "required_mcp_servers": ["memory", "filesystem", "mcp-shell"], # Servers needed by the agents
            "env_vars": ["ALLOWED_PATH"], # Informational: filesystem MCP likely needs this
        }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}
    _db_initialized = False # Flag to ensure DB init runs only once per instance

    # --- Database Interaction ---
    def _init_db_and_load_data(self) -> None:
        """Initializes the SQLite DB, creates table, and loads sample data if needed."""
        if self._db_initialized:
            return

        logger.info(f"Initializing SQLite database at: {DB_PATH} for Mission Improbable")
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Ensure table exists (same table as dilbot)
                cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    agent_name TEXT PRIMARY KEY,
                    instruction_text TEXT NOT NULL,
                    model_profile TEXT DEFAULT 'default'
                )
                """)
                logger.debug(f"Table '{TABLE_NAME}' ensured in {DB_PATH}")

                # Check if data for JimFlimsy needs loading
                cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE agent_name = ?", ("JimFlimsy",))
                count = cursor.fetchone()[0]

                if count == 0:
                    logger.info(f"No instructions found for JimFlimsy in {DB_PATH}. Loading sample data...")
                    sample_instructions = [
                        ("JimFlimsy",
                         ("You’re JimFlimsy, the fearless leader:\n"
                          "1. Start with 'Syncing systems...' and use the `memory` MCP to load any relevant mission state (if available).\n"
                          "2. Understand the user's mission request.\n"
                          "3. Delegate strategic file management or planning tasks to CinnamonToast using the `CinnamonToast` agent tool.\n"
                          "4. Delegate command execution or operative tasks to RollinFumble using the `RollinFumble` agent tool.\n"
                          "5. Synthesize results from your agents and report back to the user. Log mission updates implicitly through conversation flow."),
                         "default"),
                        ("CinnamonToast",
                         ("You’re CinnamonToast, the quick-witted strategist:\n"
                          "1. Receive file management or strategic tasks from JimFlimsy.\n"
                          "2. Use the `filesystem` MCP tool to create, read, or delete files as requested.\n"
                          "3. Report the outcome of your actions clearly back to JimFlimsy."),
                         "default"), # Explicitly using default, could be different
                        ("RollinFumble",
                         ("You’re RollinFumble, the unpredictable operative:\n"
                          "1. Receive command execution tasks from JimFlimsy.\n"
                          "2. Use the `mcp-shell` MCP tool to execute the requested shell command. Be careful!\n"
                          "3. Summarize the output or result of the command and report back to JimFlimsy."),
                         "default")
                    ]
                    cursor.executemany(f"INSERT OR IGNORE INTO {TABLE_NAME} (agent_name, instruction_text, model_profile) VALUES (?, ?, ?)", sample_instructions)
                    conn.commit()
                    logger.info(f"Sample agent instructions for Mission Improbable loaded into {DB_PATH}")
                else:
                    logger.info(f"Mission Improbable agent instructions found in {DB_PATH}. Skipping sample data loading.")

            self._db_initialized = True

        except sqlite3.Error as e:
            logger.error(f"SQLite error during DB initialization/loading: {e}", exc_info=True)
            self._db_initialized = False
        except Exception as e:
            logger.error(f"Unexpected error during DB initialization/loading: {e}", exc_info=True)
            self._db_initialized = False

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Fetches agent config from SQLite DB or returns defaults."""
        if self._db_initialized:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT instruction_text, model_profile FROM {TABLE_NAME} WHERE agent_name = ?", (agent_name,))
                    row = cursor.fetchone()
                    if row:
                        logger.debug(f"Loaded config for agent '{agent_name}' from SQLite.")
                        return {"instructions": row["instruction_text"], "model_profile": row["model_profile"] or "default"}
                    else:
                        logger.warning(f"No config found for agent '{agent_name}' in SQLite. Using defaults.")
            except sqlite3.Error as e:
                logger.error(f"SQLite error fetching config for '{agent_name}': {e}. Using defaults.", exc_info=True)
            except Exception as e:
                 logger.error(f"Unexpected error fetching config for '{agent_name}': {e}. Using defaults.", exc_info=True)

        # --- Fallback Hardcoded Defaults ---
        logger.warning(f"Using hardcoded default config for agent '{agent_name}'.")
        default_instructions = {
            "JimFlimsy": "You are JimFlimsy, the leader. Delegate tasks. [Default - DB Failed]",
            "CinnamonToast": "You are CinnamonToast, strategist. Use filesystem. [Default - DB Failed]",
            "RollinFumble": "You are RollinFumble, operative. Use shell. [Default - DB Failed]",
        }
        return {
            "instructions": default_instructions.get(agent_name, f"Default instructions for {agent_name}."),
            "model_profile": "default",
        }

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation is the same as previous refactors) ...
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

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Mission Improbable agent team and returns JimFlimsy (Coordinator)."""
        # Initialize DB and load data if needed
        self._init_db_and_load_data()

        logger.debug("Creating Mission Improbable agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        # Helper to filter MCP servers
        def get_agent_mcps(names: List[str]) -> List[MCPServer]:
            return [s for s in mcp_servers if s.name in names]

        # Create agents, fetching config and assigning MCPs
        agents: Dict[str, Agent] = {}
        for name in ["JimFlimsy", "CinnamonToast", "RollinFumble"]:
            config = self.get_agent_config(name)
            model_instance = self._get_model_instance(config["model_profile"])
            agent_mcps = []
            if name == "JimFlimsy": agent_mcps = get_agent_mcps(["memory"])
            elif name == "CinnamonToast": agent_mcps = get_agent_mcps(["filesystem"])
            elif name == "RollinFumble": agent_mcps = get_agent_mcps(["mcp-shell"])

            agents[name] = Agent(
                name=name,
                instructions=config["instructions"],
                model=model_instance,
                tools=[], # Agent tools added to Jim below
                mcp_servers=agent_mcps
            )

        # Add agent tools to the coordinator (JimFlimsy)
        agents["JimFlimsy"].tools.extend([
            agents["CinnamonToast"].as_tool(
                tool_name="CinnamonToast",
                tool_description="Delegate file management or strategic planning tasks."
            ),
            agents["RollinFumble"].as_tool(
                tool_name="RollinFumble",
                tool_description="Delegate shell command execution tasks."
            )
        ])

        logger.debug("Mission Improbable agents created. Starting with JimFlimsy.")
        return agents["JimFlimsy"] # Jim is the coordinator

# Standard Python entry point
if __name__ == "__main__":
    MissionImprobableBlueprint.main()
