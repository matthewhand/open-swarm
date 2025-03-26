"""
Configuration Loader for Open Swarm MCP Framework.
"""

import os
import json
import re
import logging
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv
# Import save_server_config carefully
try: from .server_config import save_server_config
except ImportError: save_server_config = None
from swarm.settings import DEBUG, BASE_DIR
from swarm.utils.redact import redact_sensitive_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

config: Dict[str, Any] = {}
load_dotenv()
logger.debug("Environment variables potentially loaded from .env file.")

def process_config(config_dict: dict) -> dict:
    """Processes config: resolves placeholders, merges external MCP."""
    try:
        resolved_config = resolve_placeholders(config_dict)
        if logger.isEnabledFor(logging.DEBUG): logger.debug("Config after resolving placeholders: " + json.dumps(redact_sensitive_data(resolved_config), indent=2))

        disable_merge = os.getenv("DISABLE_MCP_MERGE", "false").lower() in ("true", "1", "yes")
        if not disable_merge:
            if os.name == "nt": external_mcp_path = Path(os.getenv("APPDATA", Path.home())) / "Claude" / "claude_desktop_config.json"
            else: external_mcp_path = Path.home() / ".vscode-server" / "data" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json"

            if external_mcp_path.exists():
                logger.info(f"Found external MCP settings file at: {external_mcp_path}")
                try:
                    with open(external_mcp_path, "r") as mcp_file: external_mcp_config = json.load(mcp_file)
                    if logger.isEnabledFor(logging.DEBUG): logger.debug("Loaded external MCP settings: " + json.dumps(redact_sensitive_data(external_mcp_config), indent=2))

                    main_mcp_servers = resolved_config.get("mcpServers", {})
                    external_mcp_servers = external_mcp_config.get("mcpServers", {})
                    merged_mcp_servers = main_mcp_servers.copy()
                    servers_added_count = 0
                    for server_name, server_config in external_mcp_servers.items():
                        if server_name not in merged_mcp_servers and not server_config.get("disabled", False):
                            merged_mcp_servers[server_name] = server_config
                            servers_added_count += 1
                    if servers_added_count > 0:
                         resolved_config["mcpServers"] = merged_mcp_servers
                         logger.info(f"Merged {servers_added_count} MCP servers from external settings.")
                         if logger.isEnabledFor(logging.DEBUG): logger.debug("Merged MCP servers config: " + json.dumps(redact_sensitive_data(merged_mcp_servers), indent=2))
                    else: logger.debug("No new MCP servers added from external settings.")
                except Exception as merge_err: logger.error(f"Failed to load/merge MCP settings from '{external_mcp_path}': {merge_err}", exc_info=logger.isEnabledFor(logging.DEBUG))
            else: logger.debug(f"External MCP settings file not found at {external_mcp_path}. Skipping merge.")
        else: logger.debug("MCP settings merge disabled via DISABLE_MCP_MERGE env var.")
    except Exception as e: logger.error(f"Failed during configuration processing: {e}", exc_info=logger.isEnabledFor(logging.DEBUG)); raise
    globals()["config"] = resolved_config
    return resolved_config

def resolve_placeholders(obj: Any) -> Any:
    """Recursively resolve ${VAR_NAME} placeholders. Returns None if var not found."""
    if isinstance(obj, dict): return {k: resolve_placeholders(v) for k, v in obj.items()}
    elif isinstance(obj, list): return [resolve_placeholders(item) for item in obj]
    elif isinstance(obj, str):
        pattern = re.compile(r'\$\{(\w+)\}')
        resolved_string = obj
        placeholders_found = pattern.findall(obj)
        all_resolved = True # Flag to track if all placeholders in string were resolved
        for var_name in placeholders_found:
            env_value = os.getenv(var_name)
            placeholder = f'${{{var_name}}}'
            if env_value is None:
                logger.warning(f"Env var '{var_name}' not set for placeholder '{placeholder}'. Placeholder will resolve to None.")
                # If only a placeholder exists, return None directly
                if resolved_string == placeholder:
                     return None
                # If placeholder is part of larger string, replace with empty string or marker?
                # Let's replace with empty string for now to avoid partial resolution issues.
                resolved_string = resolved_string.replace(placeholder, "")
                all_resolved = False # Mark that not all placeholders resolved fully
            else:
                resolved_string = resolved_string.replace(placeholder, env_value)
                if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Resolved placeholder '{placeholder}' using env var '{var_name}'.")

        # If any placeholder failed to resolve in a mixed string, log it.
        # If the original string was *only* an unresolved placeholder, we already returned None.
        if not all_resolved and len(placeholders_found) > 0:
            logger.warning(f"String '{obj}' contained unresolved placeholders. Result: '{resolved_string}'")

        return resolved_string
    else: return obj

def load_server_config(file_path: Optional[str] = None) -> dict:
    """Loads, resolves, and merges server config from JSON file."""
    config_path: Optional[Path] = None
    if file_path:
         path_obj = Path(file_path)
         if path_obj.is_file(): config_path = path_obj; logger.info(f"Using provided config file path: {config_path}")
         else: logger.warning(f"Provided path '{file_path}' not found/not file. Searching standard locations.")
    if not config_path:
        current_dir = Path.cwd()
        standard_paths = [ current_dir / "swarm_config.json", Path(BASE_DIR) / "swarm_config.json", Path.home() / ".swarm" / "swarm_config.json" ]
        for candidate in standard_paths:
            if candidate.is_file(): config_path = candidate; logger.info(f"Using config file found at: {config_path}"); break
        if not config_path: raise FileNotFoundError(f"Config file 'swarm_config.json' not found in provided path or standard locations: {[str(p) for p in standard_paths]}")
    logger.debug(f"Attempting to load config from: {config_path}")
    try:
        # Ensure reading with UTF-8 encoding
        raw_config = json.loads(config_path.read_text(encoding='utf-8'))
        if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Raw config loaded: {redact_sensitive_data(raw_config)}")
    except json.JSONDecodeError as json_err:
        logger.critical(f"Invalid JSON in config file {config_path}: {json_err}")
        raise ValueError(f"Invalid JSON in config {config_path}: {json_err}") from json_err
    except Exception as load_err:
        logger.critical(f"Failed to read config file {config_path}: {load_err}")
        raise ValueError(f"Failed to read config {config_path}") from load_err
    try:
         processed_config = process_config(raw_config)
         globals()["config"] = processed_config
         logger.info(f"Config loaded and processed from {config_path}")
         return processed_config
    except Exception as process_err: logger.critical(f"Failed to process config from {config_path}: {process_err}", exc_info=True); raise ValueError(f"Failed to process config from {config_path}") from process_err

# --- Start of Missing Functions ---

def are_required_mcp_servers_configured(required_servers: List[str], config_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Checks if required MCP servers are present in the config."""
    if not required_servers: return True, []
    mcp_servers = config_dict.get("mcpServers", {})
    if not isinstance(mcp_servers, dict):
        logger.warning("MCP servers configuration ('mcpServers') is missing or invalid.")
        return False, required_servers # All are missing if section is invalid

    missing = [server for server in required_servers if server not in mcp_servers]
    if missing:
        logger.warning(f"Required MCP servers are missing from configuration: {missing}")
        return False, missing
    else:
        logger.debug("All required MCP servers are configured.")
        return True, []

def validate_mcp_server_env(mcp_servers: Dict[str, Any], required_servers: Optional[List[str]] = None) -> None:
    """
    Validates that required environment variables specified within MCP server
    configurations are actually set in the environment. Assumes placeholders in
    the config's `env` section values are *already resolved* before calling this.

    Args:
        mcp_servers: Dictionary of MCP server configurations (placeholders resolved).
        required_servers: Optional list of specific server names to validate. If None, validates all.

    Raises:
        ValueError: If a required environment variable for a validated server is not set.
    """
    servers_to_validate = mcp_servers
    if required_servers is not None:
        servers_to_validate = {k: v for k, v in mcp_servers.items() if k in required_servers}
        missing_keys = [k for k in required_servers if k not in mcp_servers]
        if missing_keys: logger.warning(f"Required MCP servers missing during env validation: {missing_keys}")

    logger.debug(f"Validating environment variables for MCP servers: {list(servers_to_validate.keys())}")

    for server_name, server_config in servers_to_validate.items():
        env_section = server_config.get("env", {})
        if not isinstance(env_section, dict): logger.warning(f"'env' for MCP server '{server_name}' invalid. Skipping."); continue
        logger.debug(f"Validating env for MCP server '{server_name}'.")
        for env_key, env_spec in env_section.items():
            # Determine if required (default is True)
            is_required = env_spec.get("required", True) if isinstance(env_spec, dict) else True
            if not is_required: logger.debug(f"Skipping optional env var '{env_key}' for '{server_name}'."); continue

            # Get the RESOLVED value from the config dict
            config_value = env_spec.get("value") if isinstance(env_spec, dict) else env_spec

            # Check if the resolved value is missing or empty
            if config_value is None or (isinstance(config_value, str) and not config_value.strip()):
                # This check assumes resolve_placeholders returned None or empty for missing env vars
                 raise ValueError(f"Required env var '{env_key}' for MCP server '{server_name}' is missing or empty in resolved config.")
            else: logger.debug(f"Env var '{env_key}' for '{server_name}' present in resolved config.")

def get_default_llm_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves the config dict for the default LLM profile."""
    selected_llm_name = os.getenv("DEFAULT_LLM", "default")
    logger.debug(f"Getting default LLM config for profile: '{selected_llm_name}'")
    llm_profiles = config_dict.get("llm", {})
    if not isinstance(llm_profiles, dict): raise ValueError("'llm' section missing or invalid.")
    llm_config = llm_profiles.get(selected_llm_name)
    if not llm_config:
        if selected_llm_name != "default" and "default" in llm_profiles:
             logger.warning(f"Profile '{selected_llm_name}' not found, falling back to 'default'.")
             llm_config = llm_profiles.get("default")
             if not llm_config: # Guard against empty 'default'
                  raise ValueError(f"LLM profile '{selected_llm_name}' not found and 'default' profile is missing or invalid.")
        else: raise ValueError(f"LLM profile '{selected_llm_name}' (nor 'default') not found.")
    if not isinstance(llm_config, dict): raise ValueError(f"LLM profile '{selected_llm_name}' invalid.")
    if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Using LLM profile '{selected_llm_name}': {redact_sensitive_data(llm_config)}")
    return llm_config

def validate_api_keys(config_dict: Dict[str, Any], selected_llm: str = "default") -> Dict[str, Any]:
    """Validates API key presence for a selected LLM profile (called by load_llm_config)."""
    logger.debug(f"Validating API keys for LLM profile '{selected_llm}'.")
    llm_profiles = config_dict.get("llm", {})
    if not isinstance(llm_profiles, dict): logger.warning("No 'llm' section found, skipping API key validation."); return config_dict
    llm_config = llm_profiles.get(selected_llm)
    if not isinstance(llm_config, dict): logger.warning(f"No config for LLM profile '{selected_llm}', skipping validation."); return config_dict

    api_key_required = llm_config.get("api_key_required", True)
    api_key = llm_config.get("api_key")
    # Use the fact that resolve_placeholders now returns None for missing env vars
    key_is_missing_or_empty = api_key is None or (isinstance(api_key, str) and not api_key.strip())

    if api_key_required and key_is_missing_or_empty:
         # If the key is missing/empty *after* resolving placeholders, it means
         # neither the config nor the specific env var had it.
         # Check OPENAI_API_KEY as a general fallback ONLY IF not found specifically.
         common_fallback_var = "OPENAI_API_KEY"
         fallback_key = os.getenv(common_fallback_var)

         specific_env_var_name = f"{selected_llm.upper()}_API_KEY" # e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY

         # Check specific env var first
         specific_key = os.getenv(specific_env_var_name)
         if specific_key:
             logger.info(f"API key missing/empty in resolved config for '{selected_llm}', using env var '{specific_env_var_name}'.")
             # Update the config dict in place (or return a modified copy if preferred)
             llm_config["api_key"] = specific_key
         elif fallback_key:
             logger.info(f"API key missing/empty for '{selected_llm}' and specific env var '{specific_env_var_name}' not set. Using fallback env var '{common_fallback_var}'.")
             llm_config["api_key"] = fallback_key
         else:
             raise ValueError(f"Required API key for LLM profile '{selected_llm}' is missing or empty. Checked config, env var '{specific_env_var_name}', and fallback '{common_fallback_var}'.")

    elif api_key_required: logger.debug(f"API key validation successful for '{selected_llm}'.")
    else: logger.debug(f"API key not required for '{selected_llm}'.")
    # Return the potentially modified config_dict (or just llm_config part if preferred)
    return config_dict


def validate_and_select_llm_provider(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the selected LLM provider and returns its config."""
    logger.debug("Validating and selecting LLM provider based on DEFAULT_LLM.")
    try:
        llm_name = os.getenv("DEFAULT_LLM", "default")
        llm_config = load_llm_config(config_dict, llm_name) # Use load_llm_config which includes validation
        logger.debug(f"LLM provider '{llm_name}' validated successfully.")
        return llm_config
    except ValueError as e: logger.error(f"LLM provider validation failed: {e}"); raise

def inject_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures placeholders are resolved (delegates to resolve_placeholders)."""
    logger.debug("Ensuring environment variable placeholders are resolved.")
    return resolve_placeholders(config_dict)

def load_llm_config(config_dict: Optional[Dict[str, Any]] = None, llm_name: Optional[str] = None) -> Dict[str, Any]:
    """Loads and validates config for a specific LLM profile."""
    if config_dict is None:
        # Try loading from global if not provided
        global_config = globals().get("config")
        if not global_config:
             try: config_dict = load_server_config(); globals()["config"] = config_dict
             except Exception as e: raise ValueError("Global config not loaded and no config_dict provided.") from e
        else:
             config_dict = global_config

    target_llm_name = llm_name or os.getenv("DEFAULT_LLM", "default")
    logger.debug(f"Loading LLM config for profile: '{target_llm_name}'")
    # Resolve placeholders FIRST using the provided or loaded config_dict
    resolved_config = resolve_placeholders(config_dict)

    llm_profiles = resolved_config.get("llm", {})
    if not isinstance(llm_profiles, dict): raise ValueError("'llm' section must be a dictionary.")
    llm_config = llm_profiles.get(target_llm_name)

    # Fallback Logic (if profile not found after resolving)
    if not llm_config:
        logger.warning(f"LLM config for '{target_llm_name}' not found. Generating fallback.")
        fb_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai"); fb_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
        # Check env vars for fallback API key *after* trying the specific one based on target_llm_name
        specific_env_key = os.getenv(f"{target_llm_name.upper()}_API_KEY")
        openai_env_key = os.getenv("OPENAI_API_KEY")
        fb_api_key = specific_env_key or openai_env_key or "" # Use specific, then openai, then empty

        specific_env_url = os.getenv(f"{target_llm_name.upper()}_BASE_URL")
        openai_env_url = os.getenv("OPENAI_API_BASE")
        default_openai_url = "https://api.openai.com/v1" if fb_provider == "openai" else None
        fb_base_url = specific_env_url or openai_env_url or default_openai_url

        llm_config = {k: v for k, v in {
             "provider": fb_provider,
             "model": fb_model,
             "base_url": fb_base_url,
             "api_key": fb_api_key, # Use the determined fallback key
             # Determine requirement based on provider (adjust providers as needed)
             "api_key_required": fb_provider not in ["ollama", "lmstudio", "groq"] # Example: groq might need key
             }.items() if v is not None}
        logger.debug(f"Using fallback config for '{target_llm_name}': {redact_sensitive_data(llm_config)}")

    if not isinstance(llm_config, dict): raise ValueError(f"LLM profile '{target_llm_name}' must be a dictionary.")

    # --- API Key Validation integrated here ---
    api_key_required = llm_config.get("api_key_required", True)
    # Check the api_key *within the potentially generated or loaded llm_config*
    api_key = llm_config.get("api_key")
    key_is_missing_or_empty = api_key is None or (isinstance(api_key, str) and not api_key.strip())

    if api_key_required and key_is_missing_or_empty:
         # Key is missing/empty after config resolution and fallback generation.
         # Re-check environment variables as a final step before erroring.
         specific_env_var_name = f"{target_llm_name.upper()}_API_KEY"
         common_fallback_var = "OPENAI_API_KEY"
         specific_key_from_env = os.getenv(specific_env_var_name)
         fallback_key_from_env = os.getenv(common_fallback_var)

         if specific_key_from_env:
              logger.info(f"API key missing/empty in config/fallback for '{target_llm_name}', using env var '{specific_env_var_name}'.")
              llm_config["api_key"] = specific_key_from_env # Update config with key from env
         elif fallback_key_from_env:
              logger.info(f"API key missing/empty for '{target_llm_name}' and specific env var '{specific_env_var_name}' not set. Using fallback env var '{common_fallback_var}'.")
              llm_config["api_key"] = fallback_key_from_env # Update config with key from env
         else:
              # If still missing after checking env vars again, raise error
              raise ValueError(f"Required API key for LLM profile '{target_llm_name}' is missing or empty. Checked config, fallback generation, env var '{specific_env_var_name}', and fallback '{common_fallback_var}'.")

    # Log final config being used
    if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Final loaded config for '{target_llm_name}': {redact_sensitive_data(llm_config)}")
    return llm_config


def get_llm_model(config_dict: Dict[str, Any], llm_name: Optional[str] = None) -> str:
    """Retrieves the 'model' name string for a specific LLM profile."""
    target_llm_name = llm_name or os.getenv("DEFAULT_LLM", "default")
    try: llm_config = load_llm_config(config_dict, target_llm_name)
    except ValueError as e: raise ValueError(f"Could not load config for LLM '{target_llm_name}': {e}") from e
    model_name = llm_config.get("model")
    if not model_name or not isinstance(model_name, str): raise ValueError(f"'model' name missing/invalid for LLM '{target_llm_name}'.")
    logger.debug(f"Retrieved model name '{model_name}' for LLM '{target_llm_name}'")
    return model_name

def load_and_validate_llm(config_dict: Dict[str, Any], llm_name: Optional[str] = None) -> Dict[str, Any]:
    """Loads and validates config for a specific LLM (wrapper for load_llm_config)."""
    target_llm_name = llm_name or os.getenv("DEFAULT_LLM", "default")
    logger.debug(f"Loading and validating LLM (via load_llm_config) for profile: {target_llm_name}")
    return load_llm_config(config_dict, target_llm_name)

# --- End of Missing Functions ---
