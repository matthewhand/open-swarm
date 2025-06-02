import os
import importlib
import importlib.util
import inspect
import logging
import sys
from typing import Dict, Type, Any, Optional, TypedDict
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from swarm.core.blueprint_base import BlueprintBase
except ImportError:
    logger.error("Failed to import BlueprintBase from swarm.core.blueprint_base. Ensure it is correctly placed.", exc_info=True)
    # To prevent further issues, we should probably raise an error or exit
    # if BlueprintBase is critical and not found. For now, discovery will likely fail.
    class BlueprintBase: pass # Minimal placeholder to allow type hints, but discovery will be broken.


class BlueprintMetadata(TypedDict, total=False):
    """Structure for metadata extracted from a blueprint."""
    name: str
    version: Optional[str]
    description: Optional[str]
    author: Optional[str]
    abbreviation: Optional[str]
    # Add other common metadata fields here if needed for typing

class DiscoveredBlueprintInfo(TypedDict):
    """Structure for the information returned by discover_blueprints for each blueprint."""
    class_type: Type[BlueprintBase]
    metadata: BlueprintMetadata


class BlueprintLoadError(Exception):
    """Custom exception for errors during blueprint loading."""
    pass

# This function was defined but not used in the original discover_blueprints.
# It might be useful if blueprint names from directories need canonicalization.
# def _get_blueprint_name_from_dir(dir_name: str) -> str:
#     """Converts directory name (e.g., 'blueprint_my_agent') to blueprint name (e.g., 'my_agent')."""
#     prefix = "blueprint_"
#     if dir_name.startswith(prefix):
#         return dir_name[len(prefix):]
#     return dir_name

def discover_blueprints(blueprint_dir: str) -> Dict[str, DiscoveredBlueprintInfo]:
    """
    Discovers blueprints by looking for Python files within subdirectories
    of the given blueprint directory. Extracts metadata including name, version,
    description (with docstring fallback), and abbreviation.

    Args:
        blueprint_dir: The path to the directory containing blueprint subdirectories.

    Returns:
        A dictionary mapping blueprint directory names (as keys) to
        DiscoveredBlueprintInfo objects containing the blueprint class and its metadata.
    """
    logger.info(f"Starting blueprint discovery in directory: {blueprint_dir}")
    blueprints: Dict[str, DiscoveredBlueprintInfo] = {}
    base_dir = Path(blueprint_dir).resolve()

    if not base_dir.is_dir():
        logger.error(f"Blueprint directory not found or is not a directory: {base_dir}")
        return blueprints

    for subdir in base_dir.iterdir():
        if not subdir.is_dir() or subdir.name.startswith('.') or subdir.name == "__pycache__":
            continue

        # Use directory name as the primary identifier/key for the blueprint
        blueprint_key_name = subdir.name
        logger.debug(f"Processing potential blueprint '{blueprint_key_name}' in directory: {subdir.name}")

        # Standard search: blueprint_{blueprint_key_name}.py or {blueprint_key_name}.py
        # (Adjusted to prioritize {blueprint_key_name}.py as per common practice,
        # then blueprint_{blueprint_key_name}.py if that's a convention)
        
        # Attempt 1: {blueprint_key_name}.py (e.g., codey.py in codey/ directory)
        py_file_path = subdir / f"{blueprint_key_name}.py"
        py_file_name = py_file_path.name

        if not py_file_path.is_file():
            # Attempt 2: blueprint_{blueprint_key_name}.py (e.g., blueprint_codey.py in codey/ directory)
            py_file_path = subdir / f"blueprint_{blueprint_key_name}.py"
            py_file_name = py_file_path.name
            if not py_file_path.is_file():
                logger.warning(f"Skipping directory '{subdir.name}': No suitable main Python file "
                               f"('{blueprint_key_name}.py' or 'blueprint_{blueprint_key_name}.py') found.")
                continue
        
        logger.debug(f"Found blueprint file: {py_file_name} in {subdir}")

        # Construct module import path. Example: swarm.blueprints.codey.codey
        # This assumes 'swarm.blueprints' is a package containing subdirectories for each blueprint.
        # The base_dir is typically .../swarm/blueprints/
        # So, subdir.name would be 'codey', py_file_path.stem would be 'codey'
        module_import_path = f"{base_dir.parent.name}.{base_dir.name}.{subdir.name}.{py_file_path.stem}"
        # A more robust way if base_dir is not always '.../swarm/blueprints':
        # Find the 'swarm' package root relative to py_file_path and build from there.
        # For now, assuming a fixed structure like 'swarm.blueprints.blueprint_name.module_name'
        # If blueprint_dir is 'src/swarm/blueprints', then base_dir.parent.name is 'swarm', base_dir.name is 'blueprints'.
        # Example: src/swarm/blueprints/codey/codey.py -> swarm.blueprints.codey.codey

        try:
            # Ensure the parent of 'swarm' (e.g., 'src') is in sys.path if not already.
            # This helps Python find the 'swarm' package.
            # If blueprint_dir is 'src/swarm/blueprints', then base_dir.parent.parent is 'src'.
            project_src_dir = str(base_dir.parent.parent)
            if project_src_dir not in sys.path:
                logger.debug(f"Adding '{project_src_dir}' to sys.path for module import.")
                sys.path.insert(0, project_src_dir)

            module_spec = importlib.util.spec_from_file_location(module_import_path, py_file_path)

            if module_spec and module_spec.loader:
                module = importlib.util.module_from_spec(module_spec)
                # Register module before execution to handle circular imports within blueprint
                sys.modules[module_import_path] = module 
                module_spec.loader.exec_module(module)
                logger.debug(f"Successfully loaded module: {module_import_path}")

                found_bp_class_details = None
                for member_name, member_obj in inspect.getmembers(module):
                    if inspect.isclass(member_obj) and \
                       issubclass(member_obj, BlueprintBase) and \
                       member_obj is not BlueprintBase and \
                       member_obj.__module__ == module_import_path: # Ensure class is defined in this module

                        if found_bp_class_details:
                            logger.warning(f"Multiple BlueprintBase subclasses found in {py_file_name}. "
                                           f"Using the first one found: '{found_bp_class_details['metadata']['name']}'. "
                                           f"Previously found: '{member_name}'.")
                            continue # Stick with the first one

                        logger.debug(f"Found Blueprint class '{member_name}' in module '{module_import_path}'")
                        
                        # Extract metadata
                        class_metadata_attr = getattr(member_obj, 'metadata', {})
                        if not isinstance(class_metadata_attr, dict):
                            logger.warning(f"Blueprint class '{member_name}' has a 'metadata' attribute that is not a dict. "
                                           f"Type: {type(class_metadata_attr)}. Skipping metadata extraction for this field.")
                            class_metadata_attr = {}

                        # Description: from metadata, fallback to class docstring
                        description = class_metadata_attr.get('description')
                        if not description:
                            docstring = inspect.getdoc(member_obj)
                            if docstring:
                                description = docstring.strip()
                                logger.debug(f"Using class docstring for description of '{member_name}'.")
                        
                        current_blueprint_metadata: BlueprintMetadata = {
                            'name': class_metadata_attr.get('name', blueprint_key_name), # Fallback to dir name
                            'version': class_metadata_attr.get('version'),
                            'description': description,
                            'author': class_metadata_attr.get('author'),
                            'abbreviation': class_metadata_attr.get('abbreviation') # New field
                        }

                        found_bp_class_details = DiscoveredBlueprintInfo(
                            class_type=member_obj,
                            metadata=current_blueprint_metadata
                        )
                        # Storing by blueprint_key_name (directory name)
                        blueprints[blueprint_key_name] = found_bp_class_details
                        # break # Found the class, no need to check other members of this module for BP classes

                if not found_bp_class_details:
                    logger.warning(f"No BlueprintBase subclass found directly defined in module: {module_import_path}")
            else:
                logger.warning(f"Could not create module spec for {py_file_path}")

        except Exception as e:
            logger.error(f"Error processing blueprint file '{py_file_path}': {e}", exc_info=True)
            # Clean up sys.modules if import failed partway
            if module_import_path in sys.modules:
                del sys.modules[module_import_path]
    
    logger.info(f"Blueprint discovery complete. Found {len(blueprints)} blueprints: {list(blueprints.keys())}")
    return blueprints

if __name__ == '__main__':
    # Example Usage (assuming you have a 'blueprints' directory structured correctly)
    # Create a dummy BlueprintBase and a dummy blueprint for testing
    logging.basicConfig(level=logging.DEBUG)

    # Create dummy structure for testing
    Path("src/swarm/blueprints/example_bp").mkdir(parents=True, exist_ok=True)
    
    # Dummy swarm.core.blueprint_base
    Path("src/swarm/core").mkdir(parents=True, exist_ok=True)
    with open("src/swarm/core/blueprint_base.py", "w") as f:
        f.write("from abc import ABC, abstractmethod\n")
        f.write("class BlueprintBase(ABC):\n")
        f.write("    metadata = {}\n") # Ensure metadata attr exists for getattr
        f.write("    @abstractmethod\n")
        f.write("    def run(self):\n")
        f.write("        pass\n")

    # Dummy blueprint file: src/swarm/blueprints/example_bp/example_bp.py
    with open("src/swarm/blueprints/example_bp/example_bp.py", "w") as f:
        f.write("from swarm.core.blueprint_base import BlueprintBase\n")
        f.write("class MyExampleBlueprint(BlueprintBase):\n")
        f.write("    \"\"\"This is an example blueprint's docstring.\"\"\"\n")
        f.write("    metadata = {\n")
        f.write("        'name': 'ExampleBP',\n")
        f.write("        'version': '1.0.1',\n")
        # No description in metadata to test docstring fallback
        f.write("        'author': 'Test Author',\n")
        f.write("        'abbreviation': 'exbp'\n")
        f.write("    }\n")
        f.write("    def run(self):\n")
        f.write("        print('ExampleBP running')\n")
    
    # Test discovery (assuming 'src' is in PYTHONPATH or script is run from project root)
    # The script assumes blueprint_dir is relative to where Python resolves 'swarm.blueprints'
    # For this test, let's point to 'src/swarm/blueprints'
    discovered = discover_blueprints("src/swarm/blueprints")
    for name, info in discovered.items():
        print(f"\nDiscovered Blueprint Key: {name}")
        print(f"  Class: {info['class_type'].__name__}")
        print(f"  Metadata:")
        for meta_key, meta_val in info['metadata'].items():
            print(f"    {meta_key}: {meta_val}")

    # Cleanup dummy files
    # import shutil
    # shutil.rmtree("src/swarm/blueprints/example_bp")
    # Path("src/swarm/core/blueprint_base.py").unlink()
    # Potentially rmdir for src/swarm/core and src/swarm/blueprints if they were created solely for this
