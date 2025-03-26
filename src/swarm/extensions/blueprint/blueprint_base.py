"""
Swarm Blueprint Base Module (Sync Interactive Mode)
"""

import asyncio
import json
import logging
from src.swarm.utils.message_sequence import repair_message_payload, validate_message_sequence
from src.swarm.utils.context_utils import truncate_message_history, get_token_count
import os
import uuid
import sys
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from pathlib import Path
from swarm.core import Swarm
from swarm.extensions.config.config_loader import load_server_config
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data
from swarm.utils.context_utils import get_token_count, truncate_message_history
from swarm.extensions.blueprint.agent_utils import (
    get_agent_name,
    discover_tools_for_agent,
    discover_resources_for_agent,
    initialize_agents
)
from swarm.extensions.blueprint.django_utils import register_django_components
from swarm.extensions.blueprint.spinner import Spinner
from swarm.extensions.blueprint.output_utils import pretty_print_response
from dotenv import load_dotenv
import argparse
from swarm.types import Agent, Response

logger = logging.getLogger(__name__)

class BlueprintBase(ABC):
    """Base class for Swarm blueprints with sync interactive mode and Django integration."""

    def __init__(
        self,
        config: dict,
        auto_complete_task: bool = False,
        update_user_goal: bool = False,
        update_user_goal_frequency: int = 5,
        skip_django_registration: bool = False,
        record_chat: bool = False,
        log_file_path: Optional[str] = None,
        debug: bool = False,
        use_markdown: bool = False,
        **kwargs
    ):
        self.auto_complete_task = auto_complete_task
        self.update_user_goal = update_user_goal
        self.update_user_goal_frequency = max(1, update_user_goal_frequency)
        self.last_goal_update_count = 0
        self.record_chat = record_chat
        self.conversation_id = str(uuid.uuid4()) if record_chat else None
        self.log_file_path = log_file_path
        self.debug = debug or DEBUG
        self.use_markdown = use_markdown
        self._urls_registered = False

        if self.use_markdown:
            logger.debug("Markdown rendering enabled (if rich is available).")
        logger.debug(f"Initializing {self.__class__.__name__} with config: {redact_sensitive_data(config)}")
        if not hasattr(self, 'metadata') or not isinstance(self.metadata, dict):
            raise AssertionError(f"{self.__class__.__name__} must define a 'metadata' property returning a dictionary.")

        self.truncation_mode = os.getenv("SWARM_TRUNCATION_MODE", "pairs").lower()
        self.max_context_tokens = max(1, self.metadata.get("max_context_tokens", 8000))
        self.max_context_messages = max(1, self.metadata.get("max_context_messages", 50))
        logger.debug(f"Truncation settings: mode={self.truncation_mode}, max_tokens={self.max_context_tokens}, max_messages={self.max_context_messages}")

        load_dotenv()
        logger.debug("Loaded environment variables from .env.")

        self.config = config
        self.skip_django_registration = skip_django_registration or not os.environ.get("DJANGO_SETTINGS_MODULE")
        self.swarm = kwargs.get('swarm_instance') or Swarm(config=self.config, debug=self.debug)
        logger.debug("Swarm instance initialized.")

        self.context_variables: Dict[str, Any] = {"user_goal": ""}
        self.starting_agent = None
        self._discovered_tools: Dict[str, List[Any]] = {}
        self._discovered_resources: Dict[str, List[Any]] = {}
        self.spinner = Spinner(interactive=not kwargs.get('non_interactive', False))

        required_env_vars = set(self.metadata.get('env_vars', []))
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing environment variables for {self.metadata.get('title', self.__class__.__name__)}: {', '.join(missing_vars)}")

        self.required_mcp_servers = self.metadata.get('required_mcp_servers', [])
        logger.debug(f"Required MCP servers: {self.required_mcp_servers}")

        if self._is_create_agents_overridden():
            initialize_agents(self)
        register_django_components(self)

    def _is_create_agents_overridden(self) -> bool:
        """Check if the 'create_agents' method is overridden in the subclass."""
        return self.__class__.create_agents is not BlueprintBase.create_agents

    def truncate_message_history(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """Truncate message history using the centralized utility."""
        return truncate_message_history(messages, model, self.max_context_tokens, self.max_context_messages)

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Abstract property for blueprint metadata."""
        raise NotImplementedError

    def create_agents(self) -> Dict[str, Agent]:
        """Default agent creation method."""
        return {}

    def set_starting_agent(self, agent: Agent) -> None:
        """Set the starting agent and trigger initial asset discovery."""
        agent_name = get_agent_name(agent)
        logger.debug(f"Setting starting agent to: {agent_name}")
        self.starting_agent = agent
        self.context_variables["active_agent_name"] = agent_name

        try:
            loop = asyncio.get_event_loop()
            is_running = loop.is_running()
        except RuntimeError:
            loop = None
            is_running = False

        # Corrected calls: Pass only agent and config
        if loop and is_running:
            logger.debug(f"Scheduling async asset discovery for starting agent {agent_name}.")
            asyncio.ensure_future(discover_tools_for_agent(agent, self.swarm.config))
            asyncio.ensure_future(discover_resources_for_agent(agent, self.swarm.config))
        else:
            logger.debug(f"Running sync asset discovery for starting agent {agent_name}.")
            try:
                asyncio.run(discover_tools_for_agent(agent, self.swarm.config))
                asyncio.run(discover_resources_for_agent(agent, self.swarm.config))
            except RuntimeError as e:
                 if "cannot be called from a running event loop" in str(e): logger.error("Nested asyncio.run detected during sync discovery.")
                 else: raise e

    async def determine_active_agent(self) -> Optional[Agent]:
        """Determine the currently active agent."""
        active_agent_name = self.context_variables.get("active_agent_name")
        agent_to_use = None

        if active_agent_name and active_agent_name in self.swarm.agents:
             agent_to_use = self.swarm.agents[active_agent_name]
             logger.debug(f"Determined active agent from context: {active_agent_name}")
        elif self.starting_agent:
             agent_to_use = self.starting_agent
             active_agent_name = get_agent_name(agent_to_use)
             if self.context_variables.get("active_agent_name") != active_agent_name:
                  self.context_variables["active_agent_name"] = active_agent_name
                  logger.debug(f"Falling back to starting agent: {active_agent_name} and updating context.")
             else:
                  logger.debug(f"Using starting agent: {active_agent_name}")
        else:
             logger.error("Cannot determine active agent: No agent name in context and no starting agent set.")
             return None

        agent_name_cache_key = get_agent_name(agent_to_use)
        # Corrected calls: Pass only agent and config
        if agent_name_cache_key not in self._discovered_tools:
             logger.debug(f"Cache miss for tools of agent {agent_name_cache_key}. Discovering...")
             discovered_tools = await discover_tools_for_agent(agent_to_use, self.swarm.config)
             self._discovered_tools[agent_name_cache_key] = discovered_tools

        if agent_name_cache_key not in self._discovered_resources:
             logger.debug(f"Cache miss for resources of agent {agent_name_cache_key}. Discovering...")
             discovered_resources = await discover_resources_for_agent(agent_to_use, self.swarm.config)
             self._discovered_resources[agent_name_cache_key] = discovered_resources

        return agent_to_use

    # --- Core Execution Logic ---
    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Synchronous wrapper for the async execution logic."""
        return asyncio.run(self.run_with_context_async(messages, context_variables))

    async def run_with_context_async(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Asynchronously run the blueprint's logic."""
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables updated: {self.context_variables}")

        active_agent = await self.determine_active_agent()
        if not active_agent:
            logger.error("No active agent could be determined. Cannot proceed.")
            return {"response": Response(messages=[{"role": "assistant", "content": "Error: No active agent available."}], agent=None, context_variables=self.context_variables), "context_variables": self.context_variables}

        model = getattr(active_agent, 'model', None) or self.swarm.current_llm_config.get("model", "default")
        logger.debug(f"Using model: {model} for agent {get_agent_name(active_agent)}")

        truncated_messages = self.truncate_message_history(messages, model)
        validated_messages = validate_message_sequence(truncated_messages)
        repaired_messages = repair_message_payload(validated_messages, debug=self.debug)

        if not self.swarm.agents:
            logger.warning("No agents registered; returning default response.")
            return {"response": Response(messages=[{"role": "assistant", "content": "No agents available in Swarm."}], agent=None, context_variables=self.context_variables), "context_variables": self.context_variables}

        logger.debug(f"Running Swarm core with agent: {get_agent_name(active_agent)}")
        self.spinner.start(f"Generating response from {get_agent_name(active_agent)}")
        response_obj = None
        try:
            response_obj = await self.swarm.run(
                 agent=active_agent, messages=repaired_messages, context_variables=self.context_variables,
                 stream=False, debug=self.debug,
            )
        except Exception as e:
            logger.error(f"Swarm run failed: {e}", exc_info=True)
            response_obj = Response(messages=[{"role": "assistant", "content": f"An error occurred: {str(e)}"}], agent=active_agent, context_variables=self.context_variables)
        finally:
            self.spinner.stop()

        final_agent = active_agent
        updated_context = self.context_variables.copy()

        if response_obj:
             if hasattr(response_obj, 'agent') and response_obj.agent and get_agent_name(response_obj.agent) != get_agent_name(active_agent):
                 final_agent = response_obj.agent
                 new_agent_name = get_agent_name(final_agent)
                 updated_context["active_agent_name"] = new_agent_name
                 logger.debug(f"Agent handoff occurred. New active agent: {new_agent_name}")
                 # Corrected calls: Pass only agent and config
                 asyncio.ensure_future(discover_tools_for_agent(final_agent, self.swarm.config))
                 asyncio.ensure_future(discover_resources_for_agent(final_agent, self.swarm.config))
             if hasattr(response_obj, 'context_variables'):
                  updated_context.update(response_obj.context_variables)
        else:
            logger.error("Swarm run returned None or invalid response structure.")
            response_obj = Response(messages=[{"role": "assistant", "content": "Error processing the request."}], agent=active_agent, context_variables=updated_context)

        return {"response": response_obj, "context_variables": updated_context}

    def set_active_agent(self, agent_name: str) -> None:
        """Explicitly set the active agent by name and trigger asset discovery."""
        if agent_name in self.swarm.agents:
            self.context_variables["active_agent_name"] = agent_name
            agent = self.swarm.agents[agent_name]
            logger.debug(f"Explicitly setting active agent to: {agent_name}")
            # Corrected calls: Pass only agent and config
            if agent_name not in self._discovered_tools:
                 logger.debug(f"Discovering tools for explicitly set agent {agent_name}.")
                 try: asyncio.run(discover_tools_for_agent(agent, self.swarm.config))
                 except RuntimeError as e:
                      if "cannot be called from a running event loop" in str(e): logger.error("Cannot run sync discovery from within an async context (set_active_agent).")
                      else: raise e
            if agent_name not in self._discovered_resources:
                 logger.debug(f"Discovering resources for explicitly set agent {agent_name}.")
                 try: asyncio.run(discover_resources_for_agent(agent, self.swarm.config))
                 except RuntimeError as e:
                       if "cannot be called from a running event loop" in str(e): logger.error("Cannot run sync discovery from within an async context (set_active_agent).")
                       else: raise e
        else:
            logger.error(f"Attempted to set active agent to '{agent_name}', but agent not found.")

    # --- Task Completion & Goal Update Logic ---
    async def _is_task_done_async(self, user_goal: str, conversation_summary: str, last_assistant_message: str) -> bool:
        """Check if the task defined by user_goal is complete using an LLM call."""
        if not user_goal:
             logger.warning("Cannot check task completion: user_goal is empty.")
             return False

        system_prompt = os.getenv("TASK_DONE_PROMPT", "You are a completion checker. Respond with ONLY 'YES' or 'NO'.")
        user_prompt = os.getenv(
            "TASK_DONE_USER_PROMPT",
            "User's goal: {user_goal}\nConversation summary: {conversation_summary}\nLast assistant message: {last_assistant_message}\nIs the task fully complete? Answer only YES or NO."
        ).format(user_goal=user_goal, conversation_summary=conversation_summary, last_assistant_message=last_assistant_message)

        check_prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        client = self.swarm.client
        model_to_use = self.swarm.current_llm_config.get("model", self.swarm.model)

        try:
            response = await client.chat.completions.create(
                model=model_to_use, messages=check_prompt, max_tokens=5, temperature=0
            )
            if response.choices:
                 result_content = response.choices[0].message.content.strip().upper()
                 is_done = result_content.startswith("YES")
                 logger.debug(f"Task completion check (Goal: '{user_goal}', LLM Raw: '{result_content}'): {is_done}")
                 return is_done
            else:
                 logger.warning("LLM response for task completion check had no choices.")
                 return False
        except Exception as e:
            logger.error(f"Task completion check LLM call failed: {e}", exc_info=True)
            return False

    async def _update_user_goal_async(self, messages: List[Dict[str, str]]) -> None:
        """Update the 'user_goal' in context_variables based on conversation history using an LLM call."""
        if not messages:
            logger.debug("Cannot update goal: No messages provided.")
            return

        system_prompt = os.getenv(
            "UPDATE_GOAL_PROMPT",
            "You are an assistant that summarizes the user's primary objective from the conversation. Provide a concise, one-sentence summary."
        )
        conversation_text = "\n".join(f"{m['role']}: {m.get('content', '')}" for m in messages if m.get('content') or m.get('tool_calls'))
        if not conversation_text:
             logger.debug("Cannot update goal: No content in messages.")
             return

        user_prompt = os.getenv(
            "UPDATE_GOAL_USER_PROMPT",
            "Summarize the user's main goal based on this conversation:\n{conversation}"
        ).format(conversation=conversation_text)

        prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        client = self.swarm.client
        model_to_use = self.swarm.current_llm_config.get("model", self.swarm.model)

        try:
            response = await client.chat.completions.create(
                model=model_to_use, messages=prompt, max_tokens=60, temperature=0.3
            )
            if response.choices:
                 new_goal = response.choices[0].message.content.strip()
                 if new_goal:
                      self.context_variables["user_goal"] = new_goal
                      logger.debug(f"Updated user goal via LLM: {new_goal}")
                 else:
                      logger.warning("LLM goal update returned empty response.")
            else:
                 logger.warning("LLM response for goal update had no choices.")
        except Exception as e:
            logger.error(f"User goal update LLM call failed: {e}", exc_info=True)

    def task_completed(self, outcome: str) -> None:
        """Placeholder method potentially used by agents to signal task completion."""
        print(f"Task Outcome: {outcome}")
        print("continue")

    @property
    def prompt(self) -> str:
        """Return the custom prompt string, potentially from the active agent."""
        active_agent = self.swarm.agents.get(self.context_variables.get("active_agent_name"))
        return getattr(active_agent, 'prompt', getattr(self, "custom_user_prompt", "User: "))

    # --- Interactive & Non-Interactive Modes ---
    def interactive_mode(self, stream: bool = False) -> None:
        """Run the blueprint in interactive command-line mode."""
        from .interactive_mode import run_interactive_mode
        run_interactive_mode(self, stream)

    def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        """Run the blueprint non-interactively with a single instruction."""
        logger.debug(f"Starting non-interactive mode with instruction: {instruction}, stream={stream}")
        try:
             asyncio.run(self.non_interactive_mode_async(instruction, stream=stream))
        except RuntimeError as e:
             if "cannot be called from a running event loop" in str(e):
                  logger.error("Cannot start non_interactive_mode with asyncio.run from an existing event loop.")
             else: raise e

    async def non_interactive_mode_async(self, instruction: str, stream: bool = False) -> None:
        """Asynchronously run the blueprint non-interactively."""
        logger.debug(f"Starting async non-interactive mode with instruction: {instruction}, stream={stream}")
        if not self.swarm:
            logger.error("Swarm instance not initialized.")
            print("Error: Swarm framework not ready.")
            return

        print(f"--- {self.metadata.get('title', 'Blueprint')} Non-Interactive Mode ---")
        instructions = [line.strip() for line in instruction.splitlines() if line.strip()]
        if not instructions:
             print("No valid instruction provided.")
             return
        messages = [{"role": "user", "content": line} for line in instructions]

        if not self.starting_agent:
             if self.swarm.agents:
                 first_agent_name = next(iter(self.swarm.agents.keys()))
                 logger.warning(f"No starting agent explicitly set. Defaulting to first agent: {first_agent_name}")
                 self.set_starting_agent(self.swarm.agents[first_agent_name])
             else:
                 logger.error("No starting agent set and no agents defined.")
                 print("Error: No agent available to handle the instruction.")
                 return

        self.context_variables["user_goal"] = instruction
        self.context_variables["active_agent_name"] = get_agent_name(self.starting_agent)

        if stream:
            logger.debug("Running non-interactive in streaming mode.")
            response_generator = self.swarm.run(
                 agent=self.starting_agent, messages=messages, context_variables=self.context_variables,
                 stream=True, debug=self.debug,
            )
            final_response_data = await self._process_and_print_streaming_response_async(response_generator)
            if self.auto_complete_task:
                 logger.warning("Auto-completion is not fully supported with streaming in non-interactive mode.")
        else:
            logger.debug("Running non-interactive in non-streaming mode.")
            result = await self.run_with_context_async(messages, self.context_variables)
            swarm_response = result.get("response")
            self.context_variables = result.get("context_variables", self.context_variables)

            response_messages = []
            if hasattr(swarm_response, 'messages'): response_messages = swarm_response.messages
            elif isinstance(swarm_response, dict) and 'messages' in swarm_response: response_messages = swarm_response.get('messages', [])

            self._pretty_print_response(response_messages)
            if self.auto_complete_task and self.swarm.agents:
                logger.debug("Starting auto-completion task.")
                current_history = messages + response_messages
                await self._auto_complete_task_async(current_history, stream=False)

        print("--- Execution Completed ---")

    async def _process_and_print_streaming_response_async(self, response_generator):
        """Async helper to process and print streaming response chunks."""
        content = ""
        last_sender = self.context_variables.get("active_agent_name", "Assistant")
        final_response_chunk_data = None
        try:
            async for chunk in response_generator:
                if isinstance(chunk, dict) and "delim" in chunk:
                    if chunk["delim"] == "start" and not content:
                        print(f"\033[94m{last_sender}\033[0m: ", end="", flush=True)
                    elif chunk["delim"] == "end" and content:
                        print()
                        content = ""
                elif hasattr(chunk, 'choices') and chunk.choices:
                     delta = chunk.choices[0].delta
                     if delta and delta.content:
                          print(delta.content, end="", flush=True)
                          content += delta.content
                elif isinstance(chunk, dict) and "response" in chunk:
                     final_response_chunk_data = chunk["response"]
                     if hasattr(final_response_chunk_data, 'agent'):
                          last_sender = get_agent_name(final_response_chunk_data.agent)
                     if hasattr(final_response_chunk_data, 'context_variables'):
                          self.context_variables.update(final_response_chunk_data.context_variables)
                     logger.debug("Received final aggregated response chunk in stream.")
                elif isinstance(chunk, dict) and "error" in chunk:
                    logger.error(f"Error received during stream: {chunk['error']}")
                    print(f"\n[Stream Error: {chunk['error']}]")
        except Exception as e:
            logger.error(f"Error processing stream: {e}", exc_info=True)
            print("\n[Error during streaming output]")
        finally:
            if content: print()
        return final_response_chunk_data

    async def _auto_complete_task_async(self, current_history: List[Dict[str, str]], stream: bool) -> None:
        """Async helper for task auto-completion loop (non-streaming)."""
        max_auto_turns = 10
        auto_turn = 0
        while auto_turn < max_auto_turns:
            auto_turn += 1
            logger.debug(f"Auto-completion Turn: {auto_turn}/{max_auto_turns}")
            conversation_summary = " ".join(m.get("content", "") for m in current_history[-4:] if m.get("content"))
            last_assistant_msg = next((m.get("content", "") for m in reversed(current_history) if m.get("role") == "assistant" and m.get("content")), "")
            user_goal = self.context_variables.get("user_goal", "")

            # Call the renamed async method
            if await self._is_task_done_async(user_goal, conversation_summary, last_assistant_msg):
                print("\033[93m[System]\033[0m: Task detected as complete.")
                break

            logger.debug("Task not complete, running next auto-completion turn.")
            result = await self.run_with_context_async(current_history, self.context_variables)
            swarm_response = result.get("response")
            self.context_variables = result.get("context_variables", self.context_variables)

            new_messages = []
            if hasattr(swarm_response, 'messages'): new_messages = swarm_response.messages
            elif isinstance(swarm_response, dict) and 'messages' in swarm_response: new_messages = swarm_response.get('messages', [])

            if not new_messages:
                 logger.warning("Auto-completion turn yielded no new messages. Stopping.")
                 break

            self._pretty_print_response(new_messages)
            current_history.extend(new_messages)

        if auto_turn >= max_auto_turns:
             logger.warning("Auto-completion reached maximum turns limit.")
             print("\033[93m[System]\033[0m: Reached max auto-completion turns.")

    def _auto_complete_task(self, messages: List[Dict[str, str]], stream: bool) -> None:
        """Synchronous wrapper for task auto-completion."""
        if stream:
             logger.warning("Auto-completion skipped because streaming is enabled.")
             return
        logger.debug("Starting synchronous auto-completion task.")
        try:
             asyncio.run(self._auto_complete_task_async(messages, stream=False))
        except RuntimeError as e:
             if "cannot be called from a running event loop" in str(e):
                  logger.error("Cannot start _auto_complete_task with asyncio.run from an existing event loop.")
             else: raise e

    # --- Class Method for Entry Point ---
    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description=f"Run the {cls.__name__} blueprint.")
        parser.add_argument("--config", default="./swarm_config.json", help="Path to the swarm_config.json file.")
        parser.add_argument("--instruction", help="Single instruction for non-interactive mode.")
        parser.add_argument("--stream", action="store_true", help="Enable streaming output in non-interactive mode.")
        parser.add_argument("--auto-complete-task", action="store_true", help="Enable task auto-completion in non-interactive mode.")
        parser.add_argument("--update-user-goal", action="store_true", help="Enable dynamic goal updates using LLM.")
        parser.add_argument("--update-user-goal-frequency", type=int, default=5, help="Frequency (in messages) for updating user goal.")
        parser.add_argument("--log-file-path", help="Path for logging output (default: ~/.swarm/logs/<blueprint_name>.log).")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging to console instead of file.")
        parser.add_argument("--use-markdown", action="store_true", help="Enable markdown rendering for assistant responses.")
        args = parser.parse_args()

        root_logger = logging.getLogger()
        log_level = logging.DEBUG if args.debug or DEBUG else logging.INFO
        root_logger.setLevel(log_level)

        if root_logger.hasHandlers(): root_logger.handlers.clear()

        log_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s")
        log_handler = logging.StreamHandler(sys.stdout) if args.debug else logging.FileHandler(
            Path(args.log_file_path or Path.home() / ".swarm" / "logs" / f"{cls.__name__.lower()}.log").resolve(), mode='a'
        )
        log_handler.setFormatter(log_formatter)
        root_logger.addHandler(log_handler)
        logger.info(f"Logging initialized. Level: {logging.getLevelName(log_level)}. Destination: {getattr(log_handler, 'baseFilename', 'console')}")

        original_stderr = sys.stderr
        dev_null = None
        if not args.debug:
            try:
                dev_null = open(os.devnull, "w")
                sys.stderr = dev_null
                logger.info(f"Redirected stderr to {os.devnull}")
            except OSError as e: logger.warning(f"Could not redirect stderr: {e}")

        try:
            config_data = load_server_config(args.config)
            blueprint_instance = cls(
                config=config_data, auto_complete_task=args.auto_complete_task, update_user_goal=args.update_user_goal,
                update_user_goal_frequency=args.update_user_goal_frequency, log_file_path=str(getattr(log_handler, 'baseFilename', None)),
                debug=args.debug, use_markdown=args.use_markdown, non_interactive=bool(args.instruction)
            )
            if args.instruction:
                 asyncio.run(blueprint_instance.non_interactive_mode_async(args.instruction, stream=args.stream))
            else:
                blueprint_instance.interactive_mode(stream=args.stream)
        except Exception as e:
             logger.critical(f"Blueprint execution failed: {e}", exc_info=True)
             print(f"Critical Error: {e}", file=original_stderr)
        finally:
             if not args.debug and dev_null is not None:
                 sys.stderr = original_stderr
                 dev_null.close()
                 logger.debug("Restored stderr.")
             logger.info("Blueprint execution finished.")

if __name__ == "__main__":
    BlueprintBase.main()
