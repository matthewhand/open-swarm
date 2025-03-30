
# --- Content for src/swarm/extensions/blueprint/blueprint_base.py ---
import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from pathlib import Path
from django.apps import apps # Import Django apps registry

# Keep the function import
from swarm.extensions.config.config_loader import get_profile_from_config

logger = logging.getLogger(__name__)

class BlueprintBase(ABC):
    """
    Abstract base class for all Swarm blueprints.

    Defines the core interface for blueprint initialization and execution.
    """
    def __init__(self, blueprint_id: str, config_path: Optional[Path] = None):
        """
        Initializes the blueprint.

        Args:
            blueprint_id: A unique identifier for this blueprint instance.
            config_path: Optional path to a specific swarm_config.json file.
                         If None, the standard search logic will be used.
        """
        if not blueprint_id:
             raise ValueError("blueprint_id cannot be empty or None") # Add validation
        self.blueprint_id = blueprint_id
        self.config_path = config_path # Note: config_path is currently unused if we rely on AppConfig
        self._config: Optional[Dict[str, Any]] = None
        self._llm_profile_name: Optional[str] = None
        self._llm_profile_data: Optional[Dict[str, Any]] = None
        self._markdown_output: bool = True # Default

        logger.info(f"Initializing blueprint '{self.blueprint_id}' (Type: {self.__class__.__name__})")
        self._load_and_process_config()

    def _load_and_process_config(self):
        """Loads the main Swarm config and extracts relevant settings."""
        try:
            # --- Get config from the AppConfig instance ---
            app_config_instance = apps.get_app_config('swarm')
            # Assuming the loaded config is stored in an attribute named 'config'
            # Adjust 'config' if your AppConfig uses a different attribute name
            if not hasattr(app_config_instance, 'config') or not app_config_instance.config:
                 logger.error("Swarm configuration not found on AppConfig instance. Was ready() called?")
                 raise ValueError("Swarm configuration unavailable via AppConfig.")
            self._config = app_config_instance.config
            # --- End change ---

            logger.debug(f"Blueprint '{self.blueprint_id}' using loaded Swarm config.")

            # Determine LLM profile
            self._llm_profile_name = self._config.get("settings", {}).get("default_llm_profile", "default")
            logger.debug(f"Attempting to use LLM profile: '{self._llm_profile_name}'")

            # Get substituted profile data
            self._llm_profile_data = get_profile_from_config(self._config, self._llm_profile_name)
            logger.info(f"Successfully loaded LLM profile '{self._llm_profile_name}'. Provider: {self._llm_profile_data.get('provider')}")

            # Get markdown setting
            blueprint_specific_settings = self._config.get("blueprints", {}).get(self.blueprint_id, {})
            global_markdown_setting = self._config.get("settings", {}).get("default_markdown_output", True)
            self._markdown_output = blueprint_specific_settings.get("markdown_output", global_markdown_setting)
            logger.debug(f"Markdown output for '{self.blueprint_id}': {self._markdown_output}")

        except ValueError as e:
            logger.error(f"Configuration error for blueprint '{self.blueprint_id}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading config for blueprint '{self.blueprint_id}': {e}", exc_info=True)
            raise

    @property
    def config(self) -> Dict[str, Any]:
        """Returns the loaded and processed Swarm configuration."""
        if self._config is None:
            raise RuntimeError("Configuration accessed before initialization or after failure.")
        return self._config

    @property
    def llm_profile(self) -> Dict[str, Any]:
        """Returns the loaded and processed LLM profile data for this blueprint."""
        if self._llm_profile_data is None:
            raise RuntimeError("LLM profile accessed before initialization or after failure.")
        return self._llm_profile_data

    @property
    def llm_profile_name(self) -> str:
        """Returns the name of the LLM profile being used."""
        if self._llm_profile_name is None:
             raise RuntimeError("LLM profile name accessed before initialization or after failure.")
        return self._llm_profile_name

    @property
    def should_output_markdown(self) -> bool:
        """Returns whether the blueprint should format output as Markdown."""
        return self._markdown_output

    @abstractmethod
    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        The main execution method for the blueprint.
        """
        raise NotImplementedError("Subclasses must implement the 'run' method.")
        yield {}

