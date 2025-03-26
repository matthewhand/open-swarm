"""
Chat Completion Module

This module handles chat completion logic for the Swarm framework, including message preparation,
tool call repair, and interaction with the OpenAI API. Located in llm/ for LLM-specific functionality.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from collections import defaultdict

import asyncio
from openai import AsyncOpenAI, OpenAIError
from ..types import ChatCompletionMessage, Agent
from ..utils.redact import redact_sensitive_data
from ..utils.general_utils import serialize_datetime
from ..utils.message_utils import filter_duplicate_system_messages, update_null_content
from ..utils.context_utils import get_token_count, truncate_message_history
from ..utils.message_sequence import repair_message_payload

# Configure module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


async def get_chat_completion(
    client: AsyncOpenAI,
    agent: Agent,
    history: List[Dict[str, Any]],
    context_variables: dict,
    current_llm_config: Dict[str, Any],
    max_context_tokens: int,
    max_context_messages: int,
    model_override: Optional[str] = None,
    stream: bool = False,
    debug: bool = False
) -> ChatCompletionMessage:
    """
    Retrieve a chat completion from the LLM for the given agent and history.

    Args:
        client: AsyncOpenAI client instance.
        agent: The agent processing the completion.
        history: List of previous messages in the conversation.
        context_variables: Variables to include in the agent's context.
        current_llm_config: Current LLM configuration dictionary.
        max_context_tokens: Maximum token limit for context.
        max_context_messages: Maximum message limit for context.
        model_override: Optional model to use instead of default.
        stream: If True, stream the response; otherwise, return complete.
        debug: If True, log detailed debugging information.

    Returns:
        ChatCompletionMessage: The LLM's response message.
    """
    if not agent:
        logger.error("Cannot generate chat completion: Agent is None")
        raise ValueError("Agent is required")

    logger.debug(f"Generating chat completion for agent '{agent.name}'")
    active_model = model_override or current_llm_config.get("model", "default")
    client_kwargs = {
        "api_key": current_llm_config.get("api_key"),
        "base_url": current_llm_config.get("base_url")
    }
    client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
    redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
    logger.debug(f"Using client with model='{active_model}', base_url='{client_kwargs.get('base_url', 'default')}', api_key={redacted_kwargs['api_key']}")

    context_variables = defaultdict(str, context_variables)
    instructions = agent.instructions(context_variables) if callable(agent.instructions) else agent.instructions
    if not isinstance(instructions, str):
        logger.warning(f"Invalid instructions type for '{agent.name}': {type(instructions)}. Converting to string.")
        instructions = str(instructions)
    messages = repair_message_payload([{"role": "system", "content": instructions}], debug=debug)

    if not isinstance(history, list):
        logger.error(f"Invalid history type for '{agent.name}': {type(history)}. Expected list.")
        history = []
    seen_ids = set()
    for msg in history:
        msg_id = msg.get("id", hash(json.dumps(msg, sort_keys=True, default=serialize_datetime)))
        if msg_id not in seen_ids:
            seen_ids.add(msg_id)
            if "tool_calls" in msg and msg["tool_calls"] is not None and not isinstance(msg["tool_calls"], list):
                logger.warning(f"Invalid tool_calls in history for '{msg.get('sender', 'unknown')}': {msg['tool_calls']}. Setting to None.")
                msg["tool_calls"] = None
            messages.append(msg)
    messages = filter_duplicate_system_messages(messages)
    messages = truncate_message_history(messages, active_model, max_context_tokens, max_context_messages)
    messages = repair_message_payload(messages, debug=debug)  # Ensure tool calls are paired post-truncation

    logger.debug(f"Prepared {len(messages)} messages for '{agent.name}'")
    if debug:
        logger.debug(f"Messages: {json.dumps(messages, indent=2, default=str)}")

    create_params = {
        "model": active_model,
        "messages": messages,
        "stream": stream,
        "temperature": current_llm_config.get("temperature", 0.7),
    }
    if getattr(agent, "response_format", None):
        create_params["response_format"] = agent.response_format
    create_params = {k: v for k, v in create_params.items() if v is not None}
    logger.debug(f"Chat completion params: model='{active_model}', messages_count={len(messages)}, stream={stream}")

    try:
        logger.debug(f"Calling OpenAI API for '{agent.name}' with model='{active_model}'")
        prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            completion = await client.chat.completions.create(**create_params)
            if stream:
                return completion  # Return stream object directly
            if completion.choices and len(completion.choices) > 0 and completion.choices[0].message:
                log_msg = completion.choices[0].message.content[:50] if completion.choices[0].message.content else "No content"
                logger.debug(f"OpenAI completion received for '{agent.name}': {log_msg}...")
                return completion.choices[0].message
            else:
                logger.warning(f"No valid message in completion for '{agent.name}'")
                return ChatCompletionMessage(content="No response generated", role="assistant")
        finally:
            if prev_openai_api_key is not None:
                os.environ["OPENAI_API_KEY"] = prev_openai_api_key
    except OpenAIError as e:
        logger.error(f"Chat completion failed for '{agent.name}': {e}")
        raise


async def get_chat_completion_message(
    client: AsyncOpenAI,
    agent: Agent,
    history: List[Dict[str, Any]],
    context_variables: dict,
    current_llm_config: Dict[str, Any],
    max_context_tokens: int,
    max_context_messages: int,
    model_override: Optional[str] = None,
    stream: bool = False,
    debug: bool = False
) -> ChatCompletionMessage:
    """
    Wrapper to retrieve and validate a chat completion message.

    Args:
        Same as get_chat_completion.

    Returns:
        ChatCompletionMessage: Validated LLM response message.
    """
    logger.debug(f"Fetching chat completion message for '{agent.name}'")
    completion = await get_chat_completion(
        client, agent, history, context_variables, current_llm_config,
        max_context_tokens, max_context_messages, model_override, stream, debug
    )
    if isinstance(completion, ChatCompletionMessage):
        return completion
    logger.warning(f"Unexpected completion type: {type(completion)}. Converting to ChatCompletionMessage.")
    return ChatCompletionMessage(content=str(completion), role="assistant")
