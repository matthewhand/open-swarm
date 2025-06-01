"""
Utility functions for blueprint management.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict
from .blueprint_discovery import discover_blueprints

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

class BlueprintFunctionTool:
    """
    A callable tool that invokes another blueprint as a synchronous function.
    """
    def __init__(self, blueprint_name: str):
        self.name = blueprint_name

    def __call__(self, instruction: str) -> str:
        """Run the specified blueprint with the given instruction and return the final content."""
        # Discover bundled blueprints in the package
        base_dir = Path(__file__).resolve().parent.parent / 'blueprints'
        blueprints = discover_blueprints(str(base_dir))
        if self.name not in blueprints:
            raise ValueError(f"Blueprint '{self.name}' not found")
        bp_cls = blueprints[self.name]
        instance = bp_cls(blueprint_id=self.name)
        last_content = ''
        async def runner():
            nonlocal last_content
            async for chunk in instance.run([{'role': 'user', 'content': instruction}]):
                msgs = chunk.get('messages', [])
                if msgs:
                    last_content = msgs[-1].get('content', last_content)
            return last_content
        return asyncio.run(runner())

def blueprint_tool(blueprint_name: str) -> BlueprintFunctionTool:
    """Factory to create a BlueprintFunctionTool for the given blueprint name."""
    return BlueprintFunctionTool(blueprint_name)
