"""
Flock Blueprint — A coordinated group of agents working together on tasks.
"""

from swarm.core.blueprint_base import BlueprintBase


class FlockBlueprint(BlueprintBase):
    """A coordinated group of agents (a flock) that collaboratively work on tasks."""

    metadata = {
        "name": "flock",
        "emoji": "🐦",
        "description": "A coordinated group of agents collaboratively working on tasks.",
        "examples": [
            "swarm-cli launch flock --message \"Research and summarize recent AI news\""
        ],
        "commands": [],
        "branding": "Unified ANSI/emoji box UX, spinner, progress, summary",
    }

    def create_starting_agent(self, mcp_servers=None):
        from agents import Agent

        model_instance = self._get_model_instance(self.config.get("llm_profile", "default"))
        return Agent(
            name="FlockLeader",
            model=model_instance,
            instructions="You are the Flock Leader, coordinating a group of agents. Break down complex tasks and synthesize results from your team.",
            mcp_servers=mcp_servers or [],
        )
