import typer
import subprocess
import platformdirs
from pathlib import Path
import logging
import os
import stat # To check execute permissions
import sys
from typing import Optional, List # <<< ADD THIS IMPORT <<<

# Try importing PyInstaller; fail gracefully if not installed unless installing
try:
    import PyInstaller.__main__
    PYINSTALLER_AVAILABLE = True
except ImportError:
    PYINSTALLER_AVAILABLE = False

app = typer.Typer()

# --- Configuration ---
# Use environment variables set in test fixtures or real environment
APP_NAME = "swarm"
APP_AUTHOR = "swarm-authors" # Replace if needed

USER_DATA_DIR = Path(os.getenv("SWARM_USER_DATA_DIR", platformdirs.user_data_dir(APP_NAME, APP_AUTHOR)))
USER_CONFIG_DIR = Path(os.getenv("SWARM_USER_CONFIG_DIR", platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)))
USER_CACHE_DIR = Path(os.getenv("SWARM_USER_CACHE_DIR", platformdirs.user_cache_dir(APP_NAME, APP_AUTHOR)))

# Define standard subdirectories
BLUEPRINTS_DIR = USER_DATA_DIR / "blueprints"
BIN_DIR = USER_DATA_DIR / "bin"
CONFIG_FILE_PATH = USER_CONFIG_DIR / "swarm_config.json" # Example config path
BUILD_CACHE_DIR = USER_CACHE_DIR / "build"


# Ensure base directories exist
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
USER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
BLUEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)
BUILD_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# --- Logging ---
# Basic logging configuration
log_level = logging.INFO
log_format = "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
logging.basicConfig(level=log_level, format=log_format)
logger = logging.getLogger(__name__)


# --- Helper Functions ---
def find_blueprint_entrypoint(blueprint_name: str) -> Optional[Path]: # Use Optional here too
    """Finds the main Python file for a blueprint."""
    bp_dir = BLUEPRINTS_DIR / blueprint_name
    if not bp_dir.is_dir():
        return None
    # Look for common entrypoint names
    possible_files = [
        bp_dir / f"blueprint_{blueprint_name}.py",
        bp_dir / "main.py",
        bp_dir / "blueprint.py",
        bp_dir / f"{blueprint_name}.py",
    ]
    for file in possible_files:
        if file.is_file():
            return file
    # Fallback: Find the first .py file? (Might be risky)
    try:
        first_py = next(bp_dir.glob('*.py'))
        return first_py
    except StopIteration:
        return None

def get_executable_path(blueprint_name: str, bin_dir_override: Optional[Path] = None) -> Path:
    """Gets the expected path for the blueprint's executable."""
    target_bin_dir = bin_dir_override if bin_dir_override else BIN_DIR
    return target_bin_dir / blueprint_name


# --- CLI Commands ---

@app.command()
def install(
    blueprint_name: str = typer.Argument(..., help="Name of the blueprint directory."),
    bin_dir: Optional[Path] = typer.Option(None, "--bin-dir", help=f"Override default install location ({BIN_DIR})."), # Use Optional hint
    force: bool = typer.Option(False, "-f", "--force", help="Force rebuild even if executable exists."),
):
    """Install a blueprint by creating a standalone executable using PyInstaller."""
    if not PYINSTALLER_AVAILABLE:
        logger.error("PyInstaller is not installed. Cannot build executable.")
        logger.error("Please install it: pip install pyinstaller")
        raise typer.Exit(code=1)

    logger.info(f"Attempting to install blueprint: {blueprint_name}")
    entrypoint = find_blueprint_entrypoint(blueprint_name)
    if not entrypoint:
        # Ensure stderr is used for user-facing errors in CLI
        typer.echo(f"Error: Blueprint directory or entrypoint file not found for '{blueprint_name}' in {BLUEPRINTS_DIR}", err=True)
        typer.echo(f"Searched in: {BLUEPRINTS_DIR / blueprint_name}", err=True)
        raise typer.Exit(code=1) # <<< EXIT HERE <<<

    target_bin_dir = bin_dir if bin_dir else BIN_DIR
    target_bin_dir.mkdir(parents=True, exist_ok=True) # Ensure target bin dir exists
    executable_path = get_executable_path(blueprint_name, target_bin_dir)

    if executable_path.exists() and not force:
        typer.echo(f"Executable already exists at {executable_path}. Use --force to rebuild.")
        return # Success, already installed

    logger.info(f"Installing: {entrypoint}")
    logger.info(f"Building executable for '{blueprint_name}'...")
    logger.info(f"Build cache: {BUILD_CACHE_DIR}")

    pyinstaller_args = [
        '--name', blueprint_name,
        '--onefile',
        '--distpath', str(target_bin_dir),
        '--workpath', str(BUILD_CACHE_DIR / "build"), # Build workspace
        '--specpath', str(BUILD_CACHE_DIR), # Where to write .spec file
        # Add src directory to python path for imports
        '--paths', str(Path(__file__).parent.parent.parent), # Assuming src is parent of swarm/extensions/launchers
        # Add blueprint's own directory for relative imports within the blueprint
        '--paths', str(entrypoint.parent),
        '--log-level', 'INFO', # PyInstaller log level
        str(entrypoint), # The script to bundle
    ]

    logger.debug(f"Running: pyinstaller {' '.join(pyinstaller_args)}")
    try:
        # Run PyInstaller
        PyInstaller.__main__.run(pyinstaller_args)
        typer.echo(f"Built: {executable_path}") # Use typer.echo for user output
        # Check execute permissions (important on Linux/macOS)
        if not os.access(executable_path, os.X_OK):
             logger.warning(f"Executable at {executable_path} may not have execute permissions. Attempting chmod +x.")
             try:
                 current_permissions = stat.S_IMODE(os.stat(executable_path).st_mode)
                 os.chmod(executable_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
             except Exception as chmod_err:
                 logger.error(f"Failed to set execute permissions: {chmod_err}")

        # Display PATH warning if custom bin_dir used or default isn't typically in PATH
        if str(target_bin_dir) not in os.environ.get("PATH", ""):
             typer.echo("---", err=True) # Use typer.echo(err=True) for warnings
             typer.echo(f"PATH WARNING: '{target_bin_dir}' not in PATH. Add manually (e.g., export PATH=\"$PATH:{target_bin_dir}\")", err=True)
             typer.echo("---", err=True)

    except Exception as e:
        typer.echo(f"Error: PyInstaller failed: {e}", err=True)
        logger.error(f"PyInstaller failed details:", exc_info=True) # Log full traceback
        raise typer.Exit(code=1)


@app.command()
def launch(
    blueprint_name: str = typer.Argument(..., help="Name of the installed blueprint to launch."),
    args: List[str] = typer.Argument(None, help="Arguments to pass to the blueprint executable."),
):
    """Launch a previously installed blueprint executable."""
    executable_path = get_executable_path(blueprint_name)
    if not executable_path.is_file():
        typer.echo(f"Error: Executable for blueprint '{blueprint_name}' not found at {executable_path}.", err=True)
        typer.echo("Please install it first using: swarm-cli install <blueprint_name>", err=True)
        raise typer.Exit(code=1)

    # Check for execute permission before trying to run
    if not os.access(executable_path, os.X_OK):
        typer.echo(f"Error: Executable at {executable_path} does not have execute permissions.", err=True)
        raise typer.Exit(code=1)


    cmd = [str(executable_path)] + (args if args else [])
    logger.info(f"Launching: {' '.join(cmd)}")
    try:
        # Use subprocess.run, stream output potentially?
        # For now, run and capture, then print. Consider streaming for long-running blueprints.
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate() # Wait for completion

        logger.info(f"Blueprint '{blueprint_name}' finished with code {process.returncode}.")
        if stdout:
             typer.echo("--- Blueprint STDOUT ---")
             typer.echo(stdout)
             typer.echo("------------------------")
        if stderr:
             typer.echo("--- Blueprint STDERR ---", err=True)
             typer.echo(stderr, err=True)
             typer.echo("------------------------", err=True)

        if process.returncode != 0:
             raise typer.Exit(code=process.returncode)

    except FileNotFoundError:
         # Should be caught by earlier check, but belt-and-suspenders
         typer.echo(f"Error: Executable not found at {executable_path}", err=True)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An unexpected error occurred during launch: {e}", err=True)
        logger.error(f"Launch exception details:", exc_info=True)
        raise typer.Exit(code=1)


@app.command(name="list") # Explicitly name the command "list"
def list_blueprints(
    installed: bool = typer.Option(False, "--installed", "-i", help="List only installed blueprint executables."),
    available: bool = typer.Option(False, "--available", "-a", help="List only available blueprints (source dirs).")
):
    """Lists available blueprints in the blueprints directory and/or installed executables."""

    list_installed = installed or not (installed or available) # Default show installed if no flags
    list_available = available or not (installed or available) # Default show available if no flags

    if list_available:
        typer.echo(f"--- Available Blueprints (in {BLUEPRINTS_DIR}) ---")
        found_available = False
        # Sort items for consistent output
        items = sorted(BLUEPRINTS_DIR.iterdir(), key=lambda p: p.name)
        for item in items:
            if item.is_dir():
                 entrypoint = find_blueprint_entrypoint(item.name)
                 status = f"(entry: {entrypoint.name})" if entrypoint else "(No entrypoint found!)"
                 typer.echo(f"- {item.name} {status}")
                 found_available = True
        if not found_available:
             typer.echo("(No blueprint directories found)")

    if list_installed:
        typer.echo(f"\n--- Installed Blueprints (in {BIN_DIR}) ---")
        found_installed = False
        # Sort items for consistent output
        items = sorted(BIN_DIR.iterdir(), key=lambda p: p.name)
        for item in items:
             # Check if it's a file and executable (on POSIX systems)
             is_executable = item.is_file() and os.access(item, os.X_OK)
             if is_executable:
                 typer.echo(f"- {item.name}")
                 found_installed = True
        if not found_installed:
             typer.echo("(No installed blueprint executables found)")

if __name__ == "__main__":
    app()
