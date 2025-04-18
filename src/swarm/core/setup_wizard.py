# src/swarm/extensions/config/setup_wizard.py

import os
import json
from typing import Dict, Any

def run_setup_wizard(config_path: str, blueprints_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Runs the interactive setup wizard.

    Args:
        config_path (str): Path to the configuration file.
        blueprints_metadata (Dict[str, Dict[str, Any]]): Metadata for available blueprints.

    Returns:
        Dict[str, Any]: Updated configuration.
    """
    config = {
        "llm_providers": {},
        "mcpServers": {}
    }

    # Configure LLM settings
    print("Configuring LLM providers:")
    while True:
        provider_name = input("Enter the name of the LLM provider to add (e.g., 'openai', 'ollama'), or type 'done' to finish: ").strip()
        if provider_name.lower() in ['done', 'exit', 'quit']:
            break
        if not provider_name:
            print("Provider name cannot be empty.")
            continue
        if provider_name in config["llm_providers"]:
            print(f"LLM provider '{provider_name}' already exists.")
            continue

        provider = {}
        provider["provider"] = input("Enter the provider identifier (e.g., 'openai', 'ollama'): ").strip()
        provider["model"] = input("Enter the model name (e.g., 'gpt-4'): ").strip()
        provider["base_url"] = input("Enter the base URL for the API (e.g., 'https://api.openai.com/v1'): ").strip()
        provider["api_key"] = input("Enter the environment variable for the API key (e.g., 'OPENAI_API_KEY') [Leave empty if not required]: ").strip()
        temperature_input = input("Enter the temperature for the model (e.g., 0.7): ").strip()
        try:
            provider["temperature"] = float(temperature_input)
        except ValueError:
            print("Invalid temperature value. Using default 0.7.")
            provider["temperature"] = 0.7

        config["llm_providers"][provider_name] = provider
        print(f"LLM provider '{provider_name}' added successfully.\n")

    # Select a default LLM provider
    if config["llm_providers"]:
        print("\nAvailable LLM Providers:")
        for idx, provider in enumerate(config["llm_providers"].keys(), start=1):
            print(f"{idx}. {provider}")
        while True:
            try:
                default_choice = input("Enter the number of the LLM provider to set as default: ").strip()
                default_choice = int(default_choice)
                if 1 <= default_choice <= len(config["llm_providers"]):
                    default_provider = list(config["llm_providers"].keys())[default_choice - 1]
                    config["llm_providers"]["default"] = config["llm_providers"][default_provider]
                    print(f"Default LLM provider set to '{default_provider}'.\n")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(config['llm_providers'])}.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")
    else:
        print("No LLM providers configured.")

    # Select a blueprint
    print("\nAvailable Blueprints:")
    for idx, (key, metadata) in enumerate(blueprints_metadata.items(), start=1):
        print(f"{idx}. {key}: {metadata.get('title', 'No title')} - {metadata.get('description', 'No description')}")

    while True:
        try:
            blueprint_choice = input("\nEnter the number of the blueprint to use (0 to skip): ").strip()
            if blueprint_choice.lower() in ["q", "quit", "exit"]:  # Handle exit inputs
                print("Exiting blueprint selection.")
                break

            blueprint_choice = int(blueprint_choice)
            if blueprint_choice == 0:
                print("No blueprint selected.")
                break
            elif 1 <= blueprint_choice <= len(blueprints_metadata):
                selected_blueprint_key = list(blueprints_metadata.keys())[blueprint_choice - 1]
                config["blueprint"] = selected_blueprint_key
                print(f"Selected Blueprint: {selected_blueprint_key}\n")
                break
            else:
                print(f"Invalid selection. Please enter a number between 0 and {len(blueprints_metadata)}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Save configuration
    with open(config_path, "w") as config_file:
        json.dump(config, config_file, indent=4)
    print(f"Configuration saved to {config_path}.\n")

    return config
