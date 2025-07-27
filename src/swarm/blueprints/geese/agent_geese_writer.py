import logging
from collections.abc import AsyncGenerator
from typing import Any

from agents import Agent, Model  # Assuming Model is the base type for self.llm
from agents.mcp import MCPServer

from .geese_memory_objects import StoryContext  # If needed by the writer

logger = logging.getLogger(__name__)

class WriterAgent(Agent):
    """
    The WriterAgent is responsible for taking a prompt or an outline segment
    and generating a narrative portion of the story.
    """
    def __init__(
        self,
        name: str,
        model: Model, # SDK Model instance
        instructions: str, # System prompt (e.g., "You are a creative writer...")
        mcp_servers: list[MCPServer] | None = None,
        blueprint_id: str | None = None,
        max_llm_calls: int = 5, # Writer might have fewer calls than coordinator
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
        messages: list[dict[str, Any]], # Should contain the writing prompt
        story_context: StoryContext | None = None, # Optional context
        **kwargs: Any
    ) -> AsyncGenerator[Any, None]: # Yields SDK interaction objects or strings
        """
        Generates a story segment based on the provided messages.
        The last message is typically the specific writing prompt.
        """
        writing_prompt = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "Write a short story."
        self.logger.info(f"WriterAgent run initiated. Prompt: {writing_prompt[:100]}...")

        # Use self.model (the SDK model instance) to generate text
        # The SDK's model instance (e.g., OpenAIChatCompletionsModel) has methods like
        # chat_completion_stream or similar.

        # Example of streaming content directly from the LLM:
        # This assumes self.model has a method like chat_completion_stream
        # and yields objects/dicts from which content can be extracted.
        # The exact structure depends on your SDK's Model implementation.

        llm_call_count = 0
        if llm_call_count < self.max_llm_calls:
            try:
                # Construct messages for the LLM call
                # The system prompt is part of self.instructions and handled by SDK Agent
                # We just need to pass the user's writing prompt.
                llm_messages = [{"role": "user", "content": writing_prompt}]

                # The actual call to the LLM via the SDK Model instance
                # self.model is an instance of e.g. OpenAIChatCompletionsModel
                async for chunk in self.model.chat_completion_stream(messages=llm_messages):
                    # Process the chunk from the LLM stream
                    # This depends on what self.model.chat_completion_stream yields.
                    # If it yields dicts like OpenAI's API:
                    if isinstance(chunk, dict):
                        content_delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content_delta:
                            yield content_delta # Yield the string content directly
                    # If it yields SDK-specific objects:
                    # elif hasattr(chunk, 'text_delta'): # Example for a hypothetical SDK object
                    #    yield chunk.text_delta
                    # else: (handle other chunk types or log)

                llm_call_count +=1
            except Exception as e:
                self.logger.error(f"Error during WriterAgent LLM call: {e}", exc_info=True)
                yield f"\n[WriterAgent Error: Could not generate text due to: {e}]\n"
        else:
            self.logger.warning(f"WriterAgent reached max LLM calls ({self.max_llm_calls}).")
            yield "\n[WriterAgent Info: Max LLM calls reached.]\n"

        # The SDK Agent's run method is an async generator.
        # It should yield its interactions. If it's just streaming text,
        # the above loop handles it. If it needs to yield structured SDK objects,
        # that would be done here.
        # For simplicity, this example directly yields text chunks.
        # A more complete SDK Agent might yield MessageStart, ContentDelta, MessageEnd objects.
