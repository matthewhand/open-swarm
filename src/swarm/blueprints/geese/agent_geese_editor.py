import logging
from collections.abc import AsyncGenerator
from typing import Any

from agents import Agent, Model  # Assuming Model is the base type for self.llm
from agents.mcp import MCPServer

from .geese_memory_objects import StoryContext  # If needed by the editor

logger = logging.getLogger(__name__)

class EditorAgent(Agent):
    """
    The EditorAgent is responsible for reviewing and refining text generated
    by the WriterAgent. It can check for grammar, style, coherence, and
    adherence to specific instructions.
    """
    def __init__(
        self,
        name: str,
        model: Model, # SDK Model instance
        instructions: str, # System prompt (e.g., "You are a meticulous editor...")
        mcp_servers: list[MCPServer] | None = None,
        blueprint_id: str | None = None,
        max_llm_calls: int = 3, # Editor might have fewer calls
        **kwargs: Any
    ):
        super().__init__(
            name=name,
            model=model,
            instructions=instructions,
            mcp_servers=mcp_servers or [],
            **kwargs
        )
        self.blueprint_id = blueprint_id
        self.max_llm_calls = max_llm_calls
        self.logger = logging.getLogger(f"swarm.geese.agent.{self.name}")

    async def run(
        self,
        messages: list[dict[str, Any]], # Should contain the text to edit and editing instructions
        story_context: StoryContext | None = None, # Optional context
        **kwargs: Any
    ) -> AsyncGenerator[Any, None]: # Yields SDK interaction objects or strings
        """
        Edits a story segment based on the provided messages.
        The last message is typically the specific editing prompt including the text to edit.
        """
        editing_prompt_and_text = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "Edit this text: 'It was a dark and stormy night.'"
        self.logger.info(f"EditorAgent run initiated. Editing task: {editing_prompt_and_text[:100]}...")

        llm_call_count = 0
        if llm_call_count < self.max_llm_calls:
            try:
                # Construct messages for the LLM call
                llm_messages = [{"role": "user", "content": editing_prompt_and_text}]

                # Call the LLM via the SDK Model instance
                async for chunk in self.model.chat_completion_stream(messages=llm_messages):
                    # Process the chunk from the LLM stream
                    if isinstance(chunk, dict):
                        content_delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content_delta:
                            yield content_delta # Yield the string content directly
                    # Add other SDK-specific chunk processing if needed

                llm_call_count += 1
            except Exception as e:
                self.logger.error(f"Error during EditorAgent LLM call: {e}", exc_info=True)
                yield f"\n[EditorAgent Error: Could not edit text due to: {e}]\n"
        else:
            self.logger.warning(f"EditorAgent reached max LLM calls ({self.max_llm_calls}).")
            yield "\n[EditorAgent Info: Max LLM calls reached.]\n"

        # Similar to WriterAgent, this example directly yields text chunks.
        # A full SDK Agent might yield more structured interaction objects.
