import logging
import sys
from typing import List, Dict, Any, Optional, ClassVar

try:
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer
    # Corrected Import: Remove 'src.' prefix
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in blueprint_gaggle: {e}. Check 'openai-agents' install and project structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tools ---
@function_tool
def create_story_outline(topic: str) -> str:
    """Generates a basic story outline based on a topic."""
    logger.info(f"Generating outline for: {topic}")
    # In a real scenario, this might involve more logic or an LLM call.
    return f"Outline for {topic}:\n1. Introduction\n2. Rising Action\n3. Climax\n4. Falling Action\n5. Resolution"

@function_tool
def write_story_part(part_name: str, outline: str, previous_parts: str) -> str:
    """Writes a specific part of the story using the outline and previous context."""
    logger.info(f"Writing story part: {part_name}")
    # Simple placeholder implementation
    return f"This is the content for the '{part_name}' part of the story, following:\n{previous_parts}\nBased on outline:\n{outline}"

@function_tool
def edit_story(full_story: str, edit_instructions: str) -> str:
    """Edits the complete story based on instructions."""
    logger.info(f"Editing story with instructions: {edit_instructions}")
    # Simple placeholder for editing
    return f"Edited Story (instructions: '{edit_instructions}'):\n{full_story}\n[Edited Content Added]"

# --- Agent Definitions ---
class PlannerAgent(Agent):
    def __init__(self, **kwargs):
        instructions = "You are the Planner. Your goal is to take a user's story topic and create a coherent outline using the 'create_story_outline' tool. Respond ONLY with the generated outline."
        super().__init__(name="Planner", instructions=instructions, tools=[create_story_outline], **kwargs)

class WriterAgent(Agent):
    def __init__(self, **kwargs):
        instructions = "You are a Writer. You receive a story part name (e.g., 'Introduction', 'Climax'), the full outline, and any previously written parts. Write the content for ONLY your assigned part using the 'write_story_part' tool, ensuring it flows logically from previous parts and fits the outline. Respond ONLY with the text generated for your part."
        super().__init__(name="Writer", instructions=instructions, tools=[write_story_part], **kwargs)

class EditorAgent(Agent):
    def __init__(self, **kwargs):
        instructions = "You are the Editor. You receive the complete draft of the story and editing instructions (e.g., 'make it funnier', 'check for consistency'). Use the 'edit_story' tool to revise the text. Respond ONLY with the final, edited story."
        super().__init__(name="Editor", instructions=instructions, tools=[edit_story], **kwargs)

class CoordinatorAgent(Agent):
    def __init__(self, team_tools: List[Tool], **kwargs):
        instructions = (
            "You are the Coordinator for a team of writing agents (Planner, Writer, Editor).\n"
            "1. Receive the user's story topic.\n"
            "2. Delegate to the Planner tool to get a story outline.\n"
            "3. Identify the story parts from the outline (e.g., Introduction, Climax, Resolution).\n"
            "4. Sequentially delegate writing each part to the Writer tool. Provide the part name, the full outline, and all previously written parts as context for the Writer.\n"
            "5. Accumulate the written parts into a full draft.\n"
            "6. Delegate the complete draft to the Editor tool with simple instructions like 'Ensure coherence and flow'.\n"
            "7. Return the final, edited story as the result."
        )
        super().__init__(name="Coordinator", instructions=instructions, tools=team_tools, **kwargs)

# --- Blueprint Definition ---
class GaggleBlueprint(BlueprintBase):
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "GaggleBlueprint",
        "title": "Gaggle Story Writing Team",
        "description": "A multi-agent blueprint for collaborative story writing.",
        "version": "1.1.0",
        "author": "Open Swarm Team",
        "tags": ["writing", "collaboration", "multi-agent"],
        "required_mcp_servers": [], # No MCP needed for this example
    }

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the story writing team and returns the Coordinator."""
        logger.info("Creating Gaggle agent team...")

        # Instantiate agents (no MCPs needed here)
        planner = PlannerAgent(model=self.config.get("llm_profile", "default"))
        writer = WriterAgent(model=self.config.get("llm_profile", "default"))
        editor = EditorAgent(model=self.config.get("llm_profile", "default"))

        # Instantiate Coordinator, giving it the other agents as tools
        coordinator = CoordinatorAgent(
            model=self.config.get("llm_profile", "default"),
            team_tools=[
                planner.as_tool(tool_name="Planner", tool_description="Delegate creating a story outline."),
                writer.as_tool(tool_name="Writer", tool_description="Delegate writing a specific part of the story."),
                editor.as_tool(tool_name="Editor", tool_description="Delegate editing the full story draft."),
            ]
        )
        logger.info("Gaggle agent team created. Coordinator is the starting agent.")
        return coordinator

if __name__ == "__main__":
    GaggleBlueprint.main()
