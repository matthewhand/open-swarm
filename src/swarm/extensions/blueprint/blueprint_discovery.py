"""
Blueprint Discovery Module for Open Swarm MCP.

This module dynamically discovers and imports blueprints from specified directories.
It identifies classes derived from BlueprintBase as valid blueprints and extracts their metadata.
"""

import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Dict, List, Any
from swarm.settings import DEBUG

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

try:
    from .blueprint_base import BlueprintBase
except ImportError as e:
    logger.critical(f"Failed to import BlueprintBase: {e}")
    raise

def discover_blueprints(directories: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Discover and load blueprints from specified directories.
    Extract metadata including title, description, and other attributes.

    Args:
        directories (List[str]): List of directories to search for blueprints.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary containing blueprint metadata.
    """
    blueprints = {}
    logger.info("Starting blueprint discovery.")
    swarm_blueprints = os.getenv("SWARM_BLUEPRINTS", "").split(",")
    if swarm_blueprints and swarm_blueprints[0]:
        logger.debug(f"Filtering blueprints to: {swarm_blueprints}")

    for directory in directories:
        logger.debug(f"Searching for blueprints in: {directory}")
        dir_path = Path(directory)

        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Invalid directory: {directory}. Skipping...")
            continue

        for blueprint_file in dir_path.rglob("blueprint_*.py"):
            module_name = blueprint_file.stem
            blueprint_name = module_name.replace("blueprint_", "")
            if swarm_blueprints and swarm_blueprints[0] and blueprint_name not in swarm_blueprints:
                logger.debug(f"Skipping blueprint '{blueprint_name}' not in SWARM_BLUEPRINTS")
                continue
            module_path = str(blueprint_file.parent)

            logger.debug(f"Found blueprint file: {blueprint_file}")
            logger.debug(f"Module name: {module_name}, Blueprint name: {blueprint_name}, Module path: {module_path}")

            try:
                spec = importlib.util.spec_from_file_location(module_name, str(blueprint_file))
                if spec is None or spec.loader is None:
                    logger.error(f"Cannot load module spec for blueprint file: {blueprint_file}. Skipping.")
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logger.debug(f"Successfully imported module: {module_name}")

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if not issubclass(obj, BlueprintBase) or obj is BlueprintBase:
                        continue

                    logger.debug(f"Discovered blueprint class: {name}")

                    try:
                        metadata = obj.metadata
                        if callable(metadata):
                            metadata = metadata()
                        elif isinstance(metadata, property):
                            if metadata.fget is not None:
                                metadata = metadata.fget(obj)
                            else:
                                logger.error(f"Blueprint '{blueprint_name}' property 'metadata' has no getter.")
                                raise ValueError(f"Blueprint '{blueprint_name}' metadata is inaccessible.")

                        if not isinstance(metadata, dict):
                            logger.error(f"Metadata for blueprint '{blueprint_name}' is not a dictionary.")
                            raise ValueError(f"Metadata for blueprint '{blueprint_name}' is invalid or inaccessible.")

                        if "title" not in metadata or "description" not in metadata:
                            logger.error(f"Required metadata fields (title, description) are missing for blueprint '{blueprint_name}'.")
                            raise ValueError(f"Metadata for blueprint '{blueprint_name}' is invalid or inaccessible.")

                    except Exception as e:
                        logger.error(f"Error retrieving metadata for blueprint '{blueprint_name}': {e}")
                        continue

                    blueprints[blueprint_name] = {
                        "blueprint_class": obj,
                        "title": metadata["title"],
                        "description": metadata["description"],
                    }
                    logger.debug(f"Added blueprint '{blueprint_name}' with metadata: {metadata}")
            except ImportError as e:
                logger.error(f"Failed to import module '{module_name}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error importing '{module_name}': {e}", exc_info=True)

    logger.info("Blueprint discovery complete.")
    logger.debug(f"Discovered blueprints: {list(blueprints.keys())}")
    return blueprints
