import argparse
import json
from swarm.core import (
    config_loader,
    config_manager,
    server_config,
    setup_wizard,
)
from pathlib import Path

CONFIG_PATH = Path("swarm_config.json").resolve()

def list_config(config):
    """
    List current configuration settings.
    
    Args:
        config (dict): The current configuration.
    """
    print(json.dumps(config, indent=4))

def edit_config_interactive(config):
    """
    Interactive editing of the configuration file.
    
    Args:
        config (dict): The current configuration.
    """
    print("Current configuration:")
    list_config(config)

    print("\nEdit the settings (leave blank to keep current value):")
    for key, value in config.items():
        new_value = input(f"{key} [{value}]: ").strip()
        if new_value:
            config[key] = new_value

    print("\nUpdated configuration:")
    list_config(config)

def edit_config_field(config, field, value):
    """
    Edit a specific field in the configuration.
    
    Args:
        config (dict): The current configuration.
        field (str): The field to edit.
        value (str): The new value for the field.
    """
    if field not in config:
        print(f"Field '{field}' not found in configuration.")
        return
    config[field] = value
    print(f"Updated {field} to {value}.")

def main():
    parser = argparse.ArgumentParser(description="Edit the swarm_config.json file.")
    parser.add_argument("--list", action="store_true", help="List current configuration")
    parser.add_argument("--field", help="The configuration field to edit")
    parser.add_argument("--value", help="The new value for the specified field")
    parser.add_argument("--interactive", action="store_true", help="Interactively edit the configuration")
    args = parser.parse_args()

    try:
        config = config_loader.load_server_config(str(CONFIG_PATH))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if args.list:
        list_config(config)
    elif args.interactive:
        edit_config_interactive(config)
        config_loader.save_server_config(str(CONFIG_PATH), config)
    elif args.field and args.value:
        edit_config_field(config, args.field, args.value)
        config_loader.save_server_config(str(CONFIG_PATH), config)
    else:
        parser.print_help()
