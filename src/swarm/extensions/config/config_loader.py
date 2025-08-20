import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILENAME = "swarm_config.json"

def _hint(msg: str) -> str:
    """Format a concise, actionable hint for CLI surfaces."""
    return f"[hint] {msg}"

def _xdg_config_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "swarm" / DEFAULT_CONFIG_FILENAME

def find_config_file(
    specific_path: str | None = None,
    start_dir: Path | None = None,
    default_dir: Path | None = None,
) -> Path | None:
    """
    Locate swarm_config.json using precedence:
      1) XDG (~/.config/swarm/swarm_config.json)
      2) User-specified path
      3) Upwards search from start_dir
      4) default_dir/swarm_config.json
      5) CWD/swarm_config.json
    Logs actionable hints on common mistakes.
    """
    # 1. XDG config path
    xdg_config = _xdg_config_path()
    if xdg_config.is_file():
        logger.debug(f"Found config XDG: {xdg_config}")
        return xdg_config.resolve()

    # 2. User-specified path
    if specific_path:
        p = Path(specific_path)
        if p.is_file():
            return p.resolve()
        logger.warning(
            f"Specified config path does not exist: {specific_path} | "
            + _hint("Create a default config with: swarm-cli config init --path "
                    f"{specific_path}")
        )
        # Fall through

    # 3. Upwards from start_dir
    if start_dir:
        current = start_dir.resolve()
        while current != current.parent:
            cp = current / DEFAULT_CONFIG_FILENAME
            if cp.is_file():
                logger.debug(f"Found config upwards: {cp}")
                return cp.resolve()
            current = current.parent
        cp = current / DEFAULT_CONFIG_FILENAME
        if cp.is_file():
            logger.debug(f"Found config at root: {cp}")
            return cp.resolve()

    # 4. Default dir
    if default_dir:
        cp = default_dir.resolve() / DEFAULT_CONFIG_FILENAME
        if cp.is_file():
            logger.debug(f"Found config default: {cp}")
            return cp.resolve()

    # 5. CWD
    cwd = Path.cwd()
    if start_dir is None or cwd != start_dir.resolve():
        cp = cwd / DEFAULT_CONFIG_FILENAME
        if cp.is_file():
            logger.debug(f"Found config cwd: {cp}")
            return cp.resolve()

    logger.debug(f"Config '{DEFAULT_CONFIG_FILENAME}' not found.")
    return None

def load_config(config_path: Path) -> dict[str, Any]:
    logger.debug(f"Loading config from {config_path}")
    try:
        with open(config_path) as f:
            config = json.load(f)
        logger.info(f"Loaded config from {config_path}")
        validate_config(config)
        return config
    except FileNotFoundError:
        logger.error(
            f"Config not found: {config_path} | "
            + _hint("Initialize a default config with: swarm-cli config init"
                    f"{' --path ' + str(config_path) if config_path else ''}")
        )
        raise
    except json.JSONDecodeError as e:
        logger.error(
            f"Invalid JSON in {config_path}: {e} | "
            + _hint("Fix the file or recreate it: mv "
                    f"{config_path} {config_path}.bak && swarm-cli config init")
        )
        raise ValueError(f"Invalid JSON: {config_path}") from e
    except Exception as e:
        logger.error(f"Load error {config_path}: {e}", exc_info=True)
        raise

def save_config(config: dict[str, Any], config_path: Path):
    logger.info(f"Saving config to {config_path}")
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open('w') as f:
            json.dump(config, f, indent=4)
        logger.debug("Save OK.")
    except Exception as e:
        logger.error(f"Save failed {config_path}: {e}", exc_info=True)
        raise

def validate_config(config: dict[str, Any]):
    logger.debug("Validating config structure...")
    if "llm" not in config or not isinstance(config["llm"], dict):
        raise ValueError(
            "Config 'llm' section missing/malformed. "
            + _hint("Use: swarm-cli config add --section llm --name default --json "
                    "'{\"provider\":\"openai\",\"model\":\"gpt-4o\",\"api_key\":\"${OPENAI_API_KEY}\"}'")
        )
    for name, prof in config.get("llm", {}).items():
        if not isinstance(prof, dict):
            raise ValueError(f"LLM profile '{name}' not dict.")
    logger.debug("Config basic structure OK.")

def get_profile_from_config(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    profile_data = config.get("llm", {}).get(profile_name)
    if profile_data is None:
        raise ValueError(
            f"LLM profile '{profile_name}' not found. "
            + _hint("List profiles or add one: swarm-cli config list; "
                    "swarm-cli config add --section llm --name default --json '{...}'")
        )
    if not isinstance(profile_data, dict):
        raise ValueError(f"LLM profile '{profile_name}' not dict.")
    return _substitute_env_vars_recursive(profile_data)

def _substitute_env_vars_recursive(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _substitute_env_vars_recursive(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_substitute_env_vars_recursive(i) for i in data]
    if isinstance(data, str):
        return os.path.expandvars(data)
    return data

def _substitute_env_vars(data: Any) -> Any:
    """Public API: Recursively substitute environment variables in dict, list, str."""
    return _substitute_env_vars_recursive(data)

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
                "api_key": "ollama",  # Usually not needed
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
        save_config(default_config, config_path)  # Use save_config to write valid JSON
        logger.debug("Default configuration file created successfully.")
        # Emit a friendly post-create hint to guide the user
        logger.warning(
            _hint("Set your API key: export OPENAI_API_KEY=sk-... "
                  "or save to secrets file: echo 'OPENAI_API_KEY=sk-...' >> ~/.config/swarm/.env")
        )
    except Exception as e:
        logger.error(f"Failed to create default config file at {config_path}: {e}", exc_info=True)
        raise
