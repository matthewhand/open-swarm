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
try: from .server_config import save_server_config
except ImportError: save_server_config = None

SWARM_DEBUG = os.getenv("SWARM_DEBUG", "False").lower() in ("true", "1", "yes")
try: from swarm.settings import BASE_DIR
except ImportError: BASE_DIR = Path(__file__).resolve().parent.parent.parent

from swarm.utils.redact import redact_sensitive_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if SWARM_DEBUG else logging.INFO)

# Add handler only if needed, DO NOT set handler level conditionally here
if not logger.handlers and not logging.getLogger().hasHandlers():
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # --- REMOVED CONDITIONAL HANDLER LEVEL SETTING ---
    # if not SWARM_DEBUG:
    #     stream_handler.setLevel(logging.WARNING)

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
                    with open(external_mcp_path, "r", encoding='utf-8') as mcp_file: external_mcp_config = json.load(mcp_file)
                    if logger.isEnabledFor(logging.DEBUG): logger.debug("Loaded external MCP settings: " + json.dumps(redact_sensitive_data(external_mcp_config), indent=2))
                    main_mcp_servers = resolved_config.get("mcpServers", {}); external_mcp_servers = external_mcp_config.get("mcpServers", {})
                    merged_mcp_servers = main_mcp_servers.copy(); servers_added_count = 0
                    for name, server_cfg in external_mcp_servers.items():
                        if name not in merged_mcp_servers and not server_cfg.get("disabled", False): merged_mcp_servers[name] = server_cfg; servers_added_count += 1
                    if servers_added_count > 0: resolved_config["mcpServers"] = merged_mcp_servers; logger.info(f"Merged {servers_added_count} MCP servers.");
                    else: logger.debug("No new MCP servers added from external settings.")
                except Exception as merge_err: logger.error(f"Failed to load/merge MCP settings from '{external_mcp_path}': {merge_err}", exc_info=logger.isEnabledFor(logging.DEBUG))
            else: logger.debug(f"External MCP settings file not found at {external_mcp_path}. Skipping merge.")
        else: logger.debug("MCP settings merge disabled.")
    except Exception as e: logger.error(f"Failed during config processing: {e}", exc_info=logger.isEnabledFor(logging.DEBUG)); raise
    globals()["config"] = resolved_config
    return resolved_config

def resolve_placeholders(obj: Any) -> Any:
    """Recursively resolve ${VAR_NAME} placeholders."""
    if isinstance(obj, dict): return {k: resolve_placeholders(v) for k, v in obj.items()}
    elif isinstance(obj, list): return [resolve_placeholders(item) for item in obj]
    elif isinstance(obj, str):
        pattern = re.compile(r'\$\{(\w+(?:[_-]\w+)*)\}')
        resolved_string = obj; any_unresolved = False
        for var_name in pattern.findall(obj):
            env_value = os.getenv(var_name); placeholder = f'${{{var_name}}}'
            if env_value is None:
                log_level = logging.DEBUG
                if resolved_string == placeholder:
                     log_level = logging.WARNING
                     resolved_string = None
                     any_unresolved = True
                     logger.log(log_level, f"Env var '{var_name}' not set for placeholder '{placeholder}'. Resolving to None.")
                     return None
                else:
                    resolved_string = resolved_string.replace(placeholder, "")
                    any_unresolved = True
                    logger.log(log_level, f"Env var '{var_name}' not set for placeholder '{placeholder}'. Removing from string.")
            else:
                 resolved_string = resolved_string.replace(placeholder, env_value)
                 if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Resolved placeholder '{placeholder}' using env var '{var_name}'.")
        if any_unresolved and resolved_string is not None:
             logger.debug(f"String '{obj}' contained unresolved placeholders. Result: '{resolved_string}'")
        return resolved_string
    else: return obj

def load_server_config(file_path: Optional[str] = None) -> dict:
    """Loads, resolves, and merges server config from JSON file."""
    config_path: Optional[Path] = None
    if file_path:
         path_obj = Path(file_path)
         if path_obj.is_file(): config_path = path_obj; logger.info(f"Using provided config file path: {config_path}")
         else: logger.warning(f"Provided path '{file_path}' not found. Searching standard locations.")
    if not config_path:
        standard_paths = [ Path.cwd() / "swarm_config.json", Path(BASE_DIR) / "swarm_config.json", Path.home() / ".swarm" / "swarm_config.json" ]
        config_path = next((p for p in standard_paths if p.is_file()), None)
        if not config_path: raise FileNotFoundError(f"Config file 'swarm_config.json' not found. Checked: {[str(p) for p in standard_paths]}")
        logger.info(f"Using config file found at: {config_path}")
    try:
        raw_config = json.loads(config_path.read_text(encoding='utf-8'))
        if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Raw config loaded: {redact_sensitive_data(raw_config)}")
        processed_config = process_config(raw_config)
        globals()["config"] = processed_config
        logger.info(f"Config loaded and processed from {config_path}")
        return processed_config
    except json.JSONDecodeError as e: logger.critical(f"Invalid JSON in {config_path}: {e}"); raise ValueError(f"Invalid JSON") from e
    except Exception as e: logger.critical(f"Failed to read/process config {config_path}: {e}"); raise ValueError("Failed to load/process config") from e

def load_llm_config(config_dict: Optional[Dict[str, Any]] = None, llm_name: Optional[str] = None) -> Dict[str, Any]:
    """Loads, validates, and resolves API keys for a specific LLM profile."""
    if config_dict is None:
        global_config = globals().get("config")
        if not global_config:
             try: config_dict = load_server_config(); globals()["config"] = config_dict
             except Exception as e: raise ValueError("Global config not loaded and no config_dict provided.") from e
        else: config_dict = global_config

    target_llm_name = llm_name or os.getenv("DEFAULT_LLM", "default")
    logger.debug(f"LOAD_LLM: Loading profile: '{target_llm_name}'.")

    resolved_config = resolve_placeholders(config_dict)
    llm_profiles = resolved_config.get("llm", {})
    if not isinstance(llm_profiles, dict): raise ValueError("'llm' section must be a dictionary.")

    llm_config = llm_profiles.get(target_llm_name)
    config_source = f"config file ('{target_llm_name}')"
    logger.debug(f"LOAD_LLM: Initial lookup for '{target_llm_name}': {'Found' if llm_config else 'Missing'}")

    if not llm_config:
        logger.warning(f"LOAD_LLM: Config for '{target_llm_name}' not found. Generating fallback.")
        config_source = "fallback generation"
        fb_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai"); fb_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
        llm_config = { "provider": fb_provider, "model": fb_model, "api_key": None, "base_url": None }
        logger.debug(f"LOAD_LLM: Generated fallback core config: {llm_config}")

    if not isinstance(llm_config, dict): raise ValueError(f"LLM profile '{target_llm_name}' must be a dictionary.")

    final_api_key = llm_config.get("api_key"); key_log_source = f"{config_source} (resolved)" if final_api_key else config_source
    provider = llm_config.get("provider"); api_key_required = llm_config.get("api_key_required", True)
    logger.debug(f"LOAD_LLM: Initial key from {key_log_source}: {'****' if final_api_key else 'None'}. Required={api_key_required}")

    logger.debug(f"LOAD_LLM: Checking ENV vars for potential override.")
    specific_env_var_name = f"{provider.upper()}_API_KEY" if provider else "PROVIDER_API_KEY"
    common_fallback_var = "OPENAI_API_KEY"
    specific_key_from_env = os.getenv(specific_env_var_name); fallback_key_from_env = os.getenv(common_fallback_var)
    logger.debug(f"LOAD_LLM: Env Check: Specific ('{specific_env_var_name}')={'****' if specific_key_from_env else 'None'}, Fallback ('{common_fallback_var}')={'****' if fallback_key_from_env else 'None'}")

    if specific_key_from_env:
        if final_api_key != specific_key_from_env: logger.info(f"LOAD_LLM: Overriding key with env var '{specific_env_var_name}'.")
        final_api_key = specific_key_from_env; key_log_source = f"env var '{specific_env_var_name}'"
    elif fallback_key_from_env:
        if not specific_key_from_env or specific_env_var_name == common_fallback_var:
            if final_api_key != fallback_key_from_env: logger.info(f"LOAD_LLM: Overriding key with fallback env var '{common_fallback_var}'.")
            final_api_key = fallback_key_from_env; key_log_source = f"env var '{common_fallback_var}'"
        else: logger.debug(f"LOAD_LLM: Specific env key '{specific_env_var_name}' unset, NOT using fallback.")
    else: logger.debug(f"LOAD_LLM: No relevant API key found in environment variables.")

    key_is_still_missing_or_empty = final_api_key is None or (isinstance(final_api_key, str) and not final_api_key.strip())
    logger.debug(f"LOAD_LLM: Key after env check: {'****' if final_api_key else 'None'}. Source: {key_log_source}. Still MissingOrEmpty={key_is_still_missing_or_empty}")

    if key_is_still_missing_or_empty:
        if api_key_required and not os.getenv("SUPPRESS_DUMMY_KEY"):
             final_api_key = "sk-DUMMYKEY"; key_log_source = "dummy key"; logger.warning(f"LOAD_LLM: Applying dummy key for '{target_llm_name}'.")
        elif api_key_required:
             key_log_source = "MISSING - ERROR"; raise ValueError(f"Required API key for LLM profile '{target_llm_name}' is missing.")
        else: key_log_source = "Not Required/Not Found"

    final_llm_config = llm_config.copy(); final_llm_config["api_key"] = final_api_key; final_llm_config["_log_key_source"] = key_log_source
    logger.debug(f"LOAD_LLM: Returning final config for '{target_llm_name}': {redact_sensitive_data(final_llm_config)}")
    return final_llm_config

def get_llm_model(config_dict: Dict[str, Any], llm_name: Optional[str] = None) -> str:
    target_llm_name = llm_name or os.getenv("DEFAULT_LLM", "default")
    try: llm_config = load_llm_config(config_dict, target_llm_name)
    except ValueError as e: raise ValueError(f"Could not load config for LLM '{target_llm_name}': {e}") from e
    model_name = llm_config.get("model")
    if not model_name or not isinstance(model_name, str): raise ValueError(f"'model' name missing/invalid for LLM '{target_llm_name}'.")
    logger.debug(f"Retrieved model name '{model_name}' for LLM '{target_llm_name}'")
    return model_name

def load_and_validate_llm(config_dict: Dict[str, Any], llm_name: Optional[str] = None) -> Dict[str, Any]:
    target_llm_name = llm_name or os.getenv("DEFAULT_LLM", "default")
    logger.debug(f"Loading and validating LLM (via load_llm_config) for profile: {target_llm_name}")
    return load_llm_config(config_dict, target_llm_name)

def get_server_params(server_config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
    """Extracts and validates parameters needed to start an MCP server."""
    command = server_config.get("command"); args = server_config.get("args", []); config_env = server_config.get("env", {})
    if not command: logger.error(f"MCP server '{server_name}' missing 'command'."); return None
    if not isinstance(args, list): logger.error(f"MCP server '{server_name}' 'args' must be list."); return None
    if not isinstance(config_env, dict): logger.error(f"MCP server '{server_name}' 'env' must be dict."); return None
    env = {**os.environ.copy(), **config_env}; valid_env = {}
    for k, v in env.items():
        if v is None: logger.warning(f"Env var '{k}' for MCP server '{server_name}' resolved to None. Omitting.")
        else: valid_env[k] = str(v)
    return {"command": command, "args": args, "env": valid_env}

def list_mcp_servers(config_dict: Dict[str, Any]) -> List[str]:
     """Returns a list of configured MCP server names."""
     return list(config_dict.get("mcpServers", {}).keys())

