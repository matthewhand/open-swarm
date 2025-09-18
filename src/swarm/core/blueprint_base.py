# --- REMOVE noisy debug/framework prints unless SWARM_DEBUG=1 ---
import os


def _should_debug():
    # Standardize debug detection: SWARM_DEBUG, SWARM_LOGLEVEL, LOGLEVEL, LOG_LEVEL, DEBUG
    import os
    # Highest precedence: explicit SWARM_DEBUG=1 or true
    debug_env = os.environ.get("SWARM_DEBUG")
    if debug_env is not None:
        return debug_env.lower() in ("1", "true", "yes", "on")
    # Next: SWARM_LOGLEVEL or LOGLEVEL or LOG_LEVEL
    for var in ("SWARM_LOGLEVEL", "LOGLEVEL", "LOG_LEVEL"):
        val = os.environ.get(var)
        if val and val.upper() == "DEBUG":
            return True
    # Next: DEBUG=1 or true
    debug_std = os.environ.get("DEBUG")
    if debug_std is not None:
        return debug_std.lower() in ("1", "true", "yes", "on")
    return False

def _debug_print(*args, **kwargs):
    if _should_debug():
        print(*args, **kwargs)

def _framework_print(*args, **kwargs):
    if _should_debug():
        print(*args, **kwargs)

# --- Content for src/swarm/extensions/blueprint/blueprint_base.py ---
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from agents import set_default_openai_client
from django.apps import apps  # Import Django apps registry
from openai import AsyncOpenAI

# Keep the function import
from swarm.core.config_loader import _substitute_env_vars

logger = logging.getLogger(__name__)
# --- PATCH: Suppress OpenAI tracing/telemetry errors if using LiteLLM/custom endpoint ---
import logging

from rich.console import Console

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
    approval_required: bool = False
    console = Console()
    session_logger = None

    def __init__(self, blueprint_id: str, config=None, config_path=None, **kwargs):
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._config = config if config is not None else None
        self._llm_profile_name = None
        self._llm_profile_data = None
        self._markdown_output = None
        self._load_configuration()  # Ensure config is loaded during init
        # Add any additional initialization logic here

    def display_splash_screen(self, animated: bool = False):
        """Default splash screen. Subclasses can override for custom CLI/API branding."""
        console = Console()
        console.print(f"[bold cyan]Welcome to {self.__class__.__name__}![/]", style="bold")

    def _load_configuration(self):
        """
        Loads blueprint configuration. This method is a stub for compatibility with tests that patch it.
        In production, configuration is loaded via _load_and_process_config.
        """
        import os
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
                    print("[SWARM_CONFIG_DEBUG] Loaded config from Django AppConfig.")
                except Exception as e:
                    if _should_debug():
                        logger.warning(f"Falling back to CLI/home config due to error: {e}")
                    # Check self.config_path
                    if self.config_path is not None:
                        config_path = Path(self.config_path)
                        if config_path.exists():
                            print(f"[SWARM_CONFIG_DEBUG] Loaded from self.config_path: {config_path}")
                            with open(config_path) as f:
                                self._config = json.load(f)
                        else:
                            logger.warning(f"Config path {config_path} does not exist.")
                            self._config = {}
                    # Check SWARM_CONFIG_PATH env var
                    if self._config is None:
                        swarm_config_path_env = os.environ.get("SWARM_CONFIG_PATH")
                        if swarm_config_path_env:
                            swarm_config_path = Path(swarm_config_path_env)
                            print(f"[SWARM_CONFIG_DEBUG] Trying SWARM_CONFIG_PATH: {swarm_config_path}")
                            if swarm_config_path.exists():
                                print(f"[SWARM_CONFIG_DEBUG] Loaded: {swarm_config_path}")
                                with open(swarm_config_path) as f:
                                    self._config = json.load(f)
                            else:
                                logger.warning(f"SWARM_CONFIG_PATH {swarm_config_path} does not exist.")
                                self._config = {}
                    if self._config is None:
                        # 1. CLI argument (not handled here, handled in cli_handler)
                        # 2. Current working directory (guard against missing CWD)
                        try:
                            cwd_config = Path.cwd() / "swarm_config.json"
                            print(f"[SWARM_CONFIG_DEBUG] Trying: {cwd_config}")
                        except Exception as e:
                            cwd_config = None
                            if _should_debug():
                                logger.warning(f"Unable to determine CWD for config lookup: {e}")
                        if cwd_config and cwd_config.exists():
                            print(f"[SWARM_CONFIG_DEBUG] Loaded: {cwd_config}")
                            with open(cwd_config) as f:
                                self._config = json.load(f)
                    # 3. XDG_CONFIG_HOME or ~/.config/swarm/swarm_config.json
                    elif os.environ.get("XDG_CONFIG_HOME"):
                        xdg_config = Path(os.environ["XDG_CONFIG_HOME"]) / "swarm" / "swarm_config.json"
                        print(f"[SWARM_CONFIG_DEBUG] Trying: {xdg_config}")
                        if xdg_config.exists():
                            print(f"[SWARM_CONFIG_DEBUG] Loaded: {xdg_config}")
                            with open(xdg_config) as f:
                                self._config = json.load(f)
                    elif (Path.home() / ".config/swarm/swarm_config.json").exists():
                        home_config = Path.home() / ".config/swarm/swarm_config.json"
                        print(f"[SWARM_CONFIG_DEBUG] Loaded: {home_config}")
                        with open(home_config) as f:
                            self._config = json.load(f)
                    # 4. Legacy fallback: ~/.swarm/swarm_config.json
                    elif (Path.home() / ".swarm/swarm_config.json").exists():
                        legacy_config = Path.home() / ".swarm/swarm_config.json"
                        print(f"[SWARM_CONFIG_DEBUG] Loaded: {legacy_config}")
                        with open(legacy_config) as f:
                            self._config = json.load(f)
                    # 5. Fallback: OPENAI_API_KEY envvar
                    elif os.environ.get("OPENAI_API_KEY"):
                        print("[SWARM_CONFIG_DEBUG] No config file found, using OPENAI_API_KEY from env.")
                        self._config = {
                            "llm": {"default": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]}},
                            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
                            "blueprints": {},
                            "llm_profile": "default",
                            "mcpServers": {}
                        }
                        logger.info("No config file found, using default config with OPENAI_API_KEY for CLI mode.")
                    else:
                        print("[SWARM_CONFIG_DEBUG] No config file found and OPENAI_API_KEY is not set. Using empty config.")
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
                    from agents import set_default_openai_client
                    from openai import AsyncOpenAI
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
            # Only set self._llm_profile_name if explicitly provided in config
            if "llm_profile" in self._config:
                self._llm_profile_name = self._config["llm_profile"]
            # Do NOT set self._llm_profile_name to default_profile here; let resolution logic handle fallback
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
            # Fallback to empty config on JSON parsing errors
            self._config = {}
        except Exception as e:
            logger.error(f"Unexpected error loading config for blueprint '{self.blueprint_id}': {e}", exc_info=True)
            # Fallback to empty config on unexpected errors
            self._config = {}

    def _load_and_process_config(self):
        """Loads the main Swarm config and extracts relevant settings. Falls back to empty config if Django unavailable or not found."""
        import os
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
                    print("[SWARM_CONFIG_DEBUG] Loaded config from Django AppConfig.")
                except Exception as e:
                    if _should_debug():
                        logger.warning(f"Falling back to CLI/home config due to error: {e}")
                    # Check SWARM_CONFIG_PATH env var
                    swarm_config_path_env = os.environ.get("SWARM_CONFIG_PATH")
                    if swarm_config_path_env:
                        swarm_config_path = Path(swarm_config_path_env)
                        print(f"[SWARM_CONFIG_DEBUG] Trying SWARM_CONFIG_PATH: {swarm_config_path}")
                        if swarm_config_path.exists():
                            print(f"[SWARM_CONFIG_DEBUG] Loaded: {swarm_config_path}")
                            with open(swarm_config_path) as f:
                                self._config = json.load(f)
                        else:
                            logger.warning(f"SWARM_CONFIG_PATH {swarm_config_path} does not exist.")
                            self._config = {}
                    if self._config is None:
                        # 1. CLI argument (not handled here, handled in cli_handler)
                        # 2. Current working directory (guard against missing CWD)
                        try:
                            cwd_config = Path.cwd() / "swarm_config.json"
                            print(f"[SWARM_CONFIG_DEBUG] Trying: {cwd_config}")
                        except Exception as e:
                            cwd_config = None
                            if _should_debug():
                                logger.warning(f"Unable to determine CWD for config lookup: {e}")
                        if cwd_config and cwd_config.exists():
                            print(f"[SWARM_CONFIG_DEBUG] Loaded: {cwd_config}")
                            with open(cwd_config) as f:
                                self._config = json.load(f)
                        # 3. XDG_CONFIG_HOME or ~/.config/swarm/swarm_config.json
                        elif os.environ.get("XDG_CONFIG_HOME"):
                            xdg_config = Path(os.environ["XDG_CONFIG_HOME"]) / "swarm" / "swarm_config.json"
                            print(f"[SWARM_CONFIG_DEBUG] Trying: {xdg_config}")
                            if xdg_config.exists():
                                print(f"[SWARM_CONFIG_DEBUG] Loaded: {xdg_config}")
                                with open(xdg_config) as f:
                                    self._config = json.load(f)
                        elif (Path.home() / ".config/swarm/swarm_config.json").exists():
                            home_config = Path.home() / ".config/swarm/swarm_config.json"
                            print(f"[SWARM_CONFIG_DEBUG] Loaded: {home_config}")
                            with open(home_config) as f:
                                self._config = json.load(f)
                        # 4. Legacy fallback: ~/.swarm/swarm_config.json
                        elif (Path.home() / ".swarm/swarm_config.json").exists():
                            legacy_config = Path.home() / ".swarm/swarm_config.json"
                            print(f"[SWARM_CONFIG_DEBUG] Loaded: {legacy_config}")
                            with open(legacy_config) as f:
                                self._config = json.load(f)
                        # 5. Fallback: OPENAI_API_KEY envvar
                        elif os.environ.get("OPENAI_API_KEY"):
                            print("[SWARM_CONFIG_DEBUG] No config file found, using OPENAI_API_KEY from env.")
                            self._config = {
                                "llm": {"default": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]}},
                                "settings": {"default_llm_profile": "default", "default_markdown_output": True},
                                "blueprints": {},
                                "llm_profile": "default",
                                "mcpServers": {}
                            }
                            logger.info("No config file found, using default config with OPENAI_API_KEY for CLI mode.")
                        else:
                            print("[SWARM_CONFIG_DEBUG] No config file found and OPENAI_API_KEY is not set. Using empty config.")
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
                    from agents import set_default_openai_client
                    from openai import AsyncOpenAI
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
            # Only set self._llm_profile_name if explicitly provided in config
            if "llm_profile" in self._config:
                self._llm_profile_name = self._config["llm_profile"]
            # Do NOT set self._llm_profile_name to default_profile here; let resolution logic handle fallback
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
            # Fallback to empty config on JSON parsing errors
            self._config = {}
        except Exception as e:
            logger.error(f"Unexpected error loading config for blueprint '{self.blueprint_id}': {e}", exc_info=True)
            # Fallback to empty config on unexpected errors
            self._config = {}

    def _resolve_llm_profile(self):
        """Resolve the LLM profile for this blueprint using the following order:
        1. If self._llm_profile_name is set, use it.
        2. If config has 'llm_profile', use it.
        3. If config['blueprints'][blueprint_id or stripped]['llm_profile'] is set, use it.
        4. If settings.default_llm in self._config, use it.
        5. If global swarm_config has blueprints.<BlueprintName>.llm_profile, use it.
        6. If settings.default_llm in global config, use it.
        7. If env var DEFAULT_LLM is set, use it.
        8. Otherwise, use 'default'.
        """
        # Use cached value if already resolved
        if getattr(self, '_resolved_llm_profile', None):
            return self._resolved_llm_profile
        name = getattr(self, 'blueprint_id', None) or getattr(self, '__class__', type(self)).__name__
        profile = None
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[DEBUG _resolve_llm_profile] blueprint_id/name: {name}")
        logger.debug(f"[DEBUG _resolve_llm_profile] self._config: {self._config}")
        # 1. Explicit override
        if getattr(self, '_llm_profile_name', None):
            logger.debug(f"[DEBUG _resolve_llm_profile] Using programmatic override: {self._llm_profile_name}")
            profile = self._llm_profile_name
        # 2. Blueprint config (top-level)
        elif self._config and self._config.get('llm_profile'):
            logger.debug(f"[DEBUG _resolve_llm_profile] Using top-level config llm_profile: {self._config['llm_profile']}")
            profile = self._config['llm_profile']
        # 3. Blueprint config (per-blueprint section)
        elif self._config and self._config.get('blueprints'):
            logger.debug(f"[DEBUG _resolve_llm_profile] Checking per-blueprint config for: {name}")
            bp_cfg = self._config['blueprints'].get(name) or self._config['blueprints'].get(name.replace('Blueprint',''))
            logger.debug(f"[DEBUG _resolve_llm_profile] bp_cfg: {bp_cfg}")
            if isinstance(bp_cfg, dict) and 'llm_profile' in bp_cfg:
                logger.debug(f"[DEBUG _resolve_llm_profile] Using per-blueprint llm_profile: {bp_cfg['llm_profile']}")
                profile = bp_cfg['llm_profile']
        # 4. settings.default_llm in self._config
        elif self._config and self._config.get('settings') and self._config['settings'].get('default_llm'):
            profile = self._config['settings']['default_llm']
        # 5. Global config lookup (blueprints.<BlueprintName>.llm_profile)
        else:
            global_config = None
            try:
                import json
                import os
                from pathlib import Path
                config_paths = [Path.cwd() / 'swarm_config.json', Path.home() / '.config/swarm/swarm_config.json']
                for path in config_paths:
                    if path.exists():
                        with open(path) as f:
                            global_config = json.load(f)
                        break
            except Exception:
                global_config = None
            if global_config and 'blueprints' in global_config:
                bp_cfg = global_config['blueprints'].get(name) or global_config['blueprints'].get(name.replace('Blueprint',''))
                if bp_cfg and 'llm_profile' in bp_cfg:
                    profile = bp_cfg['llm_profile']
            # 6. settings.default_llm in global config
            if not profile and global_config and 'settings' in global_config and global_config['settings'].get('default_llm'):
                profile = global_config['settings']['default_llm']
        # 7. Env var DEFAULT_LLM
        if not profile:
            import os
            profile = os.environ.get('DEFAULT_LLM')
        # 8. Otherwise, use 'default'
        if not profile:
            profile = 'default'
        logger.debug(f"[DEBUG _resolve_llm_profile] Final resolved profile: {profile}")
        self._resolved_llm_profile = profile
        return profile

    @property
    def config(self) -> dict[str, Any]:
        """Returns the loaded and processed Swarm configuration."""
        if self._config is None:
            raise RuntimeError("Configuration accessed before initialization or after failure.")
        return self._config

    @property
    def llm_profile(self) -> dict[str, Any]:
        """
        Returns the LLM profile dict for this blueprint.
        Raises a clear error if provider is missing.
        """
        llm_section = self._config.get("llm", {}) if self._config else {}
        profile_name = self._resolve_llm_profile()
        profile = llm_section.get(profile_name)
        if not profile:
            raise ValueError(f"LLM profile '{profile_name}' not found in config: {llm_section}")
        if "provider" not in profile:
            raise ValueError(f"'provider' missing in LLM profile '{profile_name}': {profile}")
        return profile

    @property
    def llm_profile_name(self) -> str:
        """Returns the name of the LLM profile being used."""
        return self._resolve_llm_profile()

    @llm_profile_name.setter
    def llm_profile_name(self, value: str):
        self._llm_profile_name = value
        if hasattr(self, '_resolved_llm_profile'):
            del self._resolved_llm_profile

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

    @property
    def splash(self) -> str:
        """
        Plain text splash/description for API, docs, etc.
        """
        title = self.metadata.get('title', 'Blueprint')
        desc = self.metadata.get('description', '')
        return f"{title}: {desc}"

    def get_cli_splash(self, color='cyan', emoji='🤖') -> str:
        """
        CLI splash with ANSI/emoji, only for terminal output.
        """
        from swarm.utils.ansi_box import ansi_box
        return ansi_box(self.splash, color=color, emoji=emoji)

    def _get_model_instance(self, profile_name: str):
        """Retrieves or creates an LLM Model instance, respecting LITELLM_MODEL/DEFAULT_LLM if set."""
        if not hasattr(self, '_model_instance_cache'):
            self._model_instance_cache = {}
        if not hasattr(self, '_openai_client_cache'):
            self._openai_client_cache = {}
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        import os
        # --- PATCH: API mode selection ---
        # Default to 'completions' mode unless 'responses' is explicitly specified in swarm_config.json for this blueprint
        api_mode = profile_data.get("api_mode") or self.config.get("api_mode") or "completions"
        # Allow env override for debugging if needed
        api_mode = os.getenv("SWARM_LLM_API_MODE", api_mode)
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or profile_data.get("model")
        provider = profile_data.get("provider", "openai")
        client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
        filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
        logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}' with {log_kwargs} and api_mode={api_mode}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}_{api_mode}"
        if client_cache_key not in self._openai_client_cache:
            from openai import AsyncOpenAI
            self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
        client = self._openai_client_cache[client_cache_key]
        # --- PATCH: Use correct model class based on api_mode ---
        if api_mode == "responses":
            from agents.models.openai_responses import OpenAIResponsesModel
            model_instance = OpenAIResponsesModel(model=model_name, openai_client=client)
        else:
            from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
        self._model_instance_cache[profile_name] = model_instance
        return model_instance

    def make_agent(self, name, instructions, tools, mcp_servers=None, **kwargs):
        """Factory for creating an Agent with the correct model instance from framework config."""
        from agents import Agent  # Ensure Agent is always in scope
        model_instance = self._get_model_instance(self._resolve_llm_profile())
        return Agent(
            name=name,
            model=model_instance,
            instructions=instructions,
            tools=tools,
            mcp_servers=mcp_servers or [],
            **kwargs
        )

    def request_approval(self, action_type, action_summary, action_details=None):
        """
        Prompt user for approval before executing an action.
        Returns True if approved, False if rejected, or edited action if supported.
        """
        try:
            from swarm.core.blueprint_ux import BlueprintUX
            ux = BlueprintUX(style="serious")
            box = ux.box(f"Approve {action_type}?", action_summary, summary="Details:", params=action_details)
            self.console.print(box)
        except Exception:
            print(f"Approve {action_type}?\n{action_summary}\nDetails: {action_details}")
        while True:
            resp = input("Approve this action? [y]es/[n]o/[e]dit/[s]kip: ").strip().lower()
            if resp in ("y", "yes"): return True
            if resp in ("n", "no"): return False
            if resp in ("s", "skip"): return False
            if resp in ("e", "edit"):
                if action_details:
                    print("Edit not yet implemented; skipping.")
                    return False
                else:
                    print("No editable content; skipping.")
                    return False

    def execute_tool_with_approval(self, tool_func, action_type, action_summary, action_details=None, *args, **kwargs):
        if getattr(self, 'approval_required', False):
            approved = self.request_approval(action_type, action_summary, action_details)
            if not approved:
                try:
                    self.console.print(f"[yellow]Skipped {action_type}[/yellow]")
                except Exception:
                    print(f"Skipped {action_type}")
                return None
        return tool_func(*args, **kwargs)

    def start_session_logger(self, blueprint_name: str, global_instructions: str = None, project_instructions: str = None):
        from swarm.core.session_logger import SessionLogger
        self.session_logger = SessionLogger(blueprint_name=blueprint_name)
        self.session_logger.log_instructions(global_instructions, project_instructions)

    def log_message(self, role: str, content: str):
        if self.session_logger:
            self.session_logger.log_message(role, content)

    def log_tool_call(self, tool_name: str, result: str):
        if self.session_logger:
            self.session_logger.log_tool_call(tool_name, result)

    def close_session_logger(self):
        if self.session_logger:
            self.session_logger.close()
            self.session_logger = None

    def print_help(self):
        """
        Print CLI usage/help for this blueprint. Subclasses can override for custom help.
        """
        blueprint_name = getattr(self, 'blueprint_id', self.__class__.__name__)
        print(f"\nUsage: {blueprint_name} [options] <prompt>\n")
        print("Options:")
        print("  -m, --model <model>         Model to use for completions")
        print("  -q, --quiet                 Non-interactive mode (only prints final output)")
        print("  -o, --output <file>         Output file")
        print("  --project-doc <file>        Include a markdown file as context")
        print("  --full-context              Load all project files as context")
        print("  --approval <policy>         Set approval policy for agent actions (suggest, auto-edit, full-auto)")
        print("  --version                   Show version and exit")
        print("  -h, --help                  Show this help message and exit\n")
        print("Examples:")
        print(f"  {blueprint_name} \"Refactor all utils into a single module.\"")
        print(f"  {blueprint_name} --full-context \"Analyze and fix all TODOs across the codebase.\"")
        print(f"  {blueprint_name} --approval full-auto \"Upgrade all dependencies, update changelog, and implement pending TODOs.\"")
        print(f"  {blueprint_name} --full-context --approval suggest \"Review all TODO comments and provide implementation suggestions.\"")
        print(f"  {blueprint_name} \"Generate documentation for functions with TODO comments.\"")

    @abstractmethod
    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        """
        The main execution method for the blueprint.
        """
        import os
        import pprint
        logger.debug("ENVIRONMENT DUMP BEFORE MODEL CALL:")
        pprint.pprint(dict(os.environ))
        raise NotImplementedError("Subclasses must implement the 'run' method.")
        yield {}

