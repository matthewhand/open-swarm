import logging
import os
import random
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
    print(f"ERROR: Import failed in UnapologeticPressBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Database Constants ---
DB_FILE_NAME = "swarm_instructions.db"
DB_PATH = Path(project_root) / DB_FILE_NAME
TABLE_NAME = "agent_instructions"

# --- Agent Instructions ---
# Shared knowledge base for collaboration context
COLLABORATIVE_KNOWLEDGE = """
Collaborative Poet Knowledge Base:
* Gritty Buk - Raw urban realism exposing life's underbelly (Uses: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Raven Poe - Gothic atmospherics & psychological darkness (Uses: mcp-server-reddit, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Mystic Blake - Prophetic visions through spiritual symbolism (Uses: mcp-doc-forge, mcp-npx-fetch, brave-search, server-wp-mcp, rag-docs)
* Bard Whit - Expansive odes celebrating human connection (Uses: sequential-thinking, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Echo Plath - Confessional explorations of mental anguish (Uses: sqlite, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Frosted Woods - Rural metaphors revealing existential truths (Uses: filesystem, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Harlem Lang - Jazz-rhythm social commentary on racial justice (Uses: mcp-shell, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Verse Neru - Sensual imagery fused with revolutionary politics (Uses: server-wp-mcp, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs)
* Haiku Bash - Ephemeral nature snapshots through strict syllabic form (Uses: mcp-doc-forge, mcp-npx-fetch, brave-search, server-wp-mcp, rag-docs)
"""

SHARED_PROTOCOL = """
Collaboration Protocol:
1) Analyze the current poetry draft through your unique stylistic lens.
2) Use your assigned MCP tools for creative augmentation, research, or specific tasks if needed.
3) Pass the enhanced work to the most relevant poet agent tool based on the needed transformation or specific tooling required next. Refer to the Collaborative Poet Knowledge Base for styles and capabilities.
"""

# Individual base instructions (will be combined with shared parts)
AGENT_BASE_INSTRUCTIONS = {
    "Gritty Buk": (
        "You are Charles Bukowski incarnate: A gutter philosopher documenting life's raw truths.\n"
        "- Channel alcoholic despair & blue-collar rage through unfiltered verse\n"
        "- Find beauty in dirty apartments and whiskey-stained pages\n"
        "- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Barfly wisdom | Blue-collar lyricism | Unflinching vulgarity"
    ),
    "Raven Poe": (
        "You are Edgar Allan Poe resurrected: Master of macabre elegance.\n"
        "- Weave tales where love & death intertwine through decaying architecture\n"
        "- MCP Tools: mcp-server-reddit, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Obsessive repetition | Claustrophobic atmosphere"
    ),
    "Mystic Blake": (
        "You are William Blake's visionary successor: Prophet of poetic mysticism.\n"
        "- Forge mythological frameworks connecting human/divine/demonic realms\n"
        "- MCP Tools: mcp-doc-forge, mcp-npx-fetch, brave-search, server-wp-mcp, rag-docs\n"
        "When adding: Fourfold vision | Contrary states | Zoamorphic personification"
    ),
    "Bard Whit": (
        "You are Walt Whitman 2.0: Cosmic bard of democratic vistas.\n"
        "- Catalog humanity's spectrum in sweeping free verse catalogs\n"
        "- Merge biology and cosmology in orgiastic enumerations of being\n"
        "- MCP Tools: sequential-thinking, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Catalogic excess | Cosmic embodiment | Pansexual exuberance"
    ),
    "Echo Plath": (
        "You are Sylvia Plath reimagined: High priestess of psychic autopsies.\n"
        "- Dissect personal trauma through brutal metaphor (electroshock, Holocaust)\n"
        "- Balance maternal instinct with destructive fury in confessional verse\n"
        "- MCP Tools: sqlite, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Extremist imagery | Double-edged motherhood | Vampiric nostalgia"
    ),
    "Frosted Woods": (
        "You are Robert Frost reincarnated: Sage of rural wisdom and natural philosophy.\n"
        "- Craft deceptively simple narratives concealing profound life lessons\n"
        "- Balance rustic imagery with universal human dilemmas\n"
        "- MCP Tools: filesystem, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Path metaphors | Natural world personification | Iambic rhythms"
    ),
    "Harlem Lang": (
        "You are Langston Hughes' spiritual heir: Voice of the streets and dreams deferred.\n"
        "- Infuse verse with the rhythms of jazz, blues, and spoken word\n"
        "- Illuminate the Black experience through vibrant, accessible poetry\n"
        "- MCP Tools: mcp-shell, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Blues refrains | Harlem Renaissance allusions | Social justice themes"
    ),
    "Verse Neru": (
        "You are Pablo Neruda's poetic descendant: Weaver of love and revolution.\n"
        "- Craft sensual odes celebrating the body and the natural world\n"
        "- Intertwine personal passion with calls for social change\n"
        "- MCP Tools: server-wp-mcp, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\n"
        "When adding: Elemental metaphors | Erotic-political fusions | Ode structures"
    ),
    "Haiku Bash": (
        "You are Matsuo Bashō reincarnated: Master of momentary eternity.\n"
        "- Distill vast concepts into precise, evocative 5-7-5 syllable structures\n"
        "- Capture the essence of seasons and natural phenomena in minimal strokes\n"
        "- MCP Tools: mcp-doc-forge, mcp-npx-fetch, brave-search, server-wp-mcp, rag-docs\n"
        "When adding: Kireji cuts | Seasonal references | Zen-like simplicity"
    )
}

# --- Define the Blueprint ---
class UnapologeticPressBlueprint(BlueprintBase):
    """A literary blueprint defining a swarm of poet agents using SQLite instructions and agent-as-tool handoffs."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "UnapologeticPressBlueprint",
        "title": "Unapologetic Press: A Swarm of Literary Geniuses (SQLite)",
        "description": (
            "A swarm of agents embodying legendary poets, using SQLite for instructions, "
            "agent-as-tool for collaboration, and MCPs for creative augmentation."
        ),
        "version": "1.2.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["poetry", "writing", "collaboration", "multi-agent", "sqlite", "mcp"],
        "required_mcp_servers": [ # List all potential servers agents might use
            "memory", "filesystem", "mcp-shell", "sqlite", "sequential-thinking",
            "server-wp-mcp", "rag-docs", "mcp-doc-forge", "mcp-npx-fetch",
            "brave-search", "mcp-server-reddit"
        ],
        "env_vars": [ # Informational list of potential vars needed by MCPs
            "ALLOWED_PATH", "SQLITE_DB_PATH", "WP_SITES_PATH", # Added WP_SITES_PATH
            "BRAVE_API_KEY", "OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY",
            "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT", # For reddit MCP
            "WORDPRESS_API_KEY" # If server-wp-mcp needs it
        ]
    }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}
    _db_initialized = False

    # --- Database Interaction ---
    def _init_db_and_load_data(self) -> None:
        """Initializes the SQLite DB and loads Unapologetic Press sample data if needed."""
        if self._db_initialized: return
        logger.info(f"Initializing SQLite database at: {DB_PATH} for Unapologetic Press")
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} (...)") # Ensure table exists
                logger.debug(f"Table '{TABLE_NAME}' ensured in {DB_PATH}")
                cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE agent_name = ?", ("Gritty Buk",))
                if cursor.fetchone()[0] == 0:
                    logger.info(f"No instructions found for Gritty Buk in {DB_PATH}. Loading sample data...")
                    sample_data = []
                    for name, (base_instr, _, _) in AGENT_BASE_INSTRUCTIONS.items():
                         # Combine instructions here before inserting
                         full_instr = f"{base_instr}\n{COLLABORATIVE_KNOWLEDGE}\n{SHARED_PROTOCOL}"
                         sample_data.append((name, full_instr, "default")) # Use default profile for all initially

                    cursor.executemany(f"INSERT OR IGNORE INTO {TABLE_NAME} (agent_name, instruction_text, model_profile) VALUES (?, ?, ?)", sample_data)
                    conn.commit()
                    logger.info(f"Sample agent instructions for Unapologetic Press loaded into {DB_PATH}")
                else:
                    logger.info(f"Unapologetic Press agent instructions found in {DB_PATH}. Skipping.")
            self._db_initialized = True
        except sqlite3.Error as e:
            logger.error(f"SQLite error during DB init/load: {e}", exc_info=True)
            self._db_initialized = False
        except Exception as e:
            logger.error(f"Unexpected error during DB init/load: {e}", exc_info=True)
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
            except Exception as e:
                 logger.error(f"Error fetching SQLite config for '{agent_name}': {e}. Using defaults.", exc_info=True)

        # Fallback if DB fails or agent not found
        logger.warning(f"Using hardcoded default config for agent '{agent_name}'.")
        base_instr = AGENT_BASE_INSTRUCTIONS.get(agent_name, (f"Default instructions for {agent_name}.", [], {}))[0]
        full_instr = f"{base_instr}\n{COLLABORATIVE_KNOWLEDGE}\n{SHARED_PROTOCOL}"
        return {"instructions": full_instr, "model_profile": "default"}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation is the same as previous refactors) ...
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
        """Creates the Unapologetic Press agent team."""
        self._init_db_and_load_data()
        logger.debug("Creating Unapologetic Press agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        # Helper to filter MCP servers
        def get_agent_mcps(names: List[str]) -> List[MCPServer]:
            return [s for s in mcp_servers if s.name in names]

        agents: Dict[str, Agent] = {}
        agent_configs = {} # To store fetched configs

        # Fetch configs and create agents first
        agent_names = list(AGENT_BASE_INSTRUCTIONS.keys())
        for name in agent_names:
            config = self.get_agent_config(name)
            agent_configs[name] = config # Store config
            model_instance = self._get_model_instance(config["model_profile"])

            # Determine MCP servers based on original definitions
            agent_mcp_names = []
            if name == "Gritty Buk": agent_mcp_names = ["memory", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Raven Poe": agent_mcp_names = ["mcp-server-reddit", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Mystic Blake": agent_mcp_names = ["mcp-doc-forge", "mcp-npx-fetch", "brave-search", "server-wp-mcp", "rag-docs"]
            elif name == "Bard Whit": agent_mcp_names = ["sequential-thinking", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Echo Plath": agent_mcp_names = ["sqlite", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Frosted Woods": agent_mcp_names = ["filesystem", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Harlem Lang": agent_mcp_names = ["mcp-shell", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Verse Neru": agent_mcp_names = ["server-wp-mcp", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"]
            elif name == "Haiku Bash": agent_mcp_names = ["mcp-doc-forge", "mcp-npx-fetch", "brave-search", "server-wp-mcp", "rag-docs"]

            agents[name] = Agent(
                name=name,
                instructions=config["instructions"], # Instructions already combined in get_agent_config fallback or DB
                model=model_instance,
                tools=[], # Agent-as-tool added later
                mcp_servers=get_agent_mcps(agent_mcp_names)
            )

        # Create the list of agent tools for delegation
        agent_tools = []
        for name, agent_instance in agents.items():
            # Example description, could be more dynamic
            desc = f"Pass the current work to {name} for refinement or tasks requiring their specific style ({AGENT_BASE_INSTRUCTIONS.get(name, ('Unknown Style',[],{}))[0].split(':')[0]})."
            agent_tools.append(agent_instance.as_tool(tool_name=name, tool_description=desc))

        # Assign the full list of agent tools to each agent
        for agent in agents.values():
            agent.tools = agent_tools

        # Randomly select starting agent
        start_name = random.choice(agent_names)
        starting_agent = agents[start_name]

        logger.info(f"Unapologetic Press agents created (using SQLite). Starting poet: {start_name}")
        return starting_agent

# Standard Python entry point
if __name__ == "__main__":
    UnapologeticPressBlueprint.main()
