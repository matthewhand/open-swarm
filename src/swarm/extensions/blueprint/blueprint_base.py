import argparse
import asyncio
import json
import logging
import os
import shlex
import shutil
import signal
import subprocess # Retained for potential non-MCP subprocess needs
import sys
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Coroutine, Dict, List, Optional, Type, Union
from contextlib import AsyncExitStack

# --- Core Agent Imports ---
from agents import Agent, Runner                   # Core classes
from agents.tool import FunctionToolResult, Tool, function_tool # Tool related
from agents.result import RunResult                 # Result class (was ConversationResult)
from agents.items import MessageOutputItem          # Message class (was Message)
from agents.mcp import MCPServerStdio, MCPServer    # MCP classes
# --- Optional / Utility Imports (Uncomment if needed later) ---
# from agents.function_schema import convert_pydantic_to_openai_tool_function # Function definition utils - COMMENTED OUT, location unknown/potentially unused
# from agents.llm import MODEL_PROVIDER_REGISTRY, FunctionMetadata, ModelArgs, ModelDefinition # LLM definitions - Keep if needed elsewhere

# --- Standard Library & Third-Party ---
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel

# --- Configuration & Constants ---
try:
    # Assumes blueprint_base.py is 4 levels down from the project root (src/swarm/extensions/blueprint/blueprint_base.py)
    PROJECT_ROOT = Path(__file__).resolve().parents[4]
except IndexError:
    # Basic logger setup for early error reporting if path calculation fails
    logging.basicConfig(level=logging.WARNING)
    logging.warning("Could not automatically determine project root based on file location. Defaulting to parent of current working directory.")
    PROJECT_ROOT = Path.cwd().parent # Fallback: Assume running from somewhere reasonable

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "swarm_config.json"
SWARM_VERSION = "0.2.8-finalfix" # Updated Version

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, # Default level, can be overridden by --debug flag
    format="%(message)s", # Keep format minimal, RichHandler takes care of timestamps etc.
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True, show_path=False)], # Use RichHandler for pretty logs
)
logger = logging.getLogger("swarm") # Primary logger for the application
logger.setLevel(logging.INFO) # Set default level for swarm logger

# Quieten overly verbose libraries during normal operation
# Set to DEBUG only when blueprint's --debug flag is active
for lib in ["httpx", "httpcore", "openai", "asyncio", "agents"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

# --- Utility Functions ---
def _substitute_env_vars(value: Any) -> Any:
    """
    Recursively substitute environment variables (${VAR} or $VAR) in strings
    within nested lists and dictionaries. Non-string values are returned as is.
    """
    if isinstance(value, str):
        # Use os.path.expandvars for ${VAR} and $VAR substitution
        return os.path.expandvars(value)
    elif isinstance(value, list):
        # Recursively apply to list items
        return [_substitute_env_vars(item) for item in value]
    elif isinstance(value, dict):
        # Recursively apply to dictionary values
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    else:
        # Return non-string/list/dict types unchanged
        return value

# --- Base Blueprint Class ---
class BlueprintBase(ABC):
    """
    Abstract base class for Swarm blueprints, integrating with the 'openai-agents' library.
    Handles configuration loading, MCP server management, logging, and execution flow.
    Subclasses must implement `create_starting_agent`.
    """
    # --- Class Variables ---
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "AbstractBlueprintBase", "title": "Base Blueprint (Override Me)", "version": "0.0.0",
        "description": "Subclasses must provide a meaningful description.", "author": "Unknown",
        "tags": ["base"], "required_mcp_servers": [],
    }

    # --- Instance Variables ---
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
        self._load_environment()
        try:
            self.config = self._load_configuration(config_path_override, profile_override, config_overrides)
        except (ValueError, FileNotFoundError) as e:
            logger.critical(f"[Config] Failed to load configuration: {e}", exc_info=debug)
            raise ValueError(f"Configuration loading failed: {e}") from e

        # Extract specific sections after full config is loaded and merged
        # Use .get() for safety, although _load_configuration ensures they exist
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
                logger.debug(f"[Config] .env file {'Loaded successfully' if loaded else 'Load attempted but may have failed'} at: {dotenv_path}")
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

        # --- Merging Logic ---
        # 1. Start with base defaults
        final_config = base_config.get("defaults", {}).copy()
        logger.debug(f"[Config] Applied base defaults. Current Keys: {list(final_config.keys())}")

        # 1.5 **NEW**: Explicitly merge top-level llm and mcpServers from base_config if they exist
        # This ensures they are present before blueprint/profile overrides modify them.
        if "llm" in base_config:
            final_config.setdefault("llm", {}).update(base_config["llm"])
            logger.debug(f"[Config] Merged top-level 'llm' from base config. LLM Keys: {list(final_config.get('llm', {}).keys())}")
        if "mcpServers" in base_config:
            final_config.setdefault("mcpServers", {}).update(base_config["mcpServers"])
            logger.debug(f"[Config] Merged top-level 'mcpServers' from base config. MCP Keys: {list(final_config.get('mcpServers', {}).keys())}")

        # 2. Merge blueprint-specific settings
        blueprint_name = self.__class__.__name__
        blueprint_settings = base_config.get("blueprints", {}).get(blueprint_name, {})
        if blueprint_settings:
            final_config.update(blueprint_settings) # Overwrites defaults and base llm/mcp if keys clash
            logger.debug(f"[Config] Merged settings for blueprint '{blueprint_name}'. Current Keys: {list(final_config.keys())}")

        # 3. Determine and merge profile settings
        profile_in_bp_settings = blueprint_settings.get("default_profile")
        profile_in_base_defaults = base_config.get("defaults", {}).get("default_profile")
        profile_to_use = profile_override or profile_in_bp_settings or profile_in_base_defaults or "default"
        logger.debug(f"[Config] Determined profile to use: '{profile_to_use}' (CLI:{profile_override}, BP:{profile_in_bp_settings}, Base:{profile_in_base_defaults})")

        profile_settings = base_config.get("profiles", {}).get(profile_to_use, {})
        if profile_settings:
            final_config.update(profile_settings) # Overwrites defaults, base llm/mcp, blueprint settings
            logger.debug(f"[Config] Merged settings from profile '{profile_to_use}'. Current Keys: {list(final_config.keys())}")
        elif profile_to_use != "default" and (profile_override or profile_in_bp_settings or profile_in_base_defaults):
            logger.warning(f"[Config] Profile '{profile_to_use}' was requested but not found.")

        # 4. Merge CLI overrides (highest precedence before env vars)
        if config_overrides:
            final_config.update(config_overrides)
            logger.debug(f"[Config] Merged CLI configuration overrides. Current Keys: {list(final_config.keys())}")

        # Ensure top-level keys exist (redundant now but safe)
        final_config.setdefault("llm", {})
        final_config.setdefault("mcpServers", {})

        # 5. Apply environment variable substitution
        final_config = _substitute_env_vars(final_config)
        logger.debug("[Config] Applied final environment variable substitution.")

        return final_config

    def _get_llm_profile_config(self, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the configuration for a specific LLM profile."""
        profile_to_check = profile_name or "default"
        profile_data = self.llm_profiles.get(profile_to_check)

        if profile_data:
            logger.debug(f"[LLM] Using LLM profile '{profile_to_check}'.")
            return profile_data
        elif profile_to_check != "default" and "default" in self.llm_profiles:
            logger.debug(f"[LLM] LLM profile '{profile_name}' not found, falling back to 'default' profile.")
            return self.llm_profiles["default"]
        else:
            logger.warning(f"[LLM] Could not find requested LLM profile '{profile_to_check}' and no 'default' profile is available.")
            return None

    async def _start_mcp_server_instance(self, stack: AsyncExitStack, server_name: str) -> Optional[MCPServer]:
        """Starts a single MCP server instance based on configuration using `MCPServerStdio`."""
        server_config = self.mcp_server_configs.get(server_name)
        if not server_config: logger.error(f"[MCP:{server_name}] Config not found."); return None
        command_list_or_str = server_config.get("command");
        if not command_list_or_str: logger.error(f"[MCP:{server_name}] Command missing."); return None
        additional_args = _substitute_env_vars(server_config.get("args", []))
        if not isinstance(additional_args, list): logger.error(f"[MCP:{server_name}] Args must be list."); return None
        try:
            if isinstance(command_list_or_str, str):
                cmd_str_expanded = _substitute_env_vars(command_list_or_str); cmd_parts = shlex.split(cmd_str_expanded)
                if not cmd_parts: raise ValueError("Empty cmd string"); executable_name = cmd_parts[0]; base_args = cmd_parts[1:]
            elif isinstance(command_list_or_str, list):
                cmd_parts = [_substitute_env_vars(p) for p in command_list_or_str];
                if not cmd_parts: raise ValueError("Empty cmd list"); executable_name = cmd_parts[0]; base_args = cmd_parts[1:]
            else: raise TypeError(f"Cmd must be str/list");
            full_args = base_args + additional_args
        except Exception as e: logger.error(f"[MCP:{server_name}] Cmd/Arg Error: {e}"); return None
        cmd_path = shutil.which(executable_name)
        if not cmd_path and sys.prefix != sys.base_prefix:
            for bindir in ['bin', 'Scripts']:
                venv_path = Path(sys.prefix) / bindir / executable_name;
                if venv_path.is_file(): cmd_path = str(venv_path); logger.debug(f"[MCP:{server_name}] Found in venv: {cmd_path}"); break
        if not cmd_path: logger.error(f"[MCP:{server_name}] Executable '{executable_name}' not found."); return None
        custom_env = _substitute_env_vars(server_config.get("env", {}));
        if not isinstance(custom_env, dict): logger.error(f"[MCP:{server_name}] Env must be dict."); return None
        cwd = _substitute_env_vars(server_config.get("cwd")); cwd_path: Optional[str] = None
        if cwd:
            try:
                cwd_path_obj = Path(cwd);
                if not cwd_path_obj.is_absolute(): cwd_path_obj = (PROJECT_ROOT / cwd_path_obj).resolve()
                else: cwd_path_obj = cwd_path_obj.resolve()
                if cwd_path_obj.is_dir(): cwd_path = str(cwd_path_obj)
                else: logger.warning(f"[MCP:{server_name}] Invalid CWD: {cwd}. Using default.")
            except Exception as e: logger.warning(f"[MCP:{server_name}] Error resolving CWD '{cwd}': {e}. Using default.")
        mcp_params = {"command": cmd_path, "args": full_args}
        if custom_env: mcp_params["env"] = custom_env
        if cwd_path: mcp_params["cwd"] = cwd_path
        if "encoding" in server_config: mcp_params["encoding"] = server_config["encoding"]
        if "encoding_error_handler" in server_config: mcp_params["encoding_error_handler"] = server_config["encoding_error_handler"]
        logger.debug(f"[MCP:{server_name}] Path:{cmd_path}, Args:{full_args}, CWD:{cwd_path or 'Default'}, EnvKeys:{list(custom_env.keys())}")
        logger.info(f"[MCP:{server_name}] Starting: {' '.join(shlex.quote(p) for p in [cmd_path] + full_args)}")
        try:
            server_instance = MCPServerStdio(name=server_name, params=mcp_params); started_server = await stack.enter_async_context(server_instance);
            logger.info(f"[MCP:{server_name}] Started successfully."); return started_server
        except Exception as e: logger.error(f"[MCP:{server_name}] Failed start/connect: {e}", exc_info=logger.level <= logging.DEBUG); return None

    @abstractmethod
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Abstract method for subclasses to create the primary starting Agent."""
        pass

    async def _run_non_interactive(self, instruction: str):
        """Internal method orchestrating non-interactive blueprint execution."""
        bp_title = self.metadata.get('title', self.__class__.__name__); logger.info(f"--- Run: {bp_title} v{self.metadata.get('version', 'N/A')}---")
        truncated_instruction = textwrap.shorten(instruction, width=100, placeholder="..."); logger.info(f"Instruction: '{truncated_instruction}'")
        required_servers = self.metadata.get("required_mcp_servers", []); started_mcps: List[MCPServer] = []; final_output = "Error: Blueprint exec failed."
        async with AsyncExitStack() as stack:
            if required_servers:
                logger.info(f"[MCP] Required: {required_servers}. Starting..."); results = await asyncio.gather(*(self._start_mcp_server_instance(stack, name) for name in required_servers)); started_mcps = [s for s in results if s]
                if len(started_mcps) != len(required_servers):
                    failed = set(required_servers) - {s.name for s in started_mcps}; error_msg=f"Fatal MCP Error: Failed: {', '.join(failed)}. Aborting."; logger.error(error_msg); final_output=f"Error: MCP server(s) failed: {', '.join(failed)}."; self.console.print(f"\n[bold red]--- Failed ---[/]\n{final_output}\n[bold red]------------- [/]"); return
                logger.info(f"[MCP] Started: {[s.name for s in started_mcps]}")
            else: logger.info("[MCP] No servers required.")
            try:
                logger.debug("Creating starting agent..."); agent = self.create_starting_agent(mcp_servers=started_mcps);
                if not isinstance(agent, Agent): raise TypeError(f"create_starting_agent must return Agent, got {type(agent).__name__}")
                logger.debug(f"Agent '{agent.name}' created.")
            except Exception as e: logger.critical(f"Agent creation error: {e}", exc_info=True); final_output=f"Error: Agent creation failed - {e}"; self.console.print(f"\n[bold red]--- Failed ---[/]\n{final_output}\n[bold red]------------- [/]"); return
            try:
                logger.info(f"--- >>> Runner.run ({agent.name}) ---"); result: Optional[RunResult] = await Runner.run(starting_agent=agent, input=instruction); logger.info(f"--- <<< Runner.run Finished ({agent.name}) ---")
                if result:
                    raw_out = result.final_output; logger.debug(f"Runner output type: {type(raw_out).__name__}")
                    if isinstance(raw_out, (dict, list)):
                        try: final_output = json.dumps(raw_out, indent=2, ensure_ascii=False)
                        except TypeError: logger.warning("Non-JSON serializable output."); final_output = str(raw_out)
                    elif raw_out is None: final_output = "[No output]"; logger.warning("Runner returned None output.")
                    else: final_output = str(raw_out)
                    if logger.level <= logging.DEBUG:
                        logger.debug("--- History ---")
                        if result.history:
                            for i, item in enumerate(result.history):
                                if isinstance(item, MessageOutputItem): logger.debug(f"  [{i:02d}][{item.message_type.upper()}] {item.sender_alias} -> {item.recipient_alias}: {textwrap.shorten(str(item.content), width=150)}")
                                elif isinstance(item, FunctionToolResult): logger.debug(f"  [{i:02d}][TOOL_RESULT] {item.function_name}: {textwrap.shorten(str(item.result), width=150)}")
                                else: logger.debug(f"  [{i:02d}][{type(item).__name__}] {item}")
                        else: logger.debug("  [Empty]")
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
        logger.info(f"Log level set: {logging.getLevelName(log_level)}.")
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
        except Exception as e: logger.critical(f"[Exec Error] {e}", exc_info=True); sys.exit(1) # Log full trace for unexpected
        finally: logger.debug("Blueprint run finished.")

