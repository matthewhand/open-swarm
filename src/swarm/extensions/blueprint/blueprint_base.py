import argparse
import asyncio
import json
import logging
import os
import shlex
import shutil
import signal
import subprocess
import sys
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Coroutine, Dict, List, Optional, Type, Union
from contextlib import AsyncExitStack

# --- Core Agent Imports ---
from agents import Agent, Runner
from agents.tool import FunctionToolResult, Tool, function_tool
from agents.result import RunResult
from agents.items import MessageOutputItem
from agents.mcp import MCPServerStdio, MCPServer
from agents.models.openai_responses import OpenAIResponsesModel
from agents import set_default_openai_api # Correct import

# --- Standard Library & Third-Party ---
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel

# --- Configuration & Constants ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[4]
except IndexError:
    logging.basicConfig(level=logging.WARNING)
    logging.warning("Could not determine project root. Defaulting to parent of CWD.")
    PROJECT_ROOT = Path.cwd().parent

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "swarm_config.json"
SWARM_VERSION = "0.2.8-finalfix"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True, show_path=False)],
)
logger = logging.getLogger("swarm"); logger.setLevel(logging.INFO)
for lib in ["httpx", "httpcore", "openai", "asyncio", "agents"]: logging.getLogger(lib).setLevel(logging.WARNING)

# --- Utility Functions ---
def _substitute_env_vars(value: Any) -> Any:
    """Recursively substitute environment variables in nested data structures."""
    if isinstance(value, str): return os.path.expandvars(value)
    elif isinstance(value, list): return [_substitute_env_vars(item) for item in value]
    elif isinstance(value, dict): return {k: _substitute_env_vars(v) for k, v in value.items()}
    else: return value

# --- Base Blueprint Class ---
class BlueprintBase(ABC):
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "AbstractBlueprintBase", "title": "Base Blueprint (Override Me)", "version": "0.0.0",
        "description": "Subclasses must provide a meaningful description.", "author": "Unknown",
        "tags": ["base"], "required_mcp_servers": [],
    }
    config: Dict[str, Any]; llm_profiles: Dict[str, Dict[str, Any]]; mcp_server_configs: Dict[str, Dict[str, Any]]
    console: Console; use_markdown: bool = False; max_llm_calls: Optional[int] = None

    def __init__(
        self, config_path_override: Optional[Union[str, Path]] = None, profile_override: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None, debug: bool = False,
    ):
        self.console = Console()
        if debug:
            logger.setLevel(logging.DEBUG); logging.getLogger("agents").setLevel(logging.DEBUG)
            logger.debug("[Init] Debug logging enabled.")
        try:
            set_default_openai_api("chat_completions")
            logger.debug("[Init] Set default OpenAI API to 'chat_completions'.")
        except Exception as e:
            logger.warning(f"[Init] Failed to set default OpenAI API: {e}")
        self._load_environment()
        try:
            self.config = self._load_configuration(config_path_override, profile_override, config_overrides)
        except (ValueError, FileNotFoundError) as e:
            logger.critical(f"[Config] Failed to load configuration: {e}", exc_info=debug)
            raise ValueError(f"Configuration loading failed: {e}") from e
        self.llm_profiles = self.config.get("llm", {})
        self.mcp_server_configs = self.config.get("mcpServers", {})
        self.use_markdown = self.config.get("use_markdown", False)
        self.max_llm_calls = self.config.get("max_llm_calls", None)
        logger.debug(f"[Init] Final Config Keys: {list(self.config.keys())}")
        logger.debug(f"[Init] LLM Profiles Loaded: {list(self.llm_profiles.keys())}")
        logger.debug(f"[Init] MCP Server Configs Loaded: {list(self.mcp_server_configs.keys())}")
        logger.debug(f"[Init] Use Markdown Output: {self.use_markdown}")
        logger.debug(f"[Init] Max LLM Calls (Informational): {self.max_llm_calls}")

    def _load_environment(self):
        """Loads environment variables from a `.env` file located at the project root."""
        dotenv_path = PROJECT_ROOT / ".env"
        logger.debug(f"[Config] Checking for .env file at: {dotenv_path}")
        try:
            if dotenv_path.is_file():
                loaded = load_dotenv(dotenv_path=dotenv_path, override=True)
                if loaded and logger.level <= logging.DEBUG:
                     logger.debug(f"[Config] .env file Loaded/Overridden at: {dotenv_path}")
                elif loaded:
                     logger.debug(f"[Config] .env file Loaded at: {dotenv_path}")
            else:
                logger.debug(f"[Config] No .env file found at {dotenv_path}.")
        except Exception as e:
            logger.error(f"[Config] Error loading .env file '{dotenv_path}': {e}", exc_info=logger.level <= logging.DEBUG)

    def _load_configuration(
        self, config_path_override: Optional[Union[str, Path]] = None, profile_override: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Loads and merges configuration settings."""
        config_path = Path(config_path_override) if config_path_override else DEFAULT_CONFIG_PATH
        logger.debug(f"[Config] Attempting to load base configuration from: {config_path}")
        base_config = {}
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f: base_config = json.load(f)
                logger.debug(f"[Config] Successfully loaded base configuration from: {config_path}")
            except json.JSONDecodeError as e: raise ValueError(f"Config Error: Failed to parse JSON in {config_path}: {e}") from e
            except Exception as e: raise ValueError(f"Config Error: Failed to read {config_path}: {e}") from e
        else:
            if config_path_override: raise FileNotFoundError(f"Configuration Error: Specified config file not found: {config_path}")
            else: logger.warning(f"[Config] Default configuration file not found at {config_path}. Proceeding without base configuration.")

        final_config = base_config.get("defaults", {}).copy(); logger.debug(f"[Config] Applied base defaults. Keys: {list(final_config.keys())}")
        if "llm" in base_config: final_config.setdefault("llm", {}).update(base_config["llm"]); logger.debug(f"[Config] Merged base 'llm'.")
        if "mcpServers" in base_config: final_config.setdefault("mcpServers", {}).update(base_config["mcpServers"]); logger.debug(f"[Config] Merged base 'mcpServers'.")
        blueprint_name = self.__class__.__name__; blueprint_settings = base_config.get("blueprints", {}).get(blueprint_name, {})
        if blueprint_settings: final_config.update(blueprint_settings); logger.debug(f"[Config] Merged BP '{blueprint_name}'. Keys: {list(final_config.keys())}")
        profile_in_bp_settings = blueprint_settings.get("default_profile"); profile_in_base_defaults = base_config.get("defaults", {}).get("default_profile")
        profile_to_use = profile_override or profile_in_bp_settings or profile_in_base_defaults or "default"; logger.debug(f"[Config] Using profile: '{profile_to_use}'")
        profile_settings = base_config.get("profiles", {}).get(profile_to_use, {})
        if profile_settings: final_config.update(profile_settings); logger.debug(f"[Config] Merged profile '{profile_to_use}'. Keys: {list(final_config.keys())}")
        elif profile_to_use != "default" and (profile_override or profile_in_bp_settings or profile_in_base_defaults): logger.warning(f"[Config] Profile '{profile_to_use}' requested but not found.")
        if config_overrides: final_config.update(config_overrides); logger.debug(f"[Config] Merged CLI overrides. Keys: {list(final_config.keys())}")
        final_config.setdefault("llm", {}); final_config.setdefault("mcpServers", {})
        final_config = _substitute_env_vars(final_config); logger.debug("[Config] Applied final env var substitution.")
        return final_config

    def get_llm_profile(self, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the fully resolved configuration dictionary for a given LLM profile name."""
        profile_to_check = profile_name or "default"
        profile_data = self.llm_profiles.get(profile_to_check)
        if profile_data:
            logger.debug(f"[LLM] Using resolved profile '{profile_to_check}'.")
            return profile_data
        elif profile_to_check != "default":
            logger.warning(f"LLM profile '{profile_name}' not found, falling back to 'default'.")
            profile_data = self.llm_profiles.get("default")
            if profile_data:
                logger.debug("[LLM] Using resolved profile 'default'.")
                return profile_data
        logger.error(f"LLM profile '{profile_to_check}' (and 'default' fallback) not found!")
        return None

    async def _start_mcp_server_instance(self, stack: AsyncExitStack, server_name: str) -> Optional[MCPServer]:
        """Starts a single MCP server instance."""
        server_config = self.mcp_server_configs.get(server_name)
        if not server_config: logger.error(f"[MCP:{server_name}] Config not found."); return None
        command_list_or_str = server_config.get("command");
        if not command_list_or_str: logger.error(f"[MCP:{server_name}] Command missing."); return None
        additional_args = _substitute_env_vars(server_config.get("args", []))
        if not isinstance(additional_args, list): logger.error(f"[MCP:{server_name}] Args must be list."); return None

        executable_name: str = ""; base_args: List[str] = []
        try:
            if isinstance(command_list_or_str, str):
                cmd_str_expanded = _substitute_env_vars(command_list_or_str); cmd_parts = shlex.split(cmd_str_expanded)
                if not cmd_parts: raise ValueError("Empty cmd string")
                executable_name = cmd_parts[0]; base_args = cmd_parts[1:]
            elif isinstance(command_list_or_str, list):
                cmd_parts = [_substitute_env_vars(p) for p in command_list_or_str];
                if not cmd_parts: raise ValueError("Empty cmd list")
                executable_name = cmd_parts[0]; base_args = cmd_parts[1:]
            else: raise TypeError(f"Cmd must be str/list");
            full_args = base_args + additional_args
        except Exception as e: logger.error(f"[MCP:{server_name}] Cmd/Arg Error: {e}", exc_info=logger.level<=logging.DEBUG); return None

        cmd_path = shutil.which(executable_name)
        if not cmd_path and sys.prefix != sys.base_prefix:
            for bindir in ['bin', 'Scripts']:
                venv_path = Path(sys.prefix) / bindir / executable_name;
                if venv_path.is_file(): cmd_path = str(venv_path); logger.debug(f"[MCP:{server_name}] Found in venv: {cmd_path}"); break
        if not cmd_path: logger.error(f"[MCP:{server_name}] Executable '{executable_name}' not found."); return None

        process_env = os.environ.copy()
        custom_env_config = server_config.get("env", {})
        if not isinstance(custom_env_config, dict): logger.error(f"[MCP:{server_name}] Config 'env' must be dict."); return None
        custom_env_substituted = _substitute_env_vars(custom_env_config)
        process_env.update(custom_env_substituted)
        logger.debug(f"[MCP:{server_name}] Custom Env Vars Merged: {list(custom_env_substituted.keys())}")

        cwd = _substitute_env_vars(server_config.get("cwd")); cwd_path: Optional[str] = None
        if cwd:
            try:
                cwd_path_obj = Path(cwd);
                if not cwd_path_obj.is_absolute(): cwd_path_obj = (PROJECT_ROOT / cwd_path_obj).resolve()
                else: cwd_path_obj = cwd_path_obj.resolve(strict=True)
                if cwd_path_obj.is_dir(): cwd_path = str(cwd_path_obj)
                else: logger.warning(f"[MCP:{server_name}] Invalid CWD: '{cwd_path_obj}' not directory.")
            except FileNotFoundError: logger.warning(f"[MCP:{server_name}] CWD '{cwd_path_obj}' not found.")
            except Exception as e: logger.warning(f"[MCP:{server_name}] Error resolving CWD '{cwd}': {e}.")

        mcp_params = {"command": cmd_path, "args": full_args, "env": process_env}
        if cwd_path: mcp_params["cwd"] = cwd_path
        if "encoding" in server_config: mcp_params["encoding"] = server_config["encoding"]
        if "encoding_error_handler" in server_config: mcp_params["encoding_error_handler"] = server_config["encoding_error_handler"]
        logger.debug(f"[MCP:{server_name}] Path:{cmd_path}, Args:{full_args}, CWD:{cwd_path or 'Default'}")
        # ** Log MCP start at INFO level **
        logger.info(f"[MCP:{server_name}] Starting: {' '.join(shlex.quote(p) for p in [cmd_path] + full_args)}")
        try:
            server_instance = MCPServerStdio(name=server_name, params=mcp_params); started_server = await stack.enter_async_context(server_instance);
            # ** Log successful start at INFO level **
            logger.info(f"[MCP:{server_name}] Started successfully."); return started_server
        except Exception as e: logger.error(f"[MCP:{server_name}] Failed start/connect: {e}", exc_info=logger.level <= logging.DEBUG); return None

    @abstractmethod
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Abstract method for subclasses to create the primary starting Agent."""
        pass

    # --- New Method for Splash Screen ---
    def display_splash_screen(self):
        """
        Optional method for blueprints to display an introductory message or graphic.
        Called at the start of the run. Base implementation does nothing.
        Use self.console for printing.
        """
        pass # Subclasses can override this

    async def _run_non_interactive(self, instruction: str):
        """Internal method orchestrating non-interactive blueprint execution."""
        # ** Call splash screen method **
        self.display_splash_screen()

        bp_title = self.metadata.get('title', self.__class__.__name__);
        # ** Log Run start at INFO **
        logger.info(f"--- Running Blueprint: {bp_title} (v{self.metadata.get('version', 'N/A')}) ---")
        truncated_instruction = textwrap.shorten(instruction, width=100, placeholder="...");
        # ** Log Instruction at INFO **
        logger.info(f"Instruction: '{truncated_instruction}'")

        required_servers = self.metadata.get("required_mcp_servers", []); started_mcps: List[MCPServer] = []; final_output = "Error: Blueprint exec failed."
        async with AsyncExitStack() as stack:
            if required_servers:
                # ** Log MCP start requirement at INFO **
                logger.info(f"[MCP] Required Servers: {required_servers}. Attempting to start...")
                results = await asyncio.gather(*(self._start_mcp_server_instance(stack, name) for name in required_servers)); started_mcps = [s for s in results if s]
                if len(started_mcps) != len(required_servers):
                    failed = set(required_servers) - {s.name for s in started_mcps}; error_msg=f"Fatal MCP Error: Failed: {', '.join(failed)}. Aborting."; logger.error(error_msg); final_output=f"Error: MCP server(s) failed: {', '.join(failed)}."; self.console.print(f"\n[bold red]--- Blueprint Failed ---[/]\n{final_output}\n[bold red]------------------------[/]"); return
                # ** Log successful MCP start at INFO **
                logger.info(f"[MCP] Successfully started required servers: {[s.name for s in started_mcps]}")
            else:
                 # ** Log no MCP needed at INFO **
                logger.info("[MCP] No MCP servers required for this blueprint.")
            try:
                logger.debug("Creating starting agent..."); agent = self.create_starting_agent(mcp_servers=started_mcps);
                if not isinstance(agent, Agent): raise TypeError(f"create_starting_agent must return Agent, got {type(agent).__name__}")
                logger.debug(f"Agent '{agent.name}' created.")
            except Exception as e: logger.critical(f"Agent creation error: {e}", exc_info=True); final_output=f"Error: Agent creation failed - {e}"; self.console.print(f"\n[bold red]--- Blueprint Failed ---[/]\n{final_output}\n[bold red]------------------------[/]"); return
            try:
                 # ** Log Runner start at INFO **
                logger.info(f"--- >>> Starting Agent Runner for '{agent.name}' <<< ---"); result: Optional[RunResult] = await Runner.run(starting_agent=agent, input=instruction);
                 # ** Log Runner finish at INFO **
                logger.info(f"--- <<< Agent Runner Finished for '{agent.name}' >>> ---")
                if result:
                    raw_out = result.final_output; logger.debug(f"Runner output type: {type(raw_out).__name__}")
                    if isinstance(raw_out, (dict, list)):
                        try: final_output = json.dumps(raw_out, indent=2, ensure_ascii=False)
                        except TypeError: logger.warning("Non-JSON serializable output."); final_output = str(raw_out)
                    elif raw_out is None: final_output = "[No output]"; logger.warning("Runner returned None output.")
                    else: final_output = str(raw_out)
                    if logger.level <= logging.DEBUG:
                        logger.debug("--- History ---")
                        if hasattr(result, 'history') and result.history:
                            for i, item in enumerate(result.history):
                                if isinstance(item, MessageOutputItem): logger.debug(f"  [{i:02d}][{item.message_type.upper()}] {item.sender_alias} -> {item.recipient_alias}: {textwrap.shorten(str(item.content), width=150)}")
                                elif isinstance(item, FunctionToolResult): logger.debug(f"  [{i:02d}][TOOL_RESULT] {item.function_name}: {textwrap.shorten(str(item.result), width=150)}")
                                else: logger.debug(f"  [{i:02d}][{type(item).__name__}] {item}")
                        elif hasattr(result, 'history'): logger.debug("  [History attribute exists but is empty or None]")
                        else: logger.debug("  [History attribute not found on RunResult object]")
                        logger.debug("--- End History ---")
                else: final_output = "[Runner returned None result]"; logger.warning("Runner returned None result object.")
            except Exception as e: logger.error(f"--- XXX Runner.run failed: {e}", exc_info=True); final_output = f"Error during execution: {e}"
        self.console.print(f"\n--- Final Output ({bp_title}) ---", style="bold blue")
        if self.use_markdown:
             logger.debug("Rendering output as Markdown.")
             try: md = Markdown(final_output); self.console.print(md)
             except Exception as md_err: logger.warning(f"Markdown render failed ({md_err}). Printing raw."); self.console.print(final_output)
        else: logger.debug("Printing output as plain text."); self.console.print(final_output)
        self.console.print("-----------------------------", style="bold blue")

    async def run_loop(self): logger.warning("Interactive loop not implemented."); self.console.print("[yellow]Interactive mode unavailable.[/yellow]")

    @classmethod
    def main(cls):
        """Class method entry point for command-line execution."""
        parser = argparse.ArgumentParser(description=cls.metadata.get("description", f"Run {cls.__name__}"), formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("--instruction", type=str, required=True, help="Initial instruction.")
        parser.add_argument("--config-path", type=str, default=None, help=f"Path to swarm_config.json (Default: {DEFAULT_CONFIG_PATH})")
        parser.add_argument("--config", type=str, metavar="JSON_FILE_OR_STRING", default=None, help="JSON config overrides (file path or string).")
        parser.add_argument("--profile", type=str, default=None, help="Config profile.")
        parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging.")
        parser.add_argument('--markdown', action=argparse.BooleanOptionalAction, default=None, help="Force markdown output.")
        parser.add_argument("--version", action="version", version=f"%(prog)s (BP: {cls.metadata.get('name', 'N/A')} v{cls.metadata.get('version', 'N/A')}, Core: {SWARM_VERSION})")
        args = parser.parse_args(); log_level = logging.DEBUG if args.debug else logging.INFO
        logger.setLevel(log_level);
        for lib in ["httpx", "httpcore", "openai", "asyncio", "agents"]: logging.getLogger(lib).setLevel(log_level if args.debug else logging.WARNING)
        # ** Log level setting now DEBUG **
        logger.debug(f"Log level set: {logging.getLevelName(log_level)}.")
        cli_config_overrides = {}
        if args.config:
            config_arg = args.config; config_override_path = Path(config_arg)
            if config_override_path.is_file():
                logger.info(f"Load overrides file: {config_override_path}");
                try:
                    with open(config_override_path, "r", encoding="utf-8") as f: cli_config_overrides = json.load(f); logger.debug(f"Loaded overrides keys: {list(cli_config_overrides.keys())}")
                except Exception as e: logger.error(f"Failed --config file: {e}", exc_info=args.debug); sys.exit(f"Error reading config override file: {e}")
            else:
                logger.info("Parse --config as JSON string.");
                try:
                    cli_config_overrides = json.loads(config_arg);
                    if not isinstance(cli_config_overrides, dict): raise TypeError("--config JSON string must be dict.")
                    logger.debug(f"--config JSON parsed. Keys: {list(cli_config_overrides.keys())}")
                except Exception as e: logger.error(f"Failed parsing --config JSON: {e}"); sys.exit(f"Error: Invalid --config value: {e}")
        try:
            blueprint = cls(config_path_override=args.config_path, profile_override=args.profile, config_overrides=cli_config_overrides, debug=args.debug)
            if args.markdown is not None: blueprint.use_markdown = args.markdown; logger.info(f"Markdown forced: {blueprint.use_markdown}.")
            if args.instruction: asyncio.run(blueprint._run_non_interactive(args.instruction))
            else: logger.critical("Internal Error: No instruction."); parser.print_help(); sys.exit(1)
        except (ValueError, TypeError, FileNotFoundError) as config_err: logger.critical(f"[Init Error] {config_err}", exc_info=args.debug); sys.exit(1)
        except ImportError as ie: logger.critical(f"[Import Error] {ie}. Check deps.", exc_info=args.debug); sys.exit(1)
        except Exception as e: logger.critical(f"[Exec Error] {e}", exc_info=True); sys.exit(1)
        finally: logger.debug("Blueprint run finished.")

