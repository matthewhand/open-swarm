"""
Swarm Blueprint Base Module (Sync Interactive Mode)
"""

import asyncio
import json
import logging
# Import the standalone function
from .output_utils import pretty_print_response
# --- Removed relative imports, use absolute paths ---
from swarm.utils.message_sequence import repair_message_payload, validate_message_sequence
from swarm.utils.context_utils import truncate_message_history, get_token_count
# --- End Removed relative imports ---
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
# from swarm.utils.context_utils import get_token_count, truncate_message_history # Already imported above
from swarm.extensions.blueprint.agent_utils import (
    get_agent_name,
    discover_tools_for_agent, # Keep for potential future use, but core.py handles discovery now
    discover_resources_for_agent, # Keep for potential future use
    initialize_agents
)
from swarm.extensions.blueprint.django_utils import register_django_components
from swarm.extensions.blueprint.spinner import Spinner
# from swarm.extensions.blueprint.output_utils import pretty_print_response # Imported above
from dotenv import load_dotenv
import argparse
from swarm.types import Agent, Response, ChatMessage # Added ChatMessage

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
        self._urls_registered = False # Track if URLs have been registered for this instance

        if self.use_markdown:
            logger.debug("Markdown rendering enabled (if rich is available).")
        logger.debug(f"Initializing {self.__class__.__name__} with config: {redact_sensitive_data(config)}")
        if not hasattr(self, 'metadata') or not isinstance(self.metadata, dict):
            # Ensure metadata is available early
            try:
                 _ = self.metadata # Call property getter
                 if not isinstance(self.metadata, dict): raise TypeError("Metadata is not a dict")
            except (AttributeError, NotImplementedError, TypeError) as e:
                 raise AssertionError(f"{self.__class__.__name__} must define a 'metadata' property returning a dictionary. Error: {e}")


        self.truncation_mode = os.getenv("SWARM_TRUNCATION_MODE", "pairs").lower()
        # Get limits from metadata safely
        meta = self.metadata
        self.max_context_tokens = max(1, meta.get("max_context_tokens", 8000))
        self.max_context_messages = max(1, meta.get("max_context_messages", 50))
        logger.debug(f"Truncation settings: mode={self.truncation_mode}, max_tokens={self.max_context_tokens}, max_messages={self.max_context_messages}")

        load_dotenv()
        logger.debug("Loaded environment variables from .env (if present).")

        self.config = config
        self.skip_django_registration = skip_django_registration or not os.environ.get("DJANGO_SETTINGS_MODULE")
        # Pass debug flag to Swarm constructor
        self.swarm = kwargs.get('swarm_instance') or Swarm(config=self.config, debug=self.debug)
        logger.debug("Swarm instance initialized.")

        self.context_variables: Dict[str, Any] = {"user_goal": ""}
        self.starting_agent = None # Will be set by create_agents/set_starting_agent
        # Caches for discovered assets (though Swarm core might handle this now)
        self._discovered_tools: Dict[str, List[Any]] = {}
        self._discovered_resources: Dict[str, List[Any]] = {}
        self.spinner = Spinner(interactive=not kwargs.get('non_interactive', False))

        # Check required env vars from metadata
        required_env_vars = set(meta.get('env_vars', []))
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing environment variables for {meta.get('title', self.__class__.__name__)}: {', '.join(missing_vars)}")

        self.required_mcp_servers = meta.get('required_mcp_servers', [])
        logger.debug(f"Required MCP servers listed in metadata: {self.required_mcp_servers}")

        # Initialize agents if overridden and register Django components
        if self._is_create_agents_overridden():
            initialize_agents(self) # This calls create_agents and updates self.swarm.agents
        # Register Django components AFTER swarm is initialized and agents might be created
        register_django_components(self)

    def _is_create_agents_overridden(self) -> bool:
        """Check if the 'create_agents' method is overridden in the subclass."""
        # Ensure the comparison works correctly even with inheritance layers
        return getattr(self.__class__, 'create_agents') is not getattr(BlueprintBase, 'create_agents')

    def truncate_message_history(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """Truncate message history using the centralized utility."""
        # Use limits defined on the blueprint instance
        return truncate_message_history(messages, model, self.max_context_tokens, self.max_context_messages)

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Abstract property for blueprint metadata."""
        raise NotImplementedError("Subclasses must implement the 'metadata' property.")

    def create_agents(self) -> Dict[str, Agent]:
        """Default agent creation method. Subclasses should override this."""
        logger.debug(f"{self.__class__.__name__} using default create_agents (returns empty dict). Override if agents are needed.")
        return {}

    def set_starting_agent(self, agent: Agent) -> None:
        """Set the starting agent and update context."""
        agent_name = get_agent_name(agent)
        logger.debug(f"Setting starting agent to: {agent_name}")
        self.starting_agent = agent
        self.context_variables["active_agent_name"] = agent_name
        # Note: Tool/Resource discovery is now primarily handled within Swarm.run based on the active agent


    async def determine_active_agent(self) -> Optional[Agent]:
        """Determine the currently active agent based on context or starting agent."""
        active_agent_name = self.context_variables.get("active_agent_name")
        agent_to_use = None

        if active_agent_name and active_agent_name in self.swarm.agents:
             agent_to_use = self.swarm.agents[active_agent_name]
             logger.debug(f"Determined active agent from context: {active_agent_name}")
        elif self.starting_agent:
             # Fallback to starting agent if context doesn't specify or name is invalid
             agent_to_use = self.starting_agent
             starting_agent_name = get_agent_name(agent_to_use)
             if active_agent_name != starting_agent_name:
                  logger.warning(f"Active agent name '{active_agent_name}' invalid or not set, falling back to starting agent: {starting_agent_name}")
                  self.context_variables["active_agent_name"] = starting_agent_name
             else:
                  logger.debug(f"Using starting agent: {starting_agent_name}")
        else:
             # If no starting agent either, try the first agent registered in Swarm
             if self.swarm.agents:
                  first_agent_name = next(iter(self.swarm.agents))
                  agent_to_use = self.swarm.agents[first_agent_name]
                  logger.warning(f"No active or starting agent set. Defaulting to first registered agent: {first_agent_name}")
                  self.context_variables["active_agent_name"] = first_agent_name
             else:
                  logger.error("Cannot determine active agent: No agent name in context, no starting agent set, and no agents registered in Swarm.")
                  return None

        # Note: Caching/Discovery of tools/resources is now handled by Swarm core when swarm.run is called.
        # The old caching logic here (_discovered_tools/_discovered_resources) is likely redundant.

        return agent_to_use

    # --- Core Execution Logic ---
    def run_with_context(self, messages: List[Dict[str, Any]], context_variables: dict) -> dict:
        """Synchronous wrapper for the async execution logic."""
        # Ensure messages are dicts, not Pydantic models, before passing to async
        # (Swarm core expects list of dicts)
        dict_messages = []
        for msg in messages:
             if hasattr(msg, 'model_dump'): dict_messages.append(msg.model_dump(exclude_none=True))
             elif isinstance(msg, dict): dict_messages.append(msg)
             else: logger.warning(f"Skipping non-dict message in run_with_context: {type(msg)}"); continue

        return asyncio.run(self.run_with_context_async(dict_messages, context_variables))

    async def run_with_context_async(self, messages: List[Dict[str, Any]], context_variables: dict) -> dict:
        """Asynchronously run the blueprint's logic using the Swarm core."""
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables updated/merged: {list(self.context_variables.keys())}")

        active_agent = await self.determine_active_agent()
        if not active_agent:
            logger.error("No active agent could be determined. Cannot proceed.")
            # Return a Response-like dictionary structure
            error_msg = ChatMessage(role="assistant", content="Error: No active agent available.")
            return {"response": Response(messages=[error_msg], agent=None, context_variables=self.context_variables), "context_variables": self.context_variables}

        # Determine model from agent or fallback to Swarm's config
        model = active_agent.model if active_agent.model != "default" else self.swarm.current_llm_config.get("model")
        if not model:
             logger.error(f"Could not determine model for agent {get_agent_name(active_agent)}. Swarm config: {self.swarm.current_llm_config}")
             error_msg = ChatMessage(role="assistant", content="Error: Could not determine LLM model.")
             return {"response": Response(messages=[error_msg], agent=active_agent, context_variables=self.context_variables), "context_variables": self.context_variables}

        logger.debug(f"Using model: {model} for agent {get_agent_name(active_agent)}")

        # Truncate, validate, repair message history
        truncated_messages = self.truncate_message_history(messages, model)
        validated_messages = validate_message_sequence(truncated_messages)
        repaired_messages = repair_message_payload(validated_messages, debug=self.debug) # Pass debug flag

        if not self.swarm.agents:
             logger.warning("No agents registered in Swarm; returning default response.")
             error_msg = ChatMessage(role="assistant", content="No agents available in Swarm.")
             return {"response": Response(messages=[error_msg], agent=None, context_variables=self.context_variables), "context_variables": self.context_variables}

        logger.debug(f"Running Swarm core with agent: {get_agent_name(active_agent)} ({len(repaired_messages)} messages)")
        self.spinner.start(f"Generating response from {get_agent_name(active_agent)}")
        response_obj = None
        try:
            # Call Swarm core run method
            response_obj = await self.swarm.run(
                 agent=active_agent,
                 messages=repaired_messages,
                 context_variables=self.context_variables,
                 stream=False, # Non-streaming for this method
                 debug=self.debug,
            )
        except Exception as e:
            logger.error(f"Swarm run failed: {e}", exc_info=True)
            error_msg = ChatMessage(role="assistant", content=f"An error occurred: {str(e)}")
            response_obj = Response(messages=[error_msg], agent=active_agent, context_variables=self.context_variables)
        finally:
            self.spinner.stop()

        # Process the response object from Swarm core
        final_agent = active_agent
        updated_context = self.context_variables.copy()

        if isinstance(response_obj, Response):
             # Handle agent handoff indicated by the response
             if response_obj.agent and get_agent_name(response_obj.agent) != get_agent_name(active_agent):
                 final_agent = response_obj.agent
                 new_agent_name = get_agent_name(final_agent)
                 updated_context["active_agent_name"] = new_agent_name
                 logger.debug(f"Agent handoff occurred. New active agent: {new_agent_name}")
                 # Tool/resource discovery for the new agent happens automatically in the next Swarm.run call

             # Merge context variables returned by Swarm
             if response_obj.context_variables:
                  updated_context.update(response_obj.context_variables)
        else:
            # Handle unexpected response type from Swarm.run
            logger.error(f"Swarm run returned unexpected type: {type(response_obj)}. Expected Response.")
            error_msg = ChatMessage(role="assistant", content="Error processing the request due to unexpected response format.")
            response_obj = Response(messages=[error_msg], agent=active_agent, context_variables=updated_context)


        # Ensure the returned dictionary structure is consistent
        return {"response": response_obj, "context_variables": updated_context}


    def set_active_agent(self, agent_name: str) -> None:
        """Explicitly set the active agent by name."""
        if agent_name in self.swarm.agents:
            self.context_variables["active_agent_name"] = agent_name
            logger.debug(f"Explicitly setting active agent to: {agent_name}")
            # Discovery now handled by Swarm core
        else:
            logger.error(f"Attempted to set active agent to '{agent_name}', but agent not found in Swarm agents: {list(self.swarm.agents.keys())}")

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
            # Ensure client is available
            if not client: raise ValueError("Swarm client not available for task completion check.")

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

    async def _update_user_goal_async(self, messages: List[Dict[str, Any]]) -> None:
        """Update the 'user_goal' in context_variables based on conversation history using an LLM call."""
        if not messages:
            logger.debug("Cannot update goal: No messages provided.")
            return

        system_prompt = os.getenv(
            "UPDATE_GOAL_PROMPT",
            "You are an assistant that summarizes the user's primary objective from the conversation. Provide a concise, one-sentence summary."
        )
        # Filter out non-content messages if necessary, or format differently
        conversation_text = "\n".join(
             f"{m.get('sender', m.get('role', ''))}: {m.get('content', '') or '[Tool Call]'}"
             for m in messages if m.get('content') or m.get('tool_calls')
         )

        if not conversation_text:
             logger.debug("Cannot update goal: No usable content in messages.")
             return

        user_prompt = os.getenv(
            "UPDATE_GOAL_USER_PROMPT",
            "Summarize the user's main goal based on this conversation:\n{conversation}"
        ).format(conversation=conversation_text[-2000:]) # Limit context sent for summary

        prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        client = self.swarm.client
        model_to_use = self.swarm.current_llm_config.get("model", self.swarm.model)

        try:
             # Ensure client is available
            if not client: raise ValueError("Swarm client not available for goal update.")

            response = await client.chat.completions.create(
                model=model_to_use, messages=prompt, max_tokens=60, temperature=0.3
            )
            if response.choices:
                 new_goal = response.choices[0].message.content.strip()
                 if new_goal and new_goal != self.context_variables.get("user_goal"): # Update only if changed
                      self.context_variables["user_goal"] = new_goal
                      logger.info(f"Updated user goal via LLM: {new_goal}")
                 elif not new_goal:
                      logger.warning("LLM goal update returned empty response.")
                 else:
                      logger.debug("LLM goal update returned same goal.")
            else:
                 logger.warning("LLM response for goal update had no choices.")
        except Exception as e:
            logger.error(f"User goal update LLM call failed: {e}", exc_info=True)

    def task_completed(self, outcome: str) -> None:
        """Placeholder method potentially used by agents to signal task completion."""
        print(f"\n\033[93m[System Task Outcome]\033[0m: {outcome}")
        # Decide if interactive mode should continue or exit based on outcome?
        # For now, just prints.

    @property
    def prompt(self) -> str:
        """Return the custom prompt string, potentially from the active agent or default."""
        active_agent_name = self.context_variables.get("active_agent_name")
        active_agent = self.swarm.agents.get(active_agent_name) if active_agent_name else None

        # Use agent's specific prompt if defined, otherwise use a generic default
        # The old 'custom_user_prompt' is less clear, using agent name is better
        if active_agent:
             # Could add a 'prompt_prefix' attribute to Agent type
             return f"{get_agent_name(active_agent)} > "
        else:
             return "User: " # Default prompt


    # --- Interactive & Non-Interactive Modes ---
    def interactive_mode(self, stream: bool = False) -> None:
        """Run the blueprint in interactive command-line mode."""
        # Ensure interactive_mode is imported locally to avoid potential circular deps at module level
        try:
            from .interactive_mode import run_interactive_mode
            run_interactive_mode(self, stream)
        except ImportError:
            logger.critical("Failed to import interactive_mode runner.")
            print("Error: Cannot start interactive mode.", file=sys.stderr)


    def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        """Run the blueprint non-interactively with a single instruction."""
        logger.debug(f"Starting non-interactive mode with instruction: {instruction}, stream={stream}")
        try:
             asyncio.run(self.non_interactive_mode_async(instruction, stream=stream))
        except RuntimeError as e:
             if "cannot be called from a running event loop" in str(e):
                  logger.error("Cannot start non_interactive_mode with asyncio.run from an existing event loop.")
                  # Attempt to run within the existing loop if possible (more complex)
                  # loop = asyncio.get_running_loop()
                  # loop.create_task(self.non_interactive_mode_async(instruction, stream=stream))
                  # Or just raise the error / print message
                  print("Error: Cannot run non-interactive mode from within an async context.", file=sys.stderr)
             else: raise e
        except Exception as e:
             logger.error(f"Error during non_interactive_mode: {e}", exc_info=True)
             print(f"Error: {e}", file=sys.stderr)

    async def non_interactive_mode_async(self, instruction: str, stream: bool = False) -> None:
        """Asynchronously run the blueprint non-interactively."""
        logger.debug(f"Starting async non-interactive mode with instruction: {instruction}, stream={stream}")
        if not self.swarm:
            logger.error("Swarm instance not initialized.")
            print("Error: Swarm framework not ready.", file=sys.stderr)
            return

        print(f"--- {self.metadata.get('title', 'Blueprint')} Non-Interactive Mode ---")
        instructions = [line.strip() for line in instruction.splitlines() if line.strip()]
        if not instructions:
             print("No valid instruction provided.")
             return

        # Format initial messages as dicts
        messages: List[Dict[str, Any]] = [{"role": "user", "content": line} for line in instructions]

        # Ensure starting agent is set
        if not self.starting_agent:
             if self.swarm.agents:
                 first_agent_name = next(iter(self.swarm.agents.keys()))
                 logger.warning(f"No starting agent explicitly set. Defaulting to first agent: {first_agent_name}")
                 self.set_starting_agent(self.swarm.agents[first_agent_name])
             else:
                 logger.error("No starting agent set and no agents defined.")
                 print("Error: No agent available to handle the instruction.", file=sys.stderr)
                 return

        # Set initial context
        self.context_variables["user_goal"] = instruction # Set goal from initial instruction
        # Ensure active agent is set (redundant if set_starting_agent was called, but safe)
        if "active_agent_name" not in self.context_variables:
             self.context_variables["active_agent_name"] = get_agent_name(self.starting_agent)

        if stream:
            # Streaming in non-interactive mode might be less useful unless piping output
            logger.debug("Running non-interactive in streaming mode.")
            active_agent = await self.determine_active_agent()
            if not active_agent: return # Error logged in determine_active_agent

            response_generator = self.swarm.run(
                 agent=active_agent, messages=messages, context_variables=self.context_variables,
                 stream=True, debug=self.debug,
            )
            # Process stream chunks
            final_response_data = await self._process_and_print_streaming_response_async(response_generator)
            if self.auto_complete_task:
                 logger.warning("Auto-completion is not fully supported with streaming in non-interactive mode.")

        else: # Non-streaming
            logger.debug("Running non-interactive in non-streaming mode.")
            # Use run_with_context_async which handles agent determination and Swarm call
            result = await self.run_with_context_async(messages, self.context_variables)
            swarm_response = result.get("response") # This is now a Response object or None
            self.context_variables = result.get("context_variables", self.context_variables) # Get updated context

            response_messages_objs = [] # Expect list of ChatMessage objects
            if isinstance(swarm_response, Response) and swarm_response.messages:
                 response_messages_objs = swarm_response.messages

            # Convert ChatMessage objects to dicts for printing and history
            response_messages_dicts = [
                 msg.model_dump(exclude_none=True) for msg in response_messages_objs
                 if isinstance(msg, ChatMessage)
            ]

            # Call the correctly imported function
            pretty_print_response(messages=response_messages_dicts, use_markdown=self.use_markdown, spinner=self.spinner)

            # Auto-completion logic (if enabled)
            if self.auto_complete_task and self.swarm.agents:
                logger.debug("Starting auto-completion task.")
                current_history = messages + response_messages_dicts # Combine initial and response dicts
                await self._auto_complete_task_async(current_history, stream=False) # Pass history as dicts

        print("--- Execution Completed ---")


    async def _process_and_print_streaming_response_async(self, response_generator) -> Optional[Dict[str, Any]]:
        """Async helper to process and print streaming response chunks."""
        full_content = "" # Accumulate content per assistant turn
        current_sender = self.context_variables.get("active_agent_name", "Assistant") # Initial guess
        final_response_chunk_data = None # To store the aggregated final Response data if sent

        print(f"\033[94m{current_sender}\033[0m: ", end="", flush=True) # Print initial sender prompt

        try:
            async for chunk in response_generator:
                 # Example chunk structure handling (adjust based on actual Swarm streaming format)
                 if isinstance(chunk, dict):
                     if "response" in chunk: # Check for the final aggregated response
                          final_response_chunk_data = chunk["response"]
                          if hasattr(final_response_chunk_data, 'agent'):
                               # Update sender if final response indicates handoff, though output already happened
                               # current_sender = get_agent_name(final_response_chunk_data.agent)
                                pass
                          if hasattr(final_response_chunk_data, 'context_variables'):
                               self.context_variables.update(final_response_chunk_data.context_variables)
                          logger.debug("Received final aggregated response chunk during stream.")
                          continue # Don't print this meta-chunk directly

                     if "error" in chunk: # Handle errors signaled in the stream
                          logger.error(f"Error received during stream: {chunk['error']}")
                          # Finish the current line and print error
                          if full_content: print(flush=True) # Newline if content was printed
                          print(f"\n[Stream Error: {chunk['error']}]", file=sys.stderr, flush=True)
                          full_content = "" # Reset content
                          continue

                     # Assuming simple content delta chunks for now
                     content_delta = chunk.get("content")
                     if content_delta:
                          print(content_delta, end="", flush=True)
                          full_content += content_delta

                 # Handle OpenAI specific streaming format (if Swarm yields raw chunks)
                 elif hasattr(chunk, 'choices') and chunk.choices:
                     delta = chunk.choices[0].delta
                     if delta and delta.content:
                          print(delta.content, end="", flush=True)
                          full_content += delta.content
                 # Add handling for other chunk types if necessary (e.g., tool calls in stream)

        except Exception as e:
            logger.error(f"Error processing stream: {e}", exc_info=True)
            if full_content: print(flush=True) # Ensure newline after any partial content
            print("\n[Error during streaming output]", file=sys.stderr, flush=True)
        finally:
            # Ensure a newline is printed after the assistant's streamed output
            if full_content:
                print(flush=True)

        return final_response_chunk_data

    async def _auto_complete_task_async(self, current_history: List[Dict[str, Any]], stream: bool) -> None:
        """Async helper for task auto-completion loop (non-streaming)."""
        max_auto_turns = 10 # Limit iterations
        auto_turn = 0
        while auto_turn < max_auto_turns:
            auto_turn += 1
            logger.debug(f"Auto-completion Turn: {auto_turn}/{max_auto_turns}")

            # Prepare context for task completion check
            # Use only message content for summary/last message
            conversation_summary = " ".join(m.get("content", "") for m in current_history[-4:] if m.get("content"))
            last_assistant_msg = next((m.get("content", "") for m in reversed(current_history) if m.get("role") == "assistant" and m.get("content")), "")
            user_goal = self.context_variables.get("user_goal", "")

            # Check if task is done
            if await self._is_task_done_async(user_goal, conversation_summary, last_assistant_msg):
                print("\n\033[93m[System]\033[0m: Task detected as complete.")
                break

            logger.debug("Task not complete, running next auto-completion turn.")
            # Run the next turn using run_with_context_async
            result = await self.run_with_context_async(current_history, self.context_variables)
            swarm_response = result.get("response") # Response object
            self.context_variables = result.get("context_variables", self.context_variables) # Update context

            new_messages_objs = []
            if isinstance(swarm_response, Response) and swarm_response.messages:
                 new_messages_objs = swarm_response.messages

            if not new_messages_objs:
                 logger.warning("Auto-completion turn yielded no new messages. Stopping.")
                 print("\n\033[93m[System]\033[0m: Agent provided no further response. Stopping auto-completion.")
                 break

            # Convert new messages to dicts for printing and adding to history
            new_messages_dicts = [
                 msg.model_dump(exclude_none=True) for msg in new_messages_objs
                 if isinstance(msg, ChatMessage)
            ]

            # Print the new messages
            pretty_print_response(messages=new_messages_dicts, use_markdown=self.use_markdown, spinner=self.spinner)

            # Add new messages to history for the next turn
            current_history.extend(new_messages_dicts)

            # Optional: Small delay between turns?
            # await asyncio.sleep(0.5)

        if auto_turn >= max_auto_turns:
             logger.warning("Auto-completion reached maximum turns limit.")
             print("\n\033[93m[System]\033[0m: Reached max auto-completion turns.")


    # --- Class Method for Entry Point ---
    @classmethod
    def main(cls):
        """Main entry point for running the blueprint from the command line."""
        # Argument Parsing
        parser = argparse.ArgumentParser(description=f"Run the {cls.__name__} blueprint.")
        parser.add_argument("--config", default="./swarm_config.json", help="Path to the swarm_config.json file.")
        parser.add_argument("--instruction", help="Single instruction for non-interactive mode.")
        parser.add_argument("--stream", action="store_true", help="Enable streaming output (primarily for interactive mode).")
        parser.add_argument("--auto-complete-task", action="store_true", help="Enable task auto-completion in non-interactive mode (non-streaming only).")
        parser.add_argument("--update-user-goal", action="store_true", help="Enable dynamic goal updates using LLM (interactive mode).")
        parser.add_argument("--update-user-goal-frequency", type=int, default=5, help="Frequency (in messages) for updating user goal (interactive mode).")
        parser.add_argument("--log-file-path", help="Path for logging output (default: ~/.swarm/logs/<blueprint_name>.log).")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging to console instead of file.")
        parser.add_argument("--use-markdown", action="store_true", help="Enable markdown rendering for assistant responses (requires rich).")
        args = parser.parse_args()

        # --- Logging Setup ---
        root_logger = logging.getLogger() # Get root logger
        log_level = logging.DEBUG if args.debug or DEBUG else logging.INFO
        root_logger.setLevel(log_level) # Set level on root

        # Clear existing handlers (important if run multiple times)
        if root_logger.hasHandlers():
            for handler in root_logger.handlers[:]: root_logger.removeHandler(handler)

        log_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s")

        log_dest_path = None
        if not args.debug:
            # Ensure log directory exists
            log_dir = Path(Path.home() / ".swarm" / "logs").resolve()
            log_dir.mkdir(parents=True, exist_ok=True)
            log_dest_path = Path(args.log_file_path or log_dir / f"{cls.__name__.lower()}.log").resolve()
            log_handler = logging.FileHandler(log_dest_path, mode='a')
        else:
            log_handler = logging.StreamHandler(sys.stdout) # Log to stdout in debug mode

        log_handler.setFormatter(log_formatter)
        log_handler.setLevel(log_level) # Ensure handler respects the level
        root_logger.addHandler(log_handler)
        logger.info(f"Logging initialized. Level: {logging.getLevelName(log_level)}. Destination: {log_dest_path or 'console'}")

        # --- Stderr Redirection (Optional) ---
        original_stderr = sys.stderr
        dev_null = None
        if not args.debug:
            try:
                dev_null = open(os.devnull, "w")
                sys.stderr = dev_null
                logger.info(f"Redirected stderr to {os.devnull}")
            except OSError as e:
                 logger.warning(f"Could not redirect stderr: {e}")
                 sys.stderr = original_stderr # Ensure it's reset if redirection fails

        # --- Blueprint Execution ---
        try:
            # Load main Swarm config
            config_data = load_server_config(args.config)

            # Instantiate the blueprint
            blueprint_instance = cls(
                config=config_data,
                auto_complete_task=args.auto_complete_task,
                update_user_goal=args.update_user_goal,
                update_user_goal_frequency=args.update_user_goal_frequency,
                log_file_path=str(log_dest_path) if log_dest_path else None,
                debug=args.debug,
                use_markdown=args.use_markdown,
                non_interactive=bool(args.instruction) # Pass hint for spinner
            )

            # Select mode based on --instruction argument
            if args.instruction:
                 # Run non-interactive mode (async wrapper handles asyncio.run)
                 blueprint_instance.non_interactive_mode(args.instruction, stream=args.stream)
            else:
                # Run interactive mode
                blueprint_instance.interactive_mode(stream=args.stream)

        except Exception as e:
             # Log critical errors before potentially exiting
             logger.critical(f"Blueprint execution failed: {e}", exc_info=True)
             # Print to original stderr in case logging failed or stderr was redirected
             print(f"Critical Error: {e}", file=original_stderr)
             # Optionally exit with non-zero status
             # sys.exit(1)
        finally:
             # --- Cleanup ---
             # Restore stderr if it was redirected
             if sys.stderr is dev_null and dev_null is not None:
                 sys.stderr = original_stderr
                 dev_null.close()
                 logger.debug("Restored stderr.")
             logger.info("Blueprint execution finished.")


# Guard execution when script is run directly
if __name__ == "__main__":
    # This check ensures main() is only called when the script is executed,
    # not when it's imported as a module.
    BlueprintBase.main() # Calls the class method of the specific subclass if inherited correctly

