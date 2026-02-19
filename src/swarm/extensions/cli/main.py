"""
Main entry point for Swarm CLI using a declarative command structure.
"""

import argparse
import os
import sys
from pathlib import Path

from swarm.extensions.cli.utils.discover_commands import discover_commands

COMMANDS_DIR = os.path.join(os.path.dirname(__file__), "commands")

COMMAND_DEFINITIONS = [
    {
        "alias": "list",
        "module_base_name": "list_blueprints",
        "description": "Lists available blueprints (bundled and user-provided) and/or installed executables.",
        "args_def": [
            # Arguments for list_blueprints are typically handled within its own module,
            # e.g., --installed, --available. If they need to be top-level, add here.
            # For consistency with Typer app, these might be options like:
            # {"name_or_flags": ["--installed"], "action": "store_true", "help": "List only installed blueprint executables."},
            # {"name_or_flags": ["--available"], "action": "store_true", "help": "List only available blueprints (source dirs)."}
        ]
    },
    {
        "alias": "wizard",
        "module_base_name": "team_wizard",
        "description": "Interactive wizard to create a new team blueprint and optional CLI shortcut.",
        "args_def": []  # team_wizard registers its own rich arguments
    },
    {
        # This is the NEW install command for installing blueprint SOURCE
        "alias": "install",
        "module_base_name": "install_blueprint", # Points to the new install_blueprint.py
        "description": "Install blueprint source to the user's local blueprints directory.",
        "args_def": [
            {"name_or_flags": ["name_or_path"], "help": "Name of a prebuilt blueprint, or path to a blueprint source file (.py, .zip) or directory."},
            {"name_or_flags": ["--overwrite"], "action": "store_true", "help": "Overwrite if the blueprint source already exists."}
            # Potentially add {"name_or_flags": ["--name"], "help": "Explicit name for the blueprint being installed."}
        ]
    },
    {
        # This was the OLD install, now renamed to align with Typer app's install-executable
        "alias": "install-executable",
        "module_base_name": "blueprint_management", # Assuming blueprint_management.py handles executable creation
        "description": "Install a blueprint by creating a standalone executable (using PyInstaller).",
        "args_def": [
            {"name_or_flags": ["blueprint_name"], "help": "Name of the blueprint source (must be available/installed) to compile into an executable."}
        ]
    },
    {
        "alias": "launch",
        "module_base_name": "blueprint_management", # Assuming blueprint_management.py handles launching
        "description": "Launch a previously installed blueprint executable.",
        "args_def": [
            {"name_or_flags": ["blueprint_name"], "help": "Name of the blueprint executable to launch."},
            {"name_or_flags": ["--message", "-m"], "help": "Message/instruction for the blueprint."},
            {"name_or_flags": ["--profile"], "help": "LLM profile to use (from swarm_config.json)."},
            {"name_or_flags": ["--config-path"], "help": "Path to an alternative swarm_config.json file."},
            {"name_or_flags": ["blueprint_args"], "nargs": argparse.REMAINDER,
             "help": "Additional arguments passed directly to the blueprint executable."}
        ]
    },
    {
        "alias": "add", # This seems similar to the new 'install' (source). Review if it's still needed or should be merged/aliased.
                        # For now, keeping as is from original file.
        "module_base_name": "blueprint_management",
        "description": "Add new blueprint source code to the managed directory. (Consider using 'install' instead).",
        "args_def": [
            {"name_or_flags": ["blueprint_path"], "help": "Path to the blueprint file or directory."},
            {"name_or_flags": ["--name"], "help": "Optional name for the blueprint (especially if adding a directory)."}
        ]
    },
    {
        "alias": "delete", # Deletes blueprint SOURCE
        "module_base_name": "blueprint_management",
        "description": "Remove blueprint source from the user's local blueprints directory.",
        "args_def": [
            {"name_or_flags": ["blueprint_name"], "help": "Name of the blueprint source to delete."}
        ]
    },
    {
        "alias": "uninstall", # Removes EXECUTABLE and/or SOURCE
        "module_base_name": "blueprint_management",
        "description": "Remove installed blueprint executables and/or their source code.",
        "args_def": [
            {"name_or_flags": ["blueprint_name"], "help": "Name of the blueprint to uninstall."},
            {"name_or_flags": ["--source-only"], "action": "store_true", "help": "Remove only the source code from user blueprints directory."}, # Renamed for clarity
            {"name_or_flags": ["--executable-only"], "action": "store_true", "help": "Remove only the installed executable from user bin directory."} # Renamed for clarity
        ]
    },
    {
        "alias": "config",
        "module_base_name": "config_management",
        "description": "Manage LLM profiles, MCP servers, and other settings.",
        "args_def": [
            {"name_or_flags": ["config_args"], "nargs": argparse.REMAINDER,
             "help": "Sub-command and arguments for config management (e.g., 'list --section llm'). Use 'config --help' within its module for details."}
        ]
    },
    {
        "alias": "edit-config",
        "module_base_name": "edit_config",
        "description": "Edit the Swarm configuration file.",
        "args_def": [
            # Arguments for edit_config are defined in its own module (e.g. --field, --value, --interactive)
            # If they need to be exposed at this level for help, add them.
            # For now, assuming edit_config.py handles its own arg parsing or receives remainder.
             {"name_or_flags": ["edit_config_args"], "nargs": argparse.REMAINDER, "help": "Arguments for editing config. Use 'edit-config --help' for details."}
        ]
    },
    {
        "alias": "validate-env",
        "module_base_name": "validate_env",
        "description": "Validate the Swarm environment.",
        "args_def": []
    },
    {
        "alias": "validate-envvars",
        "module_base_name": "validate_envvars",
        "description": "Validate required environment variables.",
        "args_def": []
    },
    # Add other commands from USERGUIDE.md or your design here
]

def parse_args_and_get_executor(discovered_commands_map):
    parser = argparse.ArgumentParser(prog="swarm-cli", description="Swarm CLI Utility")
    subparsers = parser.add_subparsers(dest="user_command_alias", title="Commands",
                                       help="Available commands. Type <command> --help for more details.",
                                       metavar="<command>")
    # subparsers.required = True # Making it not required allows 'swarm-cli --help' without a command

    executors = {}

    for cmd_def in COMMAND_DEFINITIONS:
        alias = cmd_def["alias"]
        module_base_name = cmd_def["module_base_name"]
        description = cmd_def["description"]
        args_definitions = cmd_def.get("args_def", []) # Ensure args_def exists

        full_module_key = f"swarm.extensions.cli.commands.{module_base_name}"

        # Support both key styles from discover_commands: base name and full module path
        command_module_metadata = (
            discovered_commands_map.get(module_base_name)
            or discovered_commands_map.get(full_module_key)
        )


        if not command_module_metadata or not callable(command_module_metadata.get("execute")):
            print(f"Warning: Execute function for alias '{alias}' (module '{module_base_name}') not found or not callable. Skipping.")
            continue

        executors[alias] = command_module_metadata["execute"]
        cmd_parser = subparsers.add_parser(alias, help=description, description=description) # Add description to parser itself

        # If the command module has a specific argument registration function, call it.
        if callable(command_module_metadata.get("register_args")):
            command_module_metadata["register_args"](cmd_parser)
        else: # Fallback to args_def in COMMAND_DEFINITIONS
            for arg_def_item in args_definitions:
                # Ensure arg_def_item is a dictionary and has 'name_or_flags'
                if isinstance(arg_def_item, dict) and "name_or_flags" in arg_def_item:
                    # Make a copy to avoid modifying the original COMMAND_DEFINITIONS
                    current_arg_def = arg_def_item.copy()
                    name_or_flags = current_arg_def.pop("name_or_flags")
                    cmd_parser.add_argument(*name_or_flags, **current_arg_def)
                else:
                    print(f"Warning: Invalid arg_def item for command '{alias}': {arg_def_item}")


    # Handle case where no command is given (e.g., 'swarm-cli' or 'swarm-cli --help')
    if not sys.argv[1:]: # No arguments provided after script name
        parser.print_help()
        sys.exit(0)

    parsed_args, unknown_args = parser.parse_known_args() # Use parse_known_args if some commands take remainder

    # If a command was parsed, try to get its executor
    executor_to_call = None
    if hasattr(parsed_args, 'user_command_alias') and parsed_args.user_command_alias:
        executor_to_call = executors.get(parsed_args.user_command_alias)
    else: # No command given, but maybe --help or --version was top-level
        if parsed_args.help if hasattr(parsed_args, 'help') else False: # Check for top-level --help
             parser.print_help()
             sys.exit(0)
        # Add similar for --version if you have a top-level version arg
        parser.print_help() # Default to help if no command and no top-level known arg
        sys.exit(1)


    # Re-attach unknown_args if the command is expected to handle them (e.g. via nargs=REMAINDER)
    # This logic might need refinement based on how 'blueprint_args' or 'config_args' are truly handled.
    # For now, we assume that if a command defines an argument with nargs=argparse.REMAINDER,
    # parsed_args will contain it. If not, unknown_args might be relevant.
    # Let's assume for now that args_def with REMAINDER handles this correctly.
    # If 'blueprint_args' was defined with REMAINDER, unknown_args should be empty or part of it.

    return parsed_args, executor_to_call

def main():
    # Ensure COMMANDS_DIR is correct relative to this file's location
    current_file_dir = Path(__file__).parent.resolve()
    commands_module_dir = current_file_dir / "commands"

    discovered_commands_map = discover_commands(str(commands_module_dir))
    args, executor = parse_args_and_get_executor(discovered_commands_map)

    if executor:
        # The executor function (e.g., in install_blueprint.py or blueprint_management.py)
        # will receive the 'args' Namespace object containing all parsed arguments for its subparser.
        executor(args)
    else:
        # This case should ideally be handled by parse_args_and_get_executor printing help or error.
        # If it reaches here, it means a command was specified but no executor found.
        print(f"Error: Command '{args.user_command_alias if hasattr(args, 'user_command_alias') else 'unknown'}' not found or not executable.")
        # parser.print_help() # Consider printing help here too.

if __name__ == "__main__":
    from pathlib import Path  # Add Path import for main execution context
    main()
