import logging
import os # Added os import
import sys
from typing import List, Dict, Any, Optional, ClassVar

# Ensure src is in path for BlueprintBase import (if needed, adjust path)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    # Corrected Import: Relative path within the package
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
    logger.info(f"Tool: Generating outline for: {topic}") # Keep INFO for tool exec start
    # In a real scenario, this might involve more logic or an LLM call.
    # Adding slight variation for clarity
    outline = f"Story Outline for '{topic}':\n1. Beginning: Introduce characters and setting.\n2. Middle: Develop conflict and rising action.\n3. Climax: The peak of the conflict.\n4. End: Resolution and aftermath."
    logger.debug(f"Generated outline: {outline}")
    return outline

@function_tool
def write_story_part(part_name: str, outline: str, previous_parts: str) -> str:
    """Writes a specific part of the story using the outline and previous context."""
    logger.info(f"Tool: Writing story part: {part_name}") # Keep INFO for tool exec start
    # Simple placeholder implementation
    content = f"## {part_name}\n\nThis is the draft content for the '{part_name}' section. It follows:\n'{previous_parts[:100]}...' \nIt should align with the outline:\n'{outline}'"
    logger.debug(f"Generated content for {part_name}: {content[:100]}...")
    return content

@function_tool
def edit_story(full_story: str, edit_instructions: str) -> str:
    """Edits the complete story based on instructions."""
    logger.info(f"Tool: Editing story with instructions: {edit_instructions}") # Keep INFO for tool exec start
    # Simple placeholder for editing
    edited_content = f"*** Edited Story Draft ***\n(Based on instructions: '{edit_instructions}')\n\n{full_story}\n\n[Editor's Notes: Minor tweaks applied for flow.]"
    logger.debug("Editing complete.")
    return edited_content

# --- Blueprint Definition ---
class GaggleBlueprint(BlueprintBase):
    """A multi-agent blueprint using a Coordinator, Planner, Writer, and Editor for collaborative story writing."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "GaggleBlueprint",
        "title": "Gaggle Story Writing Team",
        "description": "A multi-agent blueprint for collaborative story writing using Planner, Writer, and Editor roles coordinated by a central agent.",
        "version": "1.2.0", # Updated version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["writing", "collaboration", "multi-agent", "storytelling"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation is the same as in previous refactors, e.g., Dilbot's) ...
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
             logger.critical(f"LLM profile '{profile_name}' (or 'default') not found.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' missing 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")
        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init OpenAI client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM provider: {e}") from e


    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the story writing team and returns the Coordinator."""
        logger.debug("Creating Gaggle Story Writing Team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Gaggle agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # --- Define Agent Instructions ---
        planner_instructions = "You are the Planner. Your goal is to take a user's story topic and create a coherent outline using the 'create_story_outline' tool. Respond ONLY with the generated outline string."
        writer_instructions = "You are a Writer. You receive a story part name (e.g., 'Introduction', 'Climax'), the full outline, and any previously written parts. Write the content for ONLY your assigned part using the 'write_story_part' tool, ensuring it flows logically from previous parts and fits the outline. Respond ONLY with the text generated for your part."
        editor_instructions = "You are the Editor. You receive the complete draft of the story and editing instructions (e.g., 'make it funnier', 'check for consistency'). Use the 'edit_story' tool to revise the text. Respond ONLY with the final, edited story string."
        coordinator_instructions = (
            "You are the Coordinator for a team of writing agents (Planner, Writer, Editor).\n"
            "1. Receive the user's story topic.\n"
            "2. Delegate to the Planner tool to get a story outline.\n"
            "3. Identify the story parts from the outline (e.g., Beginning, Middle, Climax, End).\n"
            "4. Sequentially delegate writing each part to the Writer tool. Provide the part name, the full outline, and all previously written parts as context for the Writer.\n"
            "5. Accumulate the written parts into a full draft.\n"
            "6. Delegate the complete draft to the Editor tool with simple instructions like 'Ensure coherence and flow'.\n"
            "7. Return the final, edited story as the result."
        )

        # Instantiate agents, passing their specific function tools
        planner_agent = Agent(
            name="Planner",
            instructions=planner_instructions,
            model=model_instance,
            tools=[create_story_outline],
            mcp_servers=mcp_servers
         )
        writer_agent = Agent(
            name="Writer",
            instructions=writer_instructions,
            model=model_instance,
            tools=[write_story_part],
            mcp_servers=mcp_servers
        )
        editor_agent = Agent(
            name="Editor",
            instructions=editor_instructions,
            model=model_instance,
            tools=[edit_story],
            mcp_servers=mcp_servers
        )

        # Instantiate Coordinator, giving it the other agents as tools
        coordinator_agent = Agent(
            name="Coordinator",
            instructions=coordinator_instructions,
            model=model_instance, # Coordinator also needs a model
            tools=[
                planner_agent.as_tool(
                    tool_name="Planner",
                    tool_description="Delegate creating a story outline based on a topic."
                ),
                writer_agent.as_tool(
                    tool_name="Writer",
                    tool_description="Delegate writing a specific part of the story. Requires part_name, outline, and previous_parts."
                ),
                editor_agent.as_tool(
                    tool_name="Editor",
                    tool_description="Delegate editing the full story draft. Requires full_story and edit_instructions."
                ),
            ],
            mcp_servers=mcp_servers
        )

        logger.debug("Gaggle Story Writing Team created. Coordinator is the starting agent.")
        return coordinator_agent

if __name__ == "__main__":
    GaggleBlueprint.main()
