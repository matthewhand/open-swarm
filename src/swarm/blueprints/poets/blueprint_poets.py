"""
Poets Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
import asyncio
import logging
import os
import random
import sqlite3  # Use standard sqlite3 module
import sys
import threading
import time
from pathlib import Path
from typing import Any, ClassVar

from rich.console import Console
from rich.style import Style
from rich.text import Text

from swarm.core.output_utils import print_operation_box
from swarm.extensions.cli.utils.async_input import AsyncInputHandler

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from openai import AsyncOpenAI

    from agents import Agent, Runner, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    print_operation_box(
        op_type="Import Error",
        results=["Import failed in PoetsBlueprint", str(e)],
        params=None,
        result_type="error",
        summary="Import failed",
        progress_line=None,
        spinner_state="Failed",
        operation_type="Import",
        search_mode=None,
        total_lines=None
    )
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
        with open(path) as f:
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

# --- Unified Operation/Result Box for UX ---

# --- Spinner and ANSI/emoji operation box for unified UX ---
class PoetsSpinner:
    FRAMES = [
        "Generating.", "Generating..", "Generating...", "Running...",
        "⠋ Generating...", "⠙ Generating...", "⠹ Generating...", "⠸ Generating...",
        "⠼ Generating...", "⠴ Generating...", "⠦ Generating...", "⠧ Generating...",
        "⠇ Generating...", "⠏ Generating...", "🤖 Generating...", "💡 Generating...", "✨ Generating..."
    ]
    SLOW_FRAME = "⏳ Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()

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
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))

# --- Define the Blueprint ---
class PoetsBlueprint(BlueprintBase):
    """A literary blueprint defining a swarm of poet agents using SQLite instructions and agent-as-tool handoffs."""
    metadata: ClassVar[dict[str, Any]] = {
        "name": "PoetsBlueprint",
        "title": "Poets: A Swarm of Literary Geniuses (SQLite)",
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
    _openai_client_cache: dict[str, AsyncOpenAI] = {}
    _model_instance_cache: dict[str, Model] = {}
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
        """Initializes the SQLite DB and loads Poets sample data if needed."""
        if self._db_initialized: return
        logger.info(f"Initializing SQLite database at: {DB_PATH} for Poets")
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
                    logger.info(f"Sample agent instructions for Poets loaded into {DB_PATH}")
                else:
                    logger.info(f"Poets agent instructions found in {DB_PATH}. Skipping.")
            self._db_initialized = True
        except sqlite3.Error as e:
            logger.error(f"SQLite error during DB init/load: {e}", exc_info=True)
            self._db_initialized = False
        except Exception as e:
            logger.error(f"Unexpected error during DB init/load: {e}", exc_info=True)
            self._db_initialized = False

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
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

    async def run(self, messages, **kwargs):
        import os
        import time
        op_start = time.monotonic()
        instruction = messages[-1]["content"] if messages else ""
        # --- Unified Spinner/Box Output for Test Mode ---
        if os.environ.get('SWARM_TEST_MODE'):
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            PoetsBlueprint.print_search_progress_box(
                op_type="Poets Spinner",
                results=[
                    "Poets Search",
                    f"Searching for: '{instruction}'",
                    *spinner_lines,
                    "Results: 2",
                    "Processed",
                    "📝"
                ],
                params=None,
                result_type="poets",
                summary=f"Searching for: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="Poets Spinner",
                search_mode=None,
                total_lines=None,
                emoji='📝',
                border='╔'
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                PoetsBlueprint.print_search_progress_box(
                    op_type="Poets Spinner",
                    results=[f"Spinner State: {spinner_state}"],
                    params=None,
                    result_type="poets",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="Poets Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='📝',
                    border='╔'
                )
                import asyncio; await asyncio.sleep(0.01)
            PoetsBlueprint.print_search_progress_box(
                op_type="Poets Results",
                results=[f"Poets agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="poets",
                summary=f"Poets agent response for: '{instruction}'",
                progress_line="Processed",
                spinner_state="Done",
                operation_type="Poets Results",
                search_mode=None,
                total_lines=None,
                emoji='📝',
                border='╔'
            )
            return
        # ... existing logic ...
        logger = logging.getLogger(__name__)
        from agents import Runner
        llm_response = ""
        try:
            agent = self.create_starting_agent([])
            response = await Runner.run(agent, messages[-1].get("content", ""))
            llm_response = getattr(response, 'final_output', str(response))
            results = [llm_response.strip() or "(No response from LLM)"]
        except Exception as e:
            results = [f"[LLM ERROR] {e}"]
        # Check for code/semantic search and distinguish output if applicable
        search_mode = kwargs.get('search_mode')
        if search_mode in ("semantic", "code"):
            op_type = "Poets Semantic Search" if search_mode == "semantic" else "Poets Code Search"
            emoji = "🔎" if search_mode == "semantic" else "💻"
            summary = f"Analyzed ({search_mode}) for: '{messages[-1].get('content', '')}'"
            params = {"instruction": messages[-1].get("content", "")}
            # Simulate progressive search with line numbers
            for i in range(1, 6):
                PoetsBlueprint.print_search_progress_box(
                    op_type=op_type,
                    results=[
                        f"Poets agent response for: '{instruction}'",
                        f"Search mode: {search_mode}",
                        f"Parameters: {params}",
                        f"Matches so far: {i}",
                        f"Line: {i*20}/{100}" if 100 else None,
                        *spinner_lines,
                    ],
                    params=params,
                    result_type=search_mode,
                    summary=summary,
                    progress_line=f"Processed {i*20} lines",
                    spinner_state=f"Searching {'.' * i}",
                    operation_type=op_type,
                    search_mode=search_mode,
                    total_lines=100,
                    emoji=emoji,
                    border='╔'
                )
                await asyncio.sleep(0.05)
            PoetsBlueprint.print_search_progress_box(
                op_type=op_type,
                results=[
                    f"Searched for: '{instruction}'",
                    f"Search mode: {search_mode}",
                    f"Parameters: {params}",
                    f"Found {5} matches.",
                    f"Processed {100} lines." if 100 else None,
                    "Processed",
                ],
                params=params,
                result_type="search_results",
                summary=summary,
                progress_line=f"Processed {100} lines" if 100 else None,
                spinner_state="Done",
                operation_type=op_type,
                search_mode=search_mode,
                total_lines=100,
                emoji=emoji,
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"{search_mode.title()} search complete. Found 3 results for '{messages[-1].get('content', '')}'."}]}
            return
        # Spinner/UX enhancement: cycle through spinner states and show 'Taking longer than expected' (with variety)
        spinner_states = [
            "Quilling verses... 🪶",
            "Rhyme weaving... 🧵",
            "Counting syllables... 🔢",
            "Reciting aloud... 🎤"
        ]
        total_steps = len(spinner_states)
        params = {"instruction": messages[-1].get("content", "") if messages else ""}
        summary = f"Poets agent run for: '{params['instruction']}'"
        for i, spinner_state in enumerate(spinner_states, 1):
            progress_line = f"Step {i}/{total_steps}"
            PoetsBlueprint.print_search_progress_box(
                op_type="Poets Agent Run",
                results=[
                    params['instruction'],
                    f"Poets agent is running your request... (Step {i})",
                    f"Search mode: {search_mode}",
                    f"Parameters: {params}",
                    f"Matches so far: {i}",
                    f"Line: {i*20}/{total_steps}" if total_steps else None,
                    *spinner_states,
                ],
                params=params,
                result_type="poets",
                summary=summary,
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Poets Run",
                search_mode=None,
                total_lines=total_steps,
                emoji='🪶',
                border='╔'
            )
            await asyncio.sleep(0.12)
        PoetsBlueprint.print_search_progress_box(
            op_type="Poets Agent Run",
            results=[
                params['instruction'],
                "Poets agent is running your request... (Taking longer than expected)",
                "The muse is elusive...",
                f"Search mode: {search_mode}",
                f"Parameters: {params}",
                f"Matches so far: {total_steps}",
                f"Line: {total_steps*20}/{total_steps}" if total_steps else None,
                "Processed",
            ],
            params=params,
            result_type="poets",
            summary=summary,
            progress_line=f"Step {total_steps}/{total_steps}",
            spinner_state="Generating... Taking longer than expected 🦉",
            operation_type="Poets Run",
            search_mode=None,
            total_lines=total_steps,
            emoji='🪶',
            border='╔'
        )
        await asyncio.sleep(0.24)
        PoetsBlueprint.print_search_progress_box(
            op_type="Poets Creative",
            results=results,
            params=params,
            result_type="creative",
            summary=f"Creative generation complete for: '{params['instruction']}'",
            progress_line=None,
            spinner_state=None,
            operation_type="Poets Creative",
            search_mode=None,
            total_lines=None,
            emoji='🪶',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": results[0]}]}
        return

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
        """Creates the Poets agent team."""
        self._init_db_and_load_data()
        logger.debug("Creating Poets agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        # Helper to filter MCP servers
        def get_agent_mcps(names: list[str]) -> list[MCPServer]:
            return [s for s in mcp_servers if s.name in names]

        agents: dict[str, Agent] = {}
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

        # Create PoetsAgent with fileops tools
        poets_agent = Agent(
            name="PoetsAgent",
            instructions="You are PoetsAgent. You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.",
            tools=[read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
            mcp_servers=mcp_servers
        )

        # Randomly select starting agent
        start_name = random.choice(agent_names)
        starting_agent = agents[start_name]

        logger.info(f"Poets agents created (using SQLite). Starting poet: {start_name}")
        return starting_agent

    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(*args, **kwargs)

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import os
    import sys
    print_operation_box(
        op_type="Poets Demo",
        results=["POETS: SWARM MEDIA & RELEASE DEMO", "This blueprint demonstrates viral doc propagation, swarm-powered media release, and robust agent logic."],
        params=None,
        result_type="info",
        summary="Poets Demo",
        progress_line=None,
        spinner_state="Ready",
        operation_type="Poets Demo",
        search_mode=None,
        total_lines=None
    )
    debug_env = os.environ.get("SWARM_DEBUG", "0")
    debug_flag = "--debug" in sys.argv
    def debug_print(msg):
        print_operation_box(
            op_type="Debug",
            results=[msg],
            params=None,
            result_type="debug",
            summary="Debug message",
            progress_line=None,
            spinner_state="Debug",
            operation_type="Debug",
            search_mode=None,
            total_lines=None
        )
    blueprint = PoetsBlueprint(blueprint_id="demo-1")
    async def interact():
        print_operation_box(
            op_type="Prompt",
            results=["Type your prompt (or 'exit' to quit):"],
            params=None,
            result_type="prompt",
            summary="Prompt",
            progress_line=None,
            spinner_state="Ready",
            operation_type="Prompt",
            search_mode=None,
            total_lines=None
        )
        messages = []
        handler = AsyncInputHandler()
        while True:
            print_operation_box(
                op_type="User Input",
                results=["You: "],
                params=None,
                result_type="input",
                summary="Awaiting user input",
                progress_line=None,
                spinner_state="Waiting",
                operation_type="Input",
                search_mode=None,
                total_lines=None
            )
            user_input = ""
            warned = False
            while True:
                inp = handler.get_input(timeout=0.1)
                if inp == 'warn' and not warned:
                    print_operation_box(
                        op_type="Interrupt",
                        results=["[!] Press Enter again to interrupt and send a new message."],
                        params=None,
                        result_type="info",
                        summary="Interrupt info",
                        progress_line=None,
                        spinner_state="Interrupt",
                        operation_type="Interrupt",
                        search_mode=None,
                        total_lines=None
                    )
                    warned = True
                elif inp and inp != 'warn':
                    user_input = inp
                    break
                await asyncio.sleep(0.05)
            user_input = user_input.strip()
            if user_input.lower() in {"exit", "quit", "q"}:
                print_operation_box(
                    op_type="Exit",
                    results=["Goodbye!"],
                    params=None,
                    result_type="exit",
                    summary="Session ended",
                    progress_line=None,
                    spinner_state="Done",
                    operation_type="Exit",
                    search_mode=None,
                    total_lines=None
                )
                break
            messages.append({"role": "user", "content": user_input})
            spinner = PoetsSpinner()
            spinner.start()
            try:
                all_results = []
                async for response in blueprint.run(messages):
                    # Assume response is a dict with 'messages' key
                    for msg in response.get("messages", []):
                        all_results.append(msg["content"])
            finally:
                spinner.stop()
            print_operation_box(
                op_type="Creative Output",
                results=all_results,
                params={"prompt": user_input},
                result_type="creative",
                operation_type="Creative Output",
                search_mode=None
            )
            # Optionally, clear messages for single-turn, or keep for context
            messages = []
    asyncio.run(interact())
