import json
import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILENAME = "swarm_config.json"

# --- find_config_file, load_config, save_config, validate_config, get_profile_from_config, _substitute_env_vars_recursive ---
# (Keep these functions as they were)
def find_config_file( specific_path: Optional[str]=None, start_dir: Optional[Path]=None, default_dir: Optional[Path]=None,) -> Optional[Path]:
    if specific_path: p=Path(specific_path); return p.resolve() if p.is_file() else logger.warning(f"Specified config path DNE: {specific_path}") or None # Fall through
    if start_dir:
        current=start_dir.resolve()
        while current != current.parent:
            if (cp := current / DEFAULT_CONFIG_FILENAME).is_file(): logger.debug(f"Found config upwards: {cp}"); return cp.resolve()
            current = current.parent
        if (cp := current / DEFAULT_CONFIG_FILENAME).is_file(): logger.debug(f"Found config at root: {cp}"); return cp.resolve()
    if default_dir and (cp := default_dir.resolve() / DEFAULT_CONFIG_FILENAME).is_file(): logger.debug(f"Found config default: {cp}"); return cp.resolve()
    cwd=Path.cwd();
    if start_dir is None or cwd != start_dir.resolve():
        if (cp := cwd / DEFAULT_CONFIG_FILENAME).is_file(): logger.debug(f"Found config cwd: {cp}"); return cp.resolve()
    logger.debug(f"Config '{DEFAULT_CONFIG_FILENAME}' not found."); return None

def load_config(config_path: Path) -> Dict[str, Any]:
    logger.debug(f"Loading config from {config_path}")
    try:
        with open(config_path, 'r') as f: config = json.load(f)
        logger.info(f"Loaded config from {config_path}"); validate_config(config); return config
    except FileNotFoundError: logger.error(f"Config DNE: {config_path}"); raise
    except json.JSONDecodeError as e: logger.error(f"JSON error {config_path}: {e}"); raise ValueError(f"Invalid JSON: {config_path}") from e
    except Exception as e: logger.error(f"Load error {config_path}: {e}"); raise

def save_config(config: Dict[str, Any], config_path: Path):
    logger.info(f"Saving config to {config_path}")
    try: config_path.parent.mkdir(parents=True,exist_ok=True); f = config_path.open('w'); json.dump(config, f, indent=4); f.close(); logger.debug("Save OK.")
    except Exception as e: logger.error(f"Save failed {config_path}: {e}", exc_info=True); raise

def validate_config(config: Dict[str, Any]):
    logger.debug("Validating config structure...")
    if "llm" not in config or not isinstance(config["llm"],dict): raise ValueError("Config 'llm' section missing/malformed.")
    for name, prof in config.get("llm",{}).items():
        if not isinstance(prof,dict): raise ValueError(f"LLM profile '{name}' not dict.")
    logger.debug("Config basic structure OK.")

def get_profile_from_config(config: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
    profile_data = config.get("llm", {}).get(profile_name)
    if profile_data is None: raise ValueError(f"LLM profile '{profile_name}' not found.")
    if not isinstance(profile_data, dict): raise ValueError(f"LLM profile '{profile_name}' not dict.")
    return _substitute_env_vars_recursive(profile_data)

def _substitute_env_vars_recursive(data: Any) -> Any:
    if isinstance(data,dict): return {k:_substitute_env_vars_recursive(v) for k,v in data.items()}
    if isinstance(data,list): return [_substitute_env_vars_recursive(i) for i in data]
    if isinstance(data,str): return os.path.expandvars(data)
    return data

def create_default_config(config_path: Path):
    """Creates a default configuration file with valid JSON."""
    default_config = {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "${OPENAI_API_KEY}",
                "base_url": None,
                "description": "Default OpenAI profile. Requires OPENAI_API_KEY env var."
            },
            "ollama_example": {
                 "provider": "ollama",
                 "model": "llama3",
                 "api_key": "ollama", # Usually not needed
                 "base_url": "http://localhost:11434",
                 "description": "Example for local Ollama Llama 3 model."
            }
        },
        "agents": {},
        "settings": {
             "default_markdown_output": True
        }
    }
    logger.info(f"Creating default configuration file at {config_path}")
    try:
        save_config(default_config, config_path) # Use save_config to write valid JSON
        logger.debug("Default configuration file created successfully.")
    except Exception as e:
        logger.error(f"Failed to create default config file at {config_path}: {e}", exc_info=True)
        raise

