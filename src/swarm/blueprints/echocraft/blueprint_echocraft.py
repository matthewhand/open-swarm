import logging
from typing import Dict, Any, Optional, AsyncGenerator, List # Import List

# Use the agents library components
from agents import Agent as LibraryAgent
from agents import Runner as LibraryRunner
from agents import model_settings as ModelSettings
from agents.result import RunResult

from swarm.extensions.blueprint.blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)

# --- EchoAgent Definition ---
class EchoAgent(LibraryAgent):
    """A simple agent that repeats the user's input."""
    def __init__(self, name="EchoAgent", instructions: Optional[str] = None, **kwargs):
        effective_instructions = instructions or "You are an echo agent. Repeat the user's input exactly."
        logger.debug(f"EchoAgent.__init__ called with name={name}, instructions='{effective_instructions}', kwargs={kwargs}")
        super().__init__(name=name, instructions=effective_instructions, **kwargs)
        logger.debug(f"EchoAgent super().__init__ completed.")

# --- EchoCraftBlueprint Definition ---
class EchoCraftBlueprint(BlueprintBase):
    """
    A simple blueprint demonstrating the Swarm framework.
    It uses an agent that just echoes back the input. Yields result for streaming.
    """
    @property
    def name(self) -> str: return "echocraft"
    def description(self) -> str: return "A simple echo agent blueprint."

    def create_starting_agent(self) -> LibraryAgent:
        logger.info("Creating EchoAgent")
        # Ensure llm_profile is loaded if needed by the agent
        # Example: Assuming model name comes from profile
        model_name = self.llm_profile.get("model") if self.llm_profile else "default-model"
        agent_kwargs = {
            "model": model_name,
            # Add other necessary kwargs based on EchoAgent's needs
            # "model_settings": ModelSettings.ModelSettings(temperature=self.llm_profile.get("temperature"), max_tokens=self.llm_profile.get("max_tokens"))
        }
        filtered_agent_kwargs = {k: v for k, v in agent_kwargs.items() if v is not None}
        logger.debug(f"Instantiating EchoAgent with filtered kwargs: {filtered_agent_kwargs}")
        try:
            # Pass only necessary args to EchoAgent.__init__
            agent = EchoAgent(name="EchoAgent", instructions="You are an echo agent. Repeat the user's input exactly.") # Removed **kwargs if not needed by EchoAgent directly
            logger.debug(f"EchoAgent successfully instantiated: {agent}")
            return agent
        except Exception as e:
            logger.error(f"Failed to instantiate EchoAgent with kwargs {filtered_agent_kwargs}: {e}", exc_info=True)
            raise

    # *** UPDATED: run now accepts messages list ***
    async def run(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the EchoAgent using the agents.Runner and yields the result.
        Accepts the OpenAI message list directly.
        """
        logger.info(f"EchoCraftBlueprint run called with messages: {messages}")
        # agent = self.create_starting_agent() # Agent creation might not be needed if run just echoes

        # *** UPDATED: Extract input from messages list ***
        user_input_text = "[No Input Found]" # Default fallback
        if messages and isinstance(messages[-1], dict): # Check if messages list is not empty and last item is a dict
            # Assuming the last message is the user's input
            user_input_text = messages[-1].get("content", "[No Content in Last Message]")
        logger.info(f"Extracted user input for echo: '{user_input_text}'")


        # Simulate running the agent and yielding the result
        logger.debug(f"Simulating agent run for echo.")
        try:
            # --- Simple Echo Simulation ---
            output_content = f"API Echo: {user_input_text}" # Changed prefix for clarity
            output_msg = {"role": "assistant", "content": output_content}
            final_result_chunk = {"messages": [output_msg]}
            # ----------------------------

            logger.info(f"EchoCraftBlueprint run yielding: {final_result_chunk}")
            yield final_result_chunk # Yield the result chunk

        except Exception as e:
            logger.exception(f"Error during EchoCraftBlueprint run simulation: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"Error: An exception occurred during execution: {e}"}]}

