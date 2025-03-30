import os
import typer
import platformdirs
import subprocess
import sys
from pathlib import Path
import importlib.resources as pkg_resources
import swarm # Import the main package to access its resources

# --- Configuration ---
APP_NAME = "swarm"
APP_AUTHOR = "swarm-authors" # Replace if needed

# Use platformdirs for user-specific data, config locations
USER_DATA_DIR = Path(os.getenv("SWARM_USER_DATA_DIR", platformdirs.user_data_dir(APP_NAME, APP_AUTHOR)))
USER_CONFIG_DIR = Path(os.getenv("SWARM_USER_CONFIG_DIR", platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)))

# *** CORRECTED: Define user bin dir as a subdir of user data dir ***
USER_BIN_DIR = Path(os.getenv("SWARM_USER_BIN_DIR", USER_DATA_DIR / "bin"))

# Derived paths
BLUEPRINTS_DIR = USER_DATA_DIR / "blueprints"
INSTALLED_BIN_DIR = USER_BIN_DIR # Keep using this variable name for clarity

# Ensure directories exist
BLUEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
INSTALLED_BIN_DIR.mkdir(parents=True, exist_ok=True) # Ensure the user bin dir is created
USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# --- Typer App ---
app = typer.Typer(
    help="Swarm CLI tool for managing blueprints.",
    add_completion=True # Enable shell completion commands
)

# --- Helper Functions ---
def find_entry_point(blueprint_dir: Path) -> str | None:
    """Placeholder: Finds the main Python script in a blueprint directory."""
    # Improve this logic: Look for a specific file, check pyproject.toml, etc.
    for item in blueprint_dir.glob("*.py"):
        if item.is_file() and not item.name.startswith("_"):
            return item.name
    return None

# --- CLI Commands ---

@app.command()
def install(
    blueprint_name: str = typer.Argument(..., help="Name of the blueprint directory to install."),
    # Add options for specifying source dir if needed later
):
    """
    Install a blueprint by creating a standalone executable using PyInstaller.
    """
    # Decide where to look for the source blueprint: User dir first, then bundled?
    # For now, let's assume it must exist in the user dir for installation
    # TODO: Enhance this to allow installing bundled blueprints directly?
    source_dir = BLUEPRINTS_DIR / blueprint_name
    if not source_dir.is_dir():
        # Could also check bundled blueprints here if desired
        typer.echo(f"Error: Blueprint source directory not found in user directory: {source_dir}", err=True)
        typer.echo("Currently, only blueprints placed in the user directory can be installed.", err=True)
        raise typer.Exit(code=1)

    entry_point = find_entry_point(source_dir)
    if not entry_point:
        typer.echo(f"Error: Could not find entry point script in {source_dir}", err=True)
        raise typer.Exit(code=1)

    entry_point_path = source_dir / entry_point
    output_bin = INSTALLED_BIN_DIR / blueprint_name
    dist_path = USER_DATA_DIR / "dist" # PyInstaller dist path within user data
    build_path = USER_DATA_DIR / "build" # PyInstaller build path within user data

    typer.echo(f"Installing blueprint '{blueprint_name}'...")
    typer.echo(f"  Source: {source_dir}")
    typer.echo(f"  Entry Point: {entry_point}")
    typer.echo(f"  Output Executable: {output_bin}")

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile", # Create a single executable file
        "--name", str(output_bin.name), # Name of the output executable
        "--distpath", str(INSTALLED_BIN_DIR), # Output directory for the executable
        "--workpath", str(build_path), # Directory for temporary build files
        "--specpath", str(USER_DATA_DIR), # Directory for the .spec file
        str(entry_point_path), # The main script to bundle
    ]

    typer.echo(f"Running PyInstaller: {' '.join(map(str, pyinstaller_cmd))}") # Use map(str,...) for Path objects

    try:
        # Use subprocess.run for better control and error handling
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        typer.echo("PyInstaller output:")
        typer.echo(result.stdout)
        typer.echo(f"Successfully installed '{blueprint_name}' to {output_bin}")
    except FileNotFoundError:
        typer.echo("Error: PyInstaller command not found. Is PyInstaller installed?", err=True)
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error during PyInstaller execution (Return Code: {e.returncode}):", err=True)
        typer.echo(e.stderr, err=True)
        typer.echo("Check the output above for details.", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def launch(blueprint_name: str = typer.Argument(..., help="Name of the installed blueprint executable to launch.")):
    """
    Launch a previously installed blueprint executable.
    """
    executable_path = INSTALLED_BIN_DIR / blueprint_name
    if not executable_path.is_file() or not os.access(executable_path, os.X_OK):
        typer.echo(f"Error: Blueprint executable not found or not executable: {executable_path}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Launching '{blueprint_name}' from {executable_path}...")
    try:
        # Execute the blueprint directly
        # Using subprocess.run is generally safer and more flexible than os.execv
        result = subprocess.run([str(executable_path)], capture_output=True, text=True, check=False) # check=False to handle non-zero exits gracefully
        typer.echo(f"--- {blueprint_name} Output ---")
        typer.echo(result.stdout)
        if result.stderr:
            typer.echo("--- Errors/Warnings ---", err=True)
            typer.echo(result.stderr, err=True)
        typer.echo(f"--- '{blueprint_name}' finished (Return Code: {result.returncode}) ---")

    except Exception as e:
        typer.echo(f"Error launching blueprint: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(name="list")
def list_blueprints(
    installed: bool = typer.Option(False, "--installed", "-i", help="List only installed blueprint executables."),
    available: bool = typer.Option(False, "--available", "-a", help="List only available blueprints (source dirs).")
):
    """
    Lists available blueprints (bundled and user-provided) and/or installed executables.
    """
    list_installed = not available or installed
    list_available = not installed or available

    # --- List Installed Blueprints ---
    if list_installed:
        typer.echo(f"--- Installed Blueprints (in {INSTALLED_BIN_DIR}) ---")
        found_installed = False
        if INSTALLED_BIN_DIR.exists():
            try:
                for item in INSTALLED_BIN_DIR.iterdir():
                    # Basic check: is it a file and executable? Refine as needed.
                    if item.is_file() and os.access(item, os.X_OK):
                        typer.echo(f"- {item.name}")
                        found_installed = True
            except OSError as e:
                typer.echo(f"(Warning: Could not read installed directory: {e})", err=True)
        if not found_installed:
            typer.echo("(No installed blueprint executables found)")
        typer.echo("") # Add spacing

    # --- List Available Blueprints (Bundled and User) ---
    if list_available:
        # --- Bundled ---
        typer.echo("--- Bundled Blueprints (installed with package) ---")
        bundled_found = False
        try:
            # Use importlib.resources to access the 'blueprints' directory within the installed 'swarm' package
            bundled_blueprints_path = pkg_resources.files(swarm) / 'blueprints'

            if bundled_blueprints_path.is_dir(): # Check if the directory exists in the package
                for item in bundled_blueprints_path.iterdir():
                    # Check if it's a directory containing an entry point (adapt check as needed)
                    if item.is_dir() and not item.name.startswith("__"): # Skip __pycache__ etc.
                        entry_point = find_entry_point(item) # Use helper, might need refinement
                        if entry_point:
                            typer.echo(f"- {item.name} (entry: {entry_point})")
                            bundled_found = True
        except ModuleNotFoundError:
             typer.echo("(Could not find bundled blueprints - package structure issue?)", err=True)
        except FileNotFoundError: # Can happen if package data wasn't included correctly
             typer.echo("(Could not find bundled blueprints path - package data missing?)", err=True)
        except Exception as e:
            typer.echo(f"(Error accessing bundled blueprints: {e})", err=True)

        if not bundled_found:
            typer.echo("(No bundled blueprints found or accessible)")
        typer.echo("") # Add spacing

        # --- User ---
        typer.echo(f"--- User Blueprints (in {BLUEPRINTS_DIR}) ---")
        user_found = False
        if BLUEPRINTS_DIR.exists() and BLUEPRINTS_DIR.is_dir():
            try:
                for item in BLUEPRINTS_DIR.iterdir():
                    if item.is_dir():
                        entry_point = find_entry_point(item) # Use helper
                        if entry_point:
                            typer.echo(f"- {item.name} (entry: {entry_point})")
                            user_found = True
            except OSError as e:
                typer.echo(f"(Warning: Could not read user blueprints directory: {e})", err=True)

        if not user_found:
            typer.echo("(No user blueprints found)")
        typer.echo("") # Add spacing


# --- Main Execution Guard ---
if __name__ == "__main__":
    app()
