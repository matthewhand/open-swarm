import os
import sys  # Import sys module for platform checking
from pathlib import Path

import platformdirs

APP_NAME = "swarm"
APP_AUTHOR = "OpenSwarm" # Using OpenSwarm as author for platformdirs

def get_user_data_dir_for_swarm() -> Path:
    """
    Returns the user-specific data directory for swarm.
    Example: ~/.local/share/OpenSwarm/swarm/ (or similar based on APP_AUTHOR)
    """
    # Allow override for testing/sandboxes
    override = os.environ.get("SWARM_USER_DATA_DIR")
    if override:
        return Path(override)
    return Path(platformdirs.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_user_blueprints_dir() -> Path:
    """
    Returns the directory where user-installed blueprint sources are stored.
    Example: ~/.local/share/OpenSwarm/swarm/blueprints/
    """
    return get_user_data_dir_for_swarm() / "blueprints"

def get_user_bin_dir() -> Path:
    """
    Returns the user-specific directory for Swarm's managed executables/launchers.
    This will be a 'bin' subdirectory within the application's user data directory.
    Example: ~/.local/share/OpenSwarm/swarm/bin/ on Linux
             %APPDATA%\\OpenSwarm\\swarm\\bin on Windows
    Users may need to add this location to their PATH if they wish to run these
    executables directly from any terminal location.
    """
    return get_user_data_dir_for_swarm() / "bin"

def get_user_cache_dir_for_swarm() -> Path:
    """
    Returns the user-specific cache directory for swarm.
    Example: ~/.cache/OpenSwarm/swarm/ on Linux.
    """
    return Path(platformdirs.user_cache_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_user_config_dir_for_swarm() -> Path:
    """
    Returns the user-specific config directory for swarm.
    Example: ~/.config/OpenSwarm/swarm/ on Linux.
    """
    return Path(platformdirs.user_config_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_swarm_config_file(config_filename: str = "config.yaml") -> Path:
    """
    Returns the full path to the swarm configuration file.
    Defaults to config.yaml within the user config directory.
    Uses basename only to prevent path traversal.
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
