import os
import importlib
import importlib.util
import inspect
import logging # Ensure logging is imported
import sys
from typing import Dict, Type, Any
from pathlib import Path

# *** Define logger EARLIER ***
logger = logging.getLogger(__name__)

# *** Import the ACTUAL BlueprintBase from the likely correct path ***
try:
    # Adjust this path if BlueprintBase lives elsewhere
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError:
    # This logger call is now safe
    logger.error("Failed to import BlueprintBase from swarm.extensions.blueprint.blueprint_base. Using placeholder.", exc_info=True)
    class BlueprintBase: # Fallback placeholder
        metadata: Dict[str, Any] = {}
        def __init__(self, *args, **kwargs): pass
        async def run(self, *args, **kwargs): pass


class BlueprintLoadError(Exception):
    """Custom exception for errors during blueprint loading."""
    pass

def _get_blueprint_name_from_dir(dir_name: str) -> str:
    """Converts directory name (e.g., 'blueprint_my_agent') to blueprint name (e.g., 'my_agent')."""
    prefix = "blueprint_"
    if dir_name.startswith(prefix):
        return dir_name[len(prefix):]
    return dir_name

def discover_blueprints(blueprint_dir: str) -> Dict[str, Type[BlueprintBase]]:
    """
    Discovers blueprints (subclasses of BlueprintBase) by looking for
    'blueprint_{name}.py' files within subdirectories of the given blueprint directory.

    Args:
        blueprint_dir: The path to the directory containing blueprint subdirectories.

    Returns:
        A dictionary mapping blueprint names to their corresponding class objects.
    """
    logger.info(f"Starting blueprint discovery in directory: {blueprint_dir}")
    blueprints: Dict[str, Type[BlueprintBase]] = {}
    base_dir = Path(blueprint_dir).resolve()

    if not base_dir.is_dir():
        logger.error(f"Blueprint directory not found or is not a directory: {base_dir}")
        return blueprints

    # Iterate over items inside the base blueprint directory
    for item_name in os.listdir(base_dir):
        item_path = base_dir / item_name

        if not item_path.is_dir():
            continue # Skip files directly under blueprints/

        # Use directory name as blueprint name (e.g., 'echocraft')
        blueprint_name = item_name
        logger.debug(f"Processing potential blueprint '{blueprint_name}' in directory: {item_name}")

        # Look for the specific .py file, e.g., blueprint_echocraft.py
        py_file_name = f"blueprint_{blueprint_name}.py"
        py_file_path = item_path / py_file_name

        if not py_file_path.is_file():
            # Also check for just {blueprint_name}.py if that's a convention
            alt_py_file_name = f"{blueprint_name}.py"
            alt_py_file_path = item_path / alt_py_file_name
            if alt_py_file_path.is_file():
                 py_file_path = alt_py_file_path # Use the alternative path
                 py_file_name = alt_py_file_name
                 logger.debug(f"Found alternative blueprint file: {py_file_name}")
            else:
                 logger.warning(f"Skipping directory '{item_name}': Neither '{py_file_name}' nor '{alt_py_file_name}' found.")
                 continue


        # Construct module import path, e.g., blueprints.echocraft.blueprint_echocraft
        module_import_path = f"{base_dir.name}.{item_name}.{py_file_path.stem}"

        try:
            # Ensure parent directory is in path
            parent_dir = str(base_dir.parent)
            if parent_dir not in sys.path:
                 logger.debug(f"Adding '{parent_dir}' to sys.path for blueprint discovery.")
                 sys.path.insert(0, parent_dir)

            # Create module spec from file path
            module_spec = importlib.util.spec_from_file_location(module_import_path, py_file_path)

            if module_spec and module_spec.loader:
                module = importlib.util.module_from_spec(module_spec)
                sys.modules[module_import_path] = module
                module_spec.loader.exec_module(module)
                logger.debug(f"Successfully loaded module: {module_import_path}")

                found_bp_class = None
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and obj.__module__ == module_import_path and issubclass(obj, BlueprintBase) and obj is not BlueprintBase:
                        if found_bp_class:
                            logger.warning(f"Multiple BlueprintBase subclasses found in {py_file_name}. Using the first: {found_bp_class.__name__}.")
                        else:
                            logger.debug(f"Found Blueprint class '{name}' in module '{module_import_path}'")
                            found_bp_class = obj
                            blueprints[blueprint_name] = found_bp_class
                            # break

                if not found_bp_class:
                    logger.warning(f"No BlueprintBase subclass found directly defined in module: {module_import_path}")
            else:
                logger.warning(f"Could not create module spec for {py_file_path}")

        except Exception as e:
            logger.error(f"Error processing blueprint file '{py_file_path}': {e}", exc_info=True)
            if module_import_path in sys.modules:
                 del sys.modules[module_import_path]

    logger.info(f"Blueprint discovery complete. Found: {list(blueprints.keys())}")
    return blueprints

