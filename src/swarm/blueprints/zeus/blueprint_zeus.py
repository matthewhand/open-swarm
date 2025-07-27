"""
Zeus Blueprint
A general-purpose coordinator agent using other gods as tools.
"""

import inspect  # For isasyncgenfunction and iscoroutinefunction
import os
import sys
import time

from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_ux import BlueprintUXImproved


class ZeusSpinner:
    FRAMES = ["Generating.", "Generating..", "Generating...", "Running..."]
    LONG_WAIT_MSG = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10

    def __init__(self):
        self._idx = 0
        self._start_time = None
        self._last_frame = self.FRAMES[0]

    def start(self):
        self._start_time = time.time()
        self._idx = 0
        self._last_frame = self.FRAMES[0]

    def _spin(self):
        self._idx = (self._idx + 1) % len(self.FRAMES)
        self._last_frame = self.FRAMES[self._idx]

    def current_spinner_state(self):
        if self._start_time and (time.time() - self._start_time) > self.SLOW_THRESHOLD:
            return self.LONG_WAIT_MSG
        return self._last_frame

    def stop(self):
        self._start_time = None

class ZeusCoordinatorBlueprint(BlueprintBase):
    NAME = "zeus"
    CLI_NAME = "zeus"
    DESCRIPTION = "Zeus: The coordinator agent for Open Swarm, using all other gods as tools."
    VERSION = "1.0.0"

    @classmethod
    def get_metadata(cls):
        return {
            "name": cls.NAME,
            "cli": cls.CLI_NAME,
            "description": cls.DESCRIPTION,
            "version": cls.VERSION,
        }

    def __init__(self, blueprint_id: str = None, config_path=None, **kwargs):
        if blueprint_id is None:
            blueprint_id = "zeus_test"
        self.debug = bool(kwargs.pop("debug", False))
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        self.cli_spinner = ZeusSpinner()

    def assist(self, user_input, context=None):
        self.cli_spinner.start()
        display_operation_box(
            title="Zeus Assistance",
            content=f"How can Zeus help you today? You said: {user_input}",
            spinner_state=self.cli_spinner.current_spinner_state(),
            emoji="⚡"
        )
        self.cli_spinner.stop()
        return f"How can Zeus help you today? You said: {user_input}"

    async def run(self, messages, **kwargs):
        logger = getattr(self, 'logger', None) or __import__('logging').getLogger(__name__)
        logger.info("ZeusCoordinatorBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        ux = BlueprintUXImproved(style="serious")

        initial_spinner_content = ux.spinner(0, taking_long=False)
        yield {"messages": [{"role": "assistant", "content": initial_spinner_content}]}

        spinner_idx_loop = 0
        start_time = time.time()
        spinner_yield_interval = 1.0
        last_spinner_time = start_time
        yielded_spinner_in_loop = False
        result_chunks = []

        try:
            agent = self.create_starting_agent()

            # Check if agent.run is an async generator function or a coroutine function that returns an async generator
            if inspect.isasyncgenfunction(getattr(agent, 'run', None)):
                runner_gen = agent.run(messages, **kwargs)
            elif inspect.iscoroutinefunction(getattr(agent, 'run', None)):
                # If it's a coroutine function, it might return an async generator
                # This path assumes it does, common for SDK Agent.run
                # For DummyAgent in tests, its run is already an async gen function.
                potential_gen = await agent.run(messages, **kwargs)
                if inspect.isasyncgen(potential_gen):
                    runner_gen = potential_gen
                else: # Fallback if it's a coroutine that doesn't return a generator
                    logger.warning("Agent's async run method did not return an async generator. Using fallback.")
                    async def _single_item_gen(): yield potential_gen # Wrap single result
                    runner_gen = _single_item_gen()
            else: # Fallback for non-async or missing run
                 logger.warning("Agent's run method is not an async generator or coroutine. Using test-mode fallback.")
                 async def _dummy_agent_run_wrapper():
                     yield {"messages": [{"role": "assistant", "content": "[TEST-MODE] Agent run method not suitable for async iteration."}]}
                 runner_gen = _dummy_agent_run_wrapper()

            while True:
                now = time.time()
                try:
                    chunk = await runner_gen.__anext__()
                    result_chunks.append(chunk)

                    if chunk and isinstance(chunk, dict) and "messages" in chunk:
                        if self.debug or os.environ.get("SWARM_TEST_MODE") == "1":
                            yield chunk
                        else:
                            content = chunk["messages"][0]["content"] if chunk["messages"] else ""
                            summary = ux.summary("Operation", len(result_chunks), {"instruction": instruction[:40]})
                            box = ux.ansi_emoji_box(
                                title="Zeus Result",
                                content=content,
                                summary=summary,
                                params={"instruction": instruction[:40]},
                                result_count=len(result_chunks),
                                op_type="run",
                                status="success"
                            )
                            yield {"messages": [{"role": "assistant", "content": box}]}
                    else:
                        yield chunk
                    yielded_spinner_in_loop = False
                except StopAsyncIteration:
                    break
                except Exception as e_inner_loop:
                    logger.error(f"Error from agent during run: {e_inner_loop}", exc_info=True)
                    if now - last_spinner_time >= spinner_yield_interval:
                        taking_long = (now - start_time > 10)
                        spinner_msg_content = ux.spinner(spinner_idx_loop, taking_long=taking_long)
                        yield {"messages": [{"role": "assistant", "content": spinner_msg_content}]}
                        spinner_idx_loop += 1
                        last_spinner_time = now
                        yielded_spinner_in_loop = True

            if not result_chunks and not yielded_spinner_in_loop:
                fallback_spinner_content = ux.spinner(0, taking_long=False)
                yield {"messages": [{"role": "assistant", "content": fallback_spinner_content}]}

        except Exception as e_outer:
            logger.error(f"Critical error during Zeus run setup or outer loop: {e_outer}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {str(e_outer)}"}]}

    def create_starting_agent(self, mcp_servers=None):
        from agents import Agent
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI

        model_profile_name = "default"
        if hasattr(self, 'config') and self.config:
            blueprint_specific_settings = self.config.get("blueprints", {}).get(self.NAME, {})
            model_profile_name = blueprint_specific_settings.get("model_profile", self.config.get('llm_profile', 'default'))

        llm_profile_data = {}
        if hasattr(self, 'get_llm_profile'): # Ensure method exists
             try:
                 llm_profile_data = self.get_llm_profile(model_profile_name)
             except ValueError as e: # Handle case where profile might not be found by get_llm_profile
                 logger.warning(f"Could not get LLM profile '{model_profile_name}': {e}. Using fallbacks.")
                 llm_profile_data = {}


        model_name_to_use = llm_profile_data.get("model", os.environ.get("DEFAULT_LLM", "gpt-3.5-turbo"))
        api_key = llm_profile_data.get("api_key", os.environ.get('OPENAI_API_KEY', 'sk-test')) # Ensure sk-test is only for tests
        base_url = llm_profile_data.get("base_url", os.environ.get("OPENAI_BASE_URL"))

        client_params = {"api_key": api_key}
        if base_url:
            client_params["base_url"] = base_url
        openai_client = AsyncOpenAI(**client_params)

        model_instance = OpenAIChatCompletionsModel(model=model_name_to_use, openai_client=openai_client)

        pantheon_names = [
            ("Odin", "Delegate architecture, design, and research tasks."),
            ("Hermes", "Delegate technical planning and system checks."),
            ("Hephaestus", "Delegate core coding implementation tasks."),
            ("Hecate", "Delegate specific, smaller coding tasks (usually requested by Hephaestus)."),
            ("Thoth", "Delegate database updates or code management tasks."),
            ("Mnemosyne", "Delegate DevOps, deployment, or workflow optimization tasks."),
            ("Chronos", "Delegate documentation writing tasks.")
        ]
        pantheon_agents = []
        for name, desc in pantheon_names:
            pantheon_agents.append(
                Agent(
                    name=name,
                    model=model_instance,
                    instructions=f"You are {name}, {desc}",
                    tools=[],
                    mcp_servers=mcp_servers or []
                )
            )
        pantheon_tools = [a.as_tool(tool_name=a.name, tool_description=desc) for a, (_, desc) in zip(pantheon_agents, pantheon_names, strict=False)]

        zeus_instructions = """
You are Zeus, Product Owner and Coordinator of the Divine Ops team.
Your goal is to manage the software development lifecycle based on user requests.
1. Understand the user's request.
2. Delegate tasks to the appropriate specialist agent using their Agent Tool.
3. Review results and provide feedback or request revisions.
4. Integrate results and ensure the solution meets requirements.
5. Provide the final update to the user.
Available Agent Tools: Odin, Hermes, Hephaestus, Hecate, Thoth, Mnemosyne, Chronos.
"""
        agent = Agent(
            name="Zeus",
            model=model_instance,
            instructions=zeus_instructions,
            tools=pantheon_tools,
            mcp_servers=mcp_servers or []
        )
        return agent

if __name__ == "__main__":
    import asyncio
    print("\033[1;36m\nZeus CLI Demo\033[0m") # Simplified banner
    # Ensure blueprint is initialized for CLI context (debug=True for raw output)
    blueprint = ZeusCoordinatorBlueprint(blueprint_id="cli-demo", debug=True)

    cli_spinner_instance = ZeusSpinner()

    async def run_and_print_demo():
        cli_spinner_instance.start()
        try:
            # Use a more complex prompt for demo if desired
            demo_messages = [{"role": "user", "content": "Hello Zeus, please outline a new feature: user authentication."}]
            async for response_item in blueprint.run(demo_messages):
                content_to_print = str(response_item) # Default to string representation
                if isinstance(response_item, dict) and "messages" in response_item and response_item["messages"]:
                    # Since debug=True for CLI demo, this should be the raw agent output
                    content_to_print = response_item["messages"][0].get("content", str(response_item))

                sys.stdout.write(f"\r{' ' * 80}\r")
                sys.stdout.write(f"{content_to_print}\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Demo error: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
        finally:
            cli_spinner_instance.stop()
            sys.stdout.write("Demo complete.\n")

    asyncio.run(run_and_print_demo())

ZeusBlueprint = ZeusCoordinatorBlueprint
