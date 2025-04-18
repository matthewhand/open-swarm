# --- REMOVE noisy debug/framework prints unless SWARM_DEBUG=1 ---
import os

def _should_debug():
    return os.environ.get("SWARM_DEBUG") == "1"

def _debug_print(*args, **kwargs):
    if _should_debug():
        print(*args, **kwargs)

def _framework_print(*args, **kwargs):
    if _should_debug():
        print(*args, **kwargs)

# --- Content for src/swarm/extensions/blueprint/blueprint_base.py ---
import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from pathlib import Path
from django.apps import apps # Import Django apps registry

# Keep the function import
from swarm.core.config_loader import _substitute_env_vars

from openai import AsyncOpenAI
from agents import set_default_openai_client

logger = logging.getLogger(__name__)
from rich.console import Console
import traceback

# --- PATCH: Suppress OpenAI tracing/telemetry errors if using LiteLLM/custom endpoint ---
import logging
import os
if os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL"):
    # Silence openai.agents tracing/telemetry errors
    logging.getLogger("openai.agents").setLevel(logging.CRITICAL)
    try:
        import openai.agents.tracing
        openai.agents.tracing.TracingClient = lambda *a, **kw: None
    except Exception:
        pass

# --- Spinner/Status Message Enhancements ---
# To be used by all blueprints for consistent UX
import itertools
import sys
import threading
import time

class Spinner:
    def __init__(self, message_sequence=None, interval=0.3, slow_threshold=10):
        self.message_sequence = message_sequence or ['Generating.', 'Generating..', 'Generating...', 'Running...']
        self.interval = interval
        self.slow_threshold = slow_threshold  # seconds before 'Taking longer than expected'
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None

    def start(self):
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()

    def _spin(self):
        for msg in itertools.cycle(self.message_sequence):
            if self._stop_event.is_set():
                break
            elapsed = time.time() - self._start_time
            if elapsed > self.slow_threshold:
                sys.stdout.write('\rGenerating... Taking longer than expected   ')
            else:
                sys.stdout.write(f'\r{msg}   ')
            sys.stdout.flush()
            time.sleep(self.interval)
        sys.stdout.write('\r')
        sys.stdout.flush()

    def stop(self, final_message=''):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        if final_message:
            sys.stdout.write(f'\r{final_message}\n')
            sys.stdout.flush()

# Usage Example (to be called in blueprints):
# spinner = Spinner()
# spinner.start()
# ... do work ...
# spinner.stop('Done!')

def configure_openai_client_from_env():
    """
    Framework-level function: Always instantiate and set the default OpenAI client.
    Prints out the config being used for debug.
    """
    import os
    from agents import set_default_openai_client
    from openai import AsyncOpenAI
    base_url = os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    _debug_print(f"[DEBUG] Using OpenAI client config: base_url={base_url}, api_key={'set' if api_key else 'NOT SET'}")
    if base_url and api_key:
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        set_default_openai_client(client)
        _framework_print(f"[FRAMEWORK] Set default OpenAI client: base_url={base_url}, api_key={'set' if api_key else 'NOT SET'}")
    else:
        _framework_print("[FRAMEWORK] WARNING: base_url or api_key missing, OpenAI client not set!")

configure_openai_client_from_env()

class BlueprintBase(ABC):
    """
    Abstract base class for all Swarm blueprints.

    Defines the core interface for blueprint initialization and execution.
    """
    enable_terminal_commands: bool = False  # By default, terminal command execution is disabled

    @classmethod
    def main(cls):
        """
        Standard CLI entry point for all blueprints.
        Subclasses can override metadata/config_path if needed.
        """
        from swarm.extensions.blueprint.cli_handler import run_blueprint_cli
        from pathlib import Path
        swarm_version = getattr(cls, "SWARM_VERSION", "1.0.0")
        config_path = getattr(cls, "DEFAULT_CONFIG_PATH", Path(__file__).parent / "swarm_config.json")
        run_blueprint_cli(cls, swarm_version=swarm_version, default_config_path=config_path)

    def display_splash_screen(self, animated: bool = False):
        """Default splash screen. Subclasses can override for custom CLI/API branding."""
        console = Console()
        console.print(f"[bold cyan]Welcome to {self.__class__.__name__}![/]", style="bold")

    def __init__(self, blueprint_id: str, config: dict = None, config_path: 'Optional[Path]' = None, enable_terminal_commands: 'Optional[bool]' = None, **kwargs):
        try:
            if not blueprint_id:
                raise ValueError("blueprint_id cannot be empty or None")
            self.blueprint_id = blueprint_id
            self.config_path = config_path  # for legacy compatibility
            self._config = config  # Allow test injection
            self._llm_profile_name = None
            self._llm_profile_data = None
            self._markdown_output = None
            # Allow per-instance override
            if enable_terminal_commands is not None:
                self.enable_terminal_commands = enable_terminal_commands
            # Else: use class attribute (default False or set by subclass)

            logger.info(f"Initializing blueprint '{self.blueprint_id}' (Type: {self.__class__.__name__})")
            
            # --- Ensure custom OpenAI client for custom LLM providers ---
            import os

            # Remove monkey patching and envvar hacks. Always pass config values directly.
            # (Retain only explicit AsyncOpenAI client instantiation in blueprints)
            # (No changes needed here for direct client pattern)

            self._load_and_process_config()
        except AttributeError as e:
            logger.debug(f"[BlueprintBase.__init__] AttributeError: {e}")
            traceback.print_exc()
            raise

    def _load_and_process_config(self):
        """Loads the main Swarm config and extracts relevant settings. Falls back to empty config if Django unavailable or not found."""
        import os
        import json
        from pathlib import Path
        def redact(val):
            if not isinstance(val, str) or len(val) <= 4:
                return "****"
            return val[:2] + "*" * (len(val)-4) + val[-2:]
        def redact_dict(d):
            if isinstance(d, dict):
                return {k: (redact_dict(v) if not (isinstance(v, str) and ("key" in k.lower() or "token" in k.lower() or "secret" in k.lower())) else redact(v)) for k, v in d.items()}
            elif isinstance(d, list):
                return [redact_dict(item) for item in d]
            return d
        try:
            if self._config is None:
                try:
                    # --- Get config from the AppConfig instance (Django) ---
                    app_config_instance = apps.get_app_config('swarm')
                    if not hasattr(app_config_instance, 'config') or not app_config_instance.config:
                        raise ValueError("AppConfig for 'swarm' does not have a valid 'config' attribute.")
                    self._config = app_config_instance.config
                    logger.debug("Loaded config from Django AppConfig.")
                except Exception as e:
                    if _should_debug():
                        logger.warning(f"Falling back to CLI/home config due to error: {e}")
                    # 1. CLI argument (not handled here, handled in cli_handler)
                    # 2. Current working directory
                    cwd_config = Path.cwd() / "swarm_config.json"
                    if cwd_config.exists():
                        with open(cwd_config, 'r') as f:
                            self._config = json.load(f)
                    # 3. XDG_CONFIG_HOME or ~/.config/swarm/swarm_config.json
                    elif os.environ.get("XDG_CONFIG_HOME"):
                        xdg_config = Path(os.environ["XDG_CONFIG_HOME"]) / "swarm" / "swarm_config.json"
                        if xdg_config.exists():
                            with open(xdg_config, 'r') as f:
                                self._config = json.load(f)
                    elif (Path.home() / ".config/swarm/swarm_config.json").exists():
                        with open(Path.home() / ".config/swarm/swarm_config.json", 'r') as f:
                            self._config = json.load(f)
                    # 4. Legacy fallback: ~/.swarm/swarm_config.json
                    elif (Path.home() / ".swarm/swarm_config.json").exists():
                        with open(Path.home() / ".swarm/swarm_config.json", 'r') as f:
                            self._config = json.load(f)
                    # 5. Fallback: OPENAI_API_KEY envvar
                    elif os.environ.get("OPENAI_API_KEY"):
                        self._config = {
                            "llm": {"default": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]}},
                            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
                            "blueprints": {},
                            "llm_profile": "default",
                            "mcpServers": {}
                        }
                        logger.info("No config file found, using default config with OPENAI_API_KEY for CLI mode.")
                    else:
                        self._config = {}
                        logger.warning("No config file found and OPENAI_API_KEY is not set. Using empty config. CLI blueprints may fail if LLM config is required.")
                    if self._config is not None:
                        self._config = _substitute_env_vars(self._config)
            # Ensure self._config is always a dict
            if self._config is None:
                self._config = {}
            settings_section = self._config.get("settings", {})
            llm_section = self._config.get("llm", {})

            # --- After config is loaded, set OpenAI client from config if possible ---
            try:
                llm_profiles = self._config.get("llm", {})
                default_profile = llm_profiles.get("default", {})
                base_url = default_profile.get("base_url")
                api_key = default_profile.get("api_key")
                # Expand env vars if present
                import os
                if base_url and base_url.startswith("${"):
                    var = base_url[2:-1]
                    base_url = os.environ.get(var, base_url)
                if api_key and api_key.startswith("${"):
                    var = api_key[2:-1]
                    api_key = os.environ.get(var, api_key)
                if base_url and api_key:
                    from openai import AsyncOpenAI
                    from agents import set_default_openai_client
                    _debug_print(f"[DEBUG] (config) Setting OpenAI client: base_url={base_url}, api_key={'set' if api_key else 'NOT SET'}")
                    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
                    set_default_openai_client(client)
            except Exception as e:
                _debug_print(f"[DEBUG] Failed to set OpenAI client from config: {e}")

            # --- Debug: Print and log redacted config ---
            redacted_config = redact_dict(self._config)
            logger.debug(f"Loaded config (redacted): {json.dumps(redacted_config, indent=2)}")

            # --- Process LLM profile name and data ---
            default_profile = settings_section.get("default_llm_profile") or "default"
            self._llm_profile_name = self._config.get("llm_profile") or default_profile
            if "profiles" in llm_section:
                self._llm_profile_data = llm_section["profiles"].get(self._llm_profile_name, {})
            else:
                self._llm_profile_data = llm_section.get(self._llm_profile_name, {})

            blueprint_specific_settings = self._config.get("blueprints", {}).get(self.blueprint_id, {})
            global_markdown_setting = settings_section.get("default_markdown_output", True)
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
        """
        Returns the LLM profile dict for this blueprint.
        Raises a clear error if provider is missing.
        """
        llm_section = self._config.get("llm", {}) if self._config else {}
        profile_name = self.llm_profile_name or "default"
        profile = llm_section.get(profile_name)
        if not profile:
            raise ValueError(f"LLM profile '{profile_name}' not found in config: {llm_section}")
        if "provider" not in profile:
            raise ValueError(f"'provider' missing in LLM profile '{profile_name}': {profile}")
        return profile

    @property
    def llm_profile_name(self) -> str:
        """Returns the name of the LLM profile being used."""
        if self._llm_profile_name is None:
             raise RuntimeError("LLM profile name accessed before initialization or after failure.")
        return self._llm_profile_name

    @property
    def slash_commands(self):
        from swarm.core.slash_commands import slash_registry
        return slash_registry

    def get_llm_profile(self, profile_name: str) -> dict:
        """Returns the LLM profile dict for the given profile name from config, or empty dict if not found.
        Supports both llm.profiles and direct llm keys for backward compatibility."""
        llm_section = self.config.get("llm", {})
        if "profiles" in llm_section:
            return llm_section["profiles"].get(profile_name, {})
        return llm_section.get(profile_name, {})

    @property
    def should_output_markdown(self) -> bool:
        """
        Determines if markdown output should be used for this blueprint.
        Priority: blueprint config > global config > False
        """
        settings = self._config.get("settings", {}) if self._config else {}
        bp_settings = self._config.get("blueprints", {}).get(self.blueprint_id, {}) if self._config else {}
        if "output_markdown" in bp_settings:
            return bool(bp_settings["output_markdown"])
        if "default_markdown_output" in settings:
            return bool(settings["default_markdown_output"])
        return False

    def _get_model_instance(self, profile_name: str):
        """Retrieves or creates an LLM Model instance, respecting LITELLM_MODEL/DEFAULT_LLM if set."""
        if not hasattr(self, '_model_instance_cache'):
            self._model_instance_cache = {}
        if not hasattr(self, '_openai_client_cache'):
            self._openai_client_cache = {}
        if profile_name in self._model_instance_cache:
            return self._model_instance_cache[profile_name]
        profile_data = self.get_llm_profile(profile_name)
        import os
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or profile_data.get("model") or "gpt-3.5-turbo"
        openai_kwargs = {}
        if "base_url" in profile_data:
            openai_kwargs["base_url"] = profile_data["base_url"]
        if "api_key" in profile_data:
            openai_kwargs["api_key"] = profile_data["api_key"]
        from openai import AsyncOpenAI
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        client_cache_key = f"{model_name}:{openai_kwargs.get('base_url','')}:key={bool(openai_kwargs.get('api_key'))}"
        if client_cache_key not in self._openai_client_cache:
            try:
                self._openai_client_cache[client_cache_key] = AsyncOpenAI(**openai_kwargs)
            except Exception as e:
                raise ValueError(f"Failed to init client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e:
            raise ValueError(f"Failed to init LLM: {e}") from e

    def make_agent(self, name, instructions, tools, mcp_servers=None, **kwargs):
        """Factory for creating an Agent with the correct model instance from framework config."""
        from agents import Agent  # Ensure Agent is always in scope
        model_instance = self._get_model_instance(self.config.get("llm_profile", "default"))
        return Agent(
            name=name,
            model=model_instance,
            instructions=instructions,
            tools=tools,
            mcp_servers=mcp_servers or [],
            **kwargs
        )

    @abstractmethod
    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        The main execution method for the blueprint.
        """
        import os
        import pprint
        logger.debug("ENVIRONMENT DUMP BEFORE MODEL CALL:")
        pprint.pprint(dict(os.environ))
        raise NotImplementedError("Subclasses must implement the 'run' method.")
        yield {}
