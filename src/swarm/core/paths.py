import os
import sys  # Import sys module for platform checking
from pathlib import Path

import platformdirs

APP_NAME = "swarm"
APP_AUTHOR = "OpenSwarm" # Using OpenSwarm as author for platformdirs

def get_user_data_dir_for_swarm() -> Path:
    """
    User data directory for swarm.

    On Linux XDG this is typically ``~/.local/share/swarm/`` (platformdirs
    ignores ``appauthor`` on Unix). Override with ``SWARM_USER_DATA_DIR``.
    The open-swarm-oracle unit also pins ``SWARM_RESPONSES_DIR`` under this tree.
    """
    # Allow override for testing/sandboxes
    override = os.environ.get("SWARM_USER_DATA_DIR")
    if override:
        return Path(override)
    return Path(platformdirs.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_user_blueprints_dir() -> Path:
    """User-installed blueprint sources: ``~/.local/share/swarm/blueprints/``."""
    return get_user_data_dir_for_swarm() / "blueprints"

def get_user_bin_dir() -> Path:
    """
    Managed launcher scripts: ``~/.local/share/swarm/bin/`` on Linux.

    Users may need to add this location to PATH to run launchers directly.
    """
    return get_user_data_dir_for_swarm() / "bin"

def get_user_cache_dir_for_swarm() -> Path:
    """User cache directory: ``~/.cache/swarm/`` on Linux."""
    return Path(platformdirs.user_cache_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_user_config_dir_for_swarm() -> Path:
    """
    User config directory: ``~/.config/swarm/`` on Linux.

    Live operator files: ``swarm_config.json``, ``.env``, ``teams.json``,
    ``blueprint_library.json``. The oracle unit pins
    ``SWARM_CONFIG_PATH=$HOME/.config/swarm/swarm_config.json``.
    """
    return Path(platformdirs.user_config_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_swarm_config_file(config_filename: str = "config.yaml") -> Path:
    """
    Path under the user config dir (basename only — no path traversal).

    Prefer ``swarm_config.json`` via ``SWARM_CONFIG_PATH`` / AppConfig loaders;
    this helper's default name is historical (``config.yaml``).
    """
    config_dir = get_user_config_dir_for_swarm()
    safe_filename = Path(config_filename).name  # Strip any path components
    return config_dir / safe_filename

def get_project_root_dir() -> Path:
    """
    Returns the project root directory.
    This assumes the script is located at <project_root>/src/swarm/core/paths.py.
    Useful for development, testing, or accessing project-relative resources.
    """
    return Path(__file__).resolve().parent.parent.parent.parent

def ensure_swarm_directories_exist():
    """
    Ensures all standard Swarm XDG directories and the user bin directory exist.
    Call this early in application startup.
    """
    get_user_data_dir_for_swarm().mkdir(parents=True, exist_ok=True)
    get_user_blueprints_dir().mkdir(parents=True, exist_ok=True)
    get_user_bin_dir().mkdir(parents=True, exist_ok=True) # Ensure bin dir also exists
    get_user_cache_dir_for_swarm().mkdir(parents=True, exist_ok=True)
    get_user_config_dir_for_swarm().mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print(f"Current sys.platform: {sys.platform}")
    print(f"Project Root Dir:   {get_project_root_dir()}")
    print(f"User Data Dir:      {get_user_data_dir_for_swarm()}")
    print(f"User Blueprints Dir: {get_user_blueprints_dir()}")
    print(f"User Bin Dir:       {get_user_bin_dir()}")
    print(f"User Cache Dir:     {get_user_cache_dir_for_swarm()}")
    print(f"User Config Dir:    {get_user_config_dir_for_swarm()}")
    print(f"Swarm Config File:  {get_swarm_config_file()}")
    print("\nEnsuring directories exist...")
    ensure_swarm_directories_exist()
    print("All listed directories should now exist.")
    print("Done.")
