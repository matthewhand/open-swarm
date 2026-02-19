# src/swarm/extensions/blueprint/modes/cli_mode/blueprint_runner.py

import argparse
import importlib.util
import sys
from typing import Any

from swarm.utils.general_utils import color_text

# Initialize logger for this module
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)


def load_blueprint(blueprint_path: str) -> Any:
    """
    Dynamically load a blueprint module from the given file path.

    Args:
        blueprint_path (str): Path to the blueprint's Python file.

    Returns:
        Any: The loaded blueprint module.

    Raises:
        ImportError: If the module cannot be imported.
    """
    spec = importlib.util.spec_from_file_location("blueprint_module", blueprint_path)
    print(f"DEBUG: Attempting to load blueprint at path: {blueprint_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore
        logger.info(f"Successfully loaded blueprint from {blueprint_path}")
    except Exception as e:
        logger.error(f"Failed to import blueprint at {blueprint_path}: {e}")
        raise ImportError(f"Failed to import blueprint at {blueprint_path}: {e}")
    return module


def run_blueprint_framework(blueprint_module: Any) -> None:
    """
    Runs the blueprint in framework integration mode by invoking its execute() function.

    Args:
        blueprint_module: The loaded blueprint module.

    Raises:
        AttributeError: If the blueprint does not have an execute() function.
    """
    if not hasattr(blueprint_module, 'execute'):
        logger.error("The blueprint does not have an execute() function.")
        raise AttributeError("The blueprint does not have an execute() function.")

    execute_func = blueprint_module.execute

    # Optionally, load configuration from environment or a config file
    config = {}

    try:
        result = execute_func(config)
        print("Execution Result:")
        print("Status:", result.get("status"))
        print("Messages:")
        for msg in result.get("messages", []):
            print(f"{msg.get('role')}: {msg.get('content')}")
        print("Metadata:", result.get("metadata"))
        logger.info(f"Blueprint executed successfully with result: {result}")
    except Exception as e:
        logger.error(f"Error executing blueprint: {e}")
        print(f"Error executing blueprint: {e}")


def run_blueprint_interactive(blueprint_module: Any) -> None:
    """
    Runs the blueprint in interactive standalone mode by invoking its interactive_mode() function.

    Args:
        blueprint_module: The loaded blueprint module.

    Raises:
        AttributeError: If the blueprint does not have an interactive_mode() function.
    """
    if not hasattr(blueprint_module, 'interactive_mode'):
        logger.error("The blueprint does not have an interactive_mode() function.")
        raise AttributeError("The blueprint does not have an interactive_mode() function.")

    interactive_func = blueprint_module.interactive_mode

    try:
        interactive_func()
        logger.info("Blueprint interactive mode executed successfully.")
    except Exception as e:
        logger.error(f"Error in interactive mode: {e}")
        print(f"Error in interactive mode: {e}")


async def run_blueprint_mode(
    blueprints_to_load: list[str],
    config: dict[str, Any],
    blueprints_metadata: dict[str, dict[str, Any]],
    args: Any
) -> None:
    """
    Executes the selected blueprints in the specified mode.

    Args:
        blueprints_to_load (List[str]): List of blueprint names to load.
        config (Dict[str, Any]): Configuration dictionary.
        blueprints_metadata (Dict[str, Dict[str, Any]]): Metadata of available blueprints.
        args (Any): Parsed command-line arguments.
    """
    for blueprint_name in blueprints_to_load:
        blueprint_class = blueprints_metadata[blueprint_name].get("blueprint_class")
        if not blueprint_class:
            logger.warning(f"No blueprint_class defined for blueprint '{blueprint_name}'. Skipping.")
            continue

        blueprint_instance = blueprint_class(config=config)
        logger.info(f"Running blueprint '{blueprint_name}' in '{args.mode}' mode.")

        if args.mode == "cli":
            try:
                blueprint_instance.interactive_mode(stream=False)
                logger.info(f"Blueprint '{blueprint_name}' executed in CLI mode.")
            except Exception as e:
                logger.error(f"Error running blueprint '{blueprint_name}' in CLI mode: {e}")
        elif args.mode == "rest":
            try:
                # Implement REST mode logic here
                # Example: blueprint_instance.rest_mode()
                logger.info(f"Blueprint '{blueprint_name}' executed in REST mode.")
            except Exception as e:
                logger.error(f"Error running blueprint '{blueprint_name}' in REST mode: {e}")
        elif args.mode == "mcp-host":
            try:
                # Implement MCP-host mode logic here
                # Example: blueprint_instance.mcp_host_mode()
                logger.info(f"Blueprint '{blueprint_name}' executed in MCP-host mode.")
            except Exception as e:
                logger.error(f"Error running blueprint '{blueprint_name}' in MCP-host mode: {e}")
        else:
            logger.error(f"Unsupported mode: {args.mode}")
            print(color_text(f"Unsupported mode: {args.mode}", "red"))


def prompt_user_to_select_blueprint(blueprints_metadata: dict[str, dict[str, Any]]) -> str | None:
    """
    Allow the user to select a blueprint from available options.

    Args:
        blueprints_metadata (Dict[str, Dict[str, Any]]): Metadata of available blueprints.

    Returns:
        Optional[str]: Selected blueprint name, or None if no selection is made.
    """
    if not blueprints_metadata:
        logger.warning("No blueprints available. Blueprint selection skipped.")
        print(color_text("No blueprints available. Please add blueprints to continue.", "yellow"))
        return None

    print("\nAvailable Blueprints:")
    for idx, (key, metadata) in enumerate(blueprints_metadata.items(), start=1):
        print(f"{idx}. {metadata.get('title', key)} - {metadata.get('description', 'No description available')}")

    while True:
        try:
            choice_input = input("\nEnter the number of the blueprint you want to run (0 to cancel): ").strip()
            if not choice_input:
                print(f"Please enter a number between 0 and {len(blueprints_metadata)}.")
                logger.warning("User entered empty input for blueprint selection.")
                continue

            choice = int(choice_input)
            if choice == 0:
                logger.info("User chose to cancel blueprint selection.")
                return None
            elif 1 <= choice <= len(blueprints_metadata):
                selected_key = list(blueprints_metadata.keys())[choice - 1]
                logger.info(f"User selected blueprint: '{selected_key}'")
                return selected_key
            else:
                print(f"Please enter a number between 0 and {len(blueprints_metadata)}.")
                logger.warning(f"User entered invalid blueprint number: {choice}")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
            logger.warning("User entered non-integer value for blueprint selection.")


def main():
    """
    Main entry point for the blueprint runner CLI.
    """
    parser = argparse.ArgumentParser(description="Blueprint Runner CLI")
    parser.add_argument(
        "blueprint_path",
        type=str,
        help="Path to the blueprint's Python file."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the blueprint in interactive mode."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["cli", "rest", "mcp-host"],
        default="cli",
        help="Mode to run the blueprint."
    )

    args = parser.parse_args()

    try:
        blueprint_module = load_blueprint(args.blueprint_path)
    except ImportError as e:
        print(color_text(str(e), "red"))
        sys.exit(1)

    if args.interactive:
        try:
            run_blueprint_interactive(blueprint_module)
        except AttributeError as e:
            print(color_text(str(e), "red"))
            sys.exit(1)
    else:
        try:
            run_blueprint_framework(blueprint_module)
        except AttributeError as e:
            print(color_text(str(e), "red"))
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nReceived shutdown signal (Ctrl+C)")
        logger.info("Received shutdown signal (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(color_text(f"\nFatal error: {e}", "red"))
        sys.exit(1)
    finally:
        logger.info("Blueprint runner terminated.")
        sys.exit(0)
