"""
Main entry point for Swarm CLI.
"""

import argparse
import os
from swarm.extensions.cli.utils.discover_commands import discover_commands
from swarm.extensions.cli.interactive_shell import interactive_shell

COMMANDS_DIR = os.path.join(os.path.dirname(__file__), "commands")

def parse_args(commands):
    """Parse CLI arguments dynamically."""
    parser = argparse.ArgumentParser(description="Swarm CLI Utility")
    subparsers = parser.add_subparsers(dest="command")

    for cmd_name, metadata in commands.items():
        subparsers.add_parser(cmd_name, help=metadata["description"])

    # Use parse_known_args to allow subcommands to parse their own args
    return parser.parse_known_args()

def main():
    commands = discover_commands(COMMANDS_DIR)
    args, extra_args = parse_args(commands)

    if args.command:
        command = commands.get(args.command, {}).get("execute")
        if command:
            command(extra_args)
        else:
            print(f"Command '{args.command}' is not executable.")
    else:
        interactive_shell()

if __name__ == "__main__":
    main()
