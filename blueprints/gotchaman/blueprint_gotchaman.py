"""
Gotchaman: CLI Automation Blueprint with Custom Colored Output

This blueprint provides CLI automation capabilities with the following customizations:
  - A custom colored spinner override that animates a bird-head prompt.
  - A custom render_output method that prints output in color on the CLI.
  - Five agents: Ken, Joe, Jun, Jinpei, and Ryu.
"""

import os
import sys
import time
import logging
import subprocess
import itertools
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

# Configure logging for our blueprint.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


class GotchamanSpinner:
    """
    A custom spinner object that overrides the parent's built-in spinner usage.
    Instead of the default spinner characters, this will animate various bird-face symbols.
    """

    def __init__(self):
        self.running = False
        self.thread = None
        self.status = ""
        self.error_mode = False

    def start(self, status: str = "Automating the CLI...", agent_prompt: str = "", blueprint=None):
        """
        Start spinning with the given status message, agent prompt, and blueprint.
        """
        if self.running:
            self.status = status
            self.agent_prompt = agent_prompt
            self.blueprint = blueprint
            return
        self.running = True
        self.status = status
        self.error_mode = False
        self.agent_prompt = agent_prompt
        self.blueprint = blueprint
        self.thread = None
        self.thread = self._spawn_thread()

    def stop(self):
        """
        Stop spinning.
        """
        if not self.running:
            return
        self.running = False
        if self.thread is not None:
            self.thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _spawn_thread(self):
        import threading

        def spinner_thread():
            import time
            import re
            ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
            spinner_frames = ["◉", "◕", "◔", "◡"]
            index = 0
            while self.running:
                if hasattr(self, 'blueprint') and self.blueprint.prompt:
                    agent_prompt_str = ansi_escape.sub('', self.blueprint.prompt).strip()
                elif hasattr(self, 'agent_prompt') and self.agent_prompt:
                    agent_prompt_str = ansi_escape.sub('', self.agent_prompt).strip()
                else:
                    agent_prompt_str = ""
                if agent_prompt_str and agent_prompt_str.startswith('(') and len(agent_prompt_str) >= 3:
                    animated_eye = spinner_frames[index % len(spinner_frames)]
                    new_prompt = f"({animated_eye}{agent_prompt_str[2:]}"
                elif not agent_prompt_str:
                    spin_symbols = ["( ◉ )>", "( ◕ )>", "( ◔ )>", "( ◡ )>"]
                    new_prompt = spin_symbols[index % len(spin_symbols)]
                else:
                    new_prompt = agent_prompt_str
                output = f"\r\033[94m{new_prompt}\033[0m {self.status}"
                sys.stdout.write(output)
                sys.stdout.flush()
                index += 1
                time.sleep(0.5)

        th = threading.Thread(target=spinner_thread, daemon=True)
        th.start()
        return th

    def set_error(self, status: str = "Error occurred"):
        """
        Change spinner to a fixed error display.
        """
        self.error_mode = True
        self.status = status


def execute_command(command: str) -> None:
    """
    Executes a shell command and logs its output.
    """
    try:
        logger.debug(f"Executing command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(f"Command output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr}")


def read_file(path: str) -> str:
    """
    Reads the file from the specified path.
    """
    try:
        logger.debug(f"Reading file at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file at {path}: {e}")
        return ""


def write_file(path: str, content: str) -> None:
    """
    Writes content to a file at the specified path.
    """
    try:
        logger.debug(f"Writing to file at: {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug("File write successful.")
    except Exception as e:
        logger.error(f"Error writing file at {path}: {e}")


class GotchamanBlueprint(BlueprintBase):
    """
    Gotchaman: CLI Automation Blueprint

    Agents:
      - Ken: Coordinator for delegating CLI tasks.
      - Joe: Runner, responsible for executing shell commands.
      - Jun: Logger, monitors outputs.
      - Jinpei: Auxiliary agent that provides quick suggestions.
      - Ryu: Additional agent that offers insights and reviews outputs.
    """

    def __init__(self, config: dict, **kwargs):
        super().__init__(config, **kwargs)
        # Override the built-in spinner with our custom spinner
        self.spinner = GotchamanSpinner()

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Gotchaman: CLI Automation Blueprint",
            "description": (
                "A blueprint for automating CLI tasks with custom colored output and an animated bird-head spinner. "
                "Includes agents for coordination (Ken), command execution (Joe), logging (Jun), suggestions (Jinpei), "
                "and insights (Ryu)."
            ),
            "required_mcp_servers": [],
            "env_vars": []
        }

    @property
    def prompt(self) -> str:
        agent = self.context_variables.get("active_agent_name", "Ken")
        if agent == "Ken":
            return "\033[94m(^>)\033[0m "
        elif agent == "Joe":
            return "\033[94m(O>>\033[0m "
        elif agent == "Jun":
            return "\033[94m(~>)\033[0m "
        elif agent == "Jinpei":
            return "\033[94m(o>-\033[0m "
        else:
            return "\033[94m(O)^)\033[0m "

    def create_agents(self) -> Dict[str, Agent]:
        agents: Dict[str, Agent] = {}
        # Starting agent
        agents["Ken"] = Agent(
            name="Ken",
            instructions="You are Ken, the Coordinator for Gotchaman. Delegate CLI tasks to your fellow agents.",
            mcp_servers=["memory", "mcp-shell"],
            env_vars={}
        )
        # Non-starting agents
        agents["Joe"] = Agent(
            name="Joe",
            instructions="You are Joe, the Runner for Gotchaman. Execute shell commands using available tools.",
            mcp_servers=["filesystem", "mcp-npx-fetch"],
            env_vars={}
        )
        agents["Jun"] = Agent(
            name="Jun",
            instructions="You are Jun, the Logger for Gotchaman. Monitor outputs and log system feedback.",
            mcp_servers=["memory", "sqlite"],
            env_vars={}
        )
        agents["Jinpei"] = Agent(
            name="Jinpei",
            instructions="You are Jinpei, an auxiliary agent for Gotchaman. Provide quick suggestions for tasks.",
            mcp_servers=["duckduckgo-search", "mcp-doc-forge"],
            env_vars={}
        )
        agents["Ryu"] = Agent(
            name="Ryu",
            instructions="You are Ryu, an additional agent for Gotchaman. Review outputs and offer extra insights.",
            mcp_servers=["brave-search", "mcp-server-reddit"],
            env_vars={}
        )

        def handoff_to(target: str):
            def _handoff() -> Agent:
                return agents[target]
            _handoff.__name__ = f"handoff_to_{target}"
            return _handoff

        object.__setattr__(agents["Ken"], "functions", [
            handoff_to("Joe"),
            handoff_to("Jun"),
            handoff_to("Jinpei"),
            handoff_to("Ryu")
        ])
        object.__setattr__(agents["Joe"], "functions", [handoff_to("Ken")])
        object.__setattr__(agents["Jun"], "functions", [handoff_to("Ken")])
        object.__setattr__(agents["Jinpei"], "functions", [handoff_to("Ken")])
        object.__setattr__(agents["Ryu"], "functions", [handoff_to("Ken")])

        object.__setattr__(agents["Ken"], "tools", {})
        object.__setattr__(agents["Joe"], "tools", {
            "execute_command": execute_command,
            "read_file": read_file,
            "write_file": write_file
        })
        object.__setattr__(agents["Jun"], "tools", {
            "execute_command": execute_command
        })
        object.__setattr__(agents["Jinpei"], "tools", {})
        object.__setattr__(agents["Ryu"], "tools", {})

        self.set_starting_agent(agents["Ken"])
        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents

    def spinner(self, message: str = "Automating the CLI...", error: bool = False) -> None:
        """
        Retained for backward compatibility if code references spinner() directly.
        This method defers to the custom GotchamanSpinner instance in self.spinner.
        """
        if not self.spinner or not isinstance(self.spinner, GotchamanSpinner):
            return
        if error:
            self.spinner.set_error(message)
        else:
            self.spinner.start(message, self.prompt())

    def render_output(self, text: str, color: str = "green") -> None:
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
        }
        reset_code = "\033[0m"
        color_code = colors.get(color.lower(), "\033[92m")
        print(f"{color_code}{text}{reset_code}")


if __name__ == "__main__":
    GotchamanBlueprint.main()