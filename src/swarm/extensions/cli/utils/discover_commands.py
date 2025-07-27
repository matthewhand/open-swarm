"""
Utility to discover and load CLI commands dynamically.
"""

import importlib.util
import os


def discover_commands(commands_dir):
    """
    Discover all commands in the given directory.

    Args:
        commands_dir (str): Path to the commands directory.

    Returns:
        dict: A dictionary of commands with metadata.
    """
    commands = {}
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"swarm.extensions.cli.commands.{filename[:-3]}"
            spec = importlib.util.find_spec(module_name)
            if not spec:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            commands[module_name] = {
                "description": getattr(module, "description", "No description provided."),
                "usage": getattr(module, "usage", "No usage available."),
                "execute": getattr(module, "execute", None),
            }
    return commands
