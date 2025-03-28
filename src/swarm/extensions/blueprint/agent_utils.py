"""
agent_utils.py

Utility functions for agent operations used in blueprints.
This module has been updated to remove dependency on swarm.types;
instead, it now imports Agent from the openai-agents SDK.
"""

from agents.agent import Agent  # Updated import

def get_agent_name(agent: Agent) -> str:
    """
    Returns the name of the agent.
    """
    return agent.name

def initialize_agents(blueprint) -> dict:
    """
    Initializes agents by calling the blueprint's create_agents() method.
    """
    return blueprint.create_agents()
