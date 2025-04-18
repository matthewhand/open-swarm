import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv

logger = logging.getLogger("swarm.config")

def _substitute_env_vars(value: Any) -> Any:
    """Recursively substitute environment variables in strings, lists, and dicts."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    else:
        return value

def load_environment(project_root: Path):
    """Loads environment variables from a `.env` file located at the project root."""
    dotenv_path = project_root / ".env"
    logger.debug(f"Checking for .env file at: {dotenv_path}")
    try:
        if dotenv_path.is_file():
            loaded = load_dotenv(dotenv_path=dotenv_path, override=True)
            if loaded:
                logger.debug(f".env file Loaded/Overridden at: {dotenv_path}")
        else:
            logger.debug(f"No .env file found at {dotenv_path}.")
    except Exception as e:
        logger.error(f"Error loading .env file '{dotenv_path}': {e}", exc_info=logger.level <= logging.DEBUG)

def load_full_configuration(
    blueprint_class_name: str,
    default_config_path: Path,
    config_path_override: Optional[Union[str, Path]] = None,
    profile_override: Optional[str] = None,
    cli_config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Loads and merges configuration settings from base file, blueprint specifics, profiles, and CLI overrides.

    Args:
        blueprint_class_name (str): The name of the blueprint class (e.g., "MyBlueprint").
        default_config_path (Path): The default path to the swarm_config.json file.
        config_path_override (Optional[Union[str, Path]]): Path specified via CLI argument.
        profile_override (Optional[str]): Profile specified via CLI argument.
        cli_config_overrides (Optional[Dict[str, Any]]): Overrides provided via CLI argument.

    Returns:
        Dict[str, Any]: The final, merged configuration dictionary.

    Raises:
        ValueError: If the configuration file has JSON errors or cannot be read.
        FileNotFoundError: If a specific config_path_override is given but the file doesn't exist.
    """
    config_path = Path(config_path_override) if config_path_override else default_config_path
    logger.debug(f"Attempting to load base configuration from: {config_path}")
    base_config = {}
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                base_config = json.load(f)
            logger.debug(f"Successfully loaded base configuration from: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Config Error: Failed to parse JSON in {config_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Config Error: Failed to read {config_path}: {e}") from e
    else:
        if config_path_override:
            raise FileNotFoundError(f"Configuration Error: Specified config file not found: {config_path}")
        else:
            logger.warning(f"Default configuration file not found at {config_path}. Proceeding without base configuration.")

    # 1. Start with base defaults
    final_config = base_config.get("defaults", {}).copy()
    logger.debug(f"Applied base defaults. Keys: {list(final_config.keys())}")

    # 2. Merge base llm and mcpServers sections
    if "llm" in base_config:
        final_config.setdefault("llm", {}).update(base_config["llm"])
        logger.debug("Merged base 'llm'.")
    if "mcpServers" in base_config:
        final_config.setdefault("mcpServers", {}).update(base_config["mcpServers"])
        logger.debug("Merged base 'mcpServers'.")

    # 3. Merge blueprint-specific settings
    blueprint_settings = base_config.get("blueprints", {}).get(blueprint_class_name, {})
    if blueprint_settings:
        final_config.update(blueprint_settings)
        logger.debug(f"Merged BP '{blueprint_class_name}' settings. Keys: {list(blueprint_settings.keys())}")

    # 4. Determine and merge profile settings
    # Priority: CLI > Blueprint Specific > Base Defaults > "default"
    profile_in_bp_settings = blueprint_settings.get("default_profile")
    profile_in_base_defaults = base_config.get("defaults", {}).get("default_profile")
    profile_to_use = profile_override or profile_in_bp_settings or profile_in_base_defaults or "default"
    logger.debug(f"Using profile: '{profile_to_use}'")
    profile_settings = base_config.get("profiles", {}).get(profile_to_use, {})
    if profile_settings:
        final_config.update(profile_settings)
        logger.debug(f"Merged profile '{profile_to_use}'. Keys: {list(profile_settings.keys())}")
    elif profile_to_use != "default" and (profile_override or profile_in_bp_settings or profile_in_base_defaults):
        logger.warning(f"Profile '{profile_to_use}' requested but not found.")

    # 5. Merge CLI overrides (highest priority)
    if cli_config_overrides:
        final_config.update(cli_config_overrides)
        logger.debug(f"Merged CLI overrides. Keys: {list(cli_config_overrides.keys())}")

    # Ensure top-level keys exist
    final_config.setdefault("llm", {})
    final_config.setdefault("mcpServers", {})

    # 6. Substitute environment variables in the final config
    final_config = _substitute_env_vars(final_config)
    logger.debug("Applied final env var substitution.")

    return final_config
