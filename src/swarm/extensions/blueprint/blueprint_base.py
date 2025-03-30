import typer
import json
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type
from pathlib import Path
import logging # Import standard logging
import time

# Use the config loader identified earlier
from swarm.extensions.config.config_loader import load_config, find_config_file, DEFAULT_CONFIG_FILENAME
# Assuming Agent class is needed for type hints, use the correct path
from swarm.agent.agent import Agent
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config"

class BlueprintBase(ABC):
    """Abstract base class for Swarm blueprints."""
    name: str = "BaseBlueprint"

    def __init__(
        self,
        profile: Optional[str] = None,
        config_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None, # Added for logging
        debug: bool = False,
        markdown: Optional[bool] = None,
    ):
        self.debug = debug
        self.log_level_int = logging.DEBUG if debug else logging.INFO
        self.log_level_str = logging.getLevelName(self.log_level_int)

        log_format = "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
        if not logging.getLogger().hasHandlers():
             logging.basicConfig(level=self.log_level_int, format=log_format)
             logger.info(f"Root logger configured by BlueprintBase. Level: {self.log_level_str}")
        else:
             current_level = logging.getLogger().getEffectiveLevel()
             if current_level != self.log_level_int:
                  logging.getLogger().setLevel(self.log_level_int)
                  logger.info(f"Root logger handlers exist. Adjusted level from {logging.getLevelName(current_level)} to {self.log_level_str}.")
             else: logger.info(f"Root logger handlers already exist. Level set to: {self.log_level_str}.")

        # --- Log initial config ---
        logger.debug(f"BlueprintBase.__init__ called for {self.__class__.__name__}")
        logger.debug(f"  - Profile override: {profile}")
        logger.debug(f"  - Config path override: {config_path}")
        logger.debug(f"  - Config dict override: {'Provided' if config_override else 'None'}")
        # --- End Log initial config ---

        self.profile_name = profile or os.getenv("SWARM_PROFILE", "default")
        self.config_override = config_override # Store the override dict
        self._resolved_config_path = None

        self.config = self._load_configuration(config_path)
        self.llm_profile = self._get_llm_profile()

        self._force_markdown = markdown
        self.markdown_output = self._determine_markdown_output()

        logger.info(f"Initialized blueprint '{self.name}' with profile '{self.profile_name}'")
        # Log final effective config (redacted)
        log_config = json.loads(json.dumps(self.config, default=str))
        if 'llm' in log_config:
             for prof in log_config.get('llm', {}): log_config['llm'][prof].pop('api_key', None) # Redact
        logger.debug(f"Final effective self.config (redacted): {log_config}")


    def _load_configuration(self, config_path_str: Optional[str]) -> Dict[str, Any]:
        if self.config_override is not None: # Check explicitly if override was passed
            logger.info("Using configuration override provided during instantiation.")
            # Basic validation of override?
            if "llm" not in self.config_override: self.config_override["llm"] = {}
            if "agents" not in self.config_override: self.config_override["agents"] = {} # Ensure agents key exists
            return self.config_override

        start_dir = Path.cwd(); default_dir = DEFAULT_CONFIG_DIR
        resolved_path = find_config_file(config_path_str, start_dir, default_dir)
        if not resolved_path: raise FileNotFoundError(f"Swarm config not found (path='{config_path_str}'). Try creating swarm_config.json.")
        self._resolved_config_path = resolved_path
        logger.info(f"Loading configuration from: {resolved_path}")
        try: loaded_cfg = load_config(resolved_path); loaded_cfg.setdefault("agents", {}); return loaded_cfg # Ensure agents key
        except Exception as e: logger.error(f"Failed loading config {resolved_path}: {e}", exc_info=True); raise

    def _get_llm_profile(self) -> Dict[str, Any]:
        logger.debug(f"Getting LLM profile '{self.profile_name}'. Current self.config keys: {list(self.config.keys())}") # Debug config state
        if "llm" not in self.config or not isinstance(self.config.get("llm"), dict):
            raise ValueError("Config 'llm' section missing/malformed.")
        profile_data = self.config["llm"].get(self.profile_name)
        if profile_data is None:
             raise ValueError(f"LLM profile '{self.profile_name}' not found in configuration file '{self._resolved_config_path or 'Default Path'}'. Please define it.")
        if not isinstance(profile_data, dict): raise ValueError(f"LLM profile '{self.profile_name}' not dict.")
        logger.debug(f"Using LLM profile '{self.profile_name}'.")
        return self._substitute_env_vars(profile_data)

    def _substitute_env_vars(self, data: Any) -> Any:
        if isinstance(data, dict): return {k: self._substitute_env_vars(v) for k, v in data.items()}
        if isinstance(data, list): return [self._substitute_env_vars(item) for item in data]
        if isinstance(data, str): return os.path.expandvars(data)
        return data

    def _get_model_instance(self) -> Any:
        api_key = self.llm_profile.get("api_key"); base_url = self.llm_profile.get("base_url")
        provider = self.llm_profile.get("provider", "openai").lower()
        if provider == "openai" and not api_key:
             api_key = os.getenv("OPENAI_API_KEY")
             if not api_key: raise ValueError(f"API key missing for profile '{self.profile_name}' and OPENAI_API_KEY env var.")
             else: logger.warning(f"API key not in profile '{self.profile_name}', using OPENAI_API_KEY env var.")
        logger.debug(f"Creating LLM client provider='{provider}', profile='{self.profile_name}', base_url='{base_url or 'Default'}'")
        if provider == "openai": return AsyncOpenAI(api_key=api_key, base_url=base_url)
        else: raise NotImplementedError(f"LLM provider '{provider}' not implemented.")

    def _determine_markdown_output(self) -> bool:
        if self._force_markdown is not None: return self._force_markdown
        config_setting = self.config.get("settings", {}).get("default_markdown_output", True)
        logger.info(f"Using config/default markdown setting: {config_setting}")
        return bool(config_setting)

    def get_agent_configs(self) -> Optional[Dict[str, Any]]:
        """Returns agent configurations from the main config file."""
        # Debugging added here
        agents_config = self.config.get("agents")
        logger.debug(f"get_agent_configs called. Found 'agents' key in self.config: {agents_config is not None}. Type: {type(agents_config)}")
        return agents_config

    @abstractmethod
    def description(self) -> str: pass
    @abstractmethod
    def create_starting_agent(self, mcp_servers: Optional[list] = None) -> Agent: pass
    @abstractmethod
    async def run(self, instruction: str) -> str: pass

