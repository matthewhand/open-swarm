import typer
import json
import os
import asyncio
from abc import ABC, abstractmethod
# Import AsyncGenerator for type hint
from typing import Optional, List, Dict, Any, Type, AsyncGenerator
from pathlib import Path
import logging
import time
import copy

from swarm.extensions.config.config_loader import load_config, find_config_file, DEFAULT_CONFIG_FILENAME
from agents import Agent as LibraryAgent
from agents import Runner as LibraryRunner

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config" # Example default

class BlueprintBase(ABC):
    """Abstract base class for Swarm blueprints."""

    # --- Abstract Properties/Methods ---
    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    def description(self) -> str: pass

    @abstractmethod
    def create_starting_agent(self, mcp_servers: Optional[list] = None) -> LibraryAgent: pass

    # UPDATED: 'run' is now an async generator yielding dictionaries
    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the blueprint's core logic asynchronously, yielding response chunks.

        Args:
            input_data: Dictionary containing input, typically including 'messages'.

        Yields:
            Dictionaries representing response chunks (e.g., message deltas or full messages).
        """
        # Ensure the generator actually yields something for type checkers
        # This implementation detail should be in subclasses.
        # Example: yield {"done": True}
        # The actual implementation is just 'pass' in the ABC.
        # We need this dummy yield here only if Python<3.8/typing issues arise.
        # Modern Python handles this fine with just 'pass'. For safety:
        if False: # This code is never executed, but satisfies type checkers
             yield {}
        pass # Subclasses must implement this as an async generator


    # --- End Abstract ---

    def __init__(
        self,
        profile: Optional[str] = None,
        config_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        debug: bool = False,
        markdown: Optional[bool] = None,
    ):
        # ... (rest of __init__ remains largely the same) ...
        self.debug = debug
        self.log_level_int = logging.DEBUG if debug else logging.INFO
        self.log_level_str = logging.getLevelName(self.log_level_int)
        log_format = "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
        root_logger = logging.getLogger();
        if not root_logger.hasHandlers(): logging.basicConfig(level=self.log_level_int, format=log_format); logger.info(f"Root logger configured by BlueprintBase. Level: {self.log_level_str}")
        else:
             current_level = root_logger.getEffectiveLevel()
             if current_level > self.log_level_int: root_logger.setLevel(self.log_level_int); logger.info(f"Root logger handlers exist. Lowered level from {logging.getLevelName(current_level)} to {self.log_level_str}.")
             else: logger.info(f"Root logger handlers already exist. Level ({logging.getLevelName(current_level)}) not changed by request for {self.log_level_str}.")
        logger.debug(f"BlueprintBase.__init__ called for {self.__class__.__name__}")
        self.profile_name = profile or os.getenv("SWARM_PROFILE", "default")
        self.config_override = config_override
        self._resolved_config_path = None
        self.config = self._load_configuration(config_path)
        self.llm_profile = self._get_llm_profile()
        self._force_markdown = markdown
        self.markdown_output = self._determine_markdown_output()
        try: self.runner = LibraryRunner(); logger.debug(f"Initialized LibraryRunner instance: {self.runner}") # Simplistic runner init
        except Exception as e: logger.error(f"Failed to initialize LibraryRunner: {e}", exc_info=True); raise RuntimeError(f"Could not initialize agent Runner: {e}")
        logger.info(f"Initialized blueprint '{self.name}' with profile '{self.profile_name}'")


    def _load_configuration(self, config_path_str: Optional[str]) -> Dict[str, Any]:
        if self.config_override is not None:
            logger.info("Using configuration override provided during instantiation.")
            cfg = copy.deepcopy(self.config_override); cfg.setdefault("llm", {}); cfg.setdefault("agents", {}); cfg.setdefault("settings", {}); return cfg
        logger.debug("No config override, searching for config file.")
        resolved_path = find_config_file(None, start_dir=Path.cwd().parent) # Search from project root potentially
        if not resolved_path: logger.error(f"Default config '{DEFAULT_CONFIG_FILENAME}' not found."); raise FileNotFoundError(f"Swarm config '{DEFAULT_CONFIG_FILENAME}' not found.")
        if not resolved_path.is_file(): logger.error(f"Resolved config path is not a file: {resolved_path}"); raise FileNotFoundError(f"Swarm config not found at '{resolved_path}'.")
        self._resolved_config_path = resolved_path; logger.info(f"Loading configuration from file: {resolved_path}")
        try: loaded_cfg = load_config(resolved_path); loaded_cfg.setdefault("llm", {}); loaded_cfg.setdefault("agents", {}); loaded_cfg.setdefault("settings", {}); return loaded_cfg
        except Exception as e: logger.error(f"Failed loading config file {resolved_path}: {e}", exc_info=True); raise

    def _get_llm_profile(self) -> Dict[str, Any]:
        logger.debug(f"Getting LLM profile '{self.profile_name}'.")
        if "llm" not in self.config or not isinstance(self.config.get("llm"), dict): raise ValueError("Internal Error: Config 'llm' section missing/malformed.")
        profile_data = self.config["llm"].get(self.profile_name)
        if profile_data is None: config_source = f"'{self._resolved_config_path}'" if self._resolved_config_path else "provided config_override"; raise ValueError(f"LLM profile '{self.profile_name}' not found in configuration ({config_source}). Please define it.")
        if not isinstance(profile_data, dict): raise ValueError(f"LLM profile '{self.profile_name}' is not a dictionary.")
        logger.debug(f"Using LLM profile '{self.profile_name}'.")
        return BlueprintBase._substitute_env_vars(profile_data)

    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        if isinstance(data, dict): return {k: BlueprintBase._substitute_env_vars(v) for k, v in data.items()}
        if isinstance(data, list): return [BlueprintBase._substitute_env_vars(item) for item in data]
        if isinstance(data, str): return os.path.expandvars(data)
        return data

    def _determine_markdown_output(self) -> bool:
        if self._force_markdown is not None: logger.debug(f"Markdown output forced to: {self._force_markdown}"); return self._force_markdown
        settings = self.config.get("settings", {}); config_setting = settings.get("default_markdown_output", True); logger.info(f"Using config/default markdown setting: {config_setting}")
        return bool(config_setting)

    def get_agent_configs(self) -> Dict[str, Any]: # Return dict consistently
        agents_config = self.config.get("agents", {}); logger.debug(f"get_agent_configs called. Returning 'agents' section (type: {type(agents_config)}).")
        return agents_config if isinstance(agents_config, dict) else {}

