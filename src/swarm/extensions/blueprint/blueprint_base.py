import typer
import json
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type
from pathlib import Path
import logging
import time
import copy # <<< ADD THIS IMPORT <<<

# Use the config loader identified earlier
from swarm.extensions.config.config_loader import load_config, find_config_file, DEFAULT_CONFIG_FILENAME
# Assuming Agent class is needed for type hints, use the correct path
# from swarm.agent.agent import Agent # Avoid importing the local one if using library agents
from agents import Agent as LibraryAgent # Import the library Agent

# We don't need openai client here if blueprints/agents handle it
# from openai import AsyncOpenAI

# Import Runner for type hint in __init__
from agents import Runner as LibraryRunner

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config" # Example default

class BlueprintBase(ABC):
    """Abstract base class for Swarm blueprints."""

    # --- Abstract Properties/Methods ---
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def create_starting_agent(self, mcp_servers: Optional[list] = None) -> LibraryAgent:
        pass

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    # --- End Abstract ---

    def __init__(
        self,
        profile: Optional[str] = None,
        config_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        debug: bool = False,
        markdown: Optional[bool] = None,
    ):
        self.debug = debug
        self.log_level_int = logging.DEBUG if debug else logging.INFO
        self.log_level_str = logging.getLevelName(self.log_level_int)

        log_format = "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
        root_logger = logging.getLogger()
        if not root_logger.hasHandlers():
             logging.basicConfig(level=self.log_level_int, format=log_format)
             logger.info(f"Root logger configured by BlueprintBase. Level: {self.log_level_str}")
        else:
             current_level = root_logger.getEffectiveLevel()
             if current_level > self.log_level_int:
                  root_logger.setLevel(self.log_level_int)
                  logger.info(f"Root logger handlers exist. Lowered level from {logging.getLevelName(current_level)} to {self.log_level_str}.")
             else:
                  logger.info(f"Root logger handlers already exist. Level ({logging.getLevelName(current_level)}) not changed by request for {self.log_level_str}.")

        logger.debug(f"BlueprintBase.__init__ called for {self.__class__.__name__}")
        logger.debug(f"  - Profile override: {profile}")
        logger.debug(f"  - Config path override: {config_path}")
        logger.debug(f"  - Config dict override: {'Provided' if config_override else 'None'}")

        self.profile_name = profile or os.getenv("SWARM_PROFILE", "default")
        self.config_override = config_override # Store the original override dict if needed elsewhere
        self._resolved_config_path = None # Will be set if file loading occurs

        self.config = self._load_configuration(config_path) # Loads from override or file
        self.llm_profile = self._get_llm_profile() # Gets profile from self.config

        self._force_markdown = markdown
        self.markdown_output = self._determine_markdown_output() # Uses self.config

        # Instantiate the runner here, using the resolved profile
        try:
            # Check openai-agents docs for actual Runner init signature
            # It might implicitly use env vars or require explicit client/config
            self.runner = LibraryRunner() # Simplest assumption
            # Example if it needed profile details:
            # self.runner = LibraryRunner(default_model=self.llm_profile.get('model'))
            logger.debug(f"Initialized LibraryRunner instance: {self.runner}")
        except Exception as e:
             logger.error(f"Failed to initialize LibraryRunner: {e}", exc_info=True)
             raise RuntimeError(f"Could not initialize agent Runner: {e}")

        # Use self.name (abstract property) which MUST be defined by subclass
        logger.info(f"Initialized blueprint '{self.name}' with profile '{self.profile_name}'")
        log_config = json.loads(json.dumps(self.config, default=str))
        if 'llm' in log_config:
             for prof in log_config.get('llm', {}): log_config['llm'][prof].pop('api_key', None) # Redact
        logger.debug(f"Final effective self.config (redacted): {log_config}")


    def _load_configuration(self, config_path_str: Optional[str]) -> Dict[str, Any]:
        """Loads config from override dict or finds and loads from file."""
        if self.config_override is not None:
            logger.info("Using configuration override provided during instantiation.")
            # IMPORTANT: Work on a deep copy to prevent modifying the original override dict
            cfg = copy.deepcopy(self.config_override)
            # Ensure standard top-level keys exist
            cfg.setdefault("llm", {})
            cfg.setdefault("agents", {})
            cfg.setdefault("settings", {})
            return cfg

        # --- File loading logic (only if config_override is None) ---
        if config_path_str:
            resolved_path = Path(config_path_str).resolve()
            logger.debug(f"Config path provided: {resolved_path}")
        else:
            logger.debug("No config path provided, searching for default config file.")
            # Use find_config_file to search systematically
            start_dir = Path.cwd()
            # Define potential default locations if needed, e.g., package resources
            # For now, assuming find_config_file searches cwd up to root and maybe a default dir
            resolved_path = find_config_file(filename=DEFAULT_CONFIG_FILENAME, start_dir=start_dir)
            if resolved_path:
                logger.debug(f"Found default config file at: {resolved_path}")
            else:
                # Explicitly handle case where default is not found
                logger.error(f"Default config '{DEFAULT_CONFIG_FILENAME}' not found starting from {start_dir}.")
                raise FileNotFoundError(f"Swarm config '{DEFAULT_CONFIG_FILENAME}' not found.")

        if not resolved_path.is_file():
             logger.error(f"Resolved config path is not a file: {resolved_path}")
             raise FileNotFoundError(f"Swarm config not found at '{resolved_path}'.")

        self._resolved_config_path = resolved_path # Store the path from which config was loaded
        logger.info(f"Loading configuration from file: {resolved_path}")
        try:
             loaded_cfg = load_config(resolved_path)
             # Ensure standard top-level keys exist after loading from file
             loaded_cfg.setdefault("llm", {})
             loaded_cfg.setdefault("agents", {})
             loaded_cfg.setdefault("settings", {})
             return loaded_cfg
        except Exception as e:
             logger.error(f"Failed loading config file {resolved_path}: {e}", exc_info=True)
             raise # Re-raise the exception

    def _get_llm_profile(self) -> Dict[str, Any]:
        """Gets the specified LLM profile from the loaded self.config."""
        logger.debug(f"Getting LLM profile '{self.profile_name}'. Current self.config keys: {list(self.config.keys())}")
        if "llm" not in self.config or not isinstance(self.config.get("llm"), dict):
            # This case should ideally be prevented by _load_configuration ensuring 'llm' key exists
            logger.error("Config 'llm' section missing or malformed after load.")
            raise ValueError("Internal Error: Config 'llm' section missing/malformed.")

        profile_data = self.config["llm"].get(self.profile_name)
        if profile_data is None:
             logger.error(f"LLM profile '{self.profile_name}' not found in loaded configuration.")
             # Provide context about where config was loaded from if possible
             config_source = f"'{self._resolved_config_path}'" if self._resolved_config_path else "provided config_override"
             raise ValueError(f"LLM profile '{self.profile_name}' not found in configuration ({config_source}). Please define it.")
        if not isinstance(profile_data, dict):
             logger.error(f"LLM profile '{self.profile_name}' is not a dictionary.")
             raise ValueError(f"LLM profile '{self.profile_name}' is not a dictionary.")

        logger.debug(f"Using LLM profile '{self.profile_name}'.")
        # Substitute env vars *after* getting the profile data
        return BlueprintBase._substitute_env_vars(profile_data)

    # Make static as it doesn't depend on instance state
    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """Recursively substitutes ${VAR} or $VAR in strings within data."""
        if isinstance(data, dict):
            return {k: BlueprintBase._substitute_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [BlueprintBase._substitute_env_vars(item) for item in data]
        if isinstance(data, str):
            return os.path.expandvars(data)
        return data

    def _determine_markdown_output(self) -> bool:
        """Determines markdown setting based on override, config, or default."""
        if self._force_markdown is not None:
             logger.debug(f"Markdown output forced to: {self._force_markdown}")
             return self._force_markdown
        # Ensure 'settings' exists before accessing nested keys
        settings = self.config.get("settings", {}) # Defaults to {} if 'settings' is missing
        config_setting = settings.get("default_markdown_output", True) # Default to True if key missing
        logger.info(f"Using config/default markdown setting: {config_setting}")
        return bool(config_setting)

    def get_agent_configs(self) -> Optional[Dict[str, Any]]:
        """Returns agent configurations from the main config file."""
        # Ensure 'agents' key exists (should be handled by _load_configuration)
        agents_config = self.config.get("agents", {}) # Default to {}
        logger.debug(f"get_agent_configs called. Returning 'agents' section (type: {type(agents_config)}).")
        # Return None only if it was explicitly None? Or always return dict? Let's always return dict.
        return agents_config if isinstance(agents_config, dict) else {}


