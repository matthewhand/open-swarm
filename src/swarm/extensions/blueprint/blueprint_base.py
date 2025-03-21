"""
Swarm Blueprint Base Module (Sync Interactive Mode)

This module provides the `BlueprintBase` abstract class with a synchronous `interactive_mode()`.
It retains advanced features like agent management, lazy tool/resource discovery, task auto-completion,
goal updates, and configurable message truncation that preserves assistant-tool pairs, optimized for
reliable Django integration and CLI usage.
"""

import asyncio
import json
import logging
import os
import importlib.util
import uuid
import sys
import threading
import time  # Added import
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    try:
        from nemoguardrails import LLMRails, RailsConfig  # type: ignore
    except ImportError:
        LLMRails, RailsConfig = None, None
except ImportError:
    LLMRails, RailsConfig = None, None

from swarm.core import Swarm
from swarm.extensions.config.config_loader import load_server_config
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data
from swarm.extensions.blueprint.message_utils import repair_message_payload, validate_message_sequence
from dotenv import load_dotenv
import argparse

logger = logging.getLogger(__name__)
def get_agent_name(agent: Any) -> str:
   return getattr(agent, "name", getattr(agent, "__name__", "<unknown>"))
def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """Estimate token count for messages (placeholder—replace with actual implementation)."""
    return sum(len(msg.get("content") or "") // 4 for msg in messages)  # Rough: 4 chars ≈ 1 token

class Spinner:
    """Simple terminal spinner for interactive feedback."""
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, interactive: bool):
        self.interactive = interactive
        self.term = os.environ.get("TERM", "dumb")
        self.enabled = interactive and self.term not in ["vt100", "dumb"]
        self.running = False
        self.thread = None
        self.status = ""
        self.index = 0

    def start(self, status: str = "Processing"):
        if not self.enabled or self.running:
            return
        self.status = status
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.enabled or not self.running:
            return
        self.running = False
        if self.thread is not None:
            self.thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _spin(self):
        while self.running:
            char = self.SPINNER_CHARS[self.index % len(self.SPINNER_CHARS)]
            sys.stdout.write(f"\r{char} {self.status}")
            sys.stdout.flush()
            self.index += 1
            time.sleep(0.1)  # Now works with time imported

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
        **kwargs
    ):
        self.auto_complete_task = auto_complete_task
        self.update_user_goal = update_user_goal
        self.update_user_goal_frequency = max(1, update_user_goal_frequency)
        self.last_goal_update_count = 0
        self.record_chat = record_chat
        self.conversation_id = str(uuid.uuid4()) if record_chat else None
        self.log_file_path = log_file_path
        self.debug = debug
        self._urls_registered = False

        logger.debug(f"Initializing {self.__class__.__name__} with config: {redact_sensitive_data(config)}")
        if not hasattr(self, 'metadata') or not isinstance(self.metadata, dict):
            raise AssertionError("Blueprint metadata must be defined and must be a dictionary.")

        self.truncation_mode = self.metadata.get("truncation_mode", "preserve_pairs")
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
            logger.warning(f"Missing environment variables for {self.metadata.get('title', 'this blueprint')}: {', '.join(missing_vars)}")

        self.required_mcp_servers = self.metadata.get('required_mcp_servers', [])
        logger.debug(f"Required MCP servers: {self.required_mcp_servers}")

        if self._is_create_agents_overridden():
            self._initialize_agents()

        if not self.skip_django_registration:
            self._register_django_components()

    def _initialize_agents(self):
        """Initialize agents if create_agents is overridden."""
        agents = self.create_agents()
        for agent_name, agent in agents.items():
            if LLMRails and getattr(agent, "nemo_guardrails_config", None):
                # Ensure nemo_guardrails_config is a non-empty string before joining
                if agent.nemo_guardrails_config:
                    guardrails_path = os.path.join("nemo_guardrails", agent.nemo_guardrails_config)
                    try:
                        if RailsConfig:
                            rails_config = RailsConfig.from_path(guardrails_path)
                            agent.nemo_guardrails_instance = LLMRails(rails_config)
                            logger.debug(f"Loaded NeMo Guardrails for agent: {agent.name}")
                        else:
                            logger.debug("RailsConfig is not available; skipping NeMo Guardrails for agent.")
                    except Exception as e:
                        logger.warning(f"Failed to load NeMo Guardrails for agent {agent.name}: {e}")
                else:
                    logger.debug(f"Agent {agent.name} has no valid nemo_guardrails_config; skipping guardrails loading.")
        self.swarm.agents.update(agents)
        self.starting_agent = agents.get("default") or (next(iter(agents.values())) if agents else None)
        logger.debug(f"Registered agents: {list(agents.keys())}")

        if self.starting_agent:
            self._discover_initial_agent_assets(self.starting_agent)
        else:
            logger.debug("No starting agent set; subclass may assign later.")

    def _discover_initial_agent_assets(self, agent):
        """Perform initial tool and resource discovery for the starting agent."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            asyncio.create_task(self._discover_tools_for_agent(agent))
            asyncio.create_task(self._discover_resources_for_agent(agent))
        else:
            asyncio.run(self._discover_tools_for_agent(agent))
            asyncio.run(self._discover_resources_for_agent(agent))
        logger.debug(f"Completed initial tool/resource discovery for agent: {agent.name}")

    def _register_django_components(self):
        """Register Django settings and URLs if applicable."""
        try:
            from django.apps import apps
            if not apps.ready:
                logger.debug("Django apps not ready; deferring registration to apps.py.")
                return

            self._load_local_settings()
            self._merge_installed_apps()
            self.register_blueprint_urls()
        except ImportError:
            logger.debug("Django not available; skipping component registration.")
        except Exception as e:
            logger.error(f"Failed to register Django components: {e}", exc_info=True)

    def _load_local_settings(self):
        """Load local settings from the blueprint directory if present."""
        module_spec = importlib.util.find_spec(self.__class__.__module__)
        if module_spec and module_spec.origin:
            blueprint_dir = os.path.dirname(module_spec.origin)
            local_settings_path = os.path.join(blueprint_dir, "settings.py")
            if os.path.isfile(local_settings_path):
                try:
                    spec = importlib.util.spec_from_file_location(f"{self.__class__.__name__}.settings", local_settings_path)
                    if spec is None or spec.loader is None:
                        logger.error(f"Failed to obtain module spec for local settings at {local_settings_path}")
                        self.local_settings = None
                    else:
                        local_settings = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(local_settings)
                        self.local_settings = local_settings
                    logger.debug(f"Loaded local settings from {local_settings_path}")
                except Exception as e:
                    logger.error(f"Failed to load local settings from {local_settings_path}: {e}")
                    self.local_settings = None
            else:
                self.local_settings = None
        else:
            self.local_settings = None

    def _merge_installed_apps(self):
        """Merge blueprint's INSTALLED_APPS into Django settings."""
        if hasattr(self, "local_settings") and self.local_settings and hasattr(self.local_settings, "INSTALLED_APPS"):
            try:
                from django.conf import settings
                blueprint_apps = getattr(self.local_settings, "INSTALLED_APPS")
                for app in blueprint_apps:
                    if app not in settings.INSTALLED_APPS:
                        settings.INSTALLED_APPS.append(app)
                logger.debug("Merged blueprint INSTALLED_APPS into Django settings.")
            except Exception as e:
                logger.error(f"Error merging INSTALLED_APPS: {e}")

    def truncate_message_history(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """Truncate message history based on configured mode, preserving tool responses."""
        if not messages:
            logger.debug("No messages to truncate.")
            return messages

        truncation_methods = {
            "preserve_pairs": self._truncate_preserve_pairs,
            "strict_token_limit": self._truncate_strict_token,
            "recent_only": self._truncate_recent_only
        }
        method = truncation_methods.get(self.truncation_mode, self._truncate_preserve_pairs)
        if self.truncation_mode not in truncation_methods:
            logger.warning(f"Unknown truncation mode '{self.truncation_mode}'; using 'preserve_pairs'")
        try:
            return method(messages, model)
        except Exception as e:
            logger.error(f"Error during message truncation: {e}")
            return messages

    def _truncate_preserve_pairs(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """Truncate while preserving assistant-tool message pairs within token/message limits."""
        system_msgs = [msg for msg in messages if msg.get("role") == "system"]
        non_system_msgs = [msg for msg in messages if msg.get("role") != "system"]

        current_tokens = get_token_count(non_system_msgs, model)
        if len(non_system_msgs) <= self.max_context_messages and current_tokens <= self.max_context_tokens:
            logger.debug(f"History within limits: {len(non_system_msgs)} messages, {current_tokens} tokens")
            return system_msgs + non_system_msgs

        msg_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_msgs]
        total_tokens = 0
        truncated = []
        i = len(msg_tokens) - 1

        while i >= 0 and len(truncated) < self.max_context_messages:
            msg, tokens = msg_tokens[i]
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                tool_call_id = msg["tool_call_id"]
                assistant_idx = i - 1
                pair_found = False
                while assistant_idx >= 0:
                    prev_msg, prev_tokens = msg_tokens[assistant_idx]
                    if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                        for tc in prev_msg["tool_calls"]:
                            if tc["id"] == tool_call_id and total_tokens + tokens + prev_tokens <= self.max_context_tokens and len(truncated) + 2 <= self.max_context_messages:
                                truncated.insert(0, prev_msg)
                                truncated.insert(1, msg)
                                total_tokens += tokens + prev_tokens
                                pair_found = True
                                break
                    if pair_found:
                        break
                    assistant_idx -= 1
                if not pair_found:
                    logger.debug(f"Skipping orphaned tool message (tool_call_id: {tool_call_id})")
            elif msg.get("role") == "assistant" and "tool_calls" in msg:
                tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                tool_msgs = []
                j = i + 1
                while j < len(msg_tokens) and tool_call_ids:
                    next_msg, next_tokens = msg_tokens[j]
                    if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                        tool_msgs.append((next_msg, next_tokens))
                        tool_call_ids.remove(next_msg["tool_call_id"])
                    else:
                        break
                    j += 1
                pair_tokens = tokens + sum(t for _, t in tool_msgs)
                pair_len = 1 + len(tool_msgs)
                if total_tokens + pair_tokens <= self.max_context_tokens and len(truncated) + pair_len <= self.max_context_messages:
                    truncated.insert(0, msg)
                    for tool_msg, _ in tool_msgs:
                        truncated.insert(1, tool_msg)
                    total_tokens += pair_tokens
            elif total_tokens + tokens <= self.max_context_tokens and len(truncated) < self.max_context_messages:
                truncated.insert(0, msg)
                total_tokens += tokens
            i -= 1

        final_messages = system_msgs + truncated
        logger.debug(f"Truncated to {len(final_messages)} messages, {total_tokens} tokens (preserve_pairs)")
        return final_messages

    def _truncate_strict_token(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """Truncate strictly by token limit, preserving tool pairs."""
        system_msgs = [msg for msg in messages if msg.get("role") == "system"]
        non_system_msgs = [msg for msg in messages if msg.get("role") != "system"]

        msg_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_msgs]
        total_tokens = 0
        truncated = []
        i = len(msg_tokens) - 1

        while i >= 0 and len(truncated) < self.max_context_messages:
            msg, tokens = msg_tokens[i]
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                tool_call_id = msg["tool_call_id"]
                assistant_idx = i - 1
                pair_found = False
                while assistant_idx >= 0:
                    prev_msg, prev_tokens = msg_tokens[assistant_idx]
                    if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                        for tc in prev_msg["tool_calls"]:
                            if tc["id"] == tool_call_id and total_tokens + tokens + prev_tokens <= self.max_context_tokens and len(truncated) + 2 <= self.max_context_messages:
                                truncated.insert(0, prev_msg)
                                truncated.insert(1, msg)
                                total_tokens += tokens + prev_tokens
                                pair_found = True
                                break
                    if pair_found:
                        break
                    assistant_idx -= 1
            elif msg.get("role") == "assistant" and "tool_calls" in msg:
                tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                tool_msgs = []
                j = i + 1
                while j < len(msg_tokens) and tool_call_ids:
                    next_msg, next_tokens = msg_tokens[j]
                    if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                        tool_msgs.append((next_msg, next_tokens))
                        tool_call_ids.remove(next_msg["tool_call_id"])
                    else:
                        break
                    j += 1
                pair_tokens = tokens + sum(t for _, t in tool_msgs)
                pair_len = 1 + len(tool_msgs)
                if total_tokens + pair_tokens <= self.max_context_tokens and len(truncated) + pair_len <= self.max_context_messages:
                    truncated.insert(0, msg)
                    for tool_msg, _ in tool_msgs:
                        truncated.insert(1, tool_msg)
                    total_tokens += pair_tokens
            elif total_tokens + tokens <= self.max_context_tokens and len(truncated) < self.max_context_messages:
                truncated.insert(0, msg)
                total_tokens += tokens
            i -= 1

        final_messages = system_msgs + truncated
        logger.debug(f"Truncated to {len(final_messages)} messages, {total_tokens} tokens (strict_token_limit)")
        return final_messages

    def _truncate_recent_only(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """Keep recent messages, preserving tool pairs within message limit."""
        system_msgs = [msg for msg in messages if msg.get("role") == "system"]
        non_system_msgs = [msg for msg in messages if msg.get("role") != "system"]

        msg_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_msgs]
        truncated = []
        i = len(msg_tokens) - 1

        while i >= 0 and len(truncated) < self.max_context_messages:
            msg, _ = msg_tokens[i]
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                tool_call_id = msg["tool_call_id"]
                assistant_idx = i - 1
                pair_found = False
                while assistant_idx >= 0:
                    prev_msg, _ = msg_tokens[assistant_idx]
                    if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                        for tc in prev_msg["tool_calls"]:
                            if tc["id"] == tool_call_id and len(truncated) + 2 <= self.max_context_messages:
                                truncated.insert(0, prev_msg)
                                truncated.insert(1, msg)
                                pair_found = True
                                break
                    if pair_found:
                        break
                    assistant_idx -= 1
            elif msg.get("role") == "assistant" and "tool_calls" in msg:
                tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                tool_msgs = []
                j = i + 1
                while j < len(msg_tokens) and tool_call_ids:
                    next_msg, _ = msg_tokens[j]
                    if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                        tool_msgs.append(next_msg)
                        tool_call_ids.remove(next_msg["tool_call_id"])
                    else:
                        break
                    j += 1
                pair_len = 1 + len(tool_msgs)
                if len(truncated) + pair_len <= self.max_context_messages:
                    truncated.insert(0, msg)
                    for tool_msg in tool_msgs:
                        truncated.insert(1, tool_msg)
            elif len(truncated) < self.max_context_messages:
                truncated.insert(0, msg)
            i -= 1

        final_messages = system_msgs + truncated
        total_tokens = get_token_count(final_messages, model)
        logger.debug(f"Truncated to {len(final_messages)} messages, {total_tokens} tokens (recent_only)")
        return final_messages

    def _is_create_agents_overridden(self) -> bool:
        """Check if create_agents is overridden in subclass."""
        return self.__class__.create_agents is not BlueprintBase.create_agents

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Metadata property to be implemented by subclasses."""
        raise NotImplementedError

    def create_agents(self) -> Dict[str, Any]:
        """Default agent creation; override in subclasses."""
        return {}

    async def _discover_tools_for_agent(self, agent: Any) -> None:
        """Discover and assign tools for an agent."""
        agent_id = get_agent_name(agent)
        if agent_id not in self._discovered_tools:
            logger.debug(f"Discovering tools for agent: {agent_id}")
            self.spinner.start(f"Discovering MCP tools for {agent_id}")
            try:
                tools = await self.swarm.discover_and_merge_agent_tools(agent)
                valid_tools = [tool for tool in tools if get_agent_name(tool) != "<unknown>"]
                agent.functions = (agent.functions or []) + valid_tools
                self._discovered_tools[agent_id] = valid_tools
                logger.debug(f"Discovered {len(valid_tools)} tools for '{agent_id}': " +
                             f"{[get_agent_name(t) for t in valid_tools]}")
            except Exception as e:
                logger.error(f"Failed to discover tools for '{agent_id}': {e}")
                self._discovered_tools[agent_id] = []
            finally:
                self.spinner.stop()

    async def _discover_resources_for_agent(self, agent: Any) -> None:
        """Discover and assign resources for an agent."""
        agent_id = get_agent_name(agent)
        if agent_id not in self._discovered_resources:
            logger.debug(f"Discovering resources for agent: {agent_id}")
            self.spinner.start(f"Discovering MCP resources for {agent_id}")
            try:
                resources = await self.swarm.discover_and_merge_agent_resources(agent)
                valid_resources = [res for res in resources if isinstance(res, dict) and 'name' in res]
                agent.resources = (agent.resources or []) + valid_resources
                self._discovered_resources[agent_id] = valid_resources
                logger.debug(f"Discovered {len(valid_resources)} resources for '{agent_id}': {[r['name'] for r in valid_resources]}")
            except Exception as e:
                logger.error(f"Failed to discover resources for '{agent_id}': {e}")
                self._discovered_resources[agent_id] = []
            finally:
                self.spinner.stop()

    def set_starting_agent(self, agent: Any) -> None:
        """Set the starting agent and trigger initial discovery."""
        logger.debug(f"Setting starting agent to: {agent.name}")
        self.starting_agent = agent
        self.context_variables["active_agent_name"] = agent.name
        self._discover_initial_agent_assets(agent)

    async def determine_active_agent(self) -> Any:
        """Determine the currently active agent, defaulting to starting agent if unset."""
        active_agent_name = self.context_variables.get("active_agent_name")
        if active_agent_name and active_agent_name in self.swarm.agents:
            agent = self.swarm.agents[active_agent_name]
            if active_agent_name not in self._discovered_tools:
                await self._discover_tools_for_agent(agent)
            if active_agent_name not in self._discovered_resources:
                await self._discover_resources_for_agent(agent)
            logger.debug(f"Active agent: {active_agent_name}")
            return agent
        elif self.starting_agent:
            if self.starting_agent.name not in self._discovered_tools:
                await self._discover_tools_for_agent(self.starting_agent)
            if self.starting_agent.name not in self._discovered_resources:
                await self._discover_resources_for_agent(self.starting_agent)
            self.context_variables["active_agent_name"] = self.starting_agent.name
            logger.debug(f"Defaulting to starting agent: {self.starting_agent.name}")
            return self.starting_agent
        logger.debug("No active or starting agent available.")
        return None

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Synchronous wrapper for running with context."""
        return asyncio.run(self.run_with_context_async(messages, context_variables))

    async def run_with_context_async(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Run the blueprint with given messages and context asynchronously."""
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables: {self.context_variables}")

        active_agent = await self.determine_active_agent()
        model = self.swarm.current_llm_config.get("model", "default") if active_agent else "default"
        truncated_messages = self.truncate_message_history(messages, model)
        truncated_messages = validate_message_sequence(truncated_messages)
        truncated_messages = repair_message_payload(truncated_messages, debug=self.debug)

        if not self.swarm.agents:
            logger.debug("No agents defined; returning default response.")
            return {"response": {"messages": [{"role": "assistant", "content": "No agents available."}]}, "context_variables": self.context_variables}
        if not active_agent:
            logger.debug("No active agent; returning default response.")
            return {"response": {"messages": [{"role": "assistant", "content": "No active agent available."}]}, "context_variables": self.context_variables}

        logger.debug(f"Running with agent: {active_agent.name}")
        self.spinner.start(f"Generating response from {active_agent.name}")
        try:
            prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
            try:
                response = await self.swarm.run(
                    agent=active_agent,
                    messages=truncated_messages,
                    context_variables=self.context_variables,
                    stream=False,
                    debug=self.debug,
                )
            finally:
                if prev_openai_api_key is not None:
                    os.environ["OPENAI_API_KEY"] = prev_openai_api_key
        except Exception as e:
            logger.error(f"Run failed: {e}", exc_info=True)
            response = {"messages": [{"role": "assistant", "content": "An error occurred during processing."}]}
        finally:
            self.spinner.stop()

        if not hasattr(response, 'messages'):
            logger.error("Response lacks 'messages' attribute.")
            if isinstance(response, dict):
                response["messages"] = []
            else:
                try:
                    response.messages = []
                except AttributeError:
                    logger.error("Unable to set 'messages' on response. It's neither a dict nor an object with 'messages'.")

        # Safely extract the response agent, whether response is an object or dict
        response_agent = None
        if not isinstance(response, dict):
            response_agent = getattr(response, "agent", None)  # type: ignore
        else:
            response_agent = response.get("agent")
        if response_agent and getattr(response_agent, "name", None) and get_agent_name(response_agent) != active_agent.name:
            new_agent_name = get_agent_name(response_agent)
            self.context_variables["active_agent_name"] = new_agent_name
            asyncio.create_task(self._discover_tools_for_agent(response_agent))
            asyncio.create_task(self._discover_resources_for_agent(response_agent))
            logger.debug(f"Switched to new agent: {new_agent_name}")
        else:
            logger.debug(f"Continuing with agent: {active_agent.name}")

        return {"response": response, "context_variables": self.context_variables}

    def set_active_agent(self, agent_name: str) -> None:
        """Set the active agent by name."""
        if agent_name in self.swarm.agents:
            self.context_variables["active_agent_name"] = agent_name
            agent = self.swarm.agents[agent_name]
            if agent.name not in self._discovered_tools:
                asyncio.run(self._discover_tools_for_agent(agent))
            if agent.name not in self._discovered_resources:
                asyncio.run(self._discover_resources_for_agent(agent))
            logger.debug(f"Active agent set to: {agent_name}")
        else:
            logger.error(f"Agent '{agent_name}' not found.")
            raise ValueError(f"Agent '{agent_name}' not found.")

    def _is_task_done(self, user_goal: str, conversation_summary: str, last_assistant_message: str) -> bool:
        """Check if the task is complete using LLM validation."""
        system_prompt = os.getenv("TASK_DONE_PROMPT", "You are a completion checker. Respond with ONLY 'YES' or 'NO'.")
        user_prompt = os.getenv(
            "TASK_DONE_USER_PROMPT",
            "User's goal: {user_goal}\nConversation summary: {conversation_summary}\nLast assistant message: {last_assistant_message}\nIs the task fully complete? Answer only YES or NO."
        ).format(user_goal=user_goal, conversation_summary=conversation_summary, last_assistant_message=last_assistant_message)
        check_prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            run_llm = getattr(self.swarm, "run_llm", None)
            if callable(run_llm):
                done_check = run_llm(messages=check_prompt, max_tokens=1, temperature=0)  # type: ignore
                result = done_check.choices[0].message["content"].strip().upper().startswith("YES")
                logger.debug(f"Task completion check: {result}")
                return result
            else:
                logger.error("Swarm does not implement run_llm. Cannot check task completion.")
                return False
        except Exception as e:
            logger.error(f"Task completion check failed: {e}")
            return False
        finally:
            if prev_openai_api_key is not None:
                os.environ["OPENAI_API_KEY"] = prev_openai_api_key

    def _update_user_goal(self, messages: List[Dict[str, str]]) -> None:
        """Update user goal based on conversation history."""
        system_prompt = os.getenv(
            "UPDATE_GOAL_PROMPT",
            "You are an assistant that summarizes the user's primary objective. Provide a concise, one-sentence summary."
        )
        user_prompt = os.getenv(
            "UPDATE_GOAL_USER_PROMPT",
            "Summarize the user's goal based on this conversation:\n{conversation}"
        ).format(conversation="\n".join(f"{m['role']}: {m['content']}" for m in messages))
        prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            run_llm = getattr(self.swarm, "run_llm", None)
            if callable(run_llm):
                summary_response = run_llm(messages=prompt, max_tokens=30, temperature=0.3)
                choices = getattr(summary_response, "choices", None)
                if not choices:
                    logger.error("LLM response does not contain choices for goal update")
                else:
                    new_goal = choices[0].message["content"].strip()
                    self.context_variables["user_goal"] = new_goal
                    logger.debug(f"Updated user goal: {new_goal}")
            else:
                logger.error("Swarm does not implement run_llm. Cannot update goal.")
        except Exception as e:
            logger.error(f"Goal update failed: {e}")
        finally:
            if prev_openai_api_key is not None:
                os.environ["OPENAI_API_KEY"] = prev_openai_api_key

    def task_completed(self, outcome: str) -> None:
        """
        Function available to the starting agent in non-interactive mode.
        Prints the outcome of the instructed task and auto-prompts "continue".
        """
        print(outcome)
        print("continue")
    
    @property
    def prompt(self) -> str:
        return getattr(self, "custom_user_prompt", "User: ")  # Note the space after colon
    
    def interactive_mode(self, stream: bool = False) -> None:
        from .interactive_mode import run_interactive_mode
        run_interactive_mode(self, stream)

    def _auto_complete_task(self, messages: List[Dict[str, str]], stream: bool):
        """Auto-complete the task if enabled."""
        conversation_summary = " ".join(msg["content"] for msg in messages[-4:] if msg.get("content"))
        last_assistant = next((msg["content"] for msg in reversed(messages) if msg["role"] == "assistant" and msg.get("content")), "")
        while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
            result = self.run_with_context(messages, self.context_variables)
            swarm_response = result["response"]
            response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages
            if stream:
                self._process_and_print_streaming_response(swarm_response)
            else:
                self._pretty_print_response(response_messages)
            messages.extend(response_messages)
            conversation_summary = " ".join(msg["content"] for msg in messages[-4:] if msg.get("content"))
            last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
        print("\033[93m[System]\033[0m: Task completed.")

    def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        """Run the blueprint in non-interactive mode."""
        logger.debug(f"Starting non-interactive mode with instruction: {instruction}")
        if not self.swarm:
            logger.error("Swarm instance not initialized.")
            raise ValueError("Swarm instance not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Non-Interactive Mode 🐝")
        instructions = [line.strip() for line in instruction.splitlines() if line.strip()]
        messages = []
        for line in instructions:
            if line == "/quit":
                print("Echoing command: /quit")
                print("LLM response: none")
                print("Spinner: off")
                break
            else:
                messages.append({"role": "user", "content": line})
        if messages:
            self.context_variables["user_goal"] = messages[0]["content"]
            self.context_variables["active_agent_name"] = self.starting_agent.name if self.starting_agent else "Unknown"
        
            result = self.run_with_context(messages, self.context_variables)
            swarm_response = result["response"]
            response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages
        
            if stream:
                self._process_and_print_streaming_response(swarm_response)
            else:
                self._pretty_print_response(response_messages)
                if response_messages:
                    print(response_messages[-1]["content"])
        
            if self.auto_complete_task and self.swarm.agents:
                messages.extend(response_messages)
                self._auto_complete_task(messages, stream)
        print("Execution completed.")

    async def non_interactive_mode_async(self, instruction: str, stream: bool = False) -> None:
        """Async version of non-interactive mode."""
        logger.debug(f"Starting async non-interactive mode with instruction: {instruction}")
        if not self.swarm:
            logger.error("Swarm instance not initialized.")
            raise ValueError("Swarm instance not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Non-Interactive Mode 🐝")
        messages = [{"role": "user", "content": instruction}]
        self.context_variables["user_goal"] = instruction
        self.context_variables["active_agent_name"] = self.starting_agent.name if self.starting_agent else "Unknown"

        result = await self.run_with_context_async(messages, self.context_variables)
        swarm_response = result["response"]
        response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages

        if stream:
            self._process_and_print_streaming_response(swarm_response)
        else:
            self._pretty_print_response(response_messages)
            if response_messages:
                print(response_messages[-1]["content"])

        if self.auto_complete_task and self.swarm.agents:
            messages.extend(response_messages)
            conversation_summary = " ".join(msg["content"] for msg in messages[-4:] if msg.get("content"))
            last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
            while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                result = await self.run_with_context_async(messages, self.context_variables)
                swarm_response = result["response"]
                response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages
                if stream:
                    self._process_and_print_streaming_response(swarm_response)
                else:
                    self._pretty_print_response(response_messages)
                    if response_messages:
                        print(response_messages[-1]["content"])
                messages.extend(response_messages)
                conversation_summary = " ".join(msg["content"] for msg in messages[-4:] if msg.get("content"))
                last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
            print("\033[93m[System]\033[0m: Task completed.")
        print("Execution completed.")

    def _process_and_print_streaming_response(self, response):
        """Process and print streaming response chunks."""
        content = ""
        last_sender = ""
        for chunk in response:
            if "sender" in chunk:
                last_sender = chunk["sender"]
            if "content" in chunk and chunk["content"] is not None:
                if not content and last_sender:
                    print(f"\033[94m{last_sender}:\033[0m ", end="", flush=True)
                    last_sender = ""
                print(chunk["content"], end="", flush=True)
                content += chunk["content"]
            if "tool_calls" in chunk and chunk["tool_calls"]:
                for tool_call in chunk["tool_calls"]:
                    func = tool_call["function"]
                    name = getattr(func, "name", func.get("__name__", "Unnamed Tool"))
                    print(f"\033[94m{last_sender}: \033[95m{name}\033[0m()")
            if "delim" in chunk and chunk["delim"] == "end" and content:
                print()
                content = ""
            if "response" in chunk:
                return chunk["response"]

    def register_blueprint_urls(self) -> None:
        """Register blueprint URLs with Django."""
        if self.skip_django_registration or getattr(self, "_urls_registered", False):
            logger.debug("Skipping URL registration: CLI mode or already registered.")
            return
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            logger.debug("DJANGO_SETTINGS_MODULE not set; skipping URL registration.")
            return

        module_path = self.metadata.get("django_modules", {}).get("urls")
        url_prefix = self.metadata.get("url_prefix", "")
        if not module_path:
            logger.debug("No URLs module specified in metadata; skipping.")
            return

        try:
            from django.urls import include, path
            from importlib import import_module

            core_urls = import_module("swarm.urls")
            if not hasattr(core_urls, "urlpatterns"):
                logger.error("swarm.urls has no urlpatterns attribute.")
                return

            urls_module = import_module(module_path)
            if not hasattr(urls_module, "urlpatterns"):
                logger.debug(f"No urlpatterns found in {module_path}")
                return

            if url_prefix and not url_prefix.endswith('/'):
                url_prefix += '/'
            app_name = self.metadata.get("cli_name", "blueprint")

            for pattern in core_urls.urlpatterns:
                if hasattr(pattern, 'url_patterns') and str(pattern.pattern) == url_prefix:
                    logger.debug(f"URL prefix '{url_prefix}' already registered.")
                    self._urls_registered = True
                    return

            core_urls.urlpatterns.append(path(url_prefix, include((module_path, app_name))))
            logger.info(f"Registered URLs from {module_path} at '{url_prefix}' (app_name: {app_name})")
            self._urls_registered = True

            from django.urls import clear_url_caches
            clear_url_caches()
        except ImportError as e:
            logger.error(f"Failed to register URLs from {module_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error registering URLs: {e}", exc_info=True)

    def _pretty_print_response(self, messages) -> None:
        """Format and print assistant responses."""
        import sys
        sys.stdout.write("\r" + " " * (len(self.spinner.status) + 5) + "\r")
        sys.stdout.flush()
        for msg in messages:
            if msg["role"] != "assistant":
                continue
            sender = msg.get("sender", "Assistant")
            print(f"\033[94m{sender}\033[0m: ", end="")
            if msg.get("content"):
                print(msg["content"])
            if tool_calls := msg.get("tool_calls", []):
                print("\033[92mFunction Calls:\033[0m")
                for tc in tool_calls:
                    f = tc["function"]
                    name = f["name"]
                    try:
                        args_obj = json.loads(f["arguments"])
                        args_str = ", ".join(f"{k}={v}" for k, v in args_obj.items())
                    except Exception:
                        args_str = f["arguments"]
                    print(f"\033[95m{name}\033[0m({args_str})")

    @classmethod
    def main(cls):
        """Entry point for running the blueprint standalone."""
        parser = argparse.ArgumentParser(description=f"Run the {cls.__name__} blueprint.")
        parser.add_argument("--config", default="./swarm_config.json", help="Configuration file path")
        parser.add_argument("--auto-complete-task", action="store_true", help="Enable task auto-completion")
        parser.add_argument("--update-user-goal", action="store_true", help="Enable dynamic goal updates")
        parser.add_argument("--update-user-goal-frequency", type=int, default=5, help="Messages between goal updates")
        parser.add_argument("--instruction", help="Instruction for non-interactive mode")
        parser.add_argument("--log-file-path", help="Log file path (default: ~/.swarm/logs/<blueprint>.log)")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging to console")
        args = parser.parse_args()

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if args.debug or DEBUG else logging.INFO)
        root_logger.handlers.clear()
        for logger_name in logging.root.manager.loggerDict:
            logging.getLogger(logger_name).handlers.clear()

        log_file = args.log_file_path or str(Path.home() / ".swarm" / "logs" / f"{cls.__name__.lower()}.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handler = logging.StreamHandler(sys.stdout if args.debug else open(log_file, 'a'))
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))
        root_logger.addHandler(handler)

        if not args.debug:
            sys.stderr = open("/dev/null", "w")
            logger.info("Redirected stderr to /dev/null")

        logger.debug(f"Launching with: config={args.config}, auto_complete={args.auto_complete_task}, "
                     f"update_goal={args.update_user_goal}, freq={args.update_user_goal_frequency}, "
                     f"instruction={args.instruction}, log={log_file}, debug={args.debug}")
        config = load_server_config(args.config)
        blueprint = cls(
            config=config,
            auto_complete_task=args.auto_complete_task,
            update_user_goal=args.update_user_goal,
            update_user_goal_frequency=args.update_user_goal_frequency,
            log_file_path=log_file,
            debug=args.debug,
            non_interactive=bool(args.instruction)
        )
        try:
            if args.instruction:
                blueprint.non_interactive_mode(args.instruction)
            else:
                blueprint.interactive_mode()
        finally:
            if not args.debug and not sys.stderr.isatty():
                sys.stderr.close()
                sys.stderr = sys.__stderr__
                logger.debug("Restored stderr to console")
        logger.info("Execution completed.")

if __name__ == "__main__":
    BlueprintBase.main()

