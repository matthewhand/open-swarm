"""
SuggestionBlueprint Class for Open Swarm.

This blueprint defines a single agent that generates structured JSON suggestions.
"""

import logging
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


class SuggestionBlueprint(BlueprintBase):
    """
    A blueprint that defines an agent for generating structured JSON suggestions.
    """

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Metadata for the SuggestionBlueprint.

        Returns:
            Dict[str, Any]: Dictionary containing title, description, required MCP servers, and environment variables.
        """
        return {
            "title": "Suggestion Integration Blueprint",
            "description": "An agent that provides structured suggestions for follow-up messages.",
            "required_mcp_servers": [],
            "cli_name": "suggest",
            "env_vars": [],
        }

    def create_agents(self) -> Dict[str, Agent]:
        """
        Create agents for this blueprint by defining their instructions
        and response format.

        Returns:
            Dict[str, Agent]: Dictionary containing all created agents.
        """
        logger.debug("Creating SuggestionAgent with structured JSON output.")

        # Ensure response format has required fields
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "suggestion_response",  # Required name field
                "schema": {  # Required schema field
                    "type": "object",
                    "properties": {
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 3,
                            "maxItems": 3
                        }
                    },
                    "required": ["suggestions"],
                    "additionalProperties": False
                }
            }
        }

        suggestion_agent = Agent(
            name="SuggestionAgent",
            instructions="Generate three structured follow-up questions in JSON format.",
            mcp_servers=[],
            env_vars={},
            functions=[],  # No function calls, just structured text response
            response_format=response_format,  # Structured output
        )

        self.set_starting_agent(suggestion_agent)  # Set as the starting agent

        logger.info("SuggestionAgent with structured output has been created.")
        return {"SuggestionAgent": suggestion_agent}


if __name__ == "__main__":
    SuggestionBlueprint.main()
