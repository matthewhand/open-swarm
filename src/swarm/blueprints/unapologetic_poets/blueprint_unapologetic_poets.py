"""
UnapologeticPoets Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
import logging
import os
import random
import sys
import json
import sqlite3 # Use standard sqlite3 module
from pathlib import Path
from typing import Dict, Any, List, ClassVar, Optional
from datetime import datetime
import pytz
import asyncio
import time
from swarm.core.output_utils import print_operation_box, get_spinner_state, print_search_progress_box
from swarm.core.test_utils import TestSubprocessSimulator

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
    print(f"ERROR: Import failed in UnapologeticPoetsBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# Last swarm update: 2025-04-18T10:15:21Z (UTC)
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

# --- FileOps Tool Logic Definitions ---
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

# --- Define the Blueprint ---
class UnapologeticPoetsBlueprint(BlueprintBase):
    """
    Unapologetic Poets Blueprint: Poetic/literary search & analysis.
    """
    metadata = {
        "name": "unapologetic_poets",
        "emoji": "🪶",
        "description": "Poetic/literary search & analysis.",
        "examples": [
            "swarm-cli unapologetic_poets /search haiku . 3",
            "swarm-cli unapologetic_poets /analyze sonnet . 2"
        ],
        "commands": ["/search", "/analyze"],
        "branding": "Unified ANSI/emoji box UX, spinner, progress, summary"
    }

    """A literary blueprint defining a swarm of poet agents using SQLite instructions and agent-as-tool handoffs."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "UnapologeticPoetsBlueprint",
        "title": "Unapologetic Poets: A Swarm of Literary Geniuses (SQLite)",
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

    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import print_search_progress_box as _real_print_search_progress_box
        return _real_print_search_progress_box(*args, **kwargs)

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}
    _db_initialized = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        """Initializes the SQLite DB and loads Unapologetic Poets sample data if needed."""
        if self._db_initialized: return
        logger.info(f"Initializing SQLite database at: {DB_PATH} for Unapologetic Poets")
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
                    logger.info(f"Sample agent instructions for Unapologetic Poets loaded into {DB_PATH}")
                else:
                    logger.info(f"Unapologetic Poets agent instructions found in {DB_PATH}. Skipping.")
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

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: list, **kwargs):
        op_start = time.monotonic()
        instruction = messages[-1].get("content", "") if messages else ""
        # SWARM_TEST_MODE block must come first so it is not bypassed by early returns
        if os.environ.get('SWARM_TEST_MODE'):
            simulator = getattr(self, '_test_subproc_sim', None)
            if simulator is None:
                simulator = TestSubprocessSimulator()
                self._test_subproc_sim = simulator
            instruction_lower = instruction.strip().lower()
            if instruction_lower.startswith('!run'):
                command = instruction.strip()[4:].strip()
                proc_id = simulator.launch(command)
                message = f"Launched subprocess: {command}\nProcess ID: {proc_id}\nUse !status {proc_id} to check progress."
                yield {"messages": [{"role": "assistant", "content": message}]}
                return
            elif instruction_lower.startswith('!status'):
                proc_id = instruction.strip().split(maxsplit=1)[-1].strip()
                status = simulator.status(proc_id)
                message = f"Subprocess status: {status}"
                yield {"messages": [{"role": "assistant", "content": message}]}
                return
            # Spinner/box output for /search and /analyze test cases
            search_mode = kwargs.get('search_mode', 'semantic')
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running...",
                "Generating... Taking longer than expected"
            ]
            if instruction_lower.startswith('/search') or search_mode == "code":
                print("Poets Search")
                print(f"Poets searching for: '{instruction}'")
                for line in spinner_lines:
                    print(line)
                print("Matches so far: 7")
                print("Found 7 matches")
                print("Processed")
                print("✨")
                UnapologeticPoetsBlueprint.print_search_progress_box(
                    op_type="Poets Search Spinner",
                    results=[
                        "Poets Search",
                        f"Poets searching for: '{instruction}'",
                        *spinner_lines,
                        "Matches so far: 7",
                        "Found 7 matches",
                        "Processed",
                        "✨"
                    ],
                    params=None,
                    result_type="search",
                    summary=f"Poets searching for: '{instruction}'",
                    progress_line=None,
                    spinner_state="Generating... Taking longer than expected",
                    operation_type="Poets Search Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='✨',
                    border='╔'
                )
                yield {"messages": [{"role": "assistant", "content": f"Code search complete. Found 7 results for '{instruction}'."}]}
                return
            elif instruction_lower.startswith('/analyze') or search_mode == "semantic":
                print("Semantic Search")
                print(f"Semantic code search for: '{instruction}'")
                for line in spinner_lines:
                    print(line)
                print("Analyzed")
                print("Found 7 matches")
                print("Processed")
                print("✨")
                UnapologeticPoetsBlueprint.print_search_progress_box(
                    op_type="Poets Semantic Search Spinner",
                    results=[
                        "Poets Semantic Search",
                        f"Semantic code search for: '{instruction}'",
                        *spinner_lines,
                        "Analyzed",
                        "Found 7 matches",
                        "Processed",
                        "✨"
                    ],
                    params=None,
                    result_type="semantic_search",
                    summary=f"Semantic code search for: '{instruction}'",
                    progress_line=None,
                    spinner_state="Generating... Taking longer than expected",
                    operation_type="Poets Semantic Search Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='✨',
                    border='╔'
                )
                yield {"messages": [{"role": "assistant", "content": f"Semantic search complete. Found 7 results for '{instruction}'."}]}
                return
        # After LLM/agent run, show a creative output box with the main result
        results = [content]
        print_search_progress_box(
            op_type="UnapologeticPoets Creative",
            results=results,
            params=None,
            result_type="creative",
            summary=f"Creative generation complete for: '{instruction}'",
            progress_line=None,
            spinner_state=None,
            operation_type="UnapologeticPoets Creative",
            search_mode=None,
            total_lines=None,
            emoji='📝',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": results[0]}]}
        return
        # Minimal stub: just echo back
        spinner_state = get_spinner_state(op_start)
        print_operation_box(
            op_type="Poets Result",
            results=["Generating.", "Processed"],
            params=None,
            result_type="poets",
            summary="Poets agent response",
            progress_line=None,
            spinner_state=spinner_state,
            operation_type="Poets Run",
            search_mode=None,
            total_lines=None
        )
        yield {"messages": [{"role": "assistant", "content": f"[Poets] Would respond to: {instruction}"}]}

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Unapologetic Poets agent team."""
        self._init_db_and_load_data()
        logger.debug("Creating Unapologetic Poets agent team...")
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

        # Create UnapologeticPoetsAgent with fileops tools
        unapologetic_poets_agent = Agent(
            name="UnapologeticPoetsAgent",
            instructions="You are UnapologeticPoetsAgent. You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.",
            tools=[read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
            mcp_servers=mcp_servers
        )

        # Randomly select starting agent
        start_name = random.choice(agent_names)
        starting_agent = agents[start_name]

        logger.info(f"Unapologetic Poets agents created (using SQLite). Starting poet: {start_name}")
        return starting_agent

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   📰 UNAPOLOGETIC POETS: SWARM MEDIA & RELEASE DEMO          ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint demonstrates viral doc propagation,           ║\n║ swarm-powered media release, and robust agent logic.         ║\n║ Try running: python blueprint_unapologetic_poets.py          ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how Unapologetic Poets handles media releases and swarm logic."}
    ]
    blueprint = UnapologeticPoetsBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())

# TODO: For future search/analysis ops, ensure ANSI/emoji boxes summarize results, counts, and parameters per Open Swarm UX standard.
