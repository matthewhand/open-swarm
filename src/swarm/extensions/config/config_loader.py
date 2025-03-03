"""
Configuration Loader for Open Swarm MCP Framework.

This module provides functionality to:
- Load and validate server configurations from JSON files.
- Resolve environment variable placeholders like a boss.
- Ensure all required keys and configurations are present, no excuses.

Enhanced to redact sensitive info during logging and throw robust error handling into the mix.
"""

import os
import json
import re
import logging
from typing import Any, Dict, List, Tuple, Optional
from dotenv import load_dotenv
from .server_config import save_server_config
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data

# Initialize logger for this module with style
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
config = {}

# Load environment variables from .env like a pro
load_dotenv()
logger.debug("Environment variables loaded from .env file, ready to roll.")

def process_config(config: dict) -> dict:
    """
    Processes the configuration dictionary by resolving placeholders and merging external MCP settings.
    This function is pure—no file I/O here, making it a dream for unit testing.
    """
    try:
        resolved_config = resolve_placeholders(config)
        import json
        logger.debug("Configuration after resolving placeholders: " + json.dumps(redact_sensitive_data(resolved_config)))
        disable_merge = os.getenv("DISABLE_MCP_MERGE", "false").lower() in ("true", "1", "yes")
        if not disable_merge:
            # Platform-specific paths for external MCP settings—Windows vs. Unix vibes
            if os.name == "nt":
                external_mcp_path = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Claude", "claude_desktop_config.json")
            else:
                external_mcp_path = os.path.join(os.path.expanduser("~"), ".vscode-server", "data", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")
            if os.path.exists(external_mcp_path):
                try:
                    with open(external_mcp_path, "r") as mcp_file:
                        mcp_config = json.load(mcp_file)
                    logger.debug("Loaded external MCP settings: " + json.dumps(redact_sensitive_data(mcp_config)))
                    main_mcp = resolved_config.get("mcpServers", {})
                    external_mcp = mcp_config.get("mcpServers", {})
                    # Main config takes precedence over external MCP settings—respect the hierarchy
                    merged_mcp = main_mcp.copy()
                    for server, server_config in external_mcp.items():
                        if server in main_mcp:
                            merged_mcp[server] = main_mcp[server]
                            continue
                        if server_config.get("disabled", False):
                            continue
                        merged_mcp[server] = server_config
                    resolved_config["mcpServers"] = merged_mcp
                    logger.debug("Merged MCP servers configuration: " + json.dumps(merged_mcp))
                except Exception as e:
                    logger.error(f"Failed to load or merge MCP settings from '{external_mcp_path}': {e}")
            else:
                logger.debug(f"External MCP settings file not found at {external_mcp_path}. Skipping merge.")
        else:
            logger.debug("MCP settings merge is disabled due to DISABLE_MCP_MERGE environment variable.")
    except Exception as e:
        logger.error(f"Failed to process configuration: {e}")
        raise
    globals()["config"] = resolved_config
    return resolved_config

def resolve_placeholders(obj: Any) -> Any:
    """
    Recursively resolve placeholders in the given object like a regex ninja.

    Placeholders are in the form of ${VAR_NAME} and get swapped with the corresponding env var.
    If the env var’s missing, we keep it chill and log a warning—no tantrums here.

    Args:
        obj (Any): The object to resolve placeholders in—could be a string, dict, list, whatever.

    Returns:
        Any: The object with all placeholders resolved, looking sharp.
    """
    if isinstance(obj, dict):
        return {k: resolve_placeholders(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_placeholders(item) for item in obj]
    elif isinstance(obj, str):
        pattern = re.compile(r'\$\{(\w+)\}')
        matches = pattern.findall(obj)
        for var in matches:
            env_value = os.getenv(var)
            if env_value is None:
                logger.warning(f"Environment variable '{var}' is not set but is referenced in the configuration. Placeholder will be left unresolved.")
                continue
            logger.debug(f"Resolved placeholder '${{{var}}}' with value '{redact_sensitive_data(env_value)}'")
            obj = obj.replace(f'${{{var}}}', env_value)
        return obj
    else:
        return obj

def load_server_config(file_path: Optional[str] = None) -> dict:
    """
    Loads the server configuration from a JSON file and resolves placeholders with finesse.

    Searches candidate paths if no file_path is given—adaptable like a chameleon.
    Merges external MCP settings if the stars align (and DISABLE_MCP_MERGE isn’t set).

    Args:
        file_path (str): Optional custom path to the configuration file—your call.

    Returns:
        dict: The resolved configuration, ready to rock.

    Raises:
        FileNotFoundError: If the config file’s playing hide-and-seek and can’t be found.
        ValueError: If the JSON’s busted or placeholders go rogue.
    """
    from pathlib import Path
    if file_path is None or not Path(file_path).exists():
         from swarm.settings import BASE_DIR
         current_dir = os.getcwd()
         candidate_paths = [
             str(Path(BASE_DIR) / "swarm_config.json"),
             str(Path(os.path.expanduser("~")) / ".swarm" / "swarm_config.json"),
             str(Path(current_dir) / "swarm_config.json")
         ]
         for candidate in candidate_paths:
             if Path(candidate).exists():
                 file_path = candidate
                 logger.info(f"Using alternative configuration file: {file_path}")
                 break
         if file_path is None or not Path(file_path).exists():
             logger.error("No configuration file found in candidate paths: " + ", ".join(candidate_paths))
             raise FileNotFoundError("No configuration file found in candidate paths.")

    logger.debug(f"Attempting to load configuration from {file_path}")

    try:
        with open(file_path, "r") as file:
            config = json.load(file)
            logger.debug(f"Raw configuration loaded: {redact_sensitive_data(config)}")
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {file_path}: {e}")
        raise ValueError(f"Invalid JSON in configuration file {file_path}: {e}")

    # Resolve placeholders recursively—because we don’t mess around
    try:
        resolved_config = resolve_placeholders(config)
        # logger.debug(f"Configuration after resolving placeholders: {redact_sensitive_data(resolved_config)}")

        # Merge external MCP settings if merge isn’t disabled by env var—keeping it flexible
        disable_merge = os.getenv("DISABLE_MCP_MERGE", "false").lower() in ("true", "1", "yes")
        if not disable_merge:
            # Check if the external MCP settings file exists—platform vibes matter
            if os.name == "nt":
                external_mcp_path = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Claude", "claude_desktop_config.json")
            else:
                external_mcp_path = os.path.join(os.path.expanduser("~"), ".vscode-server", "data", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")
            if os.path.exists(external_mcp_path):
                try:
                    with open(external_mcp_path, "r") as mcp_file:
                        mcp_config = json.load(mcp_file)
                    logger.debug("Loaded external MCP settings: " + json.dumps(redact_sensitive_data(mcp_config)))
                    main_mcp = resolved_config.get("mcpServers", {})
                    external_mcp = mcp_config.get("mcpServers", {})
                    # Main config takes precedence—external gets the back seat
                    merged_mcp = main_mcp.copy()
                    for server, server_config in external_mcp.items():
                        if server in main_mcp:
                            continue
                        if server_config.get("disabled", False):
                            continue
                        merged_mcp[server] = server_config
                    resolved_config["mcpServers"] = merged_mcp
                    logger.debug("Merged MCP servers configuration: " + json.dumps(merged_mcp))
                except Exception as e:
                    logger.error(f"Failed to load or merge MCP settings from '{external_mcp_path}': {e}")
            else:
                logger.debug(f"External MCP settings file not found at {external_mcp_path}. Skipping merge.")
        else:
            logger.debug("MCP settings merge is disabled due to DISABLE_MCP_MERGE environment variable.")
    except Exception as e:
        logger.error(f"Failed to resolve placeholders in configuration: {e}")
        raise

    globals()["config"] = resolved_config
    return resolved_config

def validate_mcp_server_env(mcp_servers: Dict[str, Any], required_servers: Optional[List[str]] = None) -> None:
    """
    Validates that mandatory environment variables in MCP server configs are set—no slacking allowed.

    Args:
        mcp_servers (Dict[str, Any]): MCP server configurations to check.
        required_servers (Optional[List[str]]): List of MCP servers to validate; if None, we do ‘em all.

    Raises:
        ValueError: If any mandatory env var in an `env` section is missing—gotta keep it tight.
    """
    if required_servers is not None:
        servers_to_validate = {server: config for server, config in mcp_servers.items() if server in required_servers}
    else:
        servers_to_validate = mcp_servers
    logger.debug(f"Validating environment variables for MCP servers: {list(servers_to_validate.keys())}")
    for server_name, server_config in servers_to_validate.items():
        logger.debug(f"Validating environment variables for MCP server '{server_name}'.")
        env_vars = server_config.get("env", {})
        for env_key, env_value in env_vars.items():
            logger.debug(f"Checking environment variable '{env_key}' for server '{server_name}' with value '{redact_sensitive_data(env_value)}'")
            if env_value == "":
                logger.debug(f"Environment variable '{env_key}' for MCP server '{server_name}' is optional and set to empty string.")
                # Optional: Do not raise error if env_value is empty string
                continue
            elif not env_value:
                logger.error(f"Environment variable '{env_key}' for MCP server '{server_name}' is not set.")
                raise ValueError(f"Environment variable '{env_key}' for MCP server '{server_name}' is not set.")
            else:
                logger.debug(f"Environment variable '{env_key}' for server '{server_name}' is set.")

def get_default_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves the LLM configuration based on the `LLM` environment variable—defaulting like a pro.

    Args:
        config (Dict[str, Any]): The configuration dictionary to pull from.

    Returns:
        Dict[str, Any]: The selected LLM configuration, locked and loaded.

    Raises:
        ValueError: If the `LLM` env var is set but the profile’s MIA.
    """
    selected_llm = os.getenv("DEFAULT_LLM", "default")
    logger.debug(f"Selected LLM profile from environment variable: '{selected_llm}'")

    llm_config = config.get("llm", {}).get(selected_llm)
    if not llm_config:
        logger.error(f"LLM profile '{selected_llm}' not found in configuration.")
        raise ValueError(f"LLM profile '{selected_llm}' not found in configuration.")

    logger.debug(f"Using LLM profile: '{selected_llm}'")
    return llm_config

def validate_api_keys(config: Dict[str, Any], selected_llm: str = "default") -> Dict[str, Any]:
    """
    Validates the presence of API keys for the selected LLM profile—because security matters.

    Args:
        config (Dict[str, Any]): The configuration dictionary to validate.
        selected_llm (str): The selected LLM profile—defaults to "default" for the classics.

    Returns:
        Dict[str, Any]: The validated configuration, good to go.

    Raises:
        ValueError: If a required API key is missing—don’t leave us hanging!
    """
    logger.debug(f"Validating API keys for LLM profile '{selected_llm}'.")
    llm_config = config.get("llm", {}).get(selected_llm, {})
    if not llm_config:
        logger.warning(f"No configuration found for LLM profile '{selected_llm}'.")
        return config

    api_key = llm_config.get("api_key")
    if api_key == "":
        logger.debug(f"LLM profile '{selected_llm}' does not require an API key (explicit empty string).")
        # Optional: API key is optional if set to empty string
        return config
    elif not api_key:
        logger.error(f"API key is missing for LLM profile '{selected_llm}'.")
        raise ValueError(f"API key is missing for LLM profile '{selected_llm}'.")

    logger.debug(f"API key validation successful for LLM profile '{selected_llm}'. Key: {redact_sensitive_data(api_key)}")
    return config

def are_required_mcp_servers_configured(required_servers: List[str], config: dict) -> Tuple[bool, List[str]]:
    """
    Checks if all required MCP servers are configured in the given config—don’t skip the essentials.

    Args:
        required_servers (List[str]): List of required MCP server names to verify.
        config (dict): Configuration dictionary to check against.

    Returns:
        Tuple[bool, List[str]]: True if all servers are there, plus a list of any missing ones.
    """
    configured_servers = config.get("mcpServers", {}).keys()
    missing_servers = [server for server in required_servers if server not in configured_servers]
    if missing_servers:
        logger.error(f"Missing MCP servers in configuration: {missing_servers}")
        return False, missing_servers
    return True, []

def validate_and_select_llm_provider(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the selected LLM provider and returns its config—keeping it legit.

    Args:
        config (Dict[str, Any]): The configuration dictionary to work with.

    Returns:
        Dict[str, Any]: The validated LLM provider config, ready for action.

    Raises:
        ValueError: If validation goes sideways—better safe than sorry.
    """
    logger.debug("Validating and selecting LLM provider.")
    try:
        llm_name = os.getenv("DEFAULT_LLM", "default")
        validate_api_keys(config, llm_name)
        return config.get("llm", {}).get(llm_name)
    except ValueError as e:
        logger.error(f"LLM provider validation failed: {e}")
        raise

def inject_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Injects environment variables into the configuration where placeholders exist—because we’re fancy like that.

    Args:
        config (Dict[str, Any]): The configuration dictionary to spice up.

    Returns:
        Dict[str, Any]: The config with env vars injected, looking fly.
    """
    logger.debug("Injecting environment variables into configuration.")
    # Already handled by resolve_placeholders, but keeping this for future flair
    return config

def load_llm_config(config: Optional[Dict[str, Any]] = None, llm_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the configuration for a specific LLM with all the bells and whistles.

    Args:
        config (Dict[str, Any]): The full configuration dictionary—bring your own or we’ll grab the global one.
        llm_name (Optional[str]): The name of the LLM to load—defaults to whatever’s hot in the env.

    Returns:
        Dict[str, Any]: The configuration dictionary for the specified LLM, polished and ready.

    Raises:
        ValueError: If the LLM config’s nowhere to be found or the global config’s AWOL.
    """
    if config is None:
        config = globals().get("config")
    if config is None:
        raise ValueError("Global configuration not defined and no config provided—give me something to work with!")

    logger.debug(f"Attempting to load LLM configuration for: {llm_name or 'unspecified'}")

    if not llm_name:
        llm_name = os.getenv("DEFAULT_LLM", "default")
        logger.debug(f"No LLM name provided, using DEFAULT_LLM env variable or fallback to 'default': {llm_name}")

    # Resolve placeholders right here, right now—ensure we’re always fresh
    resolved_config = resolve_placeholders(config)
    llm_config = resolved_config.get("llm", {}).get(llm_name)
    if not llm_config:
        error_message = f"LLM configuration for '{llm_name}' not found in the config—where’d it go?"
        logger.error(error_message)
        raise ValueError(error_message)

    logger.debug(f"Loaded LLM configuration for '{llm_name}': {redact_sensitive_data(llm_config)}")
    return llm_config

def get_llm_model(config: Dict[str, Any], llm_name: Optional[str] = None) -> str:
    """
    Retrieves the model name for a specific LLM—short and sweet.

    Args:
        config (Dict[str, Any]): The full configuration dictionary to dig into.
        llm_name (Optional[str]): The name of the LLM to load—defaults to whatever’s vibin’.

    Returns:
        str: The model name for the specified LLM—simple but effective.

    Raises:
        ValueError: If the model name’s missing—don’t leave me hanging!
    """
    llm_config = load_llm_config(config, llm_name)
    model_name = llm_config.get("model")
    if not model_name:
        error_message = f"Model name not found in LLM configuration for '{llm_name}'—give me the goods!"
        logger.error(error_message)
        raise ValueError(error_message)

    logger.debug(f"Retrieved model name '{model_name}' for LLM '{llm_name}'")
    return model_name

def load_and_validate_llm(config: Dict[str, Any], llm_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads and validates the configuration for a specific LLM—because we don’t half-step.

    Args:
        config (Dict[str, Any]): The full configuration dictionary to validate.
        llm_name (Optional[str]): The name of the LLM to load—defaults to the usual suspect.

    Returns:
        Dict[str, Any]: The validated LLM configuration, locked and loaded.

    Raises:
        ValueError: If validation flops—keep it real!
    """
    logger.debug(f"Loading and validating LLM configuration for: {llm_name or 'unspecified'}")

    # Load the LLM configuration with all the trimmings
    llm_config = load_llm_config(config, llm_name)

    # Validate the API keys—security first, party later
    validate_api_keys(config, llm_name or "default")

    logger.debug(f"LLM configuration for '{llm_name}' is valid and loaded—ready to rock!")
    return llm_config

