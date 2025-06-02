import argparse
import json
from swarm.core import (
    config_loader,
    # config_manager, # Not used in this file
    # server_config,  # Not used in this file
    # setup_wizard,   # Not used in this file
)
from swarm.core import paths # Import the new paths module

# Use the new paths module to get the config file path
# This will default to ~/.config/swarm/config.yaml (or platform equivalent)
CONFIG_PATH = paths.get_swarm_config_file()
# If you specifically need 'swarm_config.json', use:
# CONFIG_PATH = paths.get_swarm_config_file("swarm_config.json")
# For this refactoring, we'll use the default from paths.py

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
    # Note: This simple input method might not be ideal for complex/nested JSON/YAML
    for key, value in config.items():
        # Represent existing value for editing complex types (dicts/lists)
        current_value_display = json.dumps(value) if isinstance(value, (dict, list)) else value
        new_value_str = input(f"{key} [{current_value_display}]: ").strip()
        if new_value_str:
            try:
                # Attempt to parse as JSON if it looks like it, otherwise keep as string
                if (new_value_str.startswith('{') and new_value_str.endswith('}')) or \
                   (new_value_str.startswith('[') and new_value_str.endswith(']')):
                    config[key] = json.loads(new_value_str)
                else:
                    # Try to convert to original type if simple (e.g. int, bool)
                    # This is a basic attempt; a more robust solution would be needed for general types
                    if isinstance(value, bool):
                        config[key] = new_value_str.lower() in ['true', '1', 't', 'y', 'yes']
                    elif isinstance(value, int):
                        config[key] = int(new_value_str)
                    elif isinstance(value, float):
                        config[key] = float(new_value_str)
                    else:
                        config[key] = new_value_str # Store as string
            except ValueError:
                print(f"Warning: Could not convert '{new_value_str}' for key '{key}'. Storing as string.")
                config[key] = new_value_str # Fallback to string if conversion fails


    print("\nUpdated configuration:")
    list_config(config)

def edit_config_field(config, field, value_str):
    """
    Edit a specific field in the configuration.

    Args:
        config (dict): The current configuration.
        field (str): The field to edit (can be dot-separated for nested keys).
        value_str (str): The new value for the field (as a string from CLI).
    """
    keys = field.split('.')
    current_level = config
    for i, key_part in enumerate(keys[:-1]):
        if key_part not in current_level or not isinstance(current_level[key_part], dict):
            print(f"Field path '{field}' not found or not a nested dictionary at '{key_part}'.")
            return
        current_level = current_level[key_part]
    
    final_key = keys[-1]
    if final_key not in current_level and not isinstance(current_level, dict): # Check if current_level is a dict before assignment
        print(f"Field '{final_key}' not found in the specified path or path is invalid.")
        return

    # Attempt to parse value_str as JSON, then specific types, then string
    try:
        new_value = json.loads(value_str)
    except json.JSONDecodeError:
        # Not JSON, try common types or keep as string
        if value_str.lower() == 'true': new_value = True
        elif value_str.lower() == 'false': new_value = False
        elif value_str.lower() == 'null': new_value = None # Allow setting null
        elif value_str.isdigit(): new_value = int(value_str)
        elif value_str.replace('.', '', 1).isdigit(): # Basic float check
            try: new_value = float(value_str)
            except ValueError: new_value = value_str # Not a float
        else: new_value = value_str # Default to string

    current_level[final_key] = new_value
    print(f"Updated {field} to {json.dumps(new_value)}.")

def main():
    parser = argparse.ArgumentParser(description=f"Edit the Swarm configuration file ({CONFIG_PATH}).")
    parser.add_argument("--list", action="store_true", help="List current configuration")
    parser.add_argument("--field", help="The configuration field to edit (e.g., 'logging.level' or 'api_key')")
    parser.add_argument("--value", help="The new value for the specified field (use JSON for complex values e.g. '{\"key\":\"val\"}' or '[1,2,3]')")
    parser.add_argument("--interactive", action="store_true", help="Interactively edit the configuration")
    args = parser.parse_args()

    # Ensure config directory exists (though paths.ensure_swarm_directories_exist() should handle it globally)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        # config_loader.load_server_config expects a string path
        config = config_loader.load_server_config(str(CONFIG_PATH))
    except FileNotFoundError:
        # If config file doesn't exist, start with an empty dict or default structure
        # For now, let's inform the user and start with empty if not interactive.
        # A setup_wizard or default config generation would be better here.
        if args.list or (args.field and args.value) or args.interactive:
            print(f"Info: Configuration file '{CONFIG_PATH}' not found. Starting with an empty configuration for editing.")
            config = {}
        else: # No action specified, and file not found
            print(f"Error: Configuration file '{CONFIG_PATH}' not found.")
            print(f"You can create one by running with --interactive or by setting a --field and --value.")
            return
    except Exception as e: # Catch other potential loading errors (e.g., malformed JSON/YAML)
        print(f"Error loading configuration from '{CONFIG_PATH}': {e}")
        return


    if args.list:
        list_config(config)
    elif args.interactive:
        edit_config_interactive(config)
        config_loader.save_server_config(str(CONFIG_PATH), config)
        print(f"Configuration saved to {CONFIG_PATH}")
    elif args.field and args.value is not None: # Ensure value is provided
        edit_config_field(config, args.field, args.value)
        config_loader.save_server_config(str(CONFIG_PATH), config)
        print(f"Configuration saved to {CONFIG_PATH}")
    elif args.field and args.value is None:
        parser.error("--value is required when --field is specified.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
