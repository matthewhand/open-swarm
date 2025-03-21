"""
Agent utilities for blueprint initialization and discovery.
"""

import asyncio
import logging
import os
from swarm.extensions.blueprint.common_utils import get_agent_name

logger = logging.getLogger(__name__)

def initialize_agents(blueprint):
    """
    Initialize agents if create_agents is overridden and update blueprint's agents.
    """
    agents = blueprint.create_agents()
    for agent_name, agent in agents.items():
        if hasattr(agent, "nemo_guardrails_config") and agent.nemo_guardrails_config:
            guardrails_path = os.path.join("nemo_guardrails", agent.nemo_guardrails_config)
            try:
                from nemoguardrails import LLMRails, RailsConfig  # type: ignore
                if RailsConfig:
                    rails_config = RailsConfig.from_path(guardrails_path)
                    agent.nemo_guardrails_instance = LLMRails(rails_config)
                    logger.debug(f"Loaded NeMo Guardrails for agent: {get_agent_name(agent)}")
                else:
                    logger.debug("RailsConfig is not available; skipping NeMo Guardrails for agent.")
            except Exception as e:
                logger.warning(f"Failed to load NeMo Guardrails for agent {get_agent_name(agent)}: {e}")
    blueprint.swarm.agents.update(agents)
    blueprint.starting_agent = agents.get("default") or (next(iter(agents.values())) if agents else None)
    logger.debug(f"Registered agents: {list(agents.keys())}")

    if blueprint.starting_agent:
        discover_initial_agent_assets(blueprint, blueprint.starting_agent)
    else:
        logger.debug("No starting agent set; subclass may assign later.")

def discover_initial_agent_assets(blueprint, agent):
    """
    Perform initial tool and resource discovery for the given agent.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(blueprint._discover_tools_for_agent(agent))
        asyncio.create_task(blueprint._discover_resources_for_agent(agent))
    else:
        asyncio.run(blueprint._discover_tools_for_agent(agent))
        asyncio.run(blueprint._discover_resources_for_agent(agent))
    logger.debug(f"Completed initial tool/resource discovery for agent: {get_agent_name(agent)}")

__all__ = ["initialize_agents", "discover_initial_agent_assets"]
