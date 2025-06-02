"""
Command: list_blueprints
Description: Lists all blueprints available in the system by discovering their source code.
"""

import importlib.util # For finding installed package location
from pathlib import Path
import logging # Use logging for debug messages
from swarm.core.blueprint_discovery import discover_blueprints, DiscoveredBlueprintInfo

logger = logging.getLogger(__name__)

# Metadata for dynamic registration (if used by your CLI framework)
description = "Lists all blueprints available from their source directories."
usage = "list" # The user types 'list'

def list_blueprints_from_source() -> dict[str, DiscoveredBlueprintInfo]:
    """
    Returns a dictionary of discovered blueprints.
    Tries to find blueprints from an installed 'swarm' package first,
    then falls back to a development source tree structure.
    """
    blueprints_source_dir = None
    source_location_description = "unknown"

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

    if blueprints_source_dir is None:
        logger.debug("Falling back to development source tree for blueprints.")
        try:
            # Assuming this file is src/swarm/extensions/cli/commands/list_blueprints.py
            # Project root would be Path(__file__).resolve().parent.parent.parent.parent
            # Blueprints dir would be project_root / "src" / "swarm" / "blueprints"
            # Or, if 'src' is the root for the package, then project_root / "swarm" / "blueprints"
            # Let's assume 'src' is part of the path from project root to this file.
            # src/swarm/extensions/cli/commands/list_blueprints.py
            # ../../../.. -> src/
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
        print("ERROR: Blueprint source directory could not be determined.")
        logger.error("Blueprint source directory could not be determined from installed package or development tree.")
        return {}

    logger.info(f"Attempting to discover blueprints from: {blueprints_source_dir!r} (determined from {source_location_description})")
    
    # Ensure the path is a string for discover_blueprints if it expects that
    return discover_blueprints(str(blueprints_source_dir))

def execute(args=None):
    """Execute the command to list blueprints from source."""
    # Configure logging to see debug messages if needed
    # logging.basicConfig(level=logging.INFO) # Or DEBUG
    # logger.info("Attempting to list blueprints...")
    print("Attempting to list blueprints...") # User-facing message

    try:
        discovered_info = list_blueprints_from_source()
        if discovered_info:
            print(f"\nFound {len(discovered_info)} blueprint(s):")
            for blueprint_key, bp_info in discovered_info.items():
                # bp_info is a DiscoveredBlueprintInfo TypedDict
                # {'class_type': Type[BlueprintBase], 'metadata': BlueprintMetadata}
                metadata = bp_info.get('metadata', {})
                
                bp_name = metadata.get('name', blueprint_key) # Use blueprint_key as fallback
                version = metadata.get('version', 'N/A')
                description_text = metadata.get('description', 'No description available.')
                abbreviation = metadata.get('abbreviation', 'N/A')
                author = metadata.get('author', 'N/A')

                print(f"  - Key/ID: {blueprint_key}") # This is the directory name
                print(f"    Name: {bp_name}")
                print(f"    Abbreviation: {abbreviation}")
                print(f"    Version: {version}")
                print(f"    Author: {author}")
                print(f"    Description: {description_text}")
                # print(f"    Class: {bp_info['class_type'].__name__}") # Optional: for debugging
                print("-" * 20)
        else:
            print("No blueprints found.")

    except Exception as e:
        print(f"An error occurred while trying to list blueprints: {e}")
        logger.error("Error during blueprint listing execution.", exc_info=True)
        # import traceback
        # traceback.print_exc() # Already logged with exc_info=True

# This function might be used by your dynamic command loader in main.py
def register_args(parser):
    """Registers arguments for the list command."""
    # Example: if list had options like --verbose
    # parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    pass # No specific args for 'list' itself in this version

if __name__ == '__main__':
    # For direct testing of this script
    logging.basicConfig(level=logging.DEBUG) # Show debug logs from this script and discovery
    print("Directly running list_blueprints.execute():")
    execute()
