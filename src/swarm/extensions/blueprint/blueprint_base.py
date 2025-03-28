import asyncio
import argparse
import logging
import sys
import os
import string
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator # Ensure Dict, Any are imported
from contextlib import AsyncExitStack
import shutil
import json
from dotenv import load_dotenv, find_dotenv

from agents import Agent, Runner, RunConfig, Tool, function_tool, set_default_openai_client, set_tracing_disabled, set_default_openai_api
from agents.mcp import MCPServerStdio

logger = logging.getLogger(__name__)

set_tracing_disabled(os.environ.get("DISABLE_AGENT_TRACING", "false").lower() == "true")
DEFAULT_OPENAI_API_TYPE = os.environ.get("OPENAI_API_TYPE", "chat_completions")
set_default_openai_api(DEFAULT_OPENAI_API_TYPE)

def load_swarm_config(config_path="swarm_config.json") -> Dict[str, Any]:
    config_data = {}
    try:
        if not os.path.isabs(config_path): full_config_path = os.path.join(os.getcwd(), config_path)
        else: full_config_path = config_path
        logger.debug(f"Attempting to load full config from: {full_config_path}")
        if os.path.exists(full_config_path):
            with open(full_config_path, 'r') as f:
                config_data = json.load(f); logger.info(f"Loaded config from {full_config_path}.")
        else: logger.warning(f"Config file not found: {full_config_path}.")
    except Exception as e: logger.error(f"Error loading config from {config_path}: {e}", exc_info=True)
    return config_data

def substitute_env_vars(value: Any) -> Any:
    if isinstance(value, str): template = string.Template(value); return template.safe_substitute(os.environ)
    elif isinstance(value, list): return [substitute_env_vars(item) for item in value]
    elif isinstance(value, dict): return {k: substitute_env_vars(v) for k, v in value.items()}
    else: return value

class BlueprintBase(ABC):
    DEFAULT_MAX_LLM_CALLS = 10; DEFAULT_MARKDOWN_CLI = True; DEFAULT_MARKDOWN_API = False

    def __init__(self, cli_args: argparse.Namespace, cli_config_override: Dict = {}):
        self.debug_mode = cli_args.debug; self.cli_args = cli_args
        self.swarm_config = load_swarm_config(cli_args.config_path)
        blueprint_configs = self.swarm_config.get("blueprints", {}); global_blueprint_defaults = blueprint_configs.get("defaults", {})
        blueprint_specific_config = blueprint_configs.get(self.__class__.__name__, {})
        self.config = global_blueprint_defaults.copy()
        self.config.update(blueprint_specific_config); self.config.update(cli_config_override)
        if cli_args.profile is not None: self.config["llm_profile"] = cli_args.profile
        self.max_llm_calls = int(self.config.get("max_llm_calls", self.DEFAULT_MAX_LLM_CALLS))
        bp_default_markdown = self.config.get("default_markdown_cli", self.DEFAULT_MARKDOWN_CLI)
        self.use_markdown = cli_args.markdown if cli_args.markdown is not None else bp_default_markdown
        self.llm_profiles = self.swarm_config.get("llm", {})
        self._ensure_default_profile()
        # Agents must be created AFTER profiles are loaded so they can potentially use them
        self.agents = self.create_agents()
        self.starting_agent_name = self._determine_starting_agent()
        logger.info(f"Blueprint '{self.metadata.get('title', 'Untitled')}' initialized.")
        if self.debug_mode: logger.debug(f"Agents: {list(self.agents.keys())}, Start: {self.starting_agent_name}; MD: {self.use_markdown}; Max Calls: {self.max_llm_calls}")
        if self.starting_agent_name not in self.agents: raise ValueError(f"Start agent '{self.starting_agent_name}' not found.")

    def _ensure_default_profile(self):
        if "default" not in self.llm_profiles:
             logger.warning("No 'default' LLM profile. Trying env vars.")
             api_key = os.environ.get("OPENAI_API_KEY")
             if api_key:
                  self.llm_profiles["default"] = { "provider": "openai", "model": os.environ.get("DEFAULT_MODEL", "gpt-4o"), "base_url": os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"), "api_key": api_key }; logger.info("Created 'default' profile from env vars.")
             else: logger.critical("Failed to get 'default' profile: Check OPENAI_API_KEY/config.")

    # --- CORRECT DECORATOR ORDER ---
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Provides metadata about the blueprint (title, description, version, etc.)."""
        pass

    @abstractmethod
    def create_agents(self) -> Dict[str, Agent]:
        """Creates and returns a dictionary of Agent instances for this blueprint."""
        pass
    # --- END FIX ---

    def _determine_starting_agent(self) -> str:
        names = list(self.agents.keys());
        if not names: raise ValueError("No agents created.");
        start_agent_name = names[0]; logger.info(f"Starting agent: '{start_agent_name}'.")
        return start_agent_name

    def get_llm_profile(self, profile_name: str = "default") -> Dict[str, Any]:
        profile = self.llm_profiles.get(profile_name, self.llm_profiles.get("default"))
        if not profile: raise ValueError(f"LLM profile '{profile_name}'/'default' not found.")
        profile = substitute_env_vars(profile.copy()) # Substitute env vars in the profile dict
        # Check key existence after substitution
        if not profile.get('api_key') and profile.get('provider') != 'ollama':
            key_var = profile.get('api_key_env_var', 'OPENAI_API_KEY');
            # Check actual env var as substitution might have removed the key if var wasn't set
            if not os.environ.get(key_var): logger.warning(f"API key env var '{key_var}' not set for profile '{profile_name}'.")
        return profile

    async def _start_required_mcp_servers(self, stack: AsyncExitStack, required_servers: List[str]) -> Dict[str, MCPServerStdio]:
        started_servers = {}
        if not required_servers: return started_servers
        logger.debug(f"Starting required MCP servers: {required_servers}")
        mcp_server_configs = self.swarm_config.get("mcpServers", {})
        for server_name in required_servers:
            server_config = mcp_server_configs.get(server_name)
            if not server_config: logger.warning(f"Config not found for MCP server: {server_name}. Skipping."); continue
            command = server_config.get("command")
            if not command: logger.warning(f"No 'command' specified for MCP server: {server_name}. Skipping."); continue
            # Substitute env vars in args and env dict *before* passing to MCPServerStdio
            args = substitute_env_vars(server_config.get("args", []))
            env_overrides = substitute_env_vars(server_config.get("env", {}))
            cmd_path = shutil.which(command)
            # Basic check in venv bin if not found in PATH
            if not cmd_path and not os.path.isabs(command) and sys.prefix != sys.base_prefix:
                 venv_cmd_path = os.path.join(sys.prefix, 'bin', command)
                 if os.path.exists(venv_cmd_path): cmd_path = venv_cmd_path
            if not cmd_path: logger.error(f"MCP command '{command}' not found in PATH or venv bin."); continue
            try:
                logger.debug(f"Attempting to start MCP '{server_name}': {cmd_path} {' '.join(args)}")
                # Prepare environment, combining current env with substituted overrides
                process_env = os.environ.copy(); process_env.update(env_overrides)
                server_instance = MCPServerStdio(name=server_name, params={"command": cmd_path, "args": args, "env": process_env})
                await stack.enter_async_context(server_instance)
                started_servers[server_name] = server_instance
                logger.debug(f"Started MCP server '{server_name}'.")
            except Exception as e: logger.error(f"Failed to start MCP '{server_name}': {e}", exc_info=self.debug_mode)
        if len(started_servers) != len(required_servers): logger.warning(f"Started {len(started_servers)}/{len(required_servers)} MCP servers.")
        else: logger.info(f"Successfully started MCP servers: {list(started_servers.keys())}")
        return started_servers

    async def _run_non_interactive(self, instruction: str):
        logger.debug(f"Run non-interactive: '{instruction[:50]}...'")
        logger.info(f"Markdown rendering: {self.use_markdown}; Max Calls: {self.max_llm_calls} (informational)")
        starting_agent = self.agents.get(self.starting_agent_name);
        if not starting_agent: logger.error(f"Start agent '{self.starting_agent_name}' missing."); return
        mcp_needed = self.metadata.get("required_mcp_servers", [])
        final_output = "Error: Agent failed."
        async with AsyncExitStack() as stack:
            started_mcps = await self._start_required_mcp_servers(stack, mcp_needed) if mcp_needed else {}
            if mcp_needed and len(started_mcps) < len(mcp_needed):
                 logger.error("Aborting: Not all required MCPs started."); final_output = "Error: MCP start failed."
                 print(f"\n--- Final Output ---\n{final_output}\n--------------------"); return
            if started_mcps: logger.debug(f"Assigning MCP servers ({list(started_mcps.keys())}) to agent '{starting_agent.name}'."); starting_agent.mcp_servers = list(started_mcps.values())

            try:
                profile_name_to_use = self.config.get("llm_profile", "default")
                agent_model = getattr(starting_agent, 'model', None)
                if not agent_model: # Agent relies on profile
                     profile = self.get_llm_profile(profile_name_to_use); model_name = profile.get('model')
                     if model_name: logger.debug(f"Agent '{starting_agent.name}' relying on profile '{profile_name_to_use}' model '{model_name}'.")
                     else: raise ValueError(f"Agent model missing & profile '{profile_name_to_use}' has no 'model'.")
                else: # Agent has model specified (could be profile name or direct model ID)
                     logger.debug(f"Agent '{starting_agent.name}' using model: '{agent_model}'")
                     # Ensure the profile corresponding to the agent's model is valid, if it's a profile name
                     if agent_model in self.llm_profiles: self.get_llm_profile(agent_model) # Validate profile exists

                logger.info(f"--- >>> Calling Runner.run ({starting_agent.name}) NOW...")
                try: result = await Runner.run(starting_agent=starting_agent, input=instruction) # Call without config=...
                except Exception as runner_ex: logger.error(f"--- XXX Runner.run FAILED: {runner_ex}", exc_info=self.debug_mode); raise
                logger.info(f"--- <<< Runner.run Finished ({starting_agent.name}) ---")
                if result:
                    final_output_raw = result.final_output
                    if isinstance(final_output_raw, (dict, list)): final_output = json.dumps(final_output_raw, indent=2)
                    elif final_output_raw is None: final_output = "No output."
                    else: final_output = str(final_output_raw)
                    logger.debug(f"Runner Result (output type: {type(final_output_raw)}): {result}")
                else: final_output = "No result."; logger.warning("Runner.run returned None.")
            except ValueError as ve: logger.error(f"Config/Run error: {ve}", exc_info=self.debug_mode); final_output = f"Error: {ve}"
            except Exception as e: logger.error(f"Outer run error: {e}", exc_info=self.debug_mode); final_output = f"Error: {e}"
        # TODO: Implement markdown rendering based on self.use_markdown
        print(f"\n--- Final Output ---\n{final_output}\n--------------------")

    async def run_loop(self): logger.warning("Interactive loop needs review."); print("Use --instruction.")

    @classmethod
    def main(cls):
        env_path = find_dotenv(usecwd=True); did_load = False
        if env_path: did_load = load_dotenv(dotenv_path=env_path, override=True)
        print(f"[INFO] Dotenv: {'Loaded ' + env_path if did_load else ('Not found' if not env_path else 'Found but failed?')}", file=sys.stderr)
        parser = argparse.ArgumentParser(description=f"Run {cls.__name__}.", add_help=False)
        parser.add_argument("--instruction", type=str, default=None, help="Run non-interactively.")
        parser.add_argument("--profile", type=str, default=None, help="LLM profile (overrides config).")
        parser.add_argument("--config-path", type=str, default="swarm_config.json", help="Primary config file path.")
        parser.add_argument("--config", type=str, default=None, help="JSON config overrides file.")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
        parser.add_argument('--markdown', action=argparse.BooleanOptionalAction, default=None, help="Enable/disable markdown output.")
        parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="Show this help message and exit.")
        args = parser.parse_args()
        log_level = logging.DEBUG if args.debug else logging.INFO
        logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)8s] %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', force=True)
        logging.getLogger().setLevel(log_level); logger.info(f"Logging level set to {logging.getLevelName(log_level)}")
        logger.info(f"Set default OpenAI API to '{DEFAULT_OPENAI_API_TYPE}'.")
        libs_to_quiet = ["httpx", "httpcore", "openai", "asyncio"]; [logging.getLogger(lib).setLevel(logging.WARNING) for lib in libs_to_quiet]
        cli_config_override = {}
        if args.config and os.path.exists(args.config):
             try:
                  with open(args.config, 'r') as f: cli_config_override = json.load(f); logger.info(f"Loaded overrides from {args.config}")
             except Exception as e: logger.error(f"Failed to load --config file {args.config}: {e}")
        try:
            blueprint = cls(cli_args=args, cli_config_override=cli_config_override)
            if args.instruction:
                print(f"--- {blueprint.metadata.get('title', 'Blueprint')} Non-Interactive ---")
                asyncio.run(blueprint._run_non_interactive(args.instruction))
            else: asyncio.run(blueprint.run_loop())
        except Exception as e:
            if not args.debug: logging.getLogger().setLevel(logging.ERROR)
            logger.error(f"Failed to run {cls.__name__}: {e}", exc_info=args.debug); sys.exit(1)

