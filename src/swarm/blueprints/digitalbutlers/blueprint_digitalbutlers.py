"""
DigitalButlers Blueprint — A team of digital butler agents for household/office tasks.
"""

from swarm.core.blueprint_base import BlueprintBase


class DigitalButlersBlueprint(BlueprintBase):
    """A team of digital butler agents coordinating household and office tasks."""

    metadata = {
        "name": "digitalbutlers",
        "emoji": "🎩",
        "description": "A team of digital butler agents coordinating household and office tasks.",
        "examples": [
            "swarm-cli launch digitalbutlers --message \"Organize my schedule for today\""
        ],
        "commands": [],
        "branding": "Unified ANSI/emoji box UX, spinner, progress, summary",
    }

    def create_starting_agent(self, mcp_servers=None):
        from agents import Agent

        model_instance = self._get_model_instance(self.config.get("llm_profile", "default"))
        return Agent(
            name="HeadButler",
            model=model_instance,
            instructions="You are the Head Butler, a polite and efficient digital assistant. Help the user with scheduling, reminders, and organizational tasks.",
            mcp_servers=mcp_servers or [],
        )
