import logging
import os
import inspect
from typing import Dict, List, Any, AsyncGenerator, Optional, Type
from abc import ABC, abstractmethod
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import copy
# *** Import Django settings ***
from django.conf import settings

# *** REMOVE SwarmConfig import from apps.py ***
# from swarm.apps import SwarmConfig

# Import helpers from config_loader if needed directly
# from swarm.extensions.config.config_loader import find_config_file, DEFAULT_CONFIG_FILENAME

# *** LLMRegistry doesn't exist yet - Comment out import ***
# from swarm.llm.llm_registry import LLMRegistry # Example path - CHANGE ME!

logger = logging.getLogger(__name__)

class BlueprintBase(ABC):
    """
    Abstract base class for all blueprints.
    Ensures common interface and configuration handling.
    """
    metadata: Dict[str, Any] = {}

    @abstractmethod
    async def run(self, messages: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously runs the blueprint logic with the given messages.
        Must be implemented by subclasses.
        """
        if False: yield {}
        pass

    def __init__(
        self,
        # config_override: Optional[Dict] = None, # Override logic needs rethink
        params: Optional[Dict] = None,
    ):
        logger.debug(f"BlueprintBase.__init__ starting for {self.__class__.__name__}")
        self.params = params if params else {}
        # self._config_override = config_override # Store override for use in _configure
        # self._resolved_config_path = None # Initialize path tracker

        # Configuration loading needs rethink - access via settings for now
        self._configure() # This sets self.config attributes from settings

        # Now setup others that might depend on config
        self._setup_llm() # Uses self.config attributes
        self._setup_jinja() # Uses class path

        # Logging Adjustment
        # Check config *after* it has been loaded by _configure
        # Use self.is_debug which should be set in _configure
        if hasattr(self, 'is_debug') and self.is_debug:
             log_level_int = logging.DEBUG
             if logging.root.level > log_level_int:
                logger.info(f"Root logger level is {logging.getLevelName(logging.root.level)}. Lowering to DEBUG due to config.")
                logging.root.setLevel(log_level_int)

        # Ensure llm_profile_name is set by _setup_llm before logging it
        # Add check if llm_profile_name exists before logging
        profile_name_to_log = getattr(self, 'llm_profile_name', 'N/A')
        logger.info(f"Initialized blueprint '{self.metadata.get('name', self.__class__.__name__)}' with profile '{profile_name_to_log}'")

    def _configure(self):
        """Placeholder: Sets config attributes based on django.conf.settings."""
        logger.debug("BlueprintBase._configure accessing django.conf.settings")
        # *** Access settings directly (temporary) ***
        # This assumes swarm_config.json content is NOT yet loaded into settings
        # We'll rely on defaults or potentially fail in _setup_llm
        self.is_debug = getattr(settings, 'DEBUG', False)
        # Store blueprint-specific parts for convenience - these won't exist in settings yet!
        self.blueprint_config = {} # Placeholder
        self.blueprint_defaults = {} # Placeholder
        logger.warning("_configure is using placeholders. Swarm config file content is not loaded here.")


    def _setup_llm(self):
        """Sets up the LLM provider based on configuration stored in self.config."""
        # *** Access settings directly (temporary) ***
        # Get default profile name from settings if defined, else 'default'
        default_profile = getattr(settings, 'DEFAULT_LLM_PROFILE', 'default')
        self.llm_profile_name = self.blueprint_config.get('llm_profile', default_profile) # Use placeholder blueprint_config
        logger.debug(f"Getting LLM profile details for '{self.llm_profile_name}'.")

        # *** This part will likely fail or use defaults as swarm_config isn't in settings ***
        # Attempt to get profiles from settings if they were somehow loaded there
        all_llm_profiles = getattr(settings, 'LLM_PROFILES', {})
        profile_data = all_llm_profiles.get(self.llm_profile_name)

        if profile_data is None:
            logger.warning(f"LLM profile '{self.llm_profile_name}' not found in django settings. LLM will not be available.")
            self.llm_profile = {} # Set empty profile
            self.llm = None # Set LLM to None
            return # Exit setup early

        logger.debug(f"Using LLM profile '{self.llm_profile_name}' from settings.")
        self.llm_profile = profile_data
        # *** LLMRegistry doesn't exist yet - Comment out usage and set placeholder ***
        # self.llm = LLMRegistry.get_llm(self.llm_profile)
        self.llm = None # Placeholder until registry is implemented
        logger.warning("LLMRegistry not implemented. self.llm set to None.")


    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """Recursively substitutes environment variables in strings."""
        if isinstance(data, dict):
            return {k: BlueprintBase._substitute_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [BlueprintBase._substitute_env_vars(item) for item in data]
        if isinstance(data, str):
            return os.path.expandvars(data)
        return data

    def _setup_jinja(self):
        """Sets up Jinja2 environment."""
        try:
            blueprint_file_path = inspect.getfile(self.__class__)
            blueprint_dir = os.path.dirname(blueprint_file_path)
            template_dir = os.path.join(blueprint_dir, 'templates')
            if os.path.isdir(template_dir):
                 logger.debug(f"Setting up Jinja env with loader at: {template_dir}")
                 self.jinja_env = Environment(
                     loader=FileSystemLoader(template_dir),
                     autoescape=select_autoescape(['html', 'xml'])
                 )
            else:
                 logger.debug(f"No 'templates' directory found for blueprint at {template_dir}. Jinja env not created.")
                 self.jinja_env = None
        except Exception as e:
             logger.warning(f"Could not determine template path for {self.__class__.__name__}: {e}. Jinja env not created.")
             self.jinja_env = None

    def render_prompt(self, template_name: str, context: Dict = None) -> str:
        """Renders a Jinja2 template."""
        if not self.jinja_env:
             raise RuntimeError(f"Jinja environment not set up for blueprint {self.__class__.__name__}.")
        if context is None:
             context = {}
        try:
             template = self.jinja_env.get_template(template_name)
             full_context = {**self.params, **context}
             return template.render(full_context)
        except Exception as e:
             logger.error(f"Error rendering template '{template_name}': {e}", exc_info=True)
             raise

    def get_llm_profile(self) -> Dict:
         """Returns the configuration for the LLM profile being used."""
         if not hasattr(self, 'llm_profile'):
              logger.warning("LLM profile was not set during initialization, returning empty dict.")
              return {}
         return self.llm_profile

