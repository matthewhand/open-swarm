import logging
import random
import json
import os
import sys
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
    print(f"ERROR: Import failed in DilbotUniverseBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Database Constants ---
DB_FILE_NAME = "swarm_instructions.db"
DB_PATH = Path(project_root) / DB_FILE_NAME
TABLE_NAME = "agent_instructions"

# --- Placeholder Tools ---
@function_tool
def build_product() -> str:
    """Simulates successfully building the product."""
    logger.info("Tool: build_product executed.")
    return (
        "ACTION: build_product completed.\n"
        "GAME OVER: YOU WON!\n"
        "After much deliberation, the comedic masterpiece is finalized—behold its glory! "
        "Reasoning: It’s polished enough to survive the corporate circus."
    )

@function_tool
def sabotage_project() -> str:
    """Simulates sabotaging the project."""
    logger.info("Tool: sabotage_project executed.")
    return (
        "ACTION: sabotage_project completed.\n"
        "GAME OVER: YOU LOST!\n"
        "The project has been gleefully trashed—chaos reigns supreme! "
        "Reasoning: Why build when you can break with style?"
    )

# --- Blueprint Definition ---
class DilbotUniverseBlueprint(BlueprintBase):
    """A comedic multi-agent blueprint simulating a 9-step SDLC, using agent-as-tool for handoffs and SQLite for instructions."""
    metadata: ClassVar[Dict[str, Any]] = {
            "name": "DilbotUniverseBlueprint",
            "title": "Dilbot Universe SDLC (SQLite)",
            "description": "A comedic multi-agent blueprint using agent-as-tool handoffs and SQLite for instructions.",
            "version": "1.2.0", # Version bump for SQLite change
            "author": "Open Swarm Team (Refactored)",
            "tags": ["comedy", "multi-agent", "sdlc", "sqlite", "dynamic-config"],
            "required_mcp_servers": [],
            "cli_name": "dilbot",
            "env_vars": [],
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

        logger.info(f"Initializing SQLite database at: {DB_PATH}")
        try:
            # Ensure directory exists (though DB_PATH is project root here)
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Create table if it doesn't exist
                cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    agent_name TEXT PRIMARY KEY,
                    instruction_text TEXT NOT NULL,
                    model_profile TEXT DEFAULT 'default'
                )
                """)
                logger.debug(f"Table '{TABLE_NAME}' ensured in {DB_PATH}")

                # Check if data needs loading (check for a known agent)
                cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE agent_name = ?", ("Dilbot",))
                count = cursor.fetchone()[0]

                if count == 0:
                    logger.info(f"No instructions found for Dilbot in {DB_PATH}. Loading sample data...")
                    sample_instructions = [
                        ("Dilbot", "You are Dilbot, a meticulous engineer... [Full instructions]", "default"),
                        ("Alisa", "You are Alisa, a creative designer... [Full instructions]", "default"),
                        ("Carola", "You are Carola, an organized manager... [Full instructions]", "default"),
                        ("PointyBoss", "You are PointyBoss, an evil manager... [Full instructions]", "default"),
                        ("Dogbot", "You are Dogbot, an evil consultant... [Full instructions]", "default"),
                        ("Waldo", "You are Waldo, a lazy neutral employee... [Full instructions]", "default"),
                        ("Asoka", "You are Asoka, an eager neutral intern... [Full instructions]", "default"),
                        ("Ratbot", "You are Ratbot, a whimsical neutral character... [Full instructions]", "default"),
                    ]
                    # Replace "[Full instructions]" with the actual long instructions from the previous version
                    # Example for Dilbot:
                    sample_instructions[0] = (
                        "Dilbot",
                        "You are Dilbot, a meticulous engineer. Follow a 9-step SDLC: 1) Ask engineering questions, 2) Probe further, 3) 1/3 chance to build or pass to Waldo (reason first), 4-5) More questions, 6) 2/3 chance to build or pass, 7-8) Final questions, 9) Build or pass with comedic reasoning.",
                        "default"
                    )
                    # ... (Add the other full instructions here) ...
                    # For brevity, using placeholders:
                    sample_instructions[1] = ("Alisa", sample_instructions[1][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask design questions... 9) Build or pass with comedic reasoning."), "default")
                    sample_instructions[2] = ("Carola", sample_instructions[2][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask scheduling questions... 9) Build or pass with comedic reasoning."), "default")
                    sample_instructions[3] = ("PointyBoss", sample_instructions[3][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask business questions... 9) Sabotage or pass with comedic reasoning."), "default")
                    sample_instructions[4] = ("Dogbot", sample_instructions[4][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask consultancy questions... 9) Sabotage or pass with comedic reasoning."), "default")
                    sample_instructions[5] = ("Waldo", sample_instructions[5][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask procrastination questions... 9) Pass to Dilbot or Dogbot with comedic reasoning."), "default")
                    sample_instructions[6] = ("Asoka", sample_instructions[6][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask creative questions... 9) Pass to Carola or PointyBoss with comedic reasoning."), "default")
                    sample_instructions[7] = ("Ratbot", sample_instructions[7][1].replace("... [Full instructions]", "... Follow a 9-step SDLC: 1) Ask nonsense questions... 9) Pass to Dilbot or Dogbot with comedic reasoning."), "default")


                    cursor.executemany(f"INSERT INTO {TABLE_NAME} (agent_name, instruction_text, model_profile) VALUES (?, ?, ?)", sample_instructions)
                    conn.commit()
                    logger.info(f"Sample agent instructions loaded into {DB_PATH}")
                else:
                    logger.info(f"Agent instructions found in {DB_PATH}. Skipping sample data loading.")

            self._db_initialized = True

        except sqlite3.Error as e:
            logger.error(f"SQLite error during DB initialization/loading: {e}", exc_info=True)
            # Continue without DB? Or raise error? Let's warn and continue with defaults.
            self._db_initialized = False # Mark as failed
        except Exception as e:
            logger.error(f"Unexpected error during DB initialization/loading: {e}", exc_info=True)
            self._db_initialized = False

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Fetches agent config from SQLite DB or returns defaults."""
        if self._db_initialized:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row # Access columns by name
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT instruction_text, model_profile FROM {TABLE_NAME} WHERE agent_name = ?", (agent_name,))
                    row = cursor.fetchone()
                    if row:
                        logger.debug(f"Loaded config for agent '{agent_name}' from SQLite.")
                        return {
                            "instructions": row["instruction_text"],
                            "model_profile": row["model_profile"] or "default",
                        }
                    else:
                        logger.warning(f"No config found for agent '{agent_name}' in SQLite. Using defaults.")
            except sqlite3.Error as e:
                logger.error(f"SQLite error fetching config for '{agent_name}': {e}. Using defaults.", exc_info=True)
            except Exception as e:
                 logger.error(f"Unexpected error fetching config for '{agent_name}': {e}. Using defaults.", exc_info=True)

        # --- Fallback Hardcoded Defaults ---
        logger.warning(f"Using hardcoded default config for agent '{agent_name}'.")
        default_instructions = {
            "Dilbot": "You are Dilbot, a meticulous engineer... [Default Instructions - DB Failed]",
            # ... (Add other default instructions here) ...
             "Alisa": "You are Alisa... [Default Instructions - DB Failed]",
             "Carola": "You are Carola... [Default Instructions - DB Failed]",
             "PointyBoss": "You are PointyBoss... [Default Instructions - DB Failed]",
             "Dogbot": "You are Dogbot... [Default Instructions - DB Failed]",
             "Waldo": "You are Waldo... [Default Instructions - DB Failed]",
             "Asoka": "You are Asoka... [Default Instructions - DB Failed]",
             "Ratbot": "You are Ratbot... [Default Instructions - DB Failed]",
        }
        return {
            "instructions": default_instructions.get(agent_name, f"Default instructions for {agent_name}."),
            "model_profile": "default",
        }

    # --- Model Instantiation Helper --- (Copied from previous step)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation remains the same as in the previous response) ...
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
            logger.error(f"Unsupported LLM provider '{provider}' in profile '{profile_name}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
             except Exception as e: raise ValueError(f"Failed to initialize OpenAI client: {e}") from e
        openai_client_instance = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to initialize LLM provider: {e}") from e


    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Dilbot Universe agent team using SQLite for instructions."""
        # Initialize DB and load data if needed (runs only once)
        self._init_db_and_load_data()

        logger.debug("Creating Dilbot Universe agent team...")
        self._model_instance_cache = {} # Clear model cache for this run
        self._openai_client_cache = {} # Clear client cache for this run

        agents: Dict[str, Agent] = {}
        agent_names = ["Dilbot", "Alisa", "Carola", "PointyBoss", "Dogbot", "Waldo", "Asoka", "Ratbot"]

        # Create all agents first so they can be used as tools
        for name in agent_names:
            config = self.get_agent_config(name)
            model_instance = self._get_model_instance(config["model_profile"])
            agents[name] = Agent(
                name=name,
                instructions=config["instructions"],
                model=model_instance,
                tools=[], # Tools (including agent-as-tool) added below
                mcp_servers=mcp_servers # Pass full list for simplicity now
            )

        # --- Define Tools & Agent-as-Tool Delegations ---
        action_tools = [build_product, sabotage_project]

        # Add tools based on agent logic (using Agent-as-Tool for passes)
        agents["Dilbot"].tools.extend([action_tools[0], agents["Waldo"].as_tool(tool_name="Waldo", tool_description="Pass task to Waldo.")])
        agents["Alisa"].tools.extend([action_tools[0], agents["Asoka"].as_tool(tool_name="Asoka", tool_description="Pass task to Asoka.")])
        agents["Carola"].tools.extend([action_tools[0], agents["Waldo"].as_tool(tool_name="Waldo", tool_description="Pass task to Waldo.")])
        agents["PointyBoss"].tools.extend([action_tools[1], agents["Waldo"].as_tool(tool_name="Waldo", tool_description="Pass task to Waldo.")])
        agents["Dogbot"].tools.extend([action_tools[1], agents["Ratbot"].as_tool(tool_name="Ratbot", tool_description="Pass task to Ratbot.")])
        agents["Waldo"].tools.extend([
            agents["Dilbot"].as_tool(tool_name="Dilbot", tool_description="Pass task to Dilbot."),
            agents["Dogbot"].as_tool(tool_name="Dogbot", tool_description="Pass task to Dogbot.")
        ])
        agents["Asoka"].tools.extend([
            agents["Carola"].as_tool(tool_name="Carola", tool_description="Pass task to Carola."),
            agents["PointyBoss"].as_tool(tool_name="PointyBoss", tool_description="Pass task to PointyBoss.")
        ])
        agents["Ratbot"].tools.extend([
            agents["Dilbot"].as_tool(tool_name="Dilbot", tool_description="Pass task to Dilbot."),
            agents["Dogbot"].as_tool(tool_name="Dogbot", tool_description="Pass task to Dogbot.")
        ])

        # Randomly select starting agent from neutrals
        neutral_agents = ["Waldo", "Asoka", "Ratbot"]
        start_name = random.choice(neutral_agents)
        starting_agent = agents[start_name]

        logger.info(f"Dilbot Universe agents created (using SQLite). Starting agent: {start_name}")
        return starting_agent

# Standard Python entry point
if __name__ == "__main__":
    # No Django setup needed here anymore
    DilbotUniverseBlueprint.main()
