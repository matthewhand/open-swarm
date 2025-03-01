import asyncio
import json
import logging
import os
import importlib.util
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from nemoguardrails import LLMRails, RailsConfig  # type: ignore

from swarm.core import Swarm
from swarm.extensions.config.config_loader import load_server_config
from swarm.repl import run_demo_loop
from swarm.settings import DEBUG
from swarm.utils.redact import redact_sensitive_data
from dotenv import load_dotenv
import argparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

class BlueprintBase(ABC):
    """
    Abstract base class for Swarm blueprints.
    Manages agents, tools, and active context for executing tasks, with optional agent creation.

    NEW FEATURES:
      1. Auto-completion of tasks until completion (via single-token LLM check).
      2. Dynamic updating of the user's goal based on LLM analysis of the conversation history.
      3. Configurable update frequency for the user goal, to optimize inference costs.
      4. URL prefix registration for blueprint-specific endpoints.
      5. Optional agent creation for non-agent-focused blueprints (e.g., UI extensions).
      6. Non-interactive CLI mode for single-instruction execution.
    """

    def __init__(
        self,
        config: dict,
        auto_complete_task: bool = False,
        update_user_goal: bool = False,
        update_user_goal_frequency: int = 5,
        **kwargs
    ):
        """
        Initialize the blueprint and optionally register agents.

        Args:
            config (dict): Configuration dictionary.
            auto_complete_task (bool): If True, the system will keep executing steps until
                the task is marked complete by the LLM.
            update_user_goal (bool): If True, the system will dynamically update the user's goal
                based on an LLM analysis of the conversation history.
            update_user_goal_frequency (int): Specifies how many messages (or iterations)
                should occur between user goal updates.
            **kwargs: Additional parameters (e.g., shared swarm_instance).
        """
        self.auto_complete_task = auto_complete_task
        self.update_user_goal = update_user_goal
        self.update_user_goal_frequency = update_user_goal_frequency
        self.last_goal_update_count = 0

        logger.debug(f"Initializing BlueprintBase with config: {redact_sensitive_data(config)}")
        if not hasattr(self, 'metadata') or not isinstance(self.metadata, dict):
            raise AssertionError("Blueprint metadata must be defined and must be a dictionary.")

        load_dotenv()
        logger.debug("Environment variables loaded from .env.")

        self.config = config
        # Load blueprint-specific local settings
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

        # Merge blueprint local settings INSTALLED_APPS into Django settings if available
        if hasattr(self, "local_settings") and self.local_settings and hasattr(self.local_settings, "INSTALLED_APPS"):
            from django.conf import settings as django_settings
            blueprint_apps = getattr(self.local_settings, "INSTALLED_APPS")
            for app in blueprint_apps:
                if app not in django_settings.INSTALLED_APPS:
                    django_settings.INSTALLED_APPS.append(app)
            logger.debug("Merged blueprint local settings INSTALLED_APPS into Django settings.")

        self.swarm = kwargs.get('swarm_instance')
        if self.swarm is not None:
            logger.debug("Using shared swarm instance from kwargs.")
        else:
            logger.debug("No shared swarm instance provided; creating a new one.")
            self.swarm = Swarm(config=self.config)
        logger.debug("Swarm instance created.")

        self.context_variables: Dict[str, Any] = {}
        self.context_variables["user_goal"] = ""
        self.starting_agent = None

        # Validate Environment Variables (warn instead of crash)
        required_env_vars = set(self.metadata.get('env_vars', []))
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing optional environment variables for {self.metadata.get('title', 'this blueprint')}: {', '.join(missing_vars)}. Some functionality may be limited.")
        else:
            logger.debug("All required environment variables present.")

        # Validate MCP Servers
        self.required_mcp_servers = self.metadata.get('required_mcp_servers', [])
        logger.debug(f"Required MCP servers: {self.required_mcp_servers}")

        # Register blueprint-specific components
        self.register_blueprint_models()
        self.register_blueprint_views()
        self.register_blueprint_urls()

        # Check if create_agents is overridden and call it if present
        if self._is_create_agents_overridden():
            agents = self.create_agents()
            # Initialize NeMo Guardrails for agents
            for agent_name, agent in agents.items():
                if getattr(agent, "nemo_guardrails_config", None):
                    guardrails_path = os.path.join("nemo_guardrails", agent.nemo_guardrails_config)
                    try:
                        rails_config = RailsConfig.from_path(guardrails_path)
                        agent.nemo_guardrails_instance = LLMRails(rails_config)
                        logger.debug(f"✅ Loaded NeMo Guardrails for agent: {agent.name} ({agent.nemo_guardrails_config})")
                    except Exception as e:
                        logger.warning(f"Could not load NeMo Guardrails for agent {agent.name}: {e}")
            self.swarm.agents.update(agents)
            logger.debug(f"Agents registered: {list(agents.keys())}")
        else:
            logger.debug("create_agents() not overridden; no agents registered.")

        asyncio.run(self.async_discover_agent_tools())
        logger.debug("Tool discovery completed.")

    def _is_create_agents_overridden(self) -> bool:
        """Check if create_agents() is overridden in the subclass."""
        base_method = BlueprintBase.create_agents
        subclass_method = self.__class__.create_agents
        return subclass_method is not base_method

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Metadata for the blueprint including title, description, and dependencies."""
        raise NotImplementedError

    def create_agents(self) -> Dict[str, Any]:
        """Default implementation returning an empty agent dict; override if agents are needed."""
        return {}

    async def async_discover_agent_tools(self) -> None:
        """Discover and register tools for each agent asynchronously."""
        logger.debug("Discovering tools for agents...")
        for agent_name, agent in self.swarm.agents.items():
            logger.debug(f"Discovering tools for agent: {agent_name}")
            try:
                tools = await self.swarm.discover_and_merge_agent_tools(agent)
                logger.debug(f"Discovered tools for agent '{agent_name}': {tools}")
            except Exception as e:
                logger.error(f"Failed to discover tools for agent '{agent_name}': {e}")

    def set_starting_agent(self, agent: Any) -> None:
        """Set the starting agent for the blueprint."""
        logger.debug(f"Setting starting agent to: {agent.name}")
        self.starting_agent = agent
        self.context_variables["active_agent_name"] = agent.name

    def determine_active_agent(self) -> Any:
        """Determine and return the active agent based on context_variables."""
        active_agent_name = self.context_variables.get("active_agent_name")
        if active_agent_name and active_agent_name in self.swarm.agents:
            logger.debug(f"Active agent determined: {active_agent_name}")
            return self.swarm.agents[active_agent_name]
        logger.debug("Falling back to the starting agent as active agent.")
        return self.starting_agent

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Execute a task with the given messages and context variables."""
        self.context_variables.update(context_variables)
        logger.debug(f"Context variables before execution: {self.context_variables}")

        if not self.swarm.agents:
            logger.debug("No agents defined; returning default response.")
            return {
                "response": {"messages": [{"role": "assistant", "content": "No agents available in this blueprint."}]},
                "context_variables": self.context_variables
            }

        if "active_agent_name" not in self.context_variables:
            if self.starting_agent:
                self.context_variables["active_agent_name"] = self.starting_agent.name
                logger.debug(f"active_agent_name not found, using starting agent: {self.starting_agent.name}")
            else:
                logger.error("No starting agent set and active_agent_name is missing.")
                raise ValueError("No active agent or starting agent available.")

        active_agent = self.determine_active_agent()
        logger.debug(f"Running with active agent: {active_agent.name}")

        response = self.swarm.run(
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

        if response.agent:
            self.context_variables["active_agent_name"] = response.agent.name
            logger.debug(f"Active agent updated to: {response.agent.name}")

        return {"response": response, "context_variables": self.context_variables}

    def set_active_agent(self, agent_name: str) -> None:
        """Explicitly set the active agent."""
        if agent_name in self.swarm.agents:
            self.context_variables["active_agent_name"] = agent_name
            logger.debug(f"Active agent set to: {agent_name}")
        else:
            logger.error(f"Agent '{agent_name}' not found. Cannot set as active agent.")

    def _is_task_done(self, user_goal: str, conversation_summary: str, last_assistant_message: str) -> bool:
        """Check if the task is complete by making a minimal LLM call."""
        check_prompt = [
            {"role": "system", "content": "You are a completion checker. Respond with ONLY 'YES' or 'NO' (no extra words)."},
            {"role": "user", "content": f"User's goal: {user_goal}\nConversation summary: {conversation_summary}\nLast assistant message: {last_assistant_message}\nIs the task fully complete? Answer only YES or NO."}
        ]
        done_check = self.swarm.run_llm(messages=check_prompt, max_tokens=1, temperature=0)
        raw_content = done_check.choices[0].message["content"].strip().upper()
        logger.debug(f"Done check response: {raw_content}")
        return raw_content.startswith("YES")

    def _update_user_goal(self, messages: List[Dict[str, str]]) -> None:
        """Update the user's goal based on an LLM analysis of the conversation history."""
        prompt = [
            {"role": "system", "content": "You are an assistant that summarizes the user's primary objective based on the conversation so far. Provide a concise, one-sentence summary capturing the user's goal."},
            {"role": "user", "content": "Summarize the user's goal based on this conversation:\n" + "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])}
        ]
        summary_response = self.swarm.run_llm(messages=prompt, max_tokens=30, temperature=0.3)
        new_goal = summary_response.choices[0].message["content"].strip()
        logger.debug(f"Updated user goal from LLM: {new_goal}")
        self.context_variables["user_goal"] = new_goal

    def interactive_mode(self, stream: bool = False) -> None:
        """Start the interactive REPL loop using the blueprint's Swarm instance."""
        logger.debug("Starting interactive mode.")
        if self.swarm.agents and not self.starting_agent:
            logger.error("Starting agent is not set but agents exist. Ensure set_starting_agent is called.")
            raise ValueError("Starting agent is not set.")
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Interactive Mode 🐝")
        messages: List[Dict[str, str]] = []
        agent = self.starting_agent if self.swarm.agents else None
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

            result = self.run_with_context(messages, self.context_variables or {})
            swarm_response = result["response"]

            if stream:
                self._process_and_print_streaming_response(swarm_response)
            else:
                self._pretty_print_response(swarm_response.messages)

            messages.extend(swarm_response.messages)
            if self.swarm.agents and swarm_response.agent:
                agent = swarm_response.agent

            if self.update_user_goal and (message_count - self.last_goal_update_count) >= self.update_user_goal_frequency:
                self._update_user_goal(messages)
                self.last_goal_update_count = message_count

            if self.auto_complete_task and agent:
                conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
                last_assistant = next((msg["content"] for msg in reversed(swarm_response.messages) if msg["role"] == "assistant" and msg.get("content")), "")
                while not self._is_task_done(self.context_variables.get("user_goal", ""), conversation_summary, last_assistant):
                    result2 = self.run_with_context(messages, self.context_variables or {})
                    swarm_response = result2["response"]
                    if stream:
                        self._process_and_print_streaming_response(swarm_response)
                    else:
                        self._pretty_print_response(swarm_response.messages)
                    messages.extend(swarm_response.messages)
                    if self.swarm.agents and swarm_response.agent:
                        agent = swarm_response.agent
                    conversation_summary = " ".join([msg["content"] for msg in messages[-4:] if msg.get("content")])
                    last_assistant = next((msg["content"] for msg in reversed(swarm_response.messages) if msg["role"] == "assistant" and msg.get("content")), "")
                print("\033[93m[System]\033[0m: Task is complete.")

    def non_interactive_mode(self, instruction: str, stream: bool = False) -> None:
        """Execute a single instruction and exit."""
        logger.debug(f"Starting non-interactive mode with instruction: {instruction}")
        if self.swarm.agents and not self.starting_agent:
            logger.error("Starting agent is not set but agents exist. Ensure set_starting_agent is called.")
            raise ValueError("Starting agent is not set.")
        if not self.swarm:
            logger.error("Swarm instance is not initialized.")
            raise ValueError("Swarm instance is not initialized.")

        print(f"{self.metadata.get('title', 'Blueprint')} Non-Interactive Mode 🐝")
        messages = [{"role": "user", "content": instruction}]
        self.context_variables["user_goal"] = instruction

        result = self.run_with_context(messages, self.context_variables or {})
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
                result2 = self.run_with_context(messages, self.context_variables or {})
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
        """Process and display the streaming response from Swarm."""
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
        self._register_module("models_module", "models")

    def register_blueprint_views(self) -> None:
        self._register_module("views_module", "views")

    def register_blueprint_urls(self) -> None:
        """Register blueprint URLs with the specified url_prefix."""
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
            import django.conf.urls
            import swarm.urls as core_urls
            
            m = importlib.import_module(module_path)
            if not hasattr(m, "urlpatterns"):
                logger.debug(f"No urlpatterns found in {module_path}")
                return

            if url_prefix and not url_prefix.endswith('/'):
                url_prefix += '/'

            # Use cli_name as the namespace for consistency with blueprint identity
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
        """Pretty print the messages returned by the Swarm."""
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
                name, args = f["name"], f["arguments"]
                arg_str = json.dumps(json.loads(args)).replace(":", "=")
                print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")

    @classmethod
    def main(cls):
        """Main entry point for running a blueprint in CLI mode."""
        parser = argparse.ArgumentParser(description=f"Launch the {cls.__name__} blueprint.")
        parser.add_argument("--config", type=str, default="./swarm_config.json", help="Path to the configuration file")
        parser.add_argument("--auto-complete-task", action="store_true", help="Enable multi-step auto-completion")
        parser.add_argument("--update-user-goal", action="store_true", help="Enable dynamic user goal updates")
        parser.add_argument("--update-user-goal-frequency", type=int, default=5, help="Messages between goal updates")
        parser.add_argument("--instruction", type=str, help="Single instruction for non-interactive mode")
        args = parser.parse_args()

        logger.debug(f"Launching blueprint with config: {args.config}, auto_complete_task={args.auto_complete_task}, update_user_goal={args.update_user_goal}, update_user_goal_frequency={args.update_user_goal_frequency}, instruction={args.instruction}")
        config = load_server_config(args.config)
        blueprint = cls(
            config=config,
            auto_complete_task=args.auto_complete_task,
            update_user_goal=args.update_user_goal,
            update_user_goal_frequency=args.update_user_goal_frequency
        )
        if args.instruction:
            blueprint.non_interactive_mode(args.instruction)
        else:
            blueprint.interactive_mode()
