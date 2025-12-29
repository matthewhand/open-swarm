import logging
from typing import Any

from swarm.utils.color_utils import color_text

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        return None  # Updated to remove 'default blueprint'

    print("\nAvailable Blueprints:")
    for idx, (key, metadata) in enumerate(blueprints_metadata.items(), start=1):
        print(f"{idx}. {metadata.get('title', key)} - {metadata.get('description', 'No description available')}")

    while True:
        try:
            choice = int(input("\nEnter the number of the blueprint you want to run (0 to cancel): "))
            if choice == 0:
                logger.info("User chose to cancel blueprint selection.")
                return None  # Explicitly return None when selection is canceled
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
