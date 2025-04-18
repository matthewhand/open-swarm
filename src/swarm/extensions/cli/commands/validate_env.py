import os
import argparse
from swarm.core import config_loader, config_manager, server_config
from swarm.core.blueprint_base import BlueprintBase

CONFIG_PATH = "swarm_config.json"

def validate_all_env_vars(config):
    """
    Validate all environment variables for the current configuration.
    """
    required_vars = config.get("required_env_vars", [])
    missing_vars = [var for var in required_vars if var not in os.environ]

    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    print("All required environment variables are set.")
    return True

def validate_blueprint_env_vars(config, blueprint_name):
    """
    Validate environment variables for a specific blueprint.

    Args:
        config (dict): The configuration dictionary.
        blueprint_name (str): The name of the blueprint to validate.
    """
    blueprint_config = config.get("blueprints", {}).get(blueprint_name, {})
    blueprint = BlueprintBase(blueprint_config)
    required_vars = blueprint.required_env_vars()
    missing_vars = [var for var in required_vars if var not in os.environ]

    if missing_vars:
        print(f"Missing environment variables for blueprint '{blueprint_name}': {', '.join(missing_vars)}")
        return False
    print(f"All required environment variables are set for blueprint '{blueprint_name}'.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Validate environment variables.")
    parser.add_argument("--blueprint", help="Validate environment variables for a specific blueprint.")
    args = parser.parse_args()

    try:
        config = server_config.load_server_config(CONFIG_PATH)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if args.blueprint:
        validate_blueprint_env_vars(config, args.blueprint)
    else:
        validate_all_env_vars(config)

if __name__ == "__main__":
    main()
