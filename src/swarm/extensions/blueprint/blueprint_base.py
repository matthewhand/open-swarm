# src/swarm/extensions/blueprint/blueprint_base.py
"""
Swarm Blueprint Base Module (Sync Interactive Mode)

This module defines the foundational `BlueprintBase` abstract class with a synchronous interactive_mode(),
retaining advanced features from the latest async version. It manages agents, tools, resources, and conversational
context with lazy discovery, task auto-completion, and dynamic goal updates.
"""

import asyncio
import json
import logging
import os
import importlib.util
import uuid
import sys
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    from nemoguardrails import LLMRails, RailsConfig  # type: ignore
except ImportError:
    LLMRails, RailsConfig = None, None

from swarm.core import Swarm
from swarm.extensions.config.config_loader import load_server_config
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data
from dotenv import load_dotenv
import argparse

logger = logging.getLogger(__name__)

class Spinner:
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
        self.thread.join()
        sys.stdout.write(f"\r{' ' * (len(self.status) + 5)}\r")
        sys.stdout.flush()

    def _spin(self):
        while self.running:
            char = self.SPINNER_CHARS[self.index % len(self.SPINNER_CHARS)]
            sys.stdout.write(f"\r{char} {self.status}")
            sys.stdout.flush()
            self.index += 1
            time.sleep(0.1)

class BlueprintBase(ABC):
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
        self.update_user_goal_frequency = update_user_goal_frequency
        self.last_goal_update_count = 0
        self.record_chat = record_chat
        self.conversation_id = str(uuid.uuid4()) if record_chat else None
        self.log_file_path = log_file_path
        self.debug = debug

        logger.debug(f"Initializing BlueprintBase with config: {redact_sensitive_data(config)}")
        if not hasattr(self, 'metadata') or not isinstance(self.metadata, dict):
            raise AssertionError("Blueprint metadata must be defined and must be a dictionary.")

        load_dotenv()
        logger.debug("Environment variables loaded from .env.")

        self.config = config
        self.skip_django_registration = skip_django_registration

        if not skip_django_registration:
            try:
                module_spec = importlib.util.find_spec(self.__class__.__module__)
                if module_spec and module_spec.origin:
                    blueprint_dir = os.path.dirname(module_spec.origin)
                    local_settings_path = os.path.join(blueprint_dir, "settings.py")
                    if os.path.isfile(local_settings_path):
                        spec_local = importlib.util.spec_from_file_location(f"{self.__class__.__name__}.local_settings", local_settings_path)
                        local_settings = importlib.util.module_from_spec(spec_local)
                        spec_local.loader.exec_module(local_settings)
                        self.local_settings = local_settings
                        logger.debug(f"Loaded local settings from {local_settings_path}")
                    else:
                        self.local_settings = None
                else:
                    self.local_settings = None
            except Exception as e:
                logger.error(f"Failed to load local settings: {e}")
                self.local_settings = None

            if hasattr(self, "local_settings") and self.local_settings and hasattr(self.local_settings, "INSTALLED_APPS"):
                try:
                    from django.apps import apps
                    if not apps.ready:
                        logger.debug("Django apps are not ready; skipping merging INSTALLED_APPS.")
                    else:
                        from django.conf import settings as django_settings
                        blueprint_apps = getattr(self.local_settings, "INSTALLED_APPS")
                        for app in blueprint_apps:
                            if app not in django_settings.INSTALLED_APPS:
                                django_settings.INSTALLED_APPS.append(app)
                        logger.debug("Merged blueprint local settings INSTALLED_APPS into Django settings.")
                except Exception as e:
                    logger.error(f"Error merging INSTALLED_APPS: {e}")

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
            logger.warning(f"Missing optional environment variables for {self.metadata.get('title', 'this blueprint')}: {', '.join(missing_vars)}.")

        self.required_mcp_servers = self.metadata.get('required_mcp_servers', [])
        logger.debug(f"Required MCP servers: {self.required_mcp_servers}")

        if self._is_create_agents_overridden():
            agents = self.create_agents()
            for agent_name, agent in agents.items():
                if LLMRails and getattr(agent, "nemo_guardrails_config", None):
                    guardrails_path = os.path.join("nemo_guardrails", agent.nemo_guardrails_config)
                    try:
                        rails_config = RailsConfig.from_path(guardrails_path)
                        agent.nemo_guardrails_instance = LLMRails(rails_config)
                        logger.debug(f"✅ Loaded NeMo Guardrails for agent: {agent.name}")
                    except Exception as e:
                        logger.warning(f"Could not load NeMo Guardrails for agent {agent.name}: {e}")
            self.swarm.agents.update(agents)
            self.starting_agent = agents.get("default") or (next(iter(agents.values())) if agents else None)
            logger.debug(f"Agents registered: {list(agents.keys())}")

        if self.starting_agent:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                asyncio.create_task(self._discover_tools_for_agent(self.starting_agent))
                asyncio.create_task(self._discover_resources_for_agent(self.starting_agent))
            else:
                asyncio.run(self._discover_tools_for_agent(self.starting_agent))
                asyncio.run(self._discover_resources_for_agent(self.starting_agent))
            logger.debug(f"Completed proactive MCP tool and resource discovery for starting agent: {self.starting_agent.name}")
        else:
            logger.debug("No starting agent set initially; subclass may set it later.")

    def _is_create_agents_overridden(self) -> bool:
        base_method = BlueprintBase.create_agents
        subclass_method = self.__class__.create_agents
        return subclass_method is not base_method

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        raise NotImplementedError

    def create_agents(self) -> Dict[str, Any]:
        return {}

    async def _discover_tools_for_agent(self, agent: Any) -> None:
        if agent.name not in self._discovered_tools:
            logger.debug(f"Discovering tools for agent: {agent.name}")
            self.spinner.start(f"Discovering MCP tools for {agent.name}")
            try:
                tools = await self.swarm.discover_and_merge_agent_tools(agent)
                valid_tools = [tool for tool in tools if hasattr(tool, 'name') and isinstance(tool.name, str)]
                agent.functions = (agent.functions or []) + valid_tools
                self._discovered_tools[agent.name] = valid_tools
                logger.debug(f"Discovered {len(valid_tools)} valid tools for agent '{agent.name}': {[tool.name for tool in valid_tools]}")
            except Exception as e:
                logger.error(f"Failed to discover tools for agent '{agent.name}': {e}")
                self._discovered_tools[agent.name] = []
            finally:
                self.spinner.stop()

    async def _discover_resources_for_agent(self, agent: Any) -> None:
        if agent.name not in self._discovered_resources:
            logger.debug(f"Discovering resources for agent: {agent.name}")
            self.spinner.start(f"Discovering MCP resources for {agent.name}")
            try:
                resources = await self.swarm.discover_and_merge_agent_resources(agent)
                # Assuming resources are dicts with a 'name' field; adjust validation as needed
                valid_resources = [res for res in resources if isinstance(res, dict) and 'name' in res]
                agent.resources = (agent.resources or []) + valid_resources
                self._discovered_resources[agent.name] = valid_resources
                logger.debug(f"Discovered {len(valid_resources)} valid resources for agent '{agent.name}': {[res['name'] for res in valid_resources]}")
            except Exception as e:
                logger.error(f"Failed to discover resources for agent '{agent.name}': {e}")
                self._discovered_resources[agent.name] = []
            finally:
                self.spinner.stop()

    def set_starting_agent(self, agent: Any) -> None:
        logger.debug(f"Setting starting agent to: {agent.name}")
        self.starting_agent = agent
        self.context_variables["active_agent_name"] = agent.name
        if agent.name not in self._discovered_tools:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                asyncio.create_task(self._discover_tools_for_agent(agent))
            else:
                asyncio.run(self._discover_tools_for_agent(agent))
        if agent.name not in self._discovered_resources:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                asyncio.create_task(self._discover_resources_for_agent(agent))
            else:
                asyncio.run(self._discover_resources_for_agent(agent))

    async def determine_active_agent(self) -> Any:
        active_agent_name = self.context_variables.get("active_agent_name")
        if active_agent_name and active_agent_name in self.swarm.agents:
            agent = self.swarm.agents[active_agent_name]
            if active_agent_name not in self._discovered_tools:
                await self._discover_tools_for_agent(agent)
            if active_agent_name not in self._discovered_resources:
                await self._discover_resources_for_agent(agent)
            logger.debug(f"Active agent determined: {active_agent_name}")
            return agent
        elif self.starting_agent:
            if self.starting_agent.name not in self._discovered_tools:
                await self._discover_tools_for_agent(self.starting_agent)
            if self.starting_agent.name not in self._discovered_resources:
                await self._discover_resources_for_agent(self.starting_agent)
            self.context_variables["active_agent_name"] = self.starting_agent.name
            logger.debug(f"No active agent set; defaulting to starting agent: {self.starting_agent.name}")
            return self.starting_agent
        logger.debug("No active or starting agent available; returning None")
        return None

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        return asyncio.run(self.run_with_context_async(messages, context_variables))

    async def run_with_context_async(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables before execution: {self.context_variables}")

        if not self.swarm.agents:
            logger.debug("No agents defined; returning default response.")
            return {
                "response": {"messages": [{"role": "assistant", "content": "No agents available in this blueprint."}]},
                "context_variables": self.context_variables
            }

        active_agent = await self.determine_active_agent()
        if not active_agent:
            logger.debug("No active agent available; returning default response.")
            return {
                "response": {"messages": [{"role": "assistant", "content": "No active agent available."}]},
                "context_variables": self.context_variables
            }

        logger.debug(f"Running with active agent: {active_agent.name}")
        self.spinner.start(f"Generating response from {active_agent.name}")
        try:
            prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
            try:
                response = await self.swarm.run(
                    agent=active_agent,
                    messages=messages,
                    context_variables=self.context_variables,
                    stream=False,
                    debug=self.debug,
                )
            finally:
                if prev_openai_api_key is not None:
                    os.environ["OPENAI_API_KEY"] = prev_openai_api_key
        finally:
            self.spinner.stop()

        if not hasattr(response, 'messages'):
            logger.error("Response does not have 'messages' attribute.")
            response.messages = []

        if response.agent and response.agent.name != active_agent.name:
            new_agent_name = response.agent.name
            self.context_variables["active_agent_name"] = new_agent_name
            if new_agent_name not in self._discovered_tools:
                asyncio.create_task(self._discover_tools_for_agent(response.agent))
            if new_agent_name not in self._discovered_resources:
                asyncio.create_task(self._discover_resources_for_agent(response.agent))
            logger.debug(f"Started background tool and resource discovery for new agent: {new_agent_name}")
        else:
            logger.debug(f"Reusing cached tools and resources for agent: {active_agent.name}")

        return {"response": response, "context_variables": self.context_variables}

    def set_active_agent(self, agent_name: str) -> None:
        if agent_name in self.swarm.agents:
            self.context_variables["active_agent_name"] = agent_name
            if agent_name not in self._discovered_tools:
                asyncio.run(self._discover_tools_for_agent(self.swarm.agents[agent_name]))
            if agent_name not in self._discovered_resources:
                asyncio.run(self._discover_resources_for_agent(self.swarm.agents[agent_name]))
            logger.debug(f"Active agent set to: {agent_name}")
        else:
            logger.error(f"Agent '{agent_name}' not found. Cannot set as active agent.")
            raise ValueError(f"Agent '{agent_name}' not found.")

    def _is_task_done(self, user_goal: str, conversation_summary: str, last_assistant_message: str) -> bool:
        default_system_prompt = "You are a completion checker. Respond with ONLY 'YES' or 'NO' (no extra words)."
        system_prompt = os.getenv("TASK_DONE_PROMPT", default_system_prompt)
        default_user_prompt = "User's goal: {user_goal}\nConversation summary: {conversation_summary}\nLast assistant message: {last_assistant_message}\nIs the task fully complete? Answer only YES or NO."
        user_prompt_template = os.getenv("TASK_DONE_USER_PROMPT", default_user_prompt)
        user_prompt = user_prompt_template.format(
            user_goal=user_goal,
            conversation_summary=conversation_summary,
            last_assistant_message=last_assistant_message
        )
        check_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            done_check = self.swarm.run_llm(messages=check_prompt, max_tokens=1, temperature=0)
        finally:
            if prev_openai_api_key is not None:
                os.environ["OPENAI_API_KEY"] = prev_openai_api_key
        raw_content = done_check.choices[0].message["content"].strip().upper()
        logger.debug(f"Done check response: {raw_content}")
        return raw_content.startswith("YES")

    def _update_user_goal(self, messages: List[Dict[str, str]]) -> None:
        default_system_prompt = "You are an assistant that summarizes the user's primary objective based on the conversation so far. Provide a concise, one-sentence summary capturing the user's goal."
        system_prompt = os.getenv("UPDATE_GOAL_PROMPT", default_system_prompt)
        default_user_prompt = "Summarize the user's goal based on this conversation:\n{conversation}"
        user_prompt_template = os.getenv("UPDATE_GOAL_USER_PROMPT", default_user_prompt)
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        user_prompt = user_prompt_template.format(conversation=conversation_text)
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            summary_response = self.swarm.run_llm(messages=prompt, max_tokens=30, temperature=0.3)
        finally:
            if prev_openai_api_key is not None:
                os.environ["OPENAI_API_KEY"] = prev_openai_api_key
        new_goal = summary_response.choices[0].message["content"].strip()
        logger.debug(f"Updated user goal from LLM: {new_goal}")
        self.context_variables["user_goal"] = new_goal

    def interactive_mode(self, stream: bool = False) -> None:
        logger.debug("Starting interactive mode.")
        if not self.starting_agent:
            logger.error("Starting agent is not set. Ensure set_starting_agent is called.")
            raise ValueError("Starting agent is not set.")
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print("Blueprint Interactive Mode 🐝")
        messages: List[Dict[str, str]] = []
        first_user_input = True
        message_count = 0

        while True:
            print("\033[90mUser\033[0m: ", end="", flush=True)
            user_input = input().strip()
            if user_input.lower() in {"exit", "quit"}:
                print("Exiting interactive mode.")
                break

            if first_user_input:
                self.context_variables["user_goal"] = user_input
                first_user_input = False

            messages.append({"role": "user", "content": user_input})
            message_count += 1

            result = self.run_with_context(messages, self.context_variables or {})
            if "error" in result:
                print(f"Error: {result['error']}")
                continue
            swarm_response = result["response"]

            response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages

            if stream:
                self._process_and_print_streaming_response(swarm_response)
            else:
                self._pretty_print_response(response_messages)

            messages.extend(response_messages)

            if self.update_user_goal and (message_count - self.last_goal_update_count) >= self.update_user_goal_frequency:
                self._update_user_goal(messages)
                self.last_goal_update_count = message_count

            if self.auto_complete_task:
                conversation_summary = " ".join(
                    [msg["content"] for msg in messages[-4:] if msg.get("content")]
                )
                last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
                while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                    result2 = self.run_with_context(messages, self.context_variables or {})
                    if "error" in result2:
                        print(f"Error: {result2['error']}")
                        break
                    swarm_response = result2["response"]
                    response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages
                    if stream:
                        self._process_and_print_streaming_response(swarm_response)
                    else:
                        self._pretty_print_response(response_messages)
                    messages.extend(response_messages)
                    conversation_summary = " ".join(
                        [msg["content"] for msg in messages[-4:] if msg.get("content")]
                    )
                    last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
                print("\033[93m[System]\033[0m: Task is complete.")

    def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        logger.debug(f"Starting non-interactive mode with instruction: {instruction}")
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Non-Interactive Mode 🐝")
        messages = [{"role": "user", "content": instruction}]
        self.context_variables["user_goal"] = instruction
        self.context_variables["active_agent_name"] = self.starting_agent.name if self.starting_agent else "Unknown"

        result = self.run_with_context(messages, self.context_variables or {})
        if "error" in result:
            print(f"Error: {result['error']}")
            return
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
            conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
            last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
            while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                result2 = self.run_with_context(messages, self.context_variables or {})
                if "error" in result2:
                    print(f"Error: {result2['error']}")
                    break
                swarm_response = result2["response"]
                response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages
                if stream:
                    self._process_and_print_streaming_response(swarm_response)
                else:
                    self._pretty_print_response(response_messages)
                    if response_messages:
                        print(response_messages[-1]["content"])
                messages.extend(response_messages)
                conversation_summary = " ".join(
                    [msg["content"] for msg in messages[-4:] if msg.get("content")]
                )
                last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
            print("\033[93m[System]\033[0m: Task is complete.")
        print("Execution completed. Exiting.")

    async def non_interactive_mode_async(self, instruction: str, stream: bool = False) -> None:
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Non-Interactive Mode 🐝")
        messages = [{"role": "user", "content": instruction}]
        self.context_variables["user_goal"] = instruction
        self.context_variables["active_agent_name"] = self.starting_agent.name if self.starting_agent else "Unknown"

        result = await self.run_with_context_async(messages, self.context_variables or {})
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
            conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
            last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
            while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                result2 = await self.run_with_context_async(messages, self.context_variables or {})
                swarm_response = result2["response"]
                response_messages = swarm_response["messages"] if isinstance(swarm_response, dict) else swarm_response.messages
                if stream:
                    self._process_and_print_streaming_response(swarm_response)
                else:
                    self._pretty_print_response(response_messages)
                    if response_messages:
                        print(response_messages[-1]["content"])
                messages.extend(response_messages)
                conversation_summary = " ".join(
                    [msg["content"] for msg in messages[-4:] if msg.get("content")]
                )
                last_assistant = next((msg["content"] for msg in reversed(response_messages) if msg["role"] == "assistant" and msg.get("content")), "")
            print("\033[93m[System]\033[0m: Task is complete.")
        print("Execution completed. Exiting.")

    def _process_and_print_streaming_response(self, response):
        content = ""
        last_sender = ""
        for chunk in response:
            if "sender" in chunk:
                last_sender = chunk["sender"]
            if "content" in chunk and chunk["content"] is not None:
                if not content and last_sender:
                    print(f"\033[94m{last_sender}:\033[0m", end=" ", flush=True)
                    last_sender = ""
                print(chunk["content"], end="", flush=True)
                content += chunk["content"]
            if "tool_calls" in chunk and chunk["tool_calls"] is not None:
                for tool_call in chunk["tool_calls"]:
                    tool_function = tool_call["function"]
                    name = getattr(tool_function, "name", None) or tool_function.get("__name__", "Unnamed Tool")
                    print(f"\033[94m{last_sender}: \033[95m{name}\033[0m()")
            if "delim" in chunk and chunk["delim"] == "end" and content:
                print()
                content = ""
            if "response" in chunk:
                return chunk["response"]

    def _register_module(self, module_key: str, module_description: str) -> None:
        module_path = self.metadata.get(module_key)
        if module_path:
            try:
                importlib.import_module(module_path)
                logger.debug(f"Registered blueprint {module_description} from module: {module_path}")
            except ImportError as e:
                logger.error(f"Failed to register blueprint {module_description} from {module_path}: {e}")
        else:
            logger.debug(f"No blueprint {module_description} to register.")

    def register_blueprint_models(self) -> None:
        if self.skip_django_registration:
            logger.debug("Skipping model registration due to CLI mode.")
            return
        self._register_module("models_module", "models")

    def register_blueprint_views(self) -> None:
        if self.skip_django_registration:
            logger.debug("Skipping view registration due to CLI mode.")
            return
        self._register_module("views_module", "views")

    def register_blueprint_urls(self) -> None:
        if self.skip_django_registration:
            logger.debug("Skipping URL registration due to CLI mode.")
            return
        if getattr(self, "_urls_registered", False):
            logger.debug("Blueprint URLs already registered. Skipping.")
            return
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            logger.debug("DJANGO_SETTINGS_MODULE not set; skipping URL registration.")
            return

        module_path = self.metadata.get("django_modules", {}).get("urls")  # Updated to use django_modules
        url_prefix = self.metadata.get("url_prefix", "")
        if not module_path:
            logger.debug("No urls module specified in django_modules; skipping URL registration.")
            return

        try:
            from django.urls import include, path
            import swarm.urls as core_urls

            m = importlib.import_module(module_path)
            if not hasattr(m, "urlpatterns"):
                logger.debug(f"No urlpatterns found in {module_path}")
                return

            if url_prefix and not url_prefix.endswith('/'):
                url_prefix += '/'

            app_name = self.metadata.get("cli_name", "blueprint")

            for pattern in core_urls.urlpatterns:
                if hasattr(pattern, 'url_patterns') and str(pattern.pattern) == url_prefix:
                    logger.debug(f"URL prefix '{url_prefix}' already registered in core URLs.")
                    self._urls_registered = True
                    return

            core_urls.urlpatterns.append(
                path(url_prefix, include((module_path, app_name)))
            )
            logger.debug(f"Registered blueprint URLs from {module_path} with prefix '{url_prefix}' and app_name '{app_name}'")
            self._urls_registered = True

            from django.urls import clear_url_caches
            clear_url_caches()
        except ImportError as e:
            logger.error(f"Failed to register blueprint URLs from {module_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error registering blueprint URLs: {e}", exc_info=True)

    def _pretty_print_response(self, messages) -> None:
        for message in messages:
            if message["role"] != "assistant":
                continue
            sender = message.get("sender", "Assistant")
            print(f"\033[94m{sender}\033[0m:", end=" ")
            if message.get("content"):
                print(message["content"])
            tool_calls = message.get("tool_calls") or []
            if len(tool_calls) > 1:
                print()
            for tool_call in tool_calls:
                f = tool_call["function"]
                name = f["name"]
                arg_str = json.dumps(json.loads(f["arguments"])).replace(":", "=")
                print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description=f"Launch the {cls.__name__} blueprint with configurable options.")
        parser.add_argument("--config", type=str, default="./swarm_config.json", help="Path to the configuration file")
        parser.add_argument("--auto-complete-task", action="store_true", help="Enable multi-step auto-completion with LLM validation")
        parser.add_argument("--update-user-goal", action="store_true", help="Enable dynamic user goal updates via LLM analysis")
        parser.add_argument("--update-user-goal-frequency", type=int, default=5, help="Number of messages between goal updates")
        parser.add_argument("--instruction", type=str, help="Single instruction for non-interactive mode execution")
        parser.add_argument("--log-file-path", type=str, help="Path to log file (default: ~/.swarm/logs/<blueprint_name>.log)")
        parser.add_argument("--debug", action="store_true", help="Print debug logs and stderr to console")
        args = parser.parse_args()

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

        for logger_name in logging.root.manager.loggerDict:
            logger_instance = logging.getLogger(logger_name)
            logger_instance.handlers.clear()
        root_logger.handlers.clear()

        log_file_path = args.log_file_path or str(Path.home() / ".swarm" / "logs" / f"{cls.__name__.lower()}.log")
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        if args.instruction:
            handler = logging.StreamHandler(sys.stdout if args.debug else open(log_file_path, 'a'))
            root_logger.handlers.append(handler)
            if not args.debug:
                sys.stderr = open(log_file_path, 'a')
                logger.info(f"Redirected stderr to {log_file_path}")
        else:
            handler = logging.StreamHandler(sys.stderr if args.debug else open(log_file_path, 'a'))
            root_logger.handlers.append(handler)
            if not args.debug:
                sys.stderr = open(log_file_path, 'a')
                logger.info(f"Redirected stderr to {log_file_path}")
            else:
                logger.info("Debug mode enabled; stderr remains on console")

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s")
        handler.setFormatter(formatter)

        logger.debug(f"Launching blueprint with config: {args.config}, auto_complete_task={args.auto_complete_task}, update_user_goal={args.update_user_goal}, update_user_goal_frequency={args.update_user_goal_frequency}, instruction={args.instruction}, log_file_path={log_file_path}, debug={args.debug}")
        config = load_server_config(args.config)
        blueprint = cls(
            config=config,
            auto_complete_task=args.auto_complete_task,
            update_user_goal=args.update_user_goal,
            update_user_goal_frequency=args.update_user_goal_frequency,
            log_file_path=log_file_path,
            debug=args.debug,
            non_interactive=bool(args.instruction)
        )
        try:
            if args.instruction:
                blueprint.non_interactive_mode(args.instruction)
            else:
                blueprint.interactive_mode()
        finally:
            if not args.debug:
                sys.stderr.close()
                sys.stderr = sys.__stderr__
                logger.debug("Restored stderr to console")
        logger.info("Blueprint execution completed")

if __name__ == "__main__":
    BlueprintBase.main()
