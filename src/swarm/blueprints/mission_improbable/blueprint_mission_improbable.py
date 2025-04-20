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
    from swarm.core.blueprint_ux import BlueprintUXImproved
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
    """
    Executes a shell command and returns its stdout and stderr.
    Timeout is configurable via SWARM_COMMAND_TIMEOUT (default: 60s).
    """
    logger.info(f"Executing shell command: {command}")
    try:
        import os
        timeout = int(os.getenv("SWARM_COMMAND_TIMEOUT", "60"))
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        logger.info(f"Command finished. Exit Code: {result.returncode}")
        return output.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {command}")
        return f"Error: Command timed out after {os.getenv('SWARM_COMMAND_TIMEOUT', '60')} seconds."
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}", exc_info=True)
        return f"Error executing command: {e}"
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

    def __init__(self, blueprint_id: str = "mission_improbable", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._config = config if config is not None else None
        self._llm_profile_name = None
        self._llm_profile_data = None
        self._markdown_output = None
        # Add other attributes as needed for MissionImprobable
        # ...

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

    async def run(self, messages: list, **kwargs):
        """Main execution entry point for the MissionImprobable blueprint."""
        logger.info("MissionImprobableBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        from agents import Runner
        ux = BlueprintUXImproved(style="serious")
        spinner_idx = 0
        start_time = time.time()
        spinner_yield_interval = 1.0  # seconds
        last_spinner_time = start_time
        yielded_spinner = False
        result_chunks = []
        try:
            runner_gen = Runner.run(self.create_starting_agent([]), instruction)
            while True:
                now = time.time()
                try:
                    chunk = next(runner_gen)
                    result_chunks.append(chunk)
                    # If chunk is a final result, wrap and yield
                    if chunk and isinstance(chunk, dict) and "messages" in chunk:
                        content = chunk["messages"][0]["content"] if chunk["messages"] else ""
                        summary = ux.summary("Operation", len(result_chunks), {"instruction": instruction[:40]})
                        box = ux.ansi_emoji_box(
                            title="MissionImprobable Result",
                            content=content,
                            summary=summary,
                            params={"instruction": instruction[:40]},
                            result_count=len(result_chunks),
                            op_type="run",
                            status="success"
                        )
                        yield {"messages": [{"role": "assistant", "content": box}]}
                    else:
                        yield chunk
                    yielded_spinner = False
                except StopIteration:
                    break
                except Exception:
                    if now - last_spinner_time >= spinner_yield_interval:
                        taking_long = (now - start_time > 10)
                        spinner_msg = ux.spinner(spinner_idx, taking_long=taking_long)
                        yield {"messages": [{"role": "assistant", "content": spinner_msg}]}
                        spinner_idx += 1
                        last_spinner_time = now
                        yielded_spinner = True
            if not result_chunks and not yielded_spinner:
                yield {"messages": [{"role": "assistant", "content": ux.spinner(0)}]}
        except Exception as e:
            logger.error(f"Error during MissionImprobable run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

# --- Spinner and ANSI/emoji operation box for unified UX (for CLI/dev runs) ---
from swarm.ux.ansi_box import ansi_box
from rich.console import Console
from rich.style import Style
from rich.text import Text
import threading
import time

class MissionImprobableSpinner:
    FRAMES = [
        "Generating.", "Generating..", "Generating...", "Running...",
        "⠋ Generating...", "⠙ Generating...", "⠹ Generating...", "⠸ Generating...",
        "⠼ Generating...", "⠴ Generating...", "⠦ Generating...", "⠧ Generating...",
        "⠇ Generating...", "⠏ Generating...", "🤖 Generating...", "💡 Generating...", "✨ Generating..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()
        self._last_frame = None
        self._last_slow = False

    def start(self):
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            if elapsed > self.SLOW_THRESHOLD:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
                self._last_frame = self.SLOW_FRAME
                self._last_slow = True
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
                self._last_frame = frame
                self._last_slow = False
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))

    def current_spinner_state(self):
        if self._last_slow:
            return self.SLOW_FRAME
        return self._last_frame or self.FRAMES[0]


def print_operation_box(op_type, results, params=None, result_type="mission", taking_long=False):
    emoji = "🕵️" if result_type == "mission" else "🔍"
    style = 'success' if result_type == "mission" else 'default'
    box_title = op_type if op_type else ("MissionImprobable Output" if result_type == "mission" else "Results")
    summary_lines = []
    count = len(results) if isinstance(results, list) else 0
    summary_lines.append(f"Results: {count}")
    if params:
        for k, v in params.items():
            summary_lines.append(f"{k.capitalize()}: {v}")
    box_content = "\n".join(summary_lines + ["\n".join(map(str, results))])
    ansi_box(box_title, box_content, count=count, params=params, style=style if not taking_long else 'warning', emoji=emoji)

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
        spinner = MissionImprobableSpinner()
        spinner.start()
        try:
            all_results = []
            async for response in blueprint.run(messages):
                content = response["messages"][0]["content"]
                all_results.append(content)
        finally:
            spinner.stop()
        print_operation_box(
            op_type="MissionImprobable Output",
            results=all_results,
            params={"prompt": messages[0]["content"]},
            result_type="mission"
        )
    asyncio.run(run_and_print())
