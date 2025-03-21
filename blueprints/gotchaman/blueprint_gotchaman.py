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
    def __init__(self):
        self.running = False
        self.thread = None
        self.status = ""

    def start(self, status: str = "Automating the CLI..."):
        if self.running:
            return
        self.running = True
        self.status = status
        def spinner_thread():
            spin_symbols = ["(●>)", "(○>)", "(◐>)", "(◑>)"]
            index = 0
            while self.running:
                symbol = spin_symbols[index % len(spin_symbols)]
                sys.stdout.write(f"\r\033[94m{symbol}\033[0m {self.status}")
                sys.stdout.flush()
                index += 1
                time.sleep(0.2)
        import threading
        th = threading.Thread(target=spinner_thread, daemon=True)
        th.start()
        self.thread = th

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


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
        self._gotchaman_spinner = GotchamanSpinner()

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Gotchaman: CLI Automation Blueprint",
            "description": (
                "A blueprint for automating CLI tasks with custom colored output and an animated bird-head spinner. "
                "Includes agents for coordination (Ken), command execution (Joe), logging (Jun), suggestions (Jinpei), "
                "and insights (Ryu)."
            ),
            "required_mcp_servers": ["slack", "mondayDotCom", "basic-memory", "mcp-npx-fetch"],
            "env_vars": ["SLACK_API_KEY", "MONDAY_API_KEY"]
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
        MCP_SERVERS = [
            "mcp-shell", "mcp-doc-forge", "mcp-server-web", "mcp-server-file",
            "mcp-server-db", "mcp-server-api", "mcp-server-search", "mcp-server-monitor"
        ]
        import random
        
        agents: Dict[str, Agent] = {}
        # Starting agent
        # Explicit agent assignments with defined MCP servers and environment variables
        agents["Ken"] = Agent(
            name="Ken",
            instructions="You are Ken, the Coordinator for Gotchaman. Your team: Joe (Runner), Jun (Logger), Jinpei (Advisor), and Ryu (Reviewer). Delegate tasks accordingly.",
            mcp_servers=["basic-memory"],
            env_vars={}
        )
        agents["Joe"] = Agent(
            name="Joe",
            instructions="You are Joe, the Runner. Your MCP server: slack. Use it to execute shell commands.",
            mcp_servers=["slack"],
            env_vars={"SLACK_API_KEY": os.getenv("SLACK_API_KEY", "")}
        )
        agents["Jun"] = Agent(
            name="Jun",
            instructions="You are Jun, the Logger. Your MCP server: mondayDotCom. Monitor outputs and log feedback.",
            mcp_servers=["mondayDotCom"],
            env_vars={"MONDAY_API_KEY": os.getenv("MONDAY_API_KEY", "")}
        )
        agents["Jinpei"] = Agent(
            name="Jinpei",
            instructions="You are Jinpei, the Advisor. Your MCP server: mcp-npx-fetch. Provide quick task suggestions.",
            mcp_servers=["mcp-npx-fetch"],
            env_vars={}
        )
        agents["Ryu"] = Agent(
            name="Ryu",
            instructions="You are Ryu, the Reviewer. Your MCP server: basic-memory. Review outputs and offer insights.",
            mcp_servers=["basic-memory"],
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

    def spinner_method(self, message: str = "Automating the CLI...", error: bool = False) -> None:
        """
        Compatibility method for direct spinner references using the custom spinner.
        """
        if not hasattr(self, "_gotchaman_spinner") or not isinstance(self._gotchaman_spinner, GotchamanSpinner):
            return
        if error:
            self._gotchaman_spinner.stop()
        else:
            self._gotchaman_spinner.start(message)

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