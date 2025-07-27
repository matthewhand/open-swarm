import importlib.resources as pkg_resources
import os
import subprocess
from pathlib import Path

import typer

import swarm  # Import the main package to access its resources
from swarm.core import paths  # Import the new paths module

# Ensure all standard Swarm XDG directories exist
paths.ensure_swarm_directories_exist()

# --- Typer App ---
app = typer.Typer(
    help="Swarm CLI tool for managing blueprints.",
    add_completion=True,  # Enable shell completion commands
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }
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

@app.command(name="install-executable") # Renamed from 'install'
def install_executable(
    blueprint_name: str = typer.Argument(..., help="Name of the blueprint directory to install as an executable."),
    # Add options for specifying source dir if needed later
):
    """
    Install a blueprint by creating a standalone executable using PyInstaller.
    The executable will be placed in the user's binary directory.
    """
    # Decide where to look for the source blueprint: User dir first, then bundled?
    source_dir_user = paths.get_user_blueprints_dir() / blueprint_name
    if source_dir_user.is_dir():
        source_dir = source_dir_user
    else:
        # Fallback to bundled blueprints in the package
        # This path is relative to the package, not XDG user paths
        bundled_base = Path(__file__).resolve().parent.parent / 'blueprints'
        bundled_dir = bundled_base / blueprint_name
        if bundled_dir.is_dir():
            source_dir = bundled_dir
            typer.echo(f"Using bundled blueprint directory: {bundled_dir}")
        else:
            typer.echo(f"Error: Blueprint '{blueprint_name}' not found in user blueprints directory ({paths.get_user_blueprints_dir()}) or bundled blueprints.", err=True)
            raise typer.Exit(code=1)

    entry_point = find_entry_point(source_dir)
    if not entry_point:
        typer.echo(f"Error: Could not find entry point script in {source_dir}", err=True)
        raise typer.Exit(code=1)

    entry_point_path = source_dir / entry_point

    # Using new XDG paths
    output_bin_name = blueprint_name # The name of the executable file
    output_bin_dir = paths.get_user_bin_dir()
    output_bin_path = output_bin_dir / output_bin_name

    # PyInstaller specific paths using XDG cache directory
    pyinstaller_workpath = paths.get_user_cache_dir_for_swarm() / "build" / blueprint_name
    pyinstaller_specpath = paths.get_user_cache_dir_for_swarm() / "specs" # Specs can go in a general specs dir

    # Ensure PyInstaller specific cache subdirectories exist
    pyinstaller_workpath.mkdir(parents=True, exist_ok=True)
    (paths.get_user_cache_dir_for_swarm() / "specs").mkdir(parents=True, exist_ok=True)


    typer.echo(f"Installing blueprint '{blueprint_name}' as executable...")
    typer.echo(f"  Source: {source_dir}")
    typer.echo(f"  Entry Point: {entry_point}")
    typer.echo(f"  Output Executable: {output_bin_path}")

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile", # Create a single executable file
        "--name", str(output_bin_name), # Name of the output executable
        "--distpath", str(output_bin_dir), # Output directory for the executable
        "--workpath", str(pyinstaller_workpath), # Directory for temporary build files
        "--specpath", str(pyinstaller_specpath), # Directory for the .spec file
        str(entry_point_path), # The main script to bundle
    ]

    # In test mode, skip PyInstaller and install a shim to the entry point script
    if os.environ.get('SWARM_TEST_MODE'):
        shim = f"#!/usr/bin/env bash\npython3 {entry_point_path} \"$@\"\n"
        try:
            with open(output_bin_path, 'w') as f:
                f.write(shim)
            os.chmod(output_bin_path, 0o755)
            typer.echo(f"Test-mode shim installed at: {output_bin_path}")
            return
        except Exception as e:
            typer.echo(f"Error installing test-mode shim: {e}", err=True)
            raise typer.Exit(code=1)

    # Production: build with PyInstaller
    typer.echo(f"Running PyInstaller: {' '.join(map(str, pyinstaller_cmd))}")
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        typer.echo("PyInstaller output:")
        typer.echo(result.stdout)
        typer.echo(f"Successfully installed '{blueprint_name}' to {output_bin_path}")
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


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def launch(
    ctx: typer.Context,
    blueprint_name: str = typer.Argument(..., help="Name of the installed blueprint executable to launch."),
    pre: str = typer.Option(None, "--pre", "-p", help="Comma-separated blueprint names to run before main task"),
    listen: str = typer.Option(None, "--listen", "-L", help="Comma-separated blueprint names to invoke on the same inputs"),
    post: str = typer.Option(None, "--post", "-o", help="Comma-separated blueprint names to run after main task"),
):
    """
    Launch a previously installed blueprint executable, forwarding any additional args.
    """
    user_bin_dir = paths.get_user_bin_dir()
    executable_path = user_bin_dir / blueprint_name
    if not executable_path.is_file() or not os.access(executable_path, os.X_OK):
        typer.echo(f"Error: Blueprint executable not found or not executable: {executable_path}", err=True)
        typer.echo(f"Ensure '{blueprint_name}' is installed using 'swarm-cli install-executable {blueprint_name}'.", err=True)
        raise typer.Exit(code=1)

    extra = ctx.args
    # Run pre-hook blueprints
    if pre:
        for bp_pre_name in [bp.strip() for bp in pre.split(',') if bp.strip()]:
            pre_exe_path = user_bin_dir / bp_pre_name
            if pre_exe_path.is_file() and os.access(pre_exe_path, os.X_OK):
                cmd_pre = [str(pre_exe_path)] + extra
                typer.echo(f"Invoking pre-hook '{bp_pre_name}' with: {' '.join(cmd_pre)}")
                subprocess.run(cmd_pre)
            else:
                typer.echo(f"Pre-hook executable '{bp_pre_name}' not found in {user_bin_dir}; skipping.", err=True)

    cmd = [str(executable_path)] + extra
    typer.echo(f"Launching '{blueprint_name}' with: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        typer.echo(f"--- {blueprint_name} Output ---")
        typer.echo(result.stdout)
        if result.stderr:
            typer.echo("--- Errors/Warnings ---", err=True)
            typer.echo(result.stderr, err=True)
        typer.echo(f"--- '{blueprint_name}' finished (Return Code: {result.returncode}) ---")
    except Exception as e:
        typer.echo(f"Error launching blueprint: {e}", err=True)
        raise typer.Exit(code=1)

    # Invoke listener blueprints if configured
    if listen:
        for listener_name in [bp.strip() for bp in listen.split(',') if bp.strip()]:
            listener_exe_path = user_bin_dir / listener_name
            if listener_exe_path.is_file() and os.access(listener_exe_path, os.X_OK):
                listener_cmd = [str(listener_exe_path)] + ctx.args
                typer.echo(f"Invoking listener '{listener_name}' with: {' '.join(listener_cmd)}")
                subprocess.run(listener_cmd)
            else:
                typer.echo(f"Listener executable '{listener_name}' not found in {user_bin_dir}; skipping.", err=True)

    # Run post-hook blueprints
    if post:
        for bp_post_name in [bp.strip() for bp in post.split(',') if bp.strip()]:
            post_exe_path = user_bin_dir / bp_post_name
            if post_exe_path.is_file() and os.access(post_exe_path, os.X_OK):
                cmd_post = [str(post_exe_path)] + ctx.args
                typer.echo(f"Invoking post-hook '{bp_post_name}' with: {' '.join(cmd_post)}")
                subprocess.run(cmd_post)
            else:
                typer.echo(f"Post-hook executable '{bp_post_name}' not found in {user_bin_dir}; skipping.", err=True)


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

    user_bin_dir = paths.get_user_bin_dir()
    user_blueprints_src_dir = paths.get_user_blueprints_dir()

    # --- List Installed Blueprints ---
    if list_installed:
        typer.echo(f"--- Installed Blueprint Executables (in {user_bin_dir}) ---")
        found_installed = False
        if user_bin_dir.exists(): # Directory is ensured by paths.ensure_swarm_directories_exist()
            try:
                for item in user_bin_dir.iterdir():
                    if item.is_file() and os.access(item, os.X_OK):
                        typer.echo(f"- {item.name}")
                        found_installed = True
            except OSError as e:
                typer.echo(f"(Warning: Could not read installed directory: {e})", err=True)
        if not found_installed:
            typer.echo(f"(No installed blueprint executables found in {user_bin_dir})")
            typer.echo("Try 'swarm-cli install-executable <blueprint_name>' or see 'swarm-cli list --available'.")
        typer.echo("")

    # --- List Available Blueprints (Bundled and User) ---
    if list_available:
        # --- Bundled ---
        typer.echo("--- Bundled Blueprints (available from package) ---")
        bundled_found = False
        try:
            bundled_blueprints_path = pkg_resources.files(swarm) / 'blueprints'
            if bundled_blueprints_path.is_dir():
                for item in bundled_blueprints_path.iterdir():
                    if item.is_dir() and not item.name.startswith("__"):
                        entry_point = find_entry_point(item)
                        if entry_point:
                            typer.echo(f"- {item.name} (entry: {entry_point})")
                            bundled_found = True
        except Exception as e: # Catching a broader exception for pkg_resources issues
            typer.echo(f"(Error accessing bundled blueprints: {e})", err=True)

        if not bundled_found:
            typer.echo("(No bundled blueprints found or accessible)")
        typer.echo("")

        # --- User ---
        typer.echo(f"--- User Blueprint Sources (in {user_blueprints_src_dir}) ---")
        user_found = False
        # user_blueprints_src_dir is ensured by paths.ensure_swarm_directories_exist()
        if user_blueprints_src_dir.is_dir():
            try:
                for item in user_blueprints_src_dir.iterdir():
                    if item.is_dir():
                        entry_point = find_entry_point(item)
                        if entry_point:
                            typer.echo(f"- {item.name} (entry: {entry_point})")
                            user_found = True
            except OSError as e:
                typer.echo(f"(Warning: Could not read user blueprints directory: {e})", err=True)

        if not user_found:
            typer.echo(f"(No user blueprint sources found in {user_blueprints_src_dir})")
            typer.echo("You can add blueprints by copying their source folders to this directory.")
        typer.echo("")


# --- Main Execution Guard ---
if __name__ == "__main__":
    app()
