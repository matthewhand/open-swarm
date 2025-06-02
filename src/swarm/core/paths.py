import platformdirs
from pathlib import Path
import sys # Import sys module for platform checking

APP_NAME = "swarm"
APP_AUTHOR = "OpenSwarm" # Using OpenSwarm as author for platformdirs

def get_user_data_dir_for_swarm() -> Path:
    """
    Returns the user-specific data directory for swarm.
    Example: ~/.local/share/swarm/ on Linux.
    """
    return Path(platformdirs.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_user_blueprints_dir() -> Path:
    """
    Returns the directory where user-installed blueprint sources are stored.
    Example: ~/.local/share/swarm/blueprints/
    """
    return get_user_data_dir_for_swarm() / "blueprints"

def get_user_bin_dir() -> Path:
    """
    Returns the user-specific binary directory, typically in the user's PATH.
    Example: ~/.local/bin/ on Linux.
    For Windows, this might point to a location like %APPDATA%\\swarm\\bin
    as a fallback if a more standard user script directory isn't easily determined
    or guaranteed to be in PATH by platformdirs.
    """
    # Use sys.platform to check the operating system
    if sys.platform == "win32":
        # For Windows, platformdirs.user_data_dir() often points to APPDATA.
        # We'll create a 'bin' subdirectory within our app's user data directory.
        # Users might need to add this to their PATH manually.
        # An alternative could be platformdirs.user_scripts_dir(appname=APP_NAME, appauthor=APP_AUTHOR)
        # but that can vary. Sticking to a subdir of user_data_dir for consistency.
        return get_user_data_dir_for_swarm() / "bin"
    else:
        # For non-Windows systems (Linux, macOS), ~/.local/bin is a strong convention.
        # platformdirs.user_bin_dir() could also be used, but it might resolve to
        # different paths on different Unix-like systems. ~/.local/bin is common.
        return Path.home() / ".local" / "bin"

def get_user_cache_dir_for_swarm() -> Path:
    """
    Returns the user-specific cache directory for swarm.
    Example: ~/.cache/swarm/ on Linux.
    """
    return Path(platformdirs.user_cache_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_user_config_dir_for_swarm() -> Path:
    """
    Returns the user-specific config directory for swarm.
    Example: ~/.config/swarm/ on Linux.
    """
    return Path(platformdirs.user_config_dir(appname=APP_NAME, appauthor=APP_AUTHOR))

def get_swarm_config_file(config_filename: str = "config.yaml") -> Path:
    """
    Returns the full path to the swarm configuration file.
    Defaults to config.yaml within the user config directory.
    """
    return get_user_config_dir_for_swarm() / config_filename

def ensure_swarm_directories_exist():
    """
    Ensures all standard Swarm XDG directories exist.
    Call this early in application startup.
    """
    get_user_data_dir_for_swarm().mkdir(parents=True, exist_ok=True)
    get_user_blueprints_dir().mkdir(parents=True, exist_ok=True)
    get_user_bin_dir().mkdir(parents=True, exist_ok=True) # Ensure bin dir also exists
    get_user_cache_dir_for_swarm().mkdir(parents=True, exist_ok=True)
    get_user_config_dir_for_swarm().mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print(f"Current sys.platform: {sys.platform}")
    print(f"User Data Dir:      {get_user_data_dir_for_swarm()}")
    print(f"User Blueprints Dir: {get_user_blueprints_dir()}")
    print(f"User Bin Dir:       {get_user_bin_dir()}")
    print(f"User Cache Dir:     {get_user_cache_dir_for_swarm()}")
    print(f"User Config Dir:    {get_user_config_dir_for_swarm()}")
    print(f"Swarm Config File:  {get_swarm_config_file()}")
    print("\nEnsuring directories exist...")
    ensure_swarm_directories_exist()
    print("Done.")
