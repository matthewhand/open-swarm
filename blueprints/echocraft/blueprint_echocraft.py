import logging
from typing import Dict, Any, Optional

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
        # Default instructions if none provided
        effective_instructions = instructions or "You are an echo agent. Repeat the user's input exactly."
        # Pass relevant kwargs to the base Agent class
        # Make sure **kwargs ONLY contains arguments accepted by LibraryAgent.__init__
        # Likely candidates: name, instructions, model, model_settings, tools, metadata, etc.
        # DO NOT pass api_key, base_url etc. here.
        logger.debug(f"EchoAgent.__init__ called with name={name}, instructions='{effective_instructions}', kwargs={kwargs}")
        super().__init__(name=name, instructions=effective_instructions, **kwargs)
        logger.debug(f"EchoAgent super().__init__ completed.")

    # Note: agents.Agent itself doesn't have a run method.
    # The logic is handled by agents.Runner.run(agent=self, input=...)


# --- EchoCraftBlueprint Definition ---
class EchoCraftBlueprint(BlueprintBase):
    """
    A simple blueprint demonstrating the Swarm framework.
    It uses an agent that just echoes back the input.
    """

    @property
    def name(self) -> str:
        return "echocraft"

    def description(self) -> str:
        return "A simple echo agent blueprint."

    def create_starting_agent(self) -> LibraryAgent:
        """Creates the initial EchoAgent instance."""
        logger.info("Creating EchoAgent")
        # Pass necessary parameters derived from the loaded config/profile
        # ONLY include parameters accepted by the LibraryAgent constructor
        agent_kwargs = {
            "model": self.llm_profile.get("model"),
            "model_settings": ModelSettings.ModelSettings(
                temperature=self.llm_profile.get("temperature"),
                max_tokens=self.llm_profile.get("max_tokens")
                # Add other relevant settings from ModelSettings if needed
            ),
            # "tools": [], # Example if tools were needed
            # "metadata": {}, # Example if metadata was needed
        }
        # Filter out None values from ALLOWED arguments before passing
        filtered_agent_kwargs = {k: v for k, v in agent_kwargs.items() if v is not None}
        logger.debug(f"Instantiating EchoAgent with filtered kwargs: {filtered_agent_kwargs}")
        try:
             # Pass only the filtered, known-good kwargs
            agent = EchoAgent(
                name="EchoAgent", # Can still set name explicitly
                instructions="You are an echo agent. Repeat the user's input exactly.", # Can set instructions
                **filtered_agent_kwargs
            )
            logger.debug(f"EchoAgent successfully instantiated: {agent}")
            return agent
        except Exception as e:
             logger.error(f"Failed to instantiate EchoAgent with kwargs {filtered_agent_kwargs}: {e}", exc_info=True)
             raise

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the EchoAgent using the agents.Runner.
        """
        logger.info(f"EchoCraftBlueprint run called with input: {input_data}")
        agent = self.create_starting_agent() # Get the configured agent

        user_input_text = input_data.get("input")
        if user_input_text is None:
            logger.warning("No 'input' key found in input_data for EchoCraftBlueprint run.")
            return {"output": "Error: No input provided."}

        # Execute the agent using the runner instance (should be mocked in tests)
        logger.debug(f"Running agent {agent.name} via runner {self.runner} (Type: {type(self.runner)})")
        try:
            run_result: RunResult = await self.runner.run(agent=agent, input=user_input_text)
            logger.debug(f"Runner execution finished. Result: {run_result}")

            if run_result and hasattr(run_result, 'final_output'):
                if isinstance(run_result.final_output, dict):
                    final_output = run_result.final_output
                elif isinstance(run_result.final_output, str):
                     final_output = {"output": run_result.final_output}
                else:
                    logger.warning(f"Unexpected final_output type: {type(run_result.final_output)}. Returning as string.")
                    final_output = {"output": str(run_result.final_output)}
            else:
                 logger.warning("RunResult or final_output missing or malformed.")
                 final_output = {"output": "Error: Agent execution did not produce expected output."}

            logger.info(f"EchoCraftBlueprint run returning: {final_output}")
            return final_output

        except Exception as e:
            # Log the specific exception during runner execution
            logger.exception(f"Error during runner.run execution: {e}", exc_info=True)
            return {"output": f"Error: An exception occurred during agent run: {e}"}

