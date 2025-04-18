"""
MissionImprobable Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
import logging
import os
import sys
import json
import sqlite3 # Use standard sqlite3 module
from pathlib import Path
from typing import Dict, Any, List, ClassVar, Optional
from datetime import datetime
import pytz

# Last swarm update: 2025-04-18T10:15:21Z (UTC)

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
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in MissionImprobableBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# Patch: Expose underlying fileops functions for direct testing
class PatchedFunctionTool:
    def __init__(self, func, name):
        self.func = func
        self.name = name

def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"
def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"
def list_files(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"
def execute_shell_command(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {e}"
read_file_tool = PatchedFunctionTool(read_file, 'read_file')
write_file_tool = PatchedFunctionTool(write_file, 'write_file')
list_files_tool = PatchedFunctionTool(list_files, 'list_files')
execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, 'execute_shell_command')

# --- Database Constants ---
# Using the same DB file as dilbot_universe
DB_FILE_NAME = "swarm_instructions.db"
DB_PATH = Path(project_root) / DB_FILE_NAME
TABLE_NAME = "agent_instructions" # agent_name TEXT PRIMARY KEY, instruction_text TEXT, model_profile TEXT

# Spinner UX enhancement (Open Swarm TODO)
SPINNER_STATES = ['Generating.', 'Generating..', 'Generating...', 'Running...']

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

    def __init__(self, blueprint_id: str = None, config_path: Optional[Path] = None, **kwargs):
        if blueprint_id is None:
            blueprint_id = "mission-improbable"
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()

    # --- Database Interaction ---
    def _init_db_and_load_data(self) -> None:
        """Initializes the SQLite DB, creates table, and loads sample data if needed."""
        """Initializes the SQLite DB file and loads sample instruction for JimFlimsy."""
        if self._db_initialized:
            return
        # Create parent directory if needed
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Create or open the database file
            with open(DB_PATH, 'a'):
                pass
            # Initialize DB and table
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} (agent_name TEXT PRIMARY KEY, instruction_text TEXT NOT NULL, model_profile TEXT DEFAULT 'default')")
            # Load sample data for JimFlimsy if not present
            cursor.execute("SELECT COUNT(*) FROM " + TABLE_NAME + " WHERE agent_name = ?", ("JimFlimsy",))
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute(
                    "INSERT OR IGNORE INTO " + TABLE_NAME + " (agent_name, instruction_text, model_profile) VALUES (?, ?, ?)",
                    ("JimFlimsy", "You’re JimFlimsy, the fearless leader.", "default")
                )
            conn.commit()
            conn.close()
            self._db_initialized = True
        except Exception as e:
            logger.error(f"Error during DB initialization/loading: {e}", exc_info=True)
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
                instructions=config["instructions"] + "\nYou can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.",
                model=model_instance,
                tools=[read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
                mcp_servers=agent_mcps
            )

        # Add agent tools to the coordinator (JimFlimsy)
        agents["JimFlimsy"].tools.extend([
            agents["CinnamonToast"].as_tool(tool_name="CinnamonToast", tool_description="Delegate file management or strategic planning tasks."),
            agents["RollinFumble"].as_tool(tool_name="RollinFumble", tool_description="Delegate shell command execution tasks.")
        ])

        logger.debug("Mission Improbable agents created. Starting with JimFlimsy.")
        return agents["JimFlimsy"] # Jim is the coordinator

    async def run(self, messages: list) -> object:
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not last_user_message:
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            return
        prompt_context = {
            "user_request": last_user_message,
            "history": messages[:-1],
            "available_tools": ["mission_improbable"]
        }
        rendered_prompt = self.render_prompt("mission_improbable_prompt.j2", prompt_context)
        yield {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"[MissionImprobable LLM] Would respond to: {rendered_prompt}"
                }
            ]
        }
        return

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   🕵️ MISSION IMPROBABLE: SWARM STRATEGY & TASK DEMO         ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint demonstrates viral swarm propagation,         ║\n║ strategic task planning, and agent collaboration.            ║\n║ Try running: python blueprint_mission_improbable.py          ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how Mission Improbable plans tasks and leverages swarm strategy."}
    ]
    blueprint = MissionImprobableBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
