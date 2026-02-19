"""
Interactive CLI shell for dynamic commands.
"""

import os

from swarm.extensions.cli.utils.discover_commands import discover_commands

COMMANDS_DIR = os.path.join(os.path.dirname(__file__), "commands")

def interactive_shell():
    """Launch an interactive CLI shell."""
    commands = discover_commands(COMMANDS_DIR)

    print("Welcome to the Swarm CLI Interactive Shell!")
    print("Type 'help' to see available commands, or 'exit' to quit.")

    while True:
        try:
            user_input = input("swarm> ").strip()
            if user_input == "exit":
                print("Exiting CLI shell.")
                break
            elif user_input == "help":
                show_help(commands)
            elif user_input in commands:
                command = commands[user_input]["execute"]
                if command:
                    command()
                else:
                    print(f"Command '{user_input}' is not executable.")
            else:
                print(f"Unknown command: {user_input}")
        except KeyboardInterrupt:
            print("\nExiting CLI shell.")
            break

def show_help(commands):
    """Display available commands with helpful context and usage."""
    print("\n\033[1;36mSwarm CLI Help\033[0m")
    print("Type the command name to run it, or 'exit' to quit.")
    print("Commands can be used to manage your Swarm config, blueprints, LLMs, MCP servers, and more.\n")
    print("Available commands:")
    for cmd, metadata in commands.items():
        desc = metadata.get('description', 'No description provided.')
        usage = metadata.get('usage', None)
        print(f"  \033[1;33m{cmd}\033[0m: {desc}")
        if usage:
            print(f"    Usage: {usage}")
    print("\nExamples:")
    print("  validate_envvars    # Check required environment variables")
    print("  edit_config         # Edit your Swarm config interactively")
    print("  list_blueprints     # List all available blueprints")
    print("  blueprint_management # Advanced blueprint management")
    print("  config_management   # Manage LLMs, MCP servers, blueprints")
    print("\nType 'exit' to leave the shell.\n")
