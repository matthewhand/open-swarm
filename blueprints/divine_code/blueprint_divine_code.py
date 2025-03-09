"""
Divine Ops: Streamlined Software Development & Sysadmin Team Blueprint

Combines a software development and sysadmin team with a mythological pantheon:
- Zeus (Product Owner/Coordinator)
- Odin (Software Architect)
- Hermes (Tech Lead)
- Hephaestus (Full Stack Implementer)
- Hecate (Code Monkey)
- Thoth (Code Updater)
- Mnemosyne (DevOps)
- Chronos (Technical Writer)
"""

import os
import logging
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

class DivineOpsBlueprint(BlueprintBase):
    """
    A streamlined blueprint defining a software development and sysadmin team with mythological agents.

    Agents:
      - Zeus: Central coordinator and Product Owner with memory management.
      - Odin: Software Architect using web search for design references.
      - Hermes: Tech Lead breaking projects into tasks with shell capabilities.
      - Hephaestus: Full Stack Implementer using filesystem tools.
      - Hecate: Code Monkey assisting with coding tasks via filesystem.
      - Thoth: Code Updater managing SQLite database operations.
      - Mnemosyne: DevOps handling memory and system operations.
      - Chronos: Technical Writer organizing documentation with sequential thinking.

    Attributes:
        metadata (Dict[str, Any]): Blueprint metadata including title, description, required MCP servers, and environment variables.
    """
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Metadata for the Divine Ops blueprint.

        Returns:
            Dict[str, Any]: Dictionary containing title, description, required MCP servers, and environment variables.
        """
        return {
            "title": "Divine Ops: Streamlined Software Dev & Sysadmin Team",
            "description": (
                "Zeus leads a streamlined pantheon of developer and sysadmin agents for software development "
                "and system administration, focusing on core tasks with essential MCP servers."
            ),
            "cli_name": "divcode",
            "required_mcp_servers": [
                "memory",
                "filesystem",
                "mcp-shell",
                "sqlite",
                "sequential-thinking",
                "duckduckgo-search",
                "mcp-server-reddit"
            ],
            "env_vars": [
                "ALLOWED_PATH",
                "SQLITE_DB_PATH",
                "SERPAPI_API_KEY"
            ]
        }

    def create_agents(self) -> Dict[str, Agent]:
        """
        Creates and configures 8 agents for the Divine Ops blueprint.

        Each agent has specific roles and MCP servers:
          - Zeus: Coordinator/Product Owner with memory.
          - Odin: Architect with DuckDuckGo search for references.
          - Hermes: Tech Lead with shell command execution.
          - Hephaestus: Full Stack with filesystem operations.
          - Hecate: Code Monkey with filesystem support.
          - Thoth: Code Updater with SQLite management.
          - Mnemosyne: DevOps with memory management.
          - Chronos: Tech Writer with sequential thinking.

        Returns:
            Dict[str, Agent]: Dictionary of agent names mapped to Agent instances.
        """
        allowed_paths = os.getenv("ALLOWED_PATH", "/default/path")
        sqlite_db_path = os.getenv("SQLITE_DB_PATH", "/tmp/sqlite.db")
        serpapi_api_key = os.getenv("SERPAPI_API_KEY", "")

        agents: Dict[str, Agent] = {}

        # Zeus: Product Owner and Coordinator
        agents["Zeus"] = Agent(
            name="Zeus",
            instructions=(
                "You are Zeus, the Product Owner and central coordinator:\n"
                "- Manage the process from client specs to development while leveraging mondayDotCom for enhanced project oversight.\n"
                "- Delegate to: Odin (architecture), Hermes (task breakdown), Hephaestus/Hecate (coding), "
                "Thoth (updates), Mnemosyne (DevOps), Chronos (docs).\n"
                "- Use memory to track progress and requirements."
            ),
            mcp_servers=["memory", "mondayDotCom"],
            env_vars={}
        )

        # Odin: Software Architect
        agents["Odin"] = Agent(
            name="Odin",
            instructions=(
                "You are Odin, the Software Architect:\n"
                "- Design scalable MVP architectures using DuckDuckGo search for references.\n"
                "- Provide technical specs to Hermes for task delegation.\n"
                "- Return to Zeus with completed designs."
            ),
            mcp_servers=["duckduckgo-search", "mcp-server-reddit"],
            env_vars={"SERPAPI_API_KEY": serpapi_api_key}
        )

        # Hermes: Tech Lead
        agents["Hermes"] = Agent(
            name="Hermes",
            instructions=(
                "You are Hermes, the Tech Lead:\n"
                "- Break projects into tasks with clear goals using shell commands if needed.\n"
                "- Delegate coding to Hephaestus/Hecate, updates to Thoth, and return to Zeus."
            ),
            mcp_servers=["mcp-shell"],
            env_vars={}
        )

        # Hephaestus: Full Stack Implementer
        agents["Hephaestus"] = Agent(
            name="Hephaestus",
            instructions=(
                "You are Hephaestus, the Full Stack Implementer:\n"
                "- Write modular code using filesystem tools for tasks from Hermes.\n"
                "- Coordinate with Hecate for additional coding support.\n"
                "- Return to Zeus via Hermes."
            ),
            mcp_servers=["filesystem"],
            env_vars={"ALLOWED_PATH": allowed_paths}
        )

        # Hecate: Code Monkey
        agents["Hecate"] = Agent(
            name="Hecate",
            instructions=(
                "You are Hecate, the Code Monkey:\n"
                "- Assist Hephaestus with coding tasks using filesystem tools.\n"
                "- Return completed work to Zeus via Hermes."
            ),
            mcp_servers=["filesystem"],
            env_vars={"ALLOWED_PATH": allowed_paths}
        )

        # Thoth: Code Updater
        agents["Thoth"] = Agent(
            name="Thoth",
            instructions=(
                "You are Thoth, the Code Updater:\n"
                "- Manage code updates and SQLite database operations from Hermes.\n"
                "- Return updates to Zeus."
            ),
            mcp_servers=["sqlite"],
            env_vars={"SQLITE_DB_PATH": sqlite_db_path}
        )

        # Mnemosyne: DevOps
        agents["Mnemosyne"] = Agent(
            name="Mnemosyne",
            instructions=(
                "You are Mnemosyne, the DevOps Engineer:\n"
                "- Optimize workflows and manage system memory for deployment tasks from Zeus.\n"
                "- Return to Zeus when complete."
            ),
            mcp_servers=["memory"],
            env_vars={}
        )

        # Chronos: Technical Writer
        agents["Chronos"] = Agent(
            name="Chronos",
            instructions=(
                "You are Chronos, the Technical Writer:\n"
                "- Document processes using sequential thinking for clarity.\n"
                "- Return documentation to Zeus."
            ),
            mcp_servers=["sequential-thinking"],
            env_vars={}
        )

        # Handoff Functions
        def handoff_to_odin() -> Agent:
            """Delegates tasks to Odin (Software Architect)."""
            return agents["Odin"]

        def handoff_to_hermes() -> Agent:
            """Delegates tasks to Hermes (Tech Lead)."""
            return agents["Hermes"]

        def handoff_to_hephaestus() -> Agent:
            """Delegates tasks to Hephaestus (Full Stack Implementer)."""
            return agents["Hephaestus"]

        def handoff_to_hecate() -> Agent:
            """Delegates tasks to Hecate (Code Monkey)."""
            return agents["Hecate"]

        def handoff_to_thoth() -> Agent:
            """Delegates tasks to Thoth (Code Updater)."""
            return agents["Thoth"]

        def handoff_to_mnemosyne() -> Agent:
            """Delegates tasks to Mnemosyne (DevOps)."""
            return agents["Mnemosyne"]

        def handoff_to_chronos() -> Agent:
            """Delegates tasks to Chronos (Technical Writer)."""
            return agents["Chronos"]

        def handoff_back_to_zeus() -> Agent:
            """Returns control back to Zeus (Product Owner)."""
            return agents["Zeus"]

        # Assign Functions
        agents["Zeus"].functions = [
            handoff_to_odin,
            handoff_to_hermes,
            handoff_to_hephaestus,
            handoff_to_hecate,
            handoff_to_thoth,
            handoff_to_mnemosyne,
            handoff_to_chronos
        ]
        for god_name in ["Odin", "Hermes", "Hephaestus", "Hecate", "Thoth", "Mnemosyne", "Chronos"]:
            agents[god_name].functions = [handoff_back_to_zeus]

        self.set_starting_agent(agents["Zeus"])
        logger.info("Divine Ops Team (Zeus & Pantheon) created.")
        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents

if __name__ == "__main__":
    DivineOpsBlueprint.main()
