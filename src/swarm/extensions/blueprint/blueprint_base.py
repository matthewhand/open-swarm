"""
Swarm Blueprint Base Module (Sync Interactive Mode) - Updated to Use openai-agents

This module provides the base class for blueprints with interactive and non-interactive modes.
It has been refactored to use the openai-agents Runner for agent execution instead of the legacy Swarm core.
Additionally, it initializes the mcp_servers attribute from the configuration and manages context variables.
Since the original swarm.types module has been removed, minimal ChatMessage and Response classes are defined here.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List

import os
import sys
import uuid

from swarm.extensions.config.config_loader import load_server_config
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data
from swarm.utils.message_sequence import repair_message_payload, validate_message_sequence
from swarm.utils.context_utils import truncate_message_history
from swarm.extensions.blueprint.agent_utils import get_agent_name, initialize_agents
from swarm.extensions.blueprint.django_utils import register_django_components
from swarm.extensions.blueprint.spinner import Spinner
from dotenv import load_dotenv
import argparse

class DummyMCPServer:
    async def list_tools(self) -> list:
        return []

# Import Runner and Agent from the openai-agents SDK.
from agents import Runner  # type: ignore
from agents.agent import Agent  # type: ignore

# Minimal definitions to replace swarm.types
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: str
    content: str

@dataclass
class Response:
    messages: List[ChatMessage]
    agent: Optional[Any]
    context_variables: Dict[str, Any]

logger = logging.getLogger(__name__)

class BlueprintBase(ABC):
    """
    Base class for blueprints using the openai-agents Runner for execution.
    Agents are expected to be created via create_agents() and stored in self.agents.
    Runner.run() is used to execute agents with a plain text input.
    
    This version initializes mcp_servers from the configuration and restores context_variables.
    """
    
    # Set up initial context variables as a class variable.
    context_variables: Dict[str, Any] = {"user_goal": ""}

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
        self._urls_registered = False  # For Django URL registration

        if self.use_markdown:
            logger.debug("Markdown rendering enabled.")
        logger.debug(f"Initializing {self.__class__.__name__} with config: {redact_sensitive_data(config)}")
        if not hasattr(self, "metadata") or not isinstance(self.metadata, dict):
            try:
                _ = self.metadata
                if not isinstance(self.metadata, dict):
                    raise TypeError("Metadata is not a dict")
            except (AttributeError, NotImplementedError, TypeError) as e:
                raise AssertionError(f"{self.__class__.__name__} must define a 'metadata' property returning a dictionary. Error: {e}")

        self.truncation_mode = os.getenv("SWARM_TRUNCATION_MODE", "pairs").lower()
        meta = self.metadata
        self.max_context_tokens = max(1, meta.get("max_context_tokens", 8000))
        self.max_context_messages = max(1, meta.get("max_context_messages", 50))
        logger.debug(f"Truncation settings: mode={self.truncation_mode}, max_tokens={self.max_context_tokens}, max_messages={self.max_context_messages}")

        load_dotenv()
        logger.debug("Loaded environment variables from .env (if present).")

        self.config = config
        # Initialize mcp_servers from configuration.
        self.mcp_servers: Dict[str, Any] = {}
        if "mcp_servers" in self.config:
            self.mcp_servers = load_server_config(self.config["mcp_servers"])
            logger.debug(f"Loaded mcp_servers: {list(self.mcp_servers.keys())}")
        else:
            logger.debug("No mcp_servers configuration found.")

        # Set default mcp server configurations if keys are missing.
        if "mcp_llms_txt_server" not in self.mcp_servers:
            logger.warning("mcp_llms_txt_server not found in mcp_servers; using default dummy configuration.")
            self.mcp_servers["mcp_llms_txt_server"] = {"command": "echo", "args": [], "env": {}}
        if "everything_server" not in self.mcp_servers:
            logger.warning("everything_server not found in mcp_servers; using default dummy configuration.")
            self.mcp_servers["everything_server"] = {"command": "echo", "args": [], "env": {}}

        self.skip_django_registration = skip_django_registration or not os.environ.get("DJANGO_SETTINGS_MODULE")
        # Initialize agents.
        initialized_agents = initialize_agents(self)  # type: ignore
        self.agents: Dict[str, Agent] = initialized_agents if initialized_agents is not None else {}
        # Restore context_variables on the instance.
        self.context_variables = {"user_goal": ""}
        self.starting_agent: Optional[Agent] = None

        self._discovered_tools: Dict[str, List[Any]] = {}
        self._discovered_resources: Dict[str, List[Any]] = {}
        self.spinner = Spinner(interactive=not kwargs.get("non_interactive", False))

        required_env_vars = set(meta.get("env_vars", []))
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing environment variables for {meta.get('title', self.__class__.__name__)}: {', '.join(missing_vars)}")

        self.required_mcp_servers = meta.get("required_mcp_servers", [])
        logger.debug(f"Required MCP servers from metadata: {self.required_mcp_servers}")

        if self._is_create_agents_overridden():
            initialized_agents = initialize_agents(self)  # type: ignore
            self.agents = initialized_agents if initialized_agents is not None else {}
        register_django_components(self)

    def _is_create_agents_overridden(self) -> bool:
        return getattr(self.__class__, "create_agents") is not getattr(BlueprintBase, "create_agents")

    def truncate_message_history(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        return truncate_message_history(messages, model, self.max_context_tokens, self.max_context_messages)

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement the 'metadata' property.")

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug(f"{self.__class__.__name__} using default create_agents (returns empty dict). Override if agents are needed.")
        return {}

    def set_starting_agent(self, agent: Agent) -> None:
        agent_name = get_agent_name(agent)  # type: ignore
        logger.debug(f"Setting starting agent to: {agent_name}")
        self.starting_agent = agent
        # Only track the active agent if handoffs are defined (indicating async runner usage).
        if hasattr(agent, "handoffs"):
            self.context_variables["active_agent_name"] = agent_name

    async def determine_active_agent(self) -> Optional[Agent]:
        active_agent_name = self.context_variables.get("active_agent_name")
        if active_agent_name and active_agent_name in self.agents:
            logger.debug(f"Active agent determined: {active_agent_name}")
            return self.agents[active_agent_name]
        elif self.starting_agent is not None:
            agent_to_use = self.starting_agent
            starting_agent_name = get_agent_name(agent_to_use)  # type: ignore
            if active_agent_name != starting_agent_name:
                logger.warning(f"Active agent name '{active_agent_name}' invalid; defaulting to starting agent: {starting_agent_name}")
                self.context_variables["active_agent_name"] = starting_agent_name
            else:
                logger.debug(f"Using starting agent: {starting_agent_name}")
            return agent_to_use
        elif self.agents:
            first_agent_name = next(iter(self.agents))
            logger.warning(f"No active agent set. Defaulting to first registered agent: {first_agent_name}")
            self.context_variables["active_agent_name"] = first_agent_name
            return self.agents[first_agent_name]
        else:
            logger.error("No agents registered in blueprint.")
            return None

    def run_with_context(self, messages: List[Dict[str, Any]], context_variables: dict) -> dict:
        dict_messages = []
        for msg in messages:
            if hasattr(msg, "model_dump"):
                dict_messages.append(msg.model_dump(exclude_none=True))  # type: ignore
            elif isinstance(msg, dict):
                dict_messages.append(msg)
            else:
                logger.warning(f"Skipping non-dict message: {type(msg)}")
                continue
        return asyncio.run(self.run_with_context_async(dict_messages, context_variables))

    async def run_with_context_async(self, messages: List[Dict[str, Any]], context_variables: dict) -> dict:
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables updated: {list(self.context_variables.keys())}")
        active_agent = await self.determine_active_agent()
        if not active_agent:
            logger.error("No active agent available.")
            error_msg = ChatMessage(role="assistant", content="Error: No active agent available.")
            return {
                "response": Response(messages=[error_msg], agent=None, context_variables=self.context_variables),
                "context_variables": self.context_variables
            }
        input_text = " ".join(msg.get("content", "") for msg in messages if "content" in msg)
        if not input_text:
            logger.warning("No valid input found in messages.")
            input_text = ""
        logger.debug(f"Running Runner with agent {get_agent_name(active_agent)} and input: {input_text[:100]}...")
        self.spinner.start(f"Generating response from {get_agent_name(active_agent)}")
        try:
            result = await Runner.run(active_agent, input_text)  # type: ignore
        except Exception as e:
            logger.error(f"Runner.run failed: {e}", exc_info=True)
            error_msg = ChatMessage(role="assistant", content=f"Error: {str(e)}")
            result = Response(messages=[error_msg], agent=active_agent, context_variables=self.context_variables)
        finally:
            self.spinner.stop()
        updated_context = self.context_variables.copy()
        return {"response": result, "context_variables": updated_context}

    def set_active_agent(self, agent_name: str) -> None:
        if agent_name in self.agents:
            self.context_variables["active_agent_name"] = agent_name
            logger.debug(f"Active agent set to: {agent_name}")
        else:
            logger.error(f"Agent '{agent_name}' not found. Available: {list(self.agents.keys())}")

    async def _is_task_done_async(self, user_goal: str, conversation_summary: str, last_assistant_message: str) -> bool:
        if not user_goal:
            logger.warning("Empty user_goal; cannot check task completion.")
            return False
        system_prompt = os.getenv("TASK_DONE_PROMPT", "You are a completion checker. Answer ONLY YES or NO.")
        user_prompt = os.getenv(
            "TASK_DONE_USER_PROMPT",
            "User's goal: {user_goal}\nConversation summary: {conversation_summary}\nLast assistant message: {last_assistant_message}\nIs the task complete? Answer only YES or NO."
        ).format(
            user_goal=user_goal,
            conversation_summary=conversation_summary,
            last_assistant_message=last_assistant_message
        )
        check_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        client = Runner.client  # type: ignore
        model_to_use = Runner.current_llm_config.get("model", Runner.model)  # type: ignore
        try:
            if not client:
                raise ValueError("Runner client not available.")
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=check_prompt,
                max_tokens=5,
                temperature=0
            )
            if response.choices:
                result_content = response.choices[0].message.content.strip().upper()
                is_done = result_content.startswith("YES")
                logger.debug(f"Task completion check: {is_done} (raw: '{result_content}')")
                return is_done
            else:
                logger.warning("No choices in LLM response for task completion check.")
                return False
        except Exception as e:
            logger.error(f"Task completion check failed: {e}", exc_info=True)
            return False

    async def _update_user_goal_async(self, messages: List[Dict[str, Any]]) -> None:
        if not messages:
            logger.debug("No messages provided for goal update.")
            return
        system_prompt = os.getenv(
            "UPDATE_GOAL_PROMPT",
            "Summarize the user's primary objective from the conversation in one sentence."
        )
        conversation_text = "\n".join(
            f"{m.get('sender', m.get('role', ''))}: {m.get('content', '') or '[Tool Call]'}"
            for m in messages if m.get("content") or m.get("tool_calls")
        )
        if not conversation_text:
            logger.debug("No usable conversation content for goal update.")
            return
        user_prompt = os.getenv(
            "UPDATE_GOAL_USER_PROMPT",
            "Summarize the user's main goal based on this conversation:\n{conversation}"
        ).format(conversation=conversation_text[-2000:])
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        client = Runner.client  # type: ignore
        model_to_use = Runner.current_llm_config.get("model", Runner.model)  # type: ignore
        try:
            if not client:
                raise ValueError("Runner client not available for goal update.")
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=prompt,
                max_tokens=60,
                temperature=0.3
            )
            if response.choices:
                new_goal = response.choices[0].message.content.strip()
                if new_goal and new_goal != self.context_variables.get("user_goal"):
                    self.context_variables["user_goal"] = new_goal
                    logger.info(f"Updated user goal: {new_goal}")
                elif not new_goal:
                    logger.warning("LLM returned an empty goal for update.")
                else:
                    logger.debug("LLM goal update produced the same goal.")
            else:
                logger.warning("No choices in LLM response for goal update.")
        except Exception as e:
            logger.error(f"Goal update failed: {e}", exc_info=True)

    def task_completed(self, outcome: str) -> None:
        print(f"\n\033[93m[System Task Outcome]\033[0m: {outcome}")

    @property
    def prompt(self) -> str:
        active_agent_name = self.context_variables.get("active_agent_name")
        active_agent = self.agents.get(active_agent_name) if active_agent_name else None
        if active_agent:
            return f"{get_agent_name(active_agent)} > "
        else:
            return "User: "

    def interactive_mode(self, stream: bool = False) -> None:
        try:
            from .interactive_mode import run_interactive_mode
            run_interactive_mode(self, stream)
        except ImportError:
            logger.critical("Failed to import interactive_mode runner.")
            print("Error: Cannot start interactive mode.", file=sys.stderr)

    def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        logger.debug(f"Starting non-interactive mode with instruction: {instruction}, stream={stream}")
        try:
            asyncio.run(self.non_interactive_mode_async(instruction, stream=stream))
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                logger.error("Non-interactive mode cannot run within an async context.")
                print("Error: Non-interactive mode cannot run within an async context.", file=sys.stderr)
            else:
                raise e
        except Exception as e:
            logger.error(f"Error during non-interactive mode: {e}", exc_info=True)
            print(f"Error: {e}", file=sys.stderr)

    async def non_interactive_mode_async(self, instruction: str, stream: bool = False) -> None:
        logger.debug(f"Starting async non-interactive mode with instruction: {instruction}, stream={stream}")
        if not self.agents:
            logger.error("No agents available in blueprint instance.")
            print("Error: No agents available.", file=sys.stderr)
            return

        print(f"--- {self.metadata.get('title', 'Blueprint')} Non-Interactive Mode ---")
        instructions = [line.strip() for line in instruction.splitlines() if line.strip()]
        if not instructions:
            print("No valid instruction provided.")
            return

        messages: List[Dict[str, Any]] = [{"role": "user", "content": line} for line in instructions]
        if not self.starting_agent:
            if self.agents:
                first_agent_name = next(iter(self.agents.keys()))
                logger.warning(f"No starting agent set. Defaulting to first agent: {first_agent_name}")
                self.set_starting_agent(self.agents[first_agent_name])
            else:
                logger.error("No starting agent set and no agents defined.")
                print("Error: No agent available.", file=sys.stderr)
                return

        self.context_variables["user_goal"] = instruction
        if "active_agent_name" not in self.context_variables:
            self.context_variables["active_agent_name"] = get_agent_name(self.starting_agent)  # type: ignore

        if stream:
            logger.debug("Running non-interactive in streaming mode.")
            active_agent = await self.determine_active_agent()
            if not active_agent:
                return
            response_generator = Runner.run(active_agent, " ".join(m.get("content", "") for m in messages))  # type: ignore
            await self._process_and_print_streaming_response_async(response_generator)
            if self.auto_complete_task:
                logger.warning("Auto-completion with streaming is not fully supported.")
        else:
            logger.debug("Running non-interactive in non-streaming mode.")
            input_text = " ".join(m.get("content", "") for m in messages)
            result = await Runner.run(self.starting_agent, input_text)  # type: ignore
            if hasattr(result, "final_output"):
                print(f"\nFinal response:\n{result.final_output}")
            else:
                print("Received unexpected response format.")
        print("--- Execution Completed ---")

    async def _process_and_print_streaming_response_async(self, response_generator) -> Optional[Dict[str, Any]]:
        full_content = ""
        async for chunk in response_generator:
            if "error" in chunk:
                logger.error(f"Streaming error: {chunk['error']}")
                print(f"Error: {chunk['error']}", file=sys.stderr)
                break
            if "choices" in chunk:
                for choice in chunk["choices"]:
                    delta = choice.get("delta", {}).get("content", "")
                    full_content += delta
                    print(delta, end="", flush=True)
        print()
        return None

    async def _auto_complete_task_async(self, current_history: List[Dict[str, Any]], stream: bool) -> None:
        logger.debug("Auto-complete task not implemented.")
        pass

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description=f"Run the {cls.__name__} blueprint.")
        parser.add_argument("--config", default="./swarm_config.json", help="Path to the configuration file.")
        parser.add_argument("--instruction", help="Instruction for non-interactive mode.")
        parser.add_argument("--stream", action="store_true", help="Enable streaming mode.")
        args = parser.parse_args()
        if not os.path.exists(args.config):
            logger.error(f"Configuration file {args.config} not found.")
            sys.exit(1)
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
        blueprint_instance = cls(config=config)
        if args.instruction:
            blueprint_instance.non_interactive_mode(instruction=args.instruction, stream=args.stream)
        else:
            blueprint_instance.interactive_mode(stream=args.stream)

if __name__ == "__main__":
    BlueprintBase.main()
