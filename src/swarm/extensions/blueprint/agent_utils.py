"""
Agent utility functions for Swarm blueprints
"""

import logging
import os
from typing import Dict, List, Any, Callable, Optional
import asyncio
from swarm.types import Agent

logger = logging.getLogger(__name__)

def get_agent_name(agent: Agent) -> str:
    """Extract an agent's name, defaulting to its class name if not explicitly set."""
    return getattr(agent, 'name', agent.__class__.__name__)

async def discover_tools_for_agent(agent: Agent, blueprint: Any) -> List[Any]:
    """Asynchronously discover tools available for an agent within a blueprint."""
    return getattr(blueprint, '_discovered_tools', {}).get(get_agent_name(agent), [])

async def discover_resources_for_agent(agent: Agent, blueprint: Any) -> List[Any]:
    """Asynchronously discover resources available for an agent within a blueprint."""
    return getattr(blueprint, '_discovered_resources', {}).get(get_agent_name(agent), [])

def initialize_agents(blueprint: Any) -> None:
    """Initialize agents defined in the blueprint's create_agents method."""
    if not callable(getattr(blueprint, 'create_agents', None)):
         logger.error(f"Blueprint {blueprint.__class__.__name__} has no callable create_agents method.")
         return

    agents = blueprint.create_agents()
    if not isinstance(agents, dict):
        logger.error(f"Blueprint {blueprint.__class__.__name__}.create_agents must return a dict, got {type(agents)}")
        return

    if hasattr(blueprint, 'swarm') and hasattr(blueprint.swarm, 'agents'):
        blueprint.swarm.agents.update(agents)
    else:
        logger.error("Blueprint or its swarm instance lacks an 'agents' attribute to update.")
        return

    if not blueprint.starting_agent and agents:
        first_agent_name = next(iter(agents.keys()))
        blueprint.starting_agent = agents[first_agent_name]
        logger.debug(f"Set default starting agent: {first_agent_name}")
