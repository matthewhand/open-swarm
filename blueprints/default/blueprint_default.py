# blueprints/default/blueprint_default.py

"""
Default Simple Agent Blueprint

This blueprint provides a simple agent that echoes user inputs.
"""

from typing import Dict, Any, Optional
from swarm import Agent
from open_swarm_mcp.blueprint_base import BlueprintBase

class DefaultBlueprint(BlueprintBase):
    """
    Default Simple Agent Blueprint Implementation.
    """

    def __init__(self):
        super().__init__()
        self._metadata = {
            "title": "Default Simple Agent",
            "description": "A simple agent that echoes user inputs.",
            "required_mcp_servers": [],
            "env_vars": []
        }

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    def validate_env_vars(self) -> None:
        """Validate that required environment variables are set."""
        # This blueprint does not require any environment variables.
        pass

    def create_agent(self) -> Agent:
        """Create and configure the default simple agent."""
        return Agent(
            name="DefaultAgent",
            instructions="""You are a simple agent that echoes user inputs.
Please repeat back what the user says.""",
            functions=[],
            # tool_choice=None,
            parallel_tool_calls=True
        )

    def execute(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the blueprint in framework integration mode.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary from the framework.

        Returns:
            Dict[str, Any]: Execution results containing status, messages, and metadata.
        """
        self.validate_env_vars()
        agent = self.create_agent()

        # Allow for message override from framework config
        default_message = {
            "role": "user",
            "content": "Hello, how are you?"
        }
        messages = config.get('messages', [default_message]) if config else [default_message]

        response = self.client.run(agent=agent, messages=messages)

        return {
            "status": "success",
            "messages": response.messages,
            "metadata": self.metadata
        }

# Entry point for standalone execution
if __name__ == "__main__":
    blueprint = DefaultBlueprint()
    try:
        blueprint.interactive_mode()
    except Exception as e:
        print(f"Error running Default Blueprint: {e}")
