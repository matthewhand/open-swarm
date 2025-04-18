"""
Utility functions for blueprint management.
"""

def filter_blueprints(all_blueprints: dict, allowed_blueprints_str: str) -> dict:
    """
    Filters the given blueprints dictionary using a comma-separated string of allowed blueprint keys.

    Args:
        all_blueprints (dict): A dictionary containing all discovered blueprints.
        allowed_blueprints_str (str): A comma-separated string of allowed blueprint keys.

    Returns:
        dict: A dictionary containing only the blueprints whose keys are present in the allowed list.
    """
    allowed_list = [bp.strip() for bp in allowed_blueprints_str.split(",")]
    return {k: v for k, v in all_blueprints.items() if k in allowed_list}
