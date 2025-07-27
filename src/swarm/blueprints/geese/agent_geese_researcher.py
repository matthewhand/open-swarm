import logging
from collections.abc import AsyncGenerator
from typing import Any

from agents import Agent, Model  # Assuming Model is the base type for self.llm
from agents.mcp import MCPServer

# from agents.tools import Tool # If the SDK provides a base Tool class for tools used by agents

# If ResearcherAgent uses specific tools, they might be defined here or imported
# For example, a hypothetical WebSearchTool
# from .geese_tools import WebSearchTool

logger = logging.getLogger(__name__)

class ResearcherAgent(Agent):
    """
    The ResearcherAgent is responsible for finding and providing information
    on specific topics when requested. It might use tools like web search
    or query its knowledge base.
    """
    def __init__(
        self,
        name: str,
        model: Model, # SDK Model instance
        instructions: str, # System prompt (e.g., "You are a helpful research assistant...")
        mcp_servers: list[MCPServer] | None = None,
        tools: list[Any] | None = None, # Placeholder for SDK Tool instances
        blueprint_id: str | None = None,
        max_llm_calls: int = 3,
        **kwargs: Any
    ):
        # If the SDK Agent takes tools in its __init__, pass them here.
        # The 'tools' argument for super().__init__ would expect a list of tool objects
        # that conform to the SDK's tool definition.
        super().__init__(
            name=name,
            model=model,
            instructions=instructions,
            mcp_servers=mcp_servers or [],
            tools=tools or [], # Pass tools to the SDK Agent
            **kwargs
        )
        self.blueprint_id = blueprint_id
        self.max_llm_calls = max_llm_calls
        self.logger = logging.getLogger(f"swarm.geese.agent.{self.name}")

    async def run(
        self,
        messages: list[dict[str, Any]], # Should contain the research query
        **kwargs: Any
    ) -> AsyncGenerator[Any, None]: # Yields SDK interaction objects or strings
        """
        Performs research based on the provided messages.
        The last message is typically the research query.
        """
        research_query = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "What is the capital of France?"
        self.logger.info(f"ResearcherAgent run initiated. Query: {research_query[:100]}...")

        # This agent might use tools. The SDK Agent base class usually handles tool
        # detection in prompts and tool execution if tools are correctly registered.
        # If a tool is called, the SDK Agent would typically:
        # 1. Yield an interaction indicating a tool call.
        # 2. Expect the tool's output to be sent back in a subsequent message.
        # 3. Continue processing with the tool's output.

        # For this placeholder, we'll just have the LLM attempt to answer directly.
        llm_call_count = 0
        if llm_call_count < self.max_llm_calls:
            try:
                # Construct messages for the LLM call
                llm_messages = [{"role": "user", "content": research_query}]

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
                self.logger.error(f"Error during ResearcherAgent LLM call: {e}", exc_info=True)
                yield f"\n[ResearcherAgent Error: Could not research due to: {e}]\n"
        else:
            self.logger.warning(f"ResearcherAgent reached max LLM calls ({self.max_llm_calls}).")
            yield "\n[ResearcherAgent Info: Max LLM calls reached.]\n"

        # If this agent were to use tools registered with the SDK Agent,
        # the SDK Agent's `run` method (which this overrides or implements)
        # would handle the tool calling flow. The `yield`s would be SDK-defined
        # interaction objects (e.g., ToolCall, ToolResult).
