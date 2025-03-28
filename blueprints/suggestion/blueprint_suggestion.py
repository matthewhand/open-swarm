import logging
import os
import sys
from typing import Dict, Any, List, TypedDict # Import TypedDict

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Use new Agent and Tool types ---
try:
    from agents import Agent # Only need Agent for this one
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
     print(f"ERROR: Failed to import 'agents' or 'BlueprintBase'. Is 'openai-agents' installed and src in PYTHONPATH? Details: {e}")
     sys.exit(1)

# Setup logger for this specific blueprint module
logger = logging.getLogger(__name__)

# --- Define the desired output structure ---
class SuggestionsOutput(TypedDict):
    suggestions: List[str]

# --- Define Agent ---
class SuggestionAgent(Agent):
    def __init__(self, **kwargs):
        # Instructions simplified slightly as output_type handles structure enforcement
        instructions = (
            "You are the SuggestionAgent. Your task is to analyze the user's input and generate exactly three relevant, concise follow-up questions or conversation starters.\n"
            "Format your response according to the required output structure."
            # Example removed as output_type should enforce it
        )

        super().__init__(
            name="SuggestionAgent",
            instructions=instructions,
            tools=[], # No function tools needed
            model="gpt-4o", # Needs a model capable of following JSON instructions
            # --- FIX: Use output_type instead of response_format ---
            output_type=SuggestionsOutput,
            # --- End Fix ---
            **kwargs
        )

# --- Define the Blueprint ---
class SuggestionBlueprint(BlueprintBase):
    """ A blueprint that defines an agent for generating structured JSON suggestions using output_type. """

    @property
    def metadata(self) -> Dict[str, Any]:
        """ Metadata for the SuggestionBlueprint. """
        return {
            "title": "Suggestion Blueprint (Structured Output)",
            "description": "An agent that provides structured suggestions using Agent(output_type=...).",
            "version": "1.1.0", # Version bump
            "author": "Open Swarm Team",
            "required_mcp_servers": [],
            "cli_name": "suggest",
            "env_vars": ["OPENAI_API_KEY"],
        }

    def create_agents(self) -> Dict[str, Agent]:
        """ Create the SuggestionAgent. """
        logger.debug("Creating agents for SuggestionBlueprint.")
        suggestion_agent = SuggestionAgent()
        return {"SuggestionAgent": suggestion_agent}


if __name__ == "__main__":
    SuggestionBlueprint.main()
