import argparse
import shutil
import zipfile
from pathlib import Path

from swarm.core import paths  # Assuming paths.py is accessible


def execute(args: argparse.Namespace):
    """
    Installs a blueprint's source code to the user's blueprint directory.
    """
    print(f"Executing 'install source' for blueprint: {args.name_or_path}")
    print(f"Overwrite: {args.overwrite}")

    source_path_str = args.name_or_path
    source_path = Path(source_path_str).resolve()
    user_blueprints_dir = paths.get_user_blueprints_dir()

    if not source_path.exists():
        print(f"Error: Source path '{source_path}' does not exist.")
        return

    # Determine blueprint name (either from source dir/file name or a --name arg if added later)
    # For now, let's use the source's name.
    # If source_path is a file like 'my_bp.py', blueprint_name = 'my_bp'
    # If source_path is a dir like './my_blueprint_project', blueprint_name = 'my_blueprint_project'
    blueprint_name = source_path.stem if source_path.is_file() else source_path.name

    import re

    # Validate blueprint_name for directory safety
    invalid_pattern = re.compile(r'[\\/:*?"<>|]')
    if invalid_pattern.search(blueprint_name):
        print(f"Error: Invalid blueprint name '{blueprint_name}'. Directory names cannot contain characters: / \\ : * ? \" < > |")
        return

    # Also check for absolute paths or parent directory references
    if blueprint_name.startswith('/') or blueprint_name.startswith('..') or '/' in blueprint_name or '\\' in blueprint_name:
        print(f"Error: Invalid blueprint name '{blueprint_name}'. Cannot contain path separators or parent references.")
        return

    target_blueprint_dir = user_blueprints_dir / blueprint_name

    print(f"Source: {source_path}")
    print(f"Target directory: {target_blueprint_dir}")

    if target_blueprint_dir.exists():
        if args.overwrite:
            print(f"Target '{target_blueprint_dir}' exists. Overwriting as per --overwrite flag.")
            # Be careful with rmtree; ensure it's what the user wants.
            # For a directory, remove it first.
            if target_blueprint_dir.is_dir():
                shutil.rmtree(target_blueprint_dir)
            else: # It's a file, just remove it
                target_blueprint_dir.unlink()
        else:
            print(f"Error: Target '{target_blueprint_dir}' already exists. Use --overwrite to replace it.")
            return

    try:
        # Ensure user_blueprints_dir exists (though paths.ensure_swarm_directories_exist() should handle it)
        user_blueprints_dir.mkdir(parents=True, exist_ok=True)

        if source_path.is_dir():
            # Copy directory
            shutil.copytree(source_path, target_blueprint_dir)
            print(f"Blueprint directory '{source_path.name}' copied to '{target_blueprint_dir}'")
        elif source_path.is_file():
            if source_path.suffix == '.zip':
                # Extract .zip file to target directory
                target_blueprint_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(source_path, 'r') as zip_ref:
                    zip_ref.extractall(target_blueprint_dir)
                print(f"Blueprint archive '{source_path.name}' extracted to '{target_blueprint_dir}'")
            else:
                # Handle other files (like .py)
                target_blueprint_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_blueprint_dir / source_path.name)
                print(f"Blueprint file '{source_path.name}' copied to '{target_blueprint_dir / source_path.name}'")
        # elif source_path.is_file() and source_path.suffix == '.zip':
        #     print(f"Extracting blueprint from zip file '{source_path.name}' to '{target_blueprint_dir}'")
        #     target_blueprint_dir.mkdir(parents=True, exist_ok=True)
        #     with zipfile.ZipFile(source_path, 'r') as zip_ref:
        #         zip_ref.extractall(target_blueprint_dir)
        else:
            print(f"Error: Source path '{source_path}' is not a recognized type (directory, .py file). ZIP support pending.")
            return

        print(f"Blueprint '{blueprint_name}' installed successfully to your user blueprints directory.")
        print(f"You can now try to compile it using 'swarm-cli compile {blueprint_name}' (if that command exists)")
        print(f"or use it if other commands load from '{user_blueprints_dir}'.")

    except Exception as e:
        print(f"Error during installation: {e}")

def register_args(parser: argparse.ArgumentParser):
    """
    Registers arguments for the 'install' (source) command.
    """
    parser.add_argument(
        "name_or_path",
        help="Name of a prebuilt blueprint, or path to a blueprint source file (.py, .zip) or directory."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the blueprint if it already exists in the user's blueprints directory."
    )
    # Add other options like --name if needed
