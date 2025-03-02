"""
Swarm Blueprint Base Module

This module defines the foundational `BlueprintBase` abstract class, serving as the backbone for all Swarm blueprints.
It provides a sophisticated framework for managing agents, tools, and conversational context, with advanced features like
lazy MCP server discovery, task auto-completion, and dynamic goal updates. Designed for extensibility and performance,
this class empowers developers to craft complex, agent-driven workflows with minimal startup overhead and seamless scalability.

Key Features:
- Precision lazy tool discovery for MCP servers, loading tools only once per agent with robust caching and async efficiency.
- Optional agent creation for blueprints focused on UI or non-agent extensions.
- Auto-completion of multi-step tasks via lightweight LLM checks, configurable via environment variables.
- Dynamic user goal updates based on conversation analysis, with configurable frequency and prompts.
- Stateless agent handoffs tracked via context variables with optimized, non-blocking transitions.
"""

import asyncio
import json
import logging
import os
import importlib.util
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from nemoguardrails import LLMRails, RailsConfig  # type: ignore

from swarm.core import Swarm
from swarm.repl import run_demo_loop
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data
from dotenv import load_dotenv
import argparse

# Configure logging for detailed diagnostics and traceability
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)


class BlueprintBase(ABC):
    """
    Abstract base class for Swarm blueprints, providing a robust foundation for agent orchestration.

    This class manages the lifecycle of a blueprint, including agent initialization, tool discovery,
    and conversational state. It optimizes performance with precision lazy loading of MCP server tools,
    discovering them only once per agent and caching results asynchronously. Optional features like task
    auto-completion and dynamic goal updates enhance adaptability, with prompts customizable via environment
    variables.

    Attributes:
        auto_complete_task (bool): Enables automatic task completion via LLM-driven checks.
        update_user_goal (bool): Activates dynamic updates to the user's goal based on conversation history.
        update_user_goal_frequency (int): Frequency (in message count) for updating the user's goal.
        swarm (Swarm): The core Swarm instance managing agent interactions and tool execution.
        context_variables (Dict[str, Any]): Persistent state tracking the active agent and user goals.
        starting_agent (Any): The default agent to use when no active agent is specified.
        _discovered_tools (Dict[str, List[Any]]): Persistent cache of discovered tools per agent.
        skip_django_registration (bool): If True, skips Django-specific registration for standalone CLI mode.
    """

    def __init__(
        self,
        config: dict,
        auto_complete_task: bool = False,
        update_user_goal: bool = False,
        update_user_goal_frequency: int = 5,
        skip_django_registration: bool = False,
        **kwargs
    ):
        """
        Initialize the blueprint with configuration and optional advanced features.

        This constructor sets up the blueprint's core components, deferring tool discovery to runtime
        for optimal performance. It supports shared Swarm instances and integrates local settings for
        blueprint-specific customization, with an option to skip Django registration in CLI mode.

        Args:
            config (dict): Configuration dictionary containing Swarm and MCP server settings.
            auto_complete_task (bool): If True, executes tasks until completion using LLM validation.
            update_user_goal (bool): If True, dynamically updates the user's goal via LLM analysis.
            update_user_goal_frequency (int): Number of messages between goal updates.
            skip_django_registration (bool): If True, skips Django model/view/url registration.
            **kwargs: Additional arguments, e.g., 'swarm_instance' for sharing an existing Swarm.

        Raises:
            AssertionError: If metadata is not defined or is not a dictionary.
        """
        # Feature flags for advanced functionality
        self.auto_complete_task = auto_complete_task
        self.update_user_goal = update_user_goal
        self.update_user_goal_frequency = update_user_goal_frequency
        self.last_goal_update_count = 0  # Tracks last goal update for frequency control

        logger.debug(f"Initializing BlueprintBase with config: {redact_sensitive_data(config)}")
        if not hasattr(self, 'metadata') or not isinstance(self.metadata, dict):
            raise AssertionError("Blueprint metadata must be defined and must be a dictionary.")

        # Load environment variables for configuration flexibility
        load_dotenv()
        logger.debug("Environment variables loaded from .env.")

        self.config = config
        self.skip_django_registration = skip_django_registration

        # Only attempt local settings and Django integration if not skipping
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
                from django.conf import settings as django_settings
                blueprint_apps = getattr(self.local_settings, "INSTALLED_APPS")
                for app in blueprint_apps:
                    if app not in django_settings.INSTALLED_APPS:
                        django_settings.INSTALLED_APPS.append(app)
                logger.debug("Merged blueprint local settings INSTALLED_APPS into Django settings.")

        # Use an existing Swarm instance if provided, otherwise create a new one
        self.swarm = kwargs.get('swarm_instance') or Swarm(config=self.config)
        logger.debug("Swarm instance initialized.")

        # Initialize context with user goal and tool cache
        self.context_variables: Dict[str, Any] = {"user_goal": ""}
        self.starting_agent = None
        self._discovered_tools: Dict[str, List[Any]] = {}  # Persistent cache to optimize tool discovery

        # Validate environment variables, warning instead of failing for robustness
        required_env_vars = set(self.metadata.get('env_vars', []))
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing optional environment variables for {self.metadata.get('title', 'this blueprint')}: {', '.join(missing_vars)}. Some functionality may be limited.")

        # Store required MCP servers for later validation
        self.required_mcp_servers = self.metadata.get('required_mcp_servers', [])
        logger.debug(f"Required MCP servers: {self.required_mcp_servers}")

        # Initialize agents if overridden, deferring tool discovery
        if self._is_create_agents_overridden():
            agents = self.create_agents()
            for agent_name, agent in agents.items():
                if getattr(agent, "nemo_guardrails_config", None):
                    guardrails_path = os.path.join("nemo_guardrails", agent.nemo_guardrails_config)
                    try:
                        rails_config = RailsConfig.from_path(guardrails_path)
                        agent.nemo_guardrails_instance = LLMRails(rails_config)
                        logger.debug(f"✅ Loaded NeMo Guardrails for agent: {agent.name}")
                    except Exception as e:
                        logger.warning(f"Could not load NeMo Guardrails for agent {agent.name}: {e}")
            self.swarm.agents.update(agents)
            logger.debug(f"Agents registered: {list(agents.keys())}")
        else:
            logger.debug("create_agents() not overridden; no agents registered.")

    def _is_create_agents_overridden(self) -> bool:
        """Determine if create_agents() is overridden in the subclass.

        Returns:
            bool: True if the method is overridden, False otherwise.
        """
        base_method = BlueprintBase.create_agents
        subclass_method = self.__class__.create_agents
        return subclass_method is not base_method

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Abstract property defining blueprint metadata.

        Subclasses must implement this to provide title, description, and dependencies such as
        required environment variables and MCP servers.

        Returns:
            Dict[str, Any]: Metadata dictionary with at least 'title' and 'description'.
        """
        raise NotImplementedError

    def create_agents(self) -> Dict[str, Any]:
        """Default implementation for agent creation, returning an empty dictionary.

        Subclasses should override this to define their agent roster if agent-based functionality
        is required. Agents are registered lazily, with tools discovered only when they become active.

        Returns:
            Dict[str, Any]: Dictionary of agent names to agent instances.
        """
        return {}

    async def _discover_tools_for_agent(self, agent: Any) -> None:
        """Asynchronously discover and cache tools for a specific agent.

        This method queries MCP servers associated with the agent and stores the results in a persistent
        cache, ensuring tools are discovered only once per agent unless the cache is explicitly cleared.
        It handles malformed tools gracefully to prevent crashes.

        Args:
            agent (Any): The agent instance for which to discover tools.
        """
        if agent.name not in self._discovered_tools:
            logger.debug(f"Discovering tools for agent: {agent.name}")
            try:
                tools = await self.swarm.discover_and_merge_agent_tools(agent)
                # Validate and filter tools to ensure they have required attributes
                valid_tools = []
                for tool in tools:
                    if not hasattr(tool, 'name') or not isinstance(tool.name, str):
                        logger.warning(f"Invalid tool detected for agent '{agent.name}': missing or invalid 'name' attribute. Skipping.")
                        continue
                    valid_tools.append(tool)
                self._discovered_tools[agent.name] = valid_tools
                agent.functions = valid_tools  # Equip agent with valid tools only
                logger.debug(f"Discovered {len(valid_tools)} valid tools for agent '{agent.name}': {[tool.name for tool in valid_tools]}")
            except Exception as e:
                logger.error(f"Failed to discover tools for agent '{agent.name}': {e}")
                self._discovered_tools[agent.name] = []  # Cache empty list on failure to avoid retries

    def set_starting_agent(self, agent: Any) -> None:
        """Set the starting agent for the blueprint, initializing its context.

        This method designates the initial agent and updates the context variable, with tool discovery
        deferred until the agent becomes active, aligning with the lazy-loading strategy.

        Args:
            agent (Any): The agent to set as the starting point.
        """
        logger.debug(f"Setting starting agent to: {agent.name}")
        self.starting_agent = agent
        self.context_variables["active_agent_name"] = agent.name

    async def determine_active_agent(self) -> Any:
        """Asynchronously resolve the currently active agent based on context variables.

        This method retrieves the active agent from `context_variables["active_agent_name"]`, falling
        back to the starting agent if none is specified. It ensures tools are discovered lazily and
        asynchronously for the active agent if not already cached, minimizing delays during handoffs.

        Returns:
            Any: The active agent instance.

        Raises:
            ValueError: If no active or starting agent is available.
        """
        active_agent_name = self.context_variables.get("active_agent_name")
        if active_agent_name and active_agent_name in self.swarm.agents:
            active_agent = self.swarm.agents[active_agent_name]
            # Lazy discover tools if not already cached (async)
            if active_agent_name not in self._discovered_tools:
                await self._discover_tools_for_agent(active_agent)
            logger.debug(f"Active agent determined: {active_agent_name}")
            return active_agent
        elif self.starting_agent:
            if self.starting_agent.name not in self._discovered_tools:
                await self._discover_tools_for_agent(self.starting_agent)
            self.context_variables["active_agent_name"] = self.starting_agent.name
            logger.debug(f"No active agent set; defaulting to starting agent: {self.starting_agent.name}")
            return self.starting_agent
        else:
            logger.error("No active agent or starting agent available.")
            raise ValueError("No active agent or starting agent available.")

    async def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Asynchronously execute a task with the given messages and context, leveraging the active agent.

        This method updates the blueprint’s context, determines the active agent asynchronously, and delegates
        execution to the Swarm. It supports efficient, stateless handoffs by lazily discovering tools for new
        agents only once, caching them for subsequent use, and running discovery in the background for seamless
        transitions.

        Args:
            messages (List[Dict[str, str]]): List of conversation messages.
            context_variables (dict): Additional context variables to merge.

        Returns:
            dict: Response containing the Swarm’s output and updated context variables.
        """
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables before execution: {self.context_variables}")

        if not self.swarm.agents:
            logger.debug("No agents defined; returning default response.")
            return {
                "response": {"messages": [{"role": "assistant", "content": "No agents available in this blueprint."}]},
                "context_variables": self.context_variables
            }

        active_agent = await self.determine_active_agent()
        logger.debug(f"Running with active agent: {active_agent.name}")

        # Execute the current agent's task asynchronously
        response = await self.swarm.run(
            agent=active_agent,
            messages=messages,
            context_variables=self.context_variables,
            stream=False,
            debug=True,
        )

        logger.debug(f"Swarm response: {response}")

        if not hasattr(response, 'messages'):
            logger.error("Response does not have 'messages' attribute.")
            response.messages = []

        # Handle agent handoff efficiently
        if response.agent and response.agent.name != active_agent.name:
            new_agent_name = response.agent.name
            self.context_variables["active_agent_name"] = new_agent_name
            if new_agent_name not in self._discovered_tools:
                # Start tool discovery in the background for the new agent
                asyncio.create_task(self._discover_tools_for_agent(response.agent))
                logger.debug(f"Started background tool discovery for new agent: {new_agent_name}")
            else:
                logger.debug(f"Reusing cached tools for agent: {new_agent_name}")

        return {"response": response, "context_variables": self.context_variables}

    def run_with_context_sync(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Synchronous wrapper for run_with_context, primarily for testing or non-async contexts.

        Args:
            messages (List[Dict[str, str]]): List of conversation messages.
            context_variables (dict): Additional context variables to merge.

        Returns:
            dict: Response containing the Swarm’s output and updated context variables.
        """
        return asyncio.run(self.run_with_context(messages, context_variables))

    def set_active_agent(self, agent_name: str) -> None:
        """Explicitly set the active agent, triggering tool discovery if needed.

        This method allows manual control over the active agent, ensuring its tools are discovered
        lazily when it’s first set. Discovery is synchronous here for simplicity, but could be made async if needed.

        Args:
            agent_name (str): Name of the agent to set as active.

        Raises:
            ValueError: If the agent name is not found in the swarm’s agents.
        """
        if agent_name in self.swarm.agents:
            self.context_variables["active_agent_name"] = agent_name
            if agent_name not in self._discovered_tools:
                asyncio.run(self._discover_tools_for_agent(self.swarm.agents[agent_name]))
            logger.debug(f"Active agent set to: {agent_name}")
        else:
            logger.error(f"Agent '{agent_name}' not found. Cannot set as active agent.")
            raise ValueError(f"Agent '{agent_name}' not found.")

    def _is_task_done(self, user_goal: str, conversation_summary: str, last_assistant_message: str) -> bool:
        """Evaluate task completion using a minimal LLM call with customizable prompts.

        This method performs a lightweight check to determine if the user’s goal is met, leveraging
        a single-token response from the LLM for efficiency. Prompts can be overridden via environment
        variables `TASK_DONE_PROMPT` (system) and `TASK_DONE_USER_PROMPT` (user) for tailored behavior.

        Args:
            user_goal (str): The current user goal.
            conversation_summary (str): Summary of recent conversation.
            last_assistant_message (str): The most recent assistant response.

        Returns:
            bool: True if the task is complete, False otherwise.
        """
        # Default prompts with environment variable overrides for flexibility
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
        done_check = self.swarm.run_llm(messages=check_prompt, max_tokens=1, temperature=0)
        raw_content = done_check.choices[0].message["content"].strip().upper()
        logger.debug(f"Done check response: {raw_content}")
        return raw_content.startswith("YES")

    def _update_user_goal(self, messages: List[Dict[str, str]]) -> None:
        """Dynamically update the user’s goal based on conversation history with customizable prompts.

        This method uses an LLM to analyze the conversation and refine the user’s goal, enhancing
        adaptability in long-running interactions. Prompts can be overridden via environment variables
        `UPDATE_GOAL_PROMPT` (system) and `UPDATE_GOAL_USER_PROMPT` (user) for precise control.

        Args:
            messages (List[Dict[str, str]]): The full conversation history.
        """
        # Default prompts with environment variable overrides for customization
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
        summary_response = self.swarm.run_llm(messages=prompt, max_tokens=30, temperature=0.3)
        new_goal = summary_response.choices[0].message["content"].strip()
        logger.debug(f"Updated user goal from LLM: {new_goal}")
        self.context_variables["user_goal"] = new_goal

    async def interactive_mode(self, stream: bool = False) -> None:
        """Launch an interactive REPL loop for user-agent interaction.

        This method provides a command-line interface for engaging with the blueprint,
        supporting streaming responses and advanced features like auto-completion and goal updates.
        Fully asynchronous to ensure non-blocking execution.

        Args:
            stream (bool): If True, streams responses incrementally; otherwise, prints them whole.
        """
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Interactive Mode 🐝")
        messages: List[Dict[str, str]] = []
        first_user_input = True
        message_count = 0

        while True:
            print("\033[90mUser\033[0m: ", end="")
            user_input = input().strip()
            if user_input.lower() in {"exit", "quit"}:
                print("Exiting interactive mode.")
                break

            if first_user_input:
                self.context_variables["user_goal"] = user_input
                first_user_input = False

            messages.append({"role": "user", "content": user_input})
            message_count += 1

            result = await self.run_with_context(messages, self.context_variables or {})
            swarm_response = result["response"]

            if stream:
                self._process_and_print_streaming_response(swarm_response)
            else:
                self._pretty_print_response(swarm_response.messages)

            messages.extend(swarm_response.messages)

            if self.update_user_goal and (message_count - self.last_goal_update_count) >= self.update_user_goal_frequency:
                self._update_user_goal(messages)
                self.last_goal_update_count = message_count

            if self.auto_complete_task:
                conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
                last_assistant = next((msg["content"] for msg in reversed(swarm_response.messages) if msg["role"] == "assistant" and msg.get("content")), "")
                while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                    result2 = await self.run_with_context(messages, self.context_variables or {})
                    swarm_response = result2["response"]
                    if stream:
                        self._process_and_print_streaming_response(swarm_response)
                    else:
                        self._pretty_print_response(swarm_response.messages)
                    messages.extend(swarm_response.messages)
                    conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
                    last_assistant = next((msg["content"] for msg in reversed(swarm_response.messages) if msg["role"] == "assistant" and msg.get("content")), "")
                print("\033[93m[System]\033[0m: Task is complete.")

    async def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        """Execute a single instruction in non-interactive mode and exit.

        This method supports one-shot executions, ideal for scripted or automated use cases,
        with optional streaming and task auto-completion, fully asynchronous for efficiency.

        Args:
            instruction (str): The user instruction to execute.
            stream (bool): If True, streams the response incrementally.
        """
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Non-Interactive Mode 🐝")
        messages = [{"role": "user", "content": instruction}]
        self.context_variables["user_goal"] = instruction

        result = await self.run_with_context(messages, self.context_variables or {})
        swarm_response = result["response"]

        if stream:
            self._process_and_print_streaming_response(swarm_response)
        else:
            self._pretty_print_response(swarm_response.messages)

        if self.auto_complete_task and self.swarm.agents:
            messages.extend(swarm_response.messages)
            conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
            last_assistant = next((msg["content"] for msg in reversed(swarm_response.messages) if msg["role"] == "assistant" and msg.get("content")), "")
            while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                result2 = await self.run_with_context(messages, self.context_variables or {})
                swarm_response = result2["response"]
                if stream:
                    self._process_and_print_streaming_response(swarm_response)
                else:
                    self._pretty_print_response(swarm_response.messages)
                messages.extend(swarm_response.messages)
                conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
                last_assistant = next((msg["content"] for msg in reversed(swarm_response.messages) if msg["role"] == "assistant" and msg.get("content")), "")
            print("\033[93m[System]\033[0m: Task is complete.")
        print("Execution completed. Exiting.")

    def _process_and_print_streaming_response(self, response):
        """Process and display streaming responses from the Swarm.

        Handles incremental output for a smooth user experience, including tool calls and delimiters.

        Args:
            response: The streaming response object from Swarm.run().
        """
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
        """Register a blueprint module (e.g., models, views) if specified in metadata.

        Args:
            module_key (str): The metadata key for the module path.
            module_description (str): Description of the module type (e.g., 'models').
        """
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
        """Register blueprint-specific models if defined in metadata."""
        if self.skip_django_registration:
            logger.debug("Skipping model registration due to CLI mode.")
            return
        self._register_module("models_module", "models")

    def register_blueprint_views(self) -> None:
        """Register blueprint-specific views if defined in metadata."""
        if self.skip_django_registration:
            logger.debug("Skipping view registration due to CLI mode.")
            return
        self._register_module("views_module", "views")

    def register_blueprint_urls(self) -> None:
        """Register blueprint-specific URLs with a configurable prefix.

        Integrates blueprint URLs into the Django URL configuration, enhancing modularity and routing flexibility.

        Note:
            Requires DJANGO_SETTINGS_MODULE to be set; skips registration if not configured or in CLI mode.
        """
        if self.skip_django_registration:
            logger.debug("Skipping URL registration due to CLI mode.")
            return
        if getattr(self, "_urls_registered", False):
            logger.debug("Blueprint URLs already registered. Skipping.")
            return
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            logger.debug("DJANGO_SETTINGS_MODULE not set; skipping URL registration.")
            return

        module_path = self.metadata.get("urls_module")
        url_prefix = self.metadata.get("url_prefix", "")
        if not module_path:
            logger.debug("No urls_module specified in metadata; skipping URL registration.")
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
                if hasattr(pattern, 'url_patterns') and pattern.pattern.regex.pattern == f'^{url_prefix}':
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
        """Pretty print the messages returned by the Swarm.

        Formats assistant responses and tool calls with color-coded output for readability.

        Args:
            messages: List of message dictionaries from the Swarm response.
        """
        for message in messages:
            if message["role"] != "assistant":
                continue
            print(f"\033[94m{message['sender']}\033[0m:", end=" ")
            if message["content"]:
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
        """Main entry point for running a blueprint in CLI mode.

        Provides a command-line interface to launch the blueprint in interactive or non-interactive mode,
        with options for enabling advanced features like auto-completion and goal updates. Runs the async
        event loop to support non-blocking execution.

        Usage:
            python -m blueprint_module --config path/to/config.json [--auto-complete-task] [--update-user-goal] [--instruction "task"]
        """
        parser = argparse.ArgumentParser(description=f"Launch the {cls.__name__} blueprint with configurable options.")
        parser.add_argument("--config", type=str, default="./swarm_config.json", help="Path to the configuration file")
        parser.add_argument("--auto-complete-task", action="store_true", help="Enable multi-step auto-completion with LLM validation")
        parser.add_argument("--update-user-goal", action="store_true", help="Enable dynamic user goal updates via LLM analysis")
        parser.add_argument("--update-user-goal-frequency", type=int, default=5, help="Number of messages between goal updates")
        parser.add_argument("--instruction", type=str, help="Single instruction for non-interactive mode execution")
        args = parser.parse_args()

        logger.debug(f"Launching blueprint with config: {args.config}, auto_complete_task={args.auto_complete_task}, update_user_goal={args.update_user_goal}, update_user_goal_frequency={args.update_user_goal_frequency}, instruction={args.instruction}")
        from swarm.extensions.config.config_loader import load_server_config
        config = load_server_config(args.config)
        blueprint = cls(
            config=config,
            auto_complete_task=args.auto_complete_task,
            update_user_goal=args.update_user_goal,
            update_user_goal_frequency=args.update_user_goal_frequency
        )
        if args.instruction:
            asyncio.run(blueprint.non_interactive_mode(args.instruction))
        else:
            asyncio.run(blueprint.interactive_mode())
