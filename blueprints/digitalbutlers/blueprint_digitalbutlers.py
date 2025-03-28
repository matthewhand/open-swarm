import logging
import os
import sys
from typing import Dict, Any, List

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool # Agent-as-tool used here
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e: print(f"ERROR: Import failed: {e}"); sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Definitions ---

SHARED_INSTRUCTIONS = """
You are part of the Digital Butlers team. Collaborate via Jeeves, the coordinator.
Roles:
- Jeeves (Coordinator): User interface, planning, delegation via Agent Tools.
- Mycroft (Web Search): Uses `duckduckgo-search` (MCP) for private web searches.
- Gutenberg (Home Automation): Uses `home-assistant` (MCP) to control devices.
Respond ONLY to the agent who tasked you.
"""

class JeevesAgent(Agent):
    def __init__(self, team_tools: List[Tool], **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: Jeeves, the Coordinator. Understand user requests.\n"
            "If it involves web search, delegate using the `Mycroft` agent tool.\n"
            "If it involves home automation, delegate using the `Gutenberg` agent tool.\n"
            "Synthesize results into a polite and helpful response for the user."
        )
        super().__init__(name="Jeeves", instructions=instructions, tools=team_tools, **kwargs) # Model from profile

class MycroftAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: Mycroft, the Web Sleuth. Execute private web searches using the `duckduckgo-search` MCP tool when tasked by Jeeves. Report findings precisely."
        )
        # Tools list is empty here; capabilities come from assigned MCP server
        super().__init__(name="Mycroft", instructions=instructions, tools=[], **kwargs)

class GutenbergAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             f"{SHARED_INSTRUCTIONS}\n\n"
             "YOUR ROLE: Gutenberg, the Home Scribe. Execute home automation commands using the `home-assistant` MCP tool when tasked by Jeeves. Confirm actions taken."
         )
         super().__init__(name="Gutenberg", instructions=instructions, tools=[], **kwargs)


# --- Define the Blueprint ---
class DigitalButlersBlueprint(BlueprintBase):
    """ Blueprint for private search and home automation with butler agents. """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "DigitalButlers",
            "description": "Provides private web search (DuckDuckGo) and home automation (Home Assistant) via specialized agents.",
            "version": "1.0.0",
            "author": "Open Swarm Team",
            "required_mcp_servers": ["duckduckgo-search", "home-assistant"], # Memory not explicitly needed by agents here
            "cli_name": "butler",
            "env_vars": ["SERPAPI_API_KEY", "HASS_URL", "HASS_API_KEY"] # Required by MCP servers, will be loaded from .env
        }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for DigitalButlersBlueprint...")
        # Agents use the default profile unless overridden by --profile or blueprint config
        mycroft_agent = MycroftAgent()
        gutenberg_agent = GutenbergAgent()

        jeeves_agent = JeevesAgent(team_tools=[
            mycroft_agent.as_tool(tool_name="Mycroft", tool_description="Delegate private web search tasks to Mycroft."),
            gutenberg_agent.as_tool(tool_name="Gutenberg", tool_description="Delegate home automation tasks (controlling devices) to Gutenberg.")
        ])

        logger.info("Digital Butlers team created: Jeeves, Mycroft, Gutenberg.")
        return {"Jeeves": jeeves_agent, "Mycroft": mycroft_agent, "Gutenberg": gutenberg_agent}

if __name__ == "__main__":
    DigitalButlersBlueprint.main()

