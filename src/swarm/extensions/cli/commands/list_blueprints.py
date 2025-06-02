"""
Command: list_blueprints
Description: Lists blueprints. By default, lists user-installed blueprint sources
             and their compiled status. Use --available to list blueprints
             available for installation from the package or development source.
"""

import argparse
import importlib.util
from pathlib import Path
import logging
import os # For os.access
from swarm.core.blueprint_discovery import discover_blueprints, DiscoveredBlueprintInfo
from swarm.core import paths # Import our XDG paths module

logger = logging.getLogger(__name__)

# Metadata for dynamic registration (if used by your CLI framework)
description = "Lists user-installed blueprints and their status, or available blueprints."
usage = "list [--available]"

def list_available_blueprints() -> dict[str, DiscoveredBlueprintInfo]:
    """
    Lists blueprints available from the package or development source tree.
    This was the original behavior of list_blueprints_from_source.
    """
    blueprints_source_dir = None
    source_location_description = "unknown"

    # Attempt 1: Try to find blueprints relative to an installed 'swarm' package
    try:
        swarm_spec = importlib.util.find_spec("swarm")
        if swarm_spec and swarm_spec.origin:
            installed_pkg_dir = Path(swarm_spec.origin).parent
            candidate_dir = installed_pkg_dir / "blueprints"
            logger.debug(f"Checking for installed package blueprints at: {candidate_dir!r}")
            if candidate_dir.is_dir():
                blueprints_source_dir = candidate_dir
                source_location_description = f"installed package location ({blueprints_source_dir})"
            else:
                logger.debug(f"Directory {candidate_dir} not found or not a directory.")
        else:
            logger.debug("'swarm' package spec not found. Cannot determine installed package location.")
    except Exception as e:
        logger.debug(f"Error trying to find installed swarm package: {e}")

    # Attempt 2: Fallback to development source tree structure
    if blueprints_source_dir is None:
        logger.debug("Falling back to development source tree for blueprints.")
        try:
            # Assuming this file is src/swarm/extensions/cli/commands/list_blueprints.py
            # Project root is ../../../../  (src/swarm/extensions/cli/commands -> src)
            # Blueprints dir would be project_root / "src" / "swarm" / "blueprints"
            # More robust: find 'src' then navigate, or use a known relative path from project root.
            # For now, this relative path assumes a standard project structure.
            # src/swarm/extensions/cli/commands/list_blueprints.py
            # Path(__file__).parent.parent.parent.parent = src/
            # So, src/swarm/blueprints
            dev_path_candidate = Path(__file__).resolve().parent.parent.parent.parent / "blueprints"
            logger.debug(f"Checking development blueprints path: {dev_path_candidate!r}")
            if dev_path_candidate.is_dir():
                blueprints_source_dir = dev_path_candidate
                source_location_description = f"development source tree ({blueprints_source_dir})"
            else:
                logger.debug(f"Development blueprints path {dev_path_candidate} not found or not a directory.")
        except Exception as e:
            logger.debug(f"Error determining development blueprints path: {e}")

    if not blueprints_source_dir:
        print("INFO: No available (package/development) blueprint source directory could be determined.")
        logger.info("No available (package/development) blueprint source directory could be determined.")
        return {}

    logger.info(f"Discovering available blueprints from: {blueprints_source_dir!r} (from {source_location_description})")
    return discover_blueprints(str(blueprints_source_dir))

def list_user_installed_blueprints() -> dict[str, DiscoveredBlueprintInfo]:
    """
    Lists blueprints whose source code is installed in the user's XDG blueprint directory.
    """
    user_bp_dir = paths.get_user_blueprints_dir()
    logger.info(f"Discovering user-installed blueprints from: {user_bp_dir!r}")
    if not user_bp_dir.is_dir():
        print(f"INFO: User blueprints directory does not exist: {user_bp_dir}")
        logger.info(f"User blueprints directory does not exist: {user_bp_dir}")
        return {}
    return discover_blueprints(str(user_bp_dir))

def print_blueprint_details(blueprint_key: str, bp_info: DiscoveredBlueprintInfo, compiled_status: str | None = None):
    """Helper function to print details of a single blueprint."""
    metadata = bp_info.get('metadata', {})
    bp_name = metadata.get('name', blueprint_key)
    version = metadata.get('version', 'N/A')
    description_text = metadata.get('description', 'No description available.')
    abbreviation = metadata.get('abbreviation', 'N/A')
    author = metadata.get('author', 'N/A')

    print(f"  - Key/ID: {blueprint_key}")
    print(f"    Name: {bp_name}")
    if abbreviation != 'N/A':
        print(f"    Abbreviation: {abbreviation}")
    print(f"    Version: {version}")
    if author != 'N/A':
        print(f"    Author: {author}")
    print(f"    Description: {description_text}")
    if compiled_status:
        print(f"    Status: {compiled_status}")
    # print(f"    Class: {bp_info['class_type'].__name__}") # Optional: for debugging
    print("-" * 20)

def execute(args=None):
    """
    Execute the command to list blueprints.
    If args.available is True, lists available blueprints.
    Otherwise, lists user-installed blueprints and their compiled status.
    """
    if args and getattr(args, 'available', False):
        print("Listing available blueprints (from package/development source)...")
        try:
            available_blueprints = list_available_blueprints()
            if available_blueprints:
                print(f"\nFound {len(available_blueprints)} available blueprint(s):")
                for bp_key, bp_info in available_blueprints.items():
                    print_blueprint_details(bp_key, bp_info)
                print(f"\nUse 'swarm-cli install <Key/ID>' to install a blueprint's source.")
            else:
                print("No available blueprints found in package or development source.")
        except Exception as e:
            print(f"An error occurred while listing available blueprints: {e}")
            logger.error("Error listing available blueprints.", exc_info=True)
    else:
        print(f"Listing user-installed blueprints (source in {paths.get_user_blueprints_dir()})...")
        try:
            user_blueprints = list_user_installed_blueprints()
            if user_blueprints:
                user_bin_dir = paths.get_user_bin_dir()
                print(f"\nFound {len(user_blueprints)} user-installed blueprint source(s):")
                for bp_key, bp_info in user_blueprints.items():
                    metadata = bp_info.get('metadata', {})
                    exe_name = metadata.get('abbreviation') or bp_key # Prefer abbreviation for exe name
                    compiled_path = user_bin_dir / exe_name
                    status = "Compiled" if compiled_path.is_file() and os.access(compiled_path, os.X_OK) else "Source only"
                    print_blueprint_details(bp_key, bp_info, compiled_status=status)
                print(f"\nUse 'swarm-cli compile <Key/ID>' to compile a blueprint.")
                print(f"Compiled executables are placed in {user_bin_dir}.")
            else:
                print(f"No user-installed blueprints found in {paths.get_user_blueprints_dir()}.")
                print(f"Use 'swarm-cli list --available' to see blueprints you can install, then 'swarm-cli install <name_or_path>'.")

        except Exception as e:
            print(f"An error occurred while listing user-installed blueprints: {e}")
            logger.error("Error listing user-installed blueprints.", exc_info=True)

def register_args(parser: argparse.ArgumentParser):
    """Registers arguments for the list command."""
    parser.add_argument(
        "--available",
        action="store_true",
        help="List blueprints available for installation from the package or development source, rather than user-installed ones."
    )
    # Add other options like --verbose if needed for this command specifically
    # parser.add_argument("--verbose", action="store_true", help="Enable verbose output for the list command.")

if __name__ == '__main__':
    # For direct testing of this script
    logging.basicConfig(level=logging.DEBUG)
    
    parser = argparse.ArgumentParser()
    register_args(parser)

    print("\nTesting default list (user-installed):")
    args_default = parser.parse_args([]) # No flags
    execute(args_default)

    print("\nTesting list --available:")
    args_available = parser.parse_args(["--available"])
    execute(args_available)
