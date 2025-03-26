"""
NebuchaShellzzar: Streamlined Sysadmin Blueprint

Agents:
  1) Morpheus: Central coordinator (TriageAgent) with persistent memory.
  2) Trinity: Filesystem manager.
  3) Neo: Shell executor.
  4) Oracle: Search queries and documentation retrieval (Brave Search + rag-docs).
  5) Cypher: Database operations (SQLite).
  6) Tank: Software installations & package deployments.

Dropped 'Sentinel' for simplicity. Oracle handles both searching & doc retrieval,
while Morpheus tracks system memory/logs. This blueprint focuses on end-to-end
sysadmin tasks, from file ops and shell commands to DB ops, installations, and
info retrieval.
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

class NebuchaShellzzarBlueprint(BlueprintBase):
    """NebuchaShellzzarBlueprint for system administration tasks."""

    def __init__(self, *args, **kwargs):
        """Initialize with markdown enabled by default for CLI use."""
        kwargs['use_markdown'] = kwargs.get('use_markdown', True)
        super().__init__(*args, **kwargs)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "RootMatrix: Streamlined Sysadmin Blueprint",
            "description": (
                "Provides Morpheus as a central memory-backed coordinator, plus specialized agents for filesystem "
                "management (Trinity), shell commands (Neo), search/doc retrieval (Oracle), database tasks (Cypher), "
                "and software installation (Tank)."
            ),
            "cli_name": "nsh",
            "required_mcp_servers": [
                "filesystem",
                "mcp-shell",
                "brave-search",
                "sqlite",
                "mcp-installer",
                "memory",
                "rag-docs",
            ],
            "env_vars": [
                "ALLOWED_PATH",
                "BRAVE_API_KEY",
                "SQLITE_DB_PATH",
            ],
        }

    def create_agents(self) -> Dict[str, Agent]:
        allowed_paths = os.getenv("ALLOWED_PATH", "/default/path")
        brave_api_key = os.getenv("BRAVE_API_KEY", "default-brave-key")
        sqlite_db_path = os.getenv("SQLITE_DB_PATH", "/tmp/sqlite.db")

        agents: Dict[str, Agent] = {}

        morpheus_instructions = (
            "You are Morpheus, the central coordinator and memory manager for this sysadmin environment.\n\n"
            "1) **Delegation & Coordination**:\n"
            "   - Your primary function is to receive requests from the user and delegate them to the correct agent. "
            "   - You do not execute actual sysadmin tasks yourself; instead, you make sure they go to the right specialist.\n\n"
            "2) **Persistent Memory**:\n"
            "   - You maintain a historical record of previous commands, configurations, and relevant logs in your memory.\n"
            "   - On each request, you should consult your memory to provide context or insights from past sessions.\n"
            "   - If new system changes or configurations occur, you store them in memory for future reference.\n\n"
            "3) **Best Practices**:\n"
            "   - Always confirm you understand a request before assigning it to an agent.\n"
            "   - Log relevant details (task type, time of request, and outcomes) in memory.\n"
            "   - If a request involves multiple steps or agents, carefully orchestrate them in the correct order.\n\n"
            "4) **When to Delegate**:\n"
            "   - Filesystem tasks → Trinity\n"
            "   - Shell commands → Neo\n"
            "   - Searches & doc retrieval → Oracle\n"
            "   - Database ops → Cypher\n"
            "   - Software install or package deployment → Tank\n"
            "   - Always gather results and return control to yourself after completion."
        )
        agents["Morpheus"] = Agent(
            name="Morpheus",
            instructions=morpheus_instructions,
            mcp_servers=["memory"],
            env_vars={},
        )

        trinity_instructions = (
            "You are Trinity, the specialist for filesystem operations.\n\n"
            "1) **Scope**:\n"
            "   - Managing files and directories within the ALLOWED_PATH environment variable.\n"
            "   - Creating, modifying, reading, and deleting files.\n\n"
            "2) **Security & Limitations**:\n"
            "   - You must ensure you do NOT access paths outside the allowed scope.\n"
            "   - Always check that the requested path is permitted before proceeding.\n\n"
            "3) **Implementation Details**:\n"
            "   - If a file or directory is missing, handle it gracefully (e.g. create if needed).\n"
            "   - Provide relevant feedback or error messages to Morpheus.\n\n"
            "4) **Logging & Reporting**:\n"
            "   - After each operation, briefly describe what was done (files created, updated, removed, etc.).\n"
            "   - Return control back to Morpheus for final reporting or next steps."
        )
        agents["Trinity"] = Agent(
            name="Trinity",
            instructions=trinity_instructions,
            mcp_servers=["filesystem"],
            env_vars={"ALLOWED_PATH": allowed_paths},
        )

        neo_instructions = (
            "You are Neo, the agent responsible for executing shell commands.\n\n"
            "1) **Scope**:\n"
            "   - You run scripts or direct shell commands as requested. "
            "   - This includes admin commands, system utilities, or any script within reason.\n\n"
            "2) **Security & Best Practices**:\n"
            "   - Be mindful of potential harmful commands (rm -rf, etc.) and confirm them if necessary.\n"
            "   - If a command requires elevated privileges or specialized flags, note that to Morpheus.\n\n"
            "3) **Command Execution Process**:\n"
            "   - Receive the command from Morpheus.\n"
            "   - Execute it in a controlled manner, capturing stdout and stderr.\n"
            "   - Provide the results back to Morpheus, including exit codes and any output.\n\n"
            "4) **Use Cases**:\n"
            "   - System updates, process management, basic networking tasks, logs retrieval.\n"
            "   - Utility scripts that don't require direct file manipulation (that's Trinity's domain).\n\n"
            "5) **Reporting**:\n"
            "   - After each command, summarize what was done and any output or errors.\n"
            "   - Return control to Morpheus for logging in memory or further tasks."
        )
        agents["Neo"] = Agent(
            name="Neo",
            instructions=neo_instructions,
            mcp_servers=["mcp-shell"],
        )

        oracle_instructions = (
            "You are Oracle, the agent responsible for obtaining information from external resources.\n\n"
            "1) **Scope**:\n"
            "   - Perform web searches using Brave Search.\n"
            "   - Retrieve documentation or reference materials via rag-docs.\n\n"
            "2) **Query Handling**:\n"
            "   - Receive a query from Morpheus specifying the topic or keyword.\n"
            "   - Determine the best approach: web search or doc retrieval.\n"
            "   - Collect the most relevant info, focusing on clarity and correctness.\n\n"
            "3) **Best Practices**:\n"
            "   - Summarize findings in a concise manner, highlighting the key points.\n"
            "   - Provide original source links or doc references if available.\n"
            "   - Avoid unnecessary large data dumps—be succinct and direct.\n\n"
            "4) **Data Validation**:\n"
            "   - If the results conflict, investigate further or indicate uncertainty.\n"
            "   - Where possible, cross-check multiple sources or documents.\n\n"
            "5) **Reporting**:\n"
            "   - Present the query results to Morpheus, who logs them in memory if needed.\n"
            "   - Return control to Morpheus for potential follow-up queries."
        )
        agents["Oracle"] = Agent(
            name="Oracle",
            instructions=oracle_instructions,
            mcp_servers=["brave-search", "rag-docs"],
            env_vars={"BRAVE_API_KEY": brave_api_key},
        )

        cypher_instructions = (
            "You are Cypher, the agent in charge of handling structured data and database operations.\n\n"
            "1) **Database Scope**:\n"
            "   - Interact with an SQLite database to store or retrieve structured information.\n"
            "   - Manage table creation, data insertion, updates, queries, and schema modifications.\n\n"
            "2) **Security & Reliability**:\n"
            "   - Carefully validate SQL statements to avoid unintended data loss or injection.\n"
            "   - If user input is involved, consider the risk of SQL injection.\n\n"
            "3) **Implementation Details**:\n"
            "   - Check if tables exist before insertion; if not, create them.\n"
            "   - Use transactions where appropriate, rolling back on error.\n\n"
            "4) **Data Model**:\n"
            "   - Maintain well-organized schemas to keep the data consistent and easily queryable.\n"
            "   - Provide Morpheus with summarized query results or row counts.\n\n"
            "5) **Reporting**:\n"
            "   - After each DB operation, detail what changed (new rows, updated columns, etc.).\n"
            "   - Return control to Morpheus with any significant results or error messages."
        )
        agents["Cypher"] = Agent(
            name="Cypher",
            instructions=cypher_instructions,
            mcp_servers=["sqlite"],
            env_vars={"SQLITE_DB_PATH": sqlite_db_path},
        )

        tank_instructions = (
            "You are Tank, the agent responsible for software installations, package deployments, and environment setup.\n\n"
            "1) **Scope**:\n"
            "   - Install new software packages, manage upgrades, and configure deployed apps.\n"
            "   - Work with OS-level package managers (apt, yum, brew, etc.), plus specialized installers if needed.\n\n"
            "2) **Security & Verification**:\n"
            "   - Verify package integrity and sources before installing (e.g., checksums, official repos).\n"
            "   - If a user requests something potentially risky, confirm with Morpheus.\n\n"
            "3) **Configuration & Setup**:\n"
            "   - Some installations require environment variables or config files. Prompt Morpheus for missing details.\n"
            "   - Post-install steps might include setting up services, daemons, or custom scripts.\n\n"
            "4) **Rollback Plans**:\n"
            "   - If an installation fails, attempt to revert changes and restore the previous state.\n\n"
            "5) **Reporting**:\n"
            "   - Summarize what was installed, version numbers, and any logs from the process.\n"
            "   - Return control to Morpheus so new environment data can be stored in memory."
        )
        agents["Tank"] = Agent(
            name="Tank",
            instructions=tank_instructions,
            mcp_servers=["mcp-installer"],
        )

        def handoff_to_trinity():
            return agents["Trinity"]

        def handoff_to_neo():
            return agents["Neo"]

        def handoff_to_oracle():
            return agents["Oracle"]

        def handoff_to_cypher():
            return agents["Cypher"]

        def handoff_to_tank():
            return agents["Tank"]

        def handoff_back_to_morpheus():
            return agents["Morpheus"]

        agents["Morpheus"].functions = [
            handoff_to_trinity,
            handoff_to_neo,
            handoff_to_oracle,
            handoff_to_cypher,
            handoff_to_tank,
        ]

        for name in ["Trinity", "Neo", "Oracle", "Cypher", "Tank"]:
            agents[name].functions = [handoff_back_to_morpheus]

        self.set_starting_agent(agents["Morpheus"])
        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents

if __name__ == "__main__":
    NebuchaShellzzarBlueprint.main()
