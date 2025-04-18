"""
Main entry point for Swarm CLI (core).
"""

import argparse
import os
from swarm.core.cli.utils.discover_commands import discover_commands
from swarm.core.cli.interactive_shell import interactive_shell

COMMANDS_DIR = os.path.join(os.path.dirname(__file__), "commands")

USER_FRIENDLY_COMMANDS = {
    "list": "list_blueprints",
    "edit-config": "edit_config",
    "validate-env": "validate_env",
    "validate-envvars": "validate_envvars",
    "blueprint-manage": "blueprint_management",
    "config-manage": "config_management",
}

def parse_args(commands):
    """Parse CLI arguments dynamically with user-friendly names."""
    parser = argparse.ArgumentParser(description="Swarm CLI Utility (core)")
    subparsers = parser.add_subparsers(dest="command")

    for cmd_name, metadata in commands.items():
        subparsers.add_parser(cmd_name, help=metadata["description"])

    return parser.parse_args()

def main():
    # Discover commands using user-friendly mapping
    raw_commands = discover_commands(COMMANDS_DIR)
    commands = {}
    for user_cmd, internal_cmd in USER_FRIENDLY_COMMANDS.items():
        if internal_cmd in raw_commands:
            commands[user_cmd] = raw_commands[internal_cmd]
    args = parse_args(commands)

    if args.command:
        command = commands.get(args.command, {}).get("execute")
        if command:
            command()
        else:
            print(f"Command '{args.command}' is not executable.")
    else:
        interactive_shell()

if __name__ == "__main__":
    main()
