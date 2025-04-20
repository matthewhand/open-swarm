"""
Jeeves Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
# [Swarm Propagation] Next Blueprint: divine_code
# divine_code key vars: logger, project_root, src_path
# divine_code guard: if src_path not in sys.path: sys.path.insert(0, src_path)
# divine_code debug: logger.debug("Divine Ops Team (Zeus & Pantheon) created successfully. Zeus is starting agent.")
# divine_code error handling: try/except ImportError with sys.exit(1)

import logging
import os
import sys
import time
import threading
from typing import Dict, Any, List, ClassVar, Optional
from datetime import datetime
import pytz
from swarm.blueprints.common.operation_box_utils import display_operation_box

class ToolRegistry:
    """
    Central registry for all tools: both LLM (OpenAI function-calling) and Python-only tools.
    """
    def __init__(self):
        self.llm_tools = {}
        self.python_tools = {}

    def register_llm_tool(self, name: str, description: str, parameters: dict, handler):
        self.llm_tools[name] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'handler': handler
        }

    def register_python_tool(self, name: str, handler, description: str = ""):
        self.python_tools[name] = handler

    def get_llm_tools(self, as_openai_spec=False):
        tools = list(self.llm_tools.values())
        if as_openai_spec:
            # Return OpenAI-compatible dicts
            return [
                {
                    'name': t['name'],
                    'description': t['description'],
                    'parameters': t['parameters']
                } for t in tools
            ]
        return tools

    def get_python_tool(self, name: str):
        return self.python_tools.get(name)

from datetime import datetime
import pytz

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from typing import Optional
from pathlib import Path
try:
    from agents import Agent, Tool, function_tool, Runner # Added Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.core.blueprint_base import BlueprintBase
    from swarm.core.blueprint_ux import BlueprintUXImproved
except ImportError as e:
    print(f"ERROR: Import failed in JeevesBlueprint: {e}. Check 'openai-agents' install and project structure.")
    print(f"Attempted import from directory: {os.path.dirname(__file__)}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# Last swarm update: 2025-04-18T10:15:21Z (UTC)
utc_now = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"# Last swarm update: {utc_now} (UTC)")

# --- Agent Instructions ---

SHARED_INSTRUCTIONS = """
You are part of the Jeeves team. Collaborate via Jeeves, the coordinator.
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
    "5. Synthesize the results received from Mycroft or Gutenberg into a polite, helpful, and complete response for the user. Do not just relay their raw output.\n"
    "You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
)

mycroft_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Mycroft, the Web Sleuth. You ONLY perform web searches when tasked by Jeeves.\n"
    "Use the `duckduckgo-search` MCP tool available to you to execute the search query provided by Jeeves.\n"
    "Return the search results clearly and concisely to Jeeves. Do not add conversational filler.\n"
    "You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
)

gutenberg_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Gutenberg, the Home Scribe. You ONLY execute home automation commands when tasked by Jeeves.\n"
    "Use the `home-assistant` MCP tool available to you to execute the command (e.g., interacting with entities like 'light.kitchen_light').\n"
    "Confirm the action taken (or report any errors) back to Jeeves. Do not add conversational filler.\n"
    "You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
)


# --- FileOps Tool Logic Definitions ---
@function_tool
def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

@function_tool
def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"

@function_tool
def list_files(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"

@function_tool
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

from dataclasses import dataclass

@dataclass
class AgentTool:
    name: str
    description: str
    parameters: dict
    handler: callable = None

# Spinner UX enhancement (Open Swarm TODO)
# --- Spinner States for progressive operation boxes ---
SPINNER_STATES = [
    "Generating.",
    "Generating..",
    "Generating...",
    "Running..."
]

# --- Spinner State Constants ---
class JeevesSpinner:
    FRAMES = [
        "Generating.",
        "Generating..",
        "Generating...",
        "Running..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        import threading, time
        from rich.console import Console
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

import re

def grep_search(pattern: str, path: str = ".", case_insensitive: bool = False, max_results: int = 100, progress_yield: int = 10):
    """Progressive regex search in files, yields dicts of matches and progress."""
    matches = []
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        total_files = 0
        for root, dirs, files in os.walk(path):
            for fname in files:
                total_files += 1
        scanned_files = 0
        for root, dirs, files in os.walk(path):
            for fname in files:
                fpath = os.path.join(root, fname)
                scanned_files += 1
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line, flags):
                                matches.append({
                                    "file": fpath,
                                    "line": i,
                                    "content": line.strip()
                                })
                                if len(matches) >= max_results:
                                    yield {"matches": matches, "progress": scanned_files, "total": total_files, "truncated": True, "done": True}
                                    return
                except Exception:
                    continue
                if scanned_files % progress_yield == 0:
                    yield {"matches": matches.copy(), "progress": scanned_files, "total": total_files, "truncated": False, "done": False}
        # Final yield
        yield {"matches": matches, "progress": scanned_files, "total": total_files, "truncated": False, "done": True}
    except Exception as e:
        yield {"matches": [], "progress": 0, "total": 0, "truncated": False, "done": True, "error": str(e)}

try:
    ToolRegistry.register_llm_tool = staticmethod(ToolRegistry.register_llm_tool)
    if not hasattr(ToolRegistry, '_grep_registered'):
        ToolRegistry._grep_registered = True
        ToolRegistry.register_llm_tool(
            ToolRegistry,
            name="grep_search",
            description="Progressively search for a regex pattern in files under a directory tree, yielding progress.",
            parameters={
                "pattern": {"type": "string", "description": "Regex pattern to search for."},
                "path": {"type": "string", "description": "Directory to search in.", "default": "."},
                "case_insensitive": {"type": "boolean", "description": "Case-insensitive search.", "default": False},
                "max_results": {"type": "integer", "description": "Maximum number of results.", "default": 100},
                "progress_yield": {"type": "integer", "description": "How often to yield progress.", "default": 10}
            },
            handler=grep_search
        )
except Exception as e:
    print(f"Error registering grep_search tool: {e}")

from rich.console import Console
from rich.panel import Panel
from rich import box as rich_box
from rich.text import Text
from rich.style import Style

console = Console()

# --- Define the Blueprint ---
class JeevesBlueprint(BlueprintBase):
    """
    Jeeves: Swarm-powered digital butler and code assistant blueprint.
    """
    metadata: ClassVar[dict] = {
        "name": "JeevesBlueprint",
        "cli_name": "jeeves",
        "title": "Jeeves: Swarm-powered digital butler and code assistant",
        "description": "A collaborative blueprint for digital butlering, code analysis, and multi-agent task management.",
        "version": "1.1.0", # Version updated
        "author": "Open Swarm Team (Refactored)",
        "tags": ["web search", "home automation", "duckduckgo", "home assistant", "multi-agent", "delegation"],
        "required_mcp_servers": ["duckduckgo-search", "home-assistant"], # List the MCP servers needed by the agents
        # Env vars listed here are informational; they are primarily used by the MCP servers themselves,
        # loaded via .env by BlueprintBase or the MCP process.
        # "env_vars": ["SERPAPI_API_KEY", "HASS_URL", "HASS_API_KEY"]
    }

    def __init__(self, blueprint_id: str = "jeeves", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        # Add other attributes as needed for Jeeves
        # ...

    # Caches for OpenAI client and Model instances
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    def get_model_name(self):
        from swarm.core.blueprint_base import BlueprintBase
        if hasattr(self, '_resolve_llm_profile'):
            profile = self._resolve_llm_profile()
        else:
            profile = getattr(self, 'llm_profile_name', None) or 'default'
        llm_section = self.config.get('llm', {}) if hasattr(self, 'config') else {}
        return llm_section.get(profile, {}).get('model', 'gpt-4o')

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

    def create_starting_agent(self, mcp_servers=None):
        # Return a real Agent with fileops and shell tools for CLI use
        from agents import Agent
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI
        model_name = self.get_model_name()
        openai_client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client)
        tool_registry = getattr(self, 'tool_registry', None)
        if tool_registry is not None:
            llm_tools = tool_registry.get_llm_tools(as_openai_spec=True)
        else:
            llm_tools = []
        python_tools = getattr(self, 'tool_registry', None)
        if python_tools is not None:
            python_tools = python_tools.python_tools
        else:
            python_tools = {}
        agent = Agent(
            name='Jeeves',  # Capitalized to match test expectations
            model=model_instance,
            instructions="You are a highly skilled automation and fileops agent.",
            tools=llm_tools
        )
        agent.python_tools = python_tools
        return agent

    def create_starting_agent_original(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Jeeves agent team: Jeeves, Mycroft, Gutenberg."""
        logger.debug("Creating Jeeves agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Jeeves agents.")
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
                ),
                read_file,
                write_file,
                list_files,
                execute_shell_command
            ],
            # Jeeves itself doesn't directly need MCP servers in this design
            mcp_servers=[]
        )

        mycroft_agent.tools.extend([read_file, write_file, list_files, execute_shell_command])
        gutenberg_agent.tools.extend([read_file, write_file, list_files, execute_shell_command])

        logger.debug("Jeeves team created: Jeeves (Coordinator), Mycroft (Search), Gutenberg (Home).")
        return jeeves_agent # Jeeves is the entry point

    async def run(self, messages: List[Dict[str, Any]], **kwargs):
        """Main execution entry point for the Jeeves blueprint."""
        logger.info("JeevesBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        ux = BlueprintUXImproved(style="serious")
        spinner_idx = 0
        start_time = time.time()
        spinner_yield_interval = 1.0  # seconds
        last_spinner_time = start_time
        yielded_spinner = False
        result_chunks = []
        try:
            from agents import Runner
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
                            title="Jeeves Result",
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
            logger.error(f"Error during Jeeves run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

    async def _run_non_interactive(self, instruction: str, **kwargs) -> Any:
        logger.info(f"Running Jeeves non-interactively with instruction: '{instruction[:100]}...'")
        mcp_servers = kwargs.get("mcp_servers", [])
        agent = self.create_starting_agent(mcp_servers=mcp_servers)
        # Use Runner.run as a classmethod for portability
        from agents import Runner
        model_name = self.get_model_name()
        try:
            result = await Runner.run(agent, instruction)
            # If result is a list/iterable, yield each chunk; else yield as single message
            if isinstance(result, (list, tuple)):
                for chunk in result:
                    yield chunk
            else:
                yield {"messages": [{"role": "assistant", "content": getattr(result, 'final_output', str(result))}]}
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   🤖 JEEVES: SWARM ULTIMATE LIMIT TEST                       ║\n╠══════════════════════════════════════════════════════════════╣\n║ ULTIMATE: Multi-agent, multi-step, parallel, cross-agent     ║\n║ orchestration, error injection, and viral patching.          ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    blueprint = JeevesBlueprint(blueprint_id="ultimate-limit-test")
    async def run_limit_test():
        tasks = []
        async def collect_responses(async_gen):
            results = []
            async for item in async_gen:
                results.append(item)
            return results
        for butler in ["Jeeves", "Mycroft", "Gutenberg"]:
            messages = [
                {"role": "user", "content": f"Have {butler} perform a complex task, inject an error, trigger rollback, and log all steps."}
            ]
            tasks.append(collect_responses(blueprint.run(messages)))
        # Step 2: Multi-agent workflow with viral patching
        messages = [
            {"role": "user", "content": "Jeeves delegates to Mycroft, who injects a bug, Gutenberg detects and patches it, Jeeves verifies the patch. Log all agent handoffs and steps."}
        ]
        tasks.append(collect_responses(blueprint.run(messages)))
        results = await asyncio.gather(*[asyncio.create_task(t) for t in tasks], return_exceptions=True)
        for idx, result in enumerate(results):
            print(f"\n[PARALLEL TASK {idx+1}] Result:")
            if isinstance(result, Exception):
                print(f"Exception: {result}")
            else:
                for response in result:
                    print(json.dumps(response, indent=2))
    asyncio.run(run_limit_test())

# --- CLI entry point ---
def main():
    import argparse
    import sys
    import asyncio
    parser = argparse.ArgumentParser(description="Jeeves: Swarm-powered digital butler and code assistant.")
    parser.add_argument("prompt", nargs="?", help="Prompt or task (quoted)")
    parser.add_argument("-i", "--input", help="Input file or directory", default=None)
    parser.add_argument("-o", "--output", help="Output file", default=None)
    parser.add_argument("--model", help="Model name (codex, gpt, etc.)", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    blueprint = JeevesBlueprint(blueprint_id="cli-jeeves")
    messages = []
    if args.prompt:
        messages.append({"role": "user", "content": args.prompt})
    else:
        print("Type your prompt (or 'exit' to quit):\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Jeeves CLI.")
                break
            if user_input.lower() in {"exit", "quit", "q"}:
                print("Goodbye!")
                break
            messages.append({"role": "user", "content": user_input})
            async def run_and_print():
                spinner = JeevesSpinner()
                spinner.start()
                try:
                    all_results = []
                    async for response in blueprint.run(messages, model=args.model):
                        content = response["messages"][0]["content"] if (isinstance(response, dict) and "messages" in response and response["messages"]) else str(response)
                        all_results.append(content)
                        # If this is a progressive search/analysis output, show operation box
                        if isinstance(response, dict) and (response.get("progress") or response.get("matches")):
                            display_operation_box(
                                title="Progressive Operation",
                                content="\n".join(response.get("matches", [])),
                                style="bold cyan" if response.get("type") == "code_search" else "bold magenta",
                                result_count=len(response.get("matches", [])) if response.get("matches") is not None else None,
                                params={k: v for k, v in response.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                                progress_line=response.get('progress'),
                                total_lines=response.get('total'),
                                spinner_state=spinner.current_spinner_state(),
                                op_type=response.get("type", "search"),
                                emoji="🔍" if response.get("type") == "code_search" else "🧠"
                            )
                finally:
                    spinner.stop()
                display_operation_box(
                    title="Jeeves Output",
                    content="\n".join(all_results),
                    style="bold green",
                    result_count=len(all_results),
                    params={"prompt": messages[0]["content"]},
                    op_type="jeeves"
                )
            asyncio.run(run_and_print())
            messages = []
        return
    async def run_and_print():
        spinner = JeevesSpinner()
        spinner.start()
        try:
            all_results = []
            async for response in blueprint.run(messages, model=args.model):
                content = response["messages"][0]["content"] if (isinstance(response, dict) and "messages" in response and response["messages"]) else str(response)
                all_results.append(content)
                # If this is a progressive search/analysis output, show operation box
                if isinstance(response, dict) and (response.get("progress") or response.get("matches")):
                    display_operation_box(
                        title="Progressive Operation",
                        content="\n".join(response.get("matches", [])),
                        style="bold cyan" if response.get("type") == "code_search" else "bold magenta",
                        result_count=len(response.get("matches", [])) if response.get("matches") is not None else None,
                        params={k: v for k, v in response.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                        progress_line=response.get('progress'),
                        total_lines=response.get('total'),
                        spinner_state=spinner.current_spinner_state(),
                        op_type=response.get("type", "search"),
                        emoji="🔍" if response.get("type") == "code_search" else "🧠"
                    )
        finally:
            spinner.stop()
        display_operation_box(
            title="Jeeves Output",
            content="\n".join(all_results),
            style="bold green",
            result_count=len(all_results),
            params={"prompt": messages[0]["content"]},
            op_type="jeeves"
        )
    asyncio.run(run_and_print())

if __name__ == "__main__":
    main()

class OperationBox:
    def print_box(self, title, content, style="blue", *, result_count: int = None, params: dict = None, op_type: str = None, progress_line: int = None, total_lines: int = None, spinner_state: str = None, emoji: str = None):
        # Use Jeeves-specific emoji and panel style
        if emoji is None:
            emoji = "🤵"
        if op_type == "search":
            emoji = "🔎"
        elif op_type == "analysis":
            emoji = "🧹"
        elif op_type == "error":
            emoji = "❌"
        style = "bold magenta" if op_type == "search" else style
        box_content = f"{emoji} {content}"
        self.console.print(Panel(box_content, title=f"{emoji} {title}", style=style, box=rich_box.ROUNDED))

from rich.console import Console
from rich.panel import Panel
from rich import box as rich_box
from rich.text import Text
from rich.style import Style

console = Console()
