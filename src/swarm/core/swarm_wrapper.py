#!/usr/bin/env python3
import os
import sys
import subprocess

MANAGED_DIR = os.path.expanduser("~/.swarm/blueprints")
BIN_DIR = os.path.expanduser("~/.swarm/bin")

def main():
    if len(sys.argv) < 2:
        print("Usage: swarm-wrapper <cli_name> [args...]")
        sys.exit(1)
    
    cli_name = sys.argv[1]
    blueprint_name = cli_name  # Default assumption; could map via config if needed
    blueprint_dir = os.path.join(MANAGED_DIR, blueprint_name)
    blueprint_file = os.path.join(blueprint_dir, f"blueprint_{blueprint_name}.py")
    cli_path = os.path.join(BIN_DIR, cli_name)
    
    if os.path.exists(cli_path):
        # Run the installed CLI
        subprocess.run([cli_path] + sys.argv[2:], check=False)
    else:
        print(f"Error: Blueprint '{blueprint_name}' not installed for CLI '{cli_name}'.")
        print(f"Please install it using: swarm-cli add <path_to_{blueprint_name}> && swarm-cli install {blueprint_name}")
        sys.exit(1)

if __name__ == "__main__":
    main()
