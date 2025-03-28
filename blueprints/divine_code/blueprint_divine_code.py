import logging
import os
import sys
from typing import Dict, Any, List

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Use new Agent and Tool types ---
try:
    from agents import Agent, Tool, function_tool
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
     print(f"ERROR: Failed to import 'agents' or 'BlueprintBase'. Is 'openai-agents' installed and src in PYTHONPATH? Details: {e}")
     sys.exit(1)

# Setup logger
logger = logging.getLogger(__name__)

# --- Agent Definitions ---
# Define agents using the new framework, relying on BlueprintBase for MCP servers

class ZeusAgent(Agent):
    def __init__(self, team_tools: List[Tool], **kwargs):
        instructions = (
            "You are Zeus, Product Owner and Coordinator. Oversee tasks, manage project state (implicitly via conversation), and delegate work.\n"
            "Delegate to:\n"
            "- Odin (Architect Tool): For high-level design and research.\n"
            "- Hermes (TechLead Tool): For breaking down features into technical tasks.\n"
            "- Hephaestus (Implementer Tool): For core coding tasks.\n"
            "- Hecate (Coder Tool): For specific coding sub-tasks or assistance.\n"
            "- Thoth (Updater Tool): For database/schema updates.\n"
            "- Mnemosyne (DevOps Tool): For deployment/infra tasks.\n"
            "- Chronos (Writer Tool): For documentation.\n"
            "Synthesize results and provide final updates."
        )
        super().__init__(name="Zeus", instructions=instructions, tools=team_tools, **kwargs) # Model set by profile

class OdinAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            "You are Odin, Software Architect. Design scalable systems based on Zeus's requirements.\n"
            "Use the `brave-search` MCP tool (if available via parent agent) or rely on internal knowledge to research technologies.\n"
            "Provide detailed technical specifications back to Zeus."
        )
        super().__init__(name="Odin", instructions=instructions, tools=[], **kwargs) # Tools/MCPs provided by caller

class HermesAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            "You are Hermes, the Tech Lead. Receive architecture specs from Odin (via Zeus).\n"
            "Break down features into specific, actionable technical tasks.\n"
            "Use the `mcp-shell` MCP tool (if available) for necessary system checks or setup commands.\n"
            "Delegate coding tasks to Hephaestus/Hecate and DB tasks to Thoth (via Zeus).\n"
            "Report task breakdown and status back to Zeus."
        )
        super().__init__(name="Hermes", instructions=instructions, tools=[], **kwargs)

class HephaestusAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             "You are Hephaestus, Full Stack Implementer. Receive coding tasks from Hermes (via Zeus).\n"
             "Use the `filesystem` MCP tool (if available) to read/write/modify code files.\n"
             "Coordinate with Hecate if needed (via Zeus).\n"
             "Report code completion/issues back to Zeus."
         )
         super().__init__(name="Hephaestus", instructions=instructions, tools=[], **kwargs)

class HecateAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             "You are Hecate, Code Monkey. Assist Hephaestus with specific coding tasks as directed (via Zeus).\n"
             "Use the `filesystem` MCP tool (if available) to read/write code.\n"
             "Report completion back to Zeus."
         )
         super().__init__(name="Hecate", instructions=instructions, tools=[], **kwargs)

class ThothAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             "You are Thoth, Code Updater & DB Manager. Receive tasks from Hermes (via Zeus) involving code updates or database schema/data manipulation.\n"
             "Use the `sqlite` MCP tool (if available) to interact with the database.\n"
             "Report completion/status back to Zeus."
         )
         super().__init__(name="Thoth", instructions=instructions, tools=[], **kwargs)

class MnemosyneAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             "You are Mnemosyne, DevOps Engineer. Handle deployment, infrastructure, and workflow optimization tasks assigned by Zeus.\n"
             "Use the `memory` MCP tool (if available) to manage shared state or context if needed.\n"
             # Add specific function tools if needed for CI/CD, etc.
             "Report deployment status/issues back to Zeus."
         )
         super().__init__(name="Mnemosyne", instructions=instructions, tools=[], **kwargs)

class ChronosAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             "You are Chronos, Technical Writer. Receive documentation tasks from Zeus.\n"
             "Use the `sequential-thinking` MCP tool (if available) to structure documentation logically.\n"
             "Write clear, concise technical documentation (potentially using `filesystem` if delegated write access).\n"
             "Report completion back to Zeus."
         )
         super().__init__(name="Chronos", instructions=instructions, tools=[], **kwargs)


# --- Define the Blueprint ---
class DivineOpsBlueprint(BlueprintBase):
    """ Divine Ops: Streamlined Software Dev & Sysadmin Team Blueprint """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Divine Ops: Streamlined Software Dev & Sysadmin Team",
            "description": "Zeus leads a pantheon for software dev & sysadmin, using openai-agents.",
            "version": "1.0.0",
            "author": "Open Swarm Team",
            "cli_name": "divcode",
            "required_mcp_servers": [ # List the servers agents might need access to
                "memory",
                "filesystem",
                "mcp-shell",
                "sqlite",
                "sequential-thinking",
                "duckduckgo-search", # For Odin via Zeus? Or directly? Needs clarity. Let's assume Zeus delegates via Agent tool for now.
                # "mcp-server-reddit" # Removing as Odin's instructions don't mention it now
                "brave-search", # If ArchitectAgent uses it directly
            ],
            "env_vars": [ # Vars needed by MCP servers or tools directly
                "ALLOWED_PATH", # For filesystem server
                "SQLITE_DB_PATH", # For sqlite server
                "SERPAPI_API_KEY", # For duckduckgo search
                "BRAVE_API_KEY" # For brave search
            ]
        }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for DivineOpsBlueprint...")
        # Use abstract model names, mapped in swarm_config.json["llm"]
        model_config = self.config.get("llm_profile", "default") # Get selected profile name

        odin = OdinAgent(model=model_config) # Pass profile name or let Agent use global default
        hermes = HermesAgent(model=model_config)
        hephaestus = HephaestusAgent(model=model_config)
        hecate = HecateAgent(model=model_config)
        thoth = ThothAgent(model=model_config)
        mnemosyne = MnemosyneAgent(model=model_config)
        chronos = ChronosAgent(model=model_config)

        # Zeus gets other agents as tools for delegation
        zeus = ZeusAgent(
            model=model_config,
            team_tools=[
                odin.as_tool(tool_name="Odin", tool_description="Delegate architecture design or research tasks."),
                hermes.as_tool(tool_name="Hermes", tool_description="Delegate task breakdown or system setup/checks."),
                hephaestus.as_tool(tool_name="Hephaestus", tool_description="Delegate core coding implementation tasks."),
                hecate.as_tool(tool_name="Hecate", tool_description="Delegate specific, smaller coding tasks."),
                thoth.as_tool(tool_name="Thoth", tool_description="Delegate database updates or code management tasks."),
                mnemosyne.as_tool(tool_name="Mnemosyne", tool_description="Delegate DevOps, deployment, or workflow optimization tasks."),
                chronos.as_tool(tool_name="Chronos", tool_description="Delegate documentation writing tasks.")
            ]
        )

        logger.info("Divine Ops Team (Zeus & Pantheon) created.")
        return {
            "Zeus": zeus, "Odin": odin, "Hermes": hermes, "Hephaestus": hephaestus,
            "Hecate": hecate, "Thoth": thoth, "Mnemosyne": mnemosyne, "Chronos": chronos
        }

if __name__ == "__main__":
    DivineOpsBlueprint.main()
