import asyncio
import json
import logging
import os
import sys
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union
from contextlib import AsyncExitStack

# --- Core Agent Imports ---
from agents import Agent, Runner
from agents.tool import FunctionToolResult
from agents.result import RunResult
from agents.items import MessageOutputItem
from agents.mcp import MCPServer
from agents import set_default_openai_api

# --- Standard Library & Third-Party ---
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

# --- Internal Imports ---
from .config_loader import load_environment, load_full_configuration
from .mcp_manager import start_mcp_server_instance
from .cli_handler import run_blueprint_cli

# --- Configuration & Constants ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[4]
except IndexError:
    logging.basicConfig(level=logging.WARNING)
    logging.warning("Could not determine project root. Defaulting to parent of CWD.")
    PROJECT_ROOT = Path.cwd().parent

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "swarm_config.json"
SWARM_VERSION = "0.2.17-test-fixes-2" # Version Bump
DEFAULT_MCP_STARTUP_TIMEOUT = 30.0

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True, show_path=False)],
)
logger = logging.getLogger("swarm")
logger.setLevel(logging.INFO)
for lib in ["httpx", "httpcore", "openai", "asyncio", "agents"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

# --- Base Blueprint Class ---
class BlueprintBase(ABC):
    """ Abstract base class for Open Swarm blueprints. """
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "AbstractBlueprintBase", "title": "Base Blueprint (Override Me)", "version": "0.0.0",
        "description": "Subclasses must provide a meaningful description.", "author": "Unknown",
        "tags": ["base"], "required_mcp_servers": [], "env_vars": [],
    }

    config: Dict[str, Any]
    llm_profiles: Dict[str, Dict[str, Any]]
    mcp_server_configs: Dict[str, Dict[str, Any]]
    console: Console
    # Default class attribute remains True
    use_markdown: bool = True
    max_llm_calls: Optional[int] = None
    quiet_mode: bool = False

    def __init__(
        self,
        config_path_override: Optional[Union[str, Path]] = None,
        profile_override: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        debug: bool = False,
        quiet: bool = False,
        force_markdown: Optional[bool] = None
    ):
        self.quiet_mode = quiet
        self.console = Console(quiet=quiet)

        # --- Configure Logging Level ---
        if quiet: log_level = logging.ERROR
        elif debug: log_level = logging.DEBUG
        else: log_level = logging.INFO
        logger.setLevel(log_level)
        logging.getLogger("agents").setLevel(logging.DEBUG if debug else logging.INFO)
        verbose_log_level = logging.INFO if debug else logging.WARNING
        for lib in ["httpx", "httpcore", "openai", "asyncio"]:
            logging.getLogger(lib).setLevel(verbose_log_level)
        logger.debug(f"[Init] Final effective log level set: {logging.getLevelName(logger.level)}.")

        # --- Set Default OpenAI API ---
        try: set_default_openai_api("chat_completions"); logger.debug("[Init] Set default OpenAI API.")
        except Exception as e: logger.warning(f"[Init] Failed to set default OpenAI API: {e}")

        # --- Load Environment & Configuration ---
        load_environment(PROJECT_ROOT)
        try:
            self.config = load_full_configuration(
                blueprint_class_name=self.__class__.__name__,
                default_config_path=DEFAULT_CONFIG_PATH,
                config_path_override=config_path_override,
                profile_override=profile_override,
                cli_config_overrides=config_overrides
            )
        except (ValueError, FileNotFoundError) as e:
            logger.critical(f"[Config] Failed to load configuration: {e}", exc_info=debug)
            raise ValueError(f"Configuration loading failed: {e}") from e

        self.llm_profiles = self.config.get("llm", {})
        self.mcp_server_configs = self.config.get("mcpServers", {})

        # --- Set Markdown Usage (Revised Logic) ---
        if force_markdown is not None:
            self.use_markdown = force_markdown # CLI wins
            logger.info(f"Markdown output explicitly set by CLI flag: {self.use_markdown}.")
        else:
            # Get config value, explicitly checking if the key exists
            config_markdown_value = self.config.get("default_markdown_cli", "KeyDoesNotExist") # Use sentinel
            if config_markdown_value != "KeyDoesNotExist":
                 # Key exists, use its value (which could be True or False)
                 self.use_markdown = bool(config_markdown_value) # Ensure boolean
                 logger.debug(f"Markdown output set by config key 'default_markdown_cli': {self.use_markdown}.")
            else:
                 # Key does not exist in config, use the class default (True)
                 # self.use_markdown = True # No need to re-assign, it's the class default
                 logger.debug(f"Markdown output using class default (True) as key 'default_markdown_cli' not found in config.")

        self.max_llm_calls = self.config.get("max_llm_calls", None)

        # --- Log Final Config State (Debug) ---
        logger.debug(f"[Init] Final Config Keys: {list(self.config.keys())}")
        logger.debug(f"[Init] LLM Profiles Loaded: {list(self.llm_profiles.keys())}")
        logger.debug(f"[Init] MCP Server Configs Loaded: {list(self.mcp_server_configs.keys())}")
        logger.debug(f"[Init] Use Markdown Output: {self.use_markdown}") # Log the final value
        logger.debug(f"[Init] Max LLM Calls (Informational): {self.max_llm_calls}")

        # --- Check Required Environment Variables ---
        self._check_required_env_vars()

    def _check_required_env_vars(self):
        """Checks if environment variables listed in metadata['env_vars'] are set."""
        required_vars = self.metadata.get("env_vars", [])
        if not isinstance(required_vars, list):
            logger.warning(f"[Init] Blueprint '{self.metadata.get('name')}' metadata 'env_vars' is not a list.")
            return
        missing_vars = [var for var in required_vars if var not in os.environ]
        if missing_vars:
            logger.warning(
                f"[Init] Blueprint '{self.metadata.get('name')}' may require env vars "
                f"not set: {', '.join(missing_vars)}. Functionality may be limited."
            )
        else:
             if required_vars: logger.debug(f"[Init] All required env vars found for '{self.metadata.get('name')}'.")

    def get_llm_profile(self, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """ Retrieves the fully resolved LLM profile, handling defaults and empty profiles. """
        profile_to_check = profile_name or "default"
        if profile_to_check in self.llm_profiles:
            profile_data = self.llm_profiles[profile_to_check]; logger.debug(f"[LLM] Using profile '{profile_to_check}'."); return profile_data
        elif profile_to_check != "default":
            logger.warning(f"LLM profile '{profile_name}' not found, falling back to 'default'.")
            if "default" in self.llm_profiles:
                profile_data = self.llm_profiles["default"]; logger.debug("[LLM] Using profile 'default'."); return profile_data
        logger.error(f"LLM profile '{profile_to_check}' (and 'default' fallback) not found!"); return None

    def get_mcp_server_description(self, server_name: str) -> Optional[str]:
        """Retrieves the description for a given MCP server name from the loaded config."""
        return self.mcp_server_configs.get(server_name, {}).get("description")

    @abstractmethod
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """ Abstract method for subclasses to create the primary starting Agent. """
        pass

    def display_splash_screen(self):
        """ Optional method for blueprints to display an introductory message. """
        pass

    async def _run_non_interactive(self, instruction: str):
        """ Internal method orchestrating non-interactive execution. """
        if not self.quiet_mode: self.display_splash_screen()
        bp_title = self.metadata.get('title', self.__class__.__name__)
        logger.debug(f"--- Running Blueprint: {bp_title} (v{self.metadata.get('version', 'N/A')}) ---")
        logger.debug(f"Instruction: '{textwrap.shorten(instruction, 100)}'")
        required_servers = self.metadata.get("required_mcp_servers", [])
        started_mcps: List[MCPServer] = []; final_output: Any = f"Error: Blueprint '{bp_title}' failed."
        async with AsyncExitStack() as stack:
            # Start MCP Servers
            if required_servers:
                logger.info(f"[MCP] Required: {required_servers}. Starting...")
                tasks = [start_mcp_server_instance(stack, name, self.mcp_server_configs.get(name, {}),
                         PROJECT_ROOT, DEFAULT_MCP_STARTUP_TIMEOUT, os.environ.copy()) for name in required_servers]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                failed_servers = {required_servers[i] for i, r in enumerate(results) if not isinstance(r, MCPServer)}
                started_mcps = [r for r in results if isinstance(r, MCPServer)]
                for i, r in enumerate(results): # Log specific gather errors
                    if isinstance(r, Exception): logger.error(f"[MCP:{required_servers[i]}] Startup gather error: {r}", exc_info=True)

                if failed_servers:
                    error_msg = f"Fatal MCP Error: Failed servers: {', '.join(sorted(failed_servers))}. Aborting."
                    logger.error(error_msg); final_output = f"Error: MCP server(s) failed: {', '.join(sorted(failed_servers))}."
                    if not self.quiet_mode: self.console.print(f"\n[bold red]Blueprint Failed: {error_msg}[/]")
                    return
                logger.info(f"[MCP] Started: {[s.name for s in started_mcps]}")
            else: logger.info("[MCP] No MCP servers required.")

            # Create Agent
            try:
                logger.debug("Creating starting agent..."); agent = self.create_starting_agent(mcp_servers=started_mcps)
                if not isinstance(agent, Agent): raise TypeError(f"create_starting_agent must return Agent, got {type(agent).__name__}")
                logger.debug(f"Agent '{agent.name}' created.")
            except Exception as e:
                logger.critical(f"Fatal Error: Agent creation failed: {e}", exc_info=True); final_output = f"Error: Agent creation failed - {e}"
                if not self.quiet_mode: self.console.print(f"\n[bold red]Blueprint Failed: Agent creation error.[/]")
                return

            # Run Agent Workflow
            try:
                logger.debug(f"--- >>> Starting Runner for '{agent.name}' <<< ---")
                result: Optional[RunResult] = await Runner.run(starting_agent=agent, input=instruction)
                logger.debug(f"--- <<< Runner Finished for '{agent.name}' >>> ---")
                final_output = result.final_output if result else "[Runner returned None result]"
                if not result: logger.warning("Runner returned None result object.")
                elif logger.level <= logging.DEBUG: self._log_run_history(result)
            except Exception as e:
                logger.error(f"--- XXX Agent Runner Failed: {e}", exc_info=True); final_output = f"Error during agent execution: {e}"

        self._process_and_print_output(final_output, bp_title)

    def _log_run_history(self, result: RunResult):
        """Logs the execution history from a RunResult in debug mode."""
        # (Implementation unchanged)
        logger.debug("--- Run History ---")
        if hasattr(result, 'history') and result.history:
            for i, item in enumerate(result.history):
                if isinstance(item, MessageOutputItem):
                    content_preview = textwrap.shorten(str(item.content), width=150, placeholder="...")
                    logger.debug(f"  [{i:02d}][{item.message_type.upper():<10}] {item.sender_alias} -> {item.recipient_alias}: {content_preview}")
                elif isinstance(item, FunctionToolResult):
                    result_preview = textwrap.shorten(str(item.result), width=150, placeholder="...")
                    logger.debug(f"  [{i:02d}][TOOL_RESULT] {item.function_name}: {result_preview}")
                else: logger.debug(f"  [{i:02d}][{type(item).__name__:^11}] {item}")
        elif hasattr(result, 'history'): logger.debug("  [History attribute exists but is empty or None]")
        else: logger.debug("  [History attribute not found on RunResult object]")
        logger.debug("--- End Run History ---")

    def _process_and_print_output(self, raw_output: Any, blueprint_title: str):
        """Formats the final output and prints it to the console."""
        # (Implementation unchanged)
        output_str: str
        if isinstance(raw_output, (dict, list)):
            try: output_str = json.dumps(raw_output, indent=2, ensure_ascii=False)
            except TypeError: output_str = str(raw_output); logger.warning("Output is dict/list but not JSON serializable.")
        elif raw_output is None: output_str = "[No output]"; logger.warning("Runner returned None output.")
        else: output_str = str(raw_output)

        if self.quiet_mode: print(output_str)
        else:
            self.console.print(f"\n--- Final Output ({blueprint_title}) ---", style="bold blue")
            if self.use_markdown:
                logger.debug("Rendering output as Markdown.")
                try: self.console.print(Markdown(output_str))
                except Exception as md_err: logger.warning(f"Markdown rendering failed ({md_err}). Printing raw."); self.console.print(output_str)
            else: logger.debug("Printing output as plain text."); self.console.print(output_str)
            self.console.print("-----------------------------", style="bold blue")

    @classmethod
    def main(cls):
        """ Class method entry point for command-line execution. Delegates to cli_handler. """
        run_blueprint_cli(cls, SWARM_VERSION, DEFAULT_CONFIG_PATH)
