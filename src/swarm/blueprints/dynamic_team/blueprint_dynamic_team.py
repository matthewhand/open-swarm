import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from swarm.core.blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)


class DynamicTeamBlueprint(BlueprintBase):
    """
    Minimal dynamic team blueprint that proxies user messages to the configured
    LLM profile via OpenAI-compatible Chat Completions and yields a single final
    assistant message.

    The blueprint_id is the team name/slug and is used as the `model` value in
    external OpenAI API clients when calling our `/v1/chat/completions`.
    """

    metadata = {
        "name": "dynamic-team",
        "description": "A dynamically-registered team using a configured LLM profile",
        "abbreviation": None,
    }

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        profile_name = self.llm_profile_name
        # Delegate to BlueprintBase to get model (and underlying client) -- no local AsyncOpenAI + caches
        model_inst = self._get_model_instance(profile_name)
        client = getattr(model_inst, "_client", None)
        model_name = getattr(model_inst, "model", None)

        if client is None or not model_name:
            logger.error("DynamicTeamBlueprint failed to obtain client/model for profile '%s'", profile_name)
            content = f"Configuration error: unable to resolve LLM client for profile '{profile_name}'."
            yield {"messages": [{"role": "assistant", "content": content}]}
            return

        stream = bool(kwargs.get("stream"))
        try:
            if stream:
                # Stream tokens; yield incremental content chunks
                async with client.chat.completions.stream(model=model_name, messages=messages) as s:
                    async for event in s:
                        try:
                            # openai v1 stream yields chunks with .choices[0].delta.content
                            delta = getattr(event, "choices", [None])[0]
                            content = getattr(getattr(delta, "delta", None), "content", None)
                            if content:
                                yield {"messages": [{"role": "assistant", "content": content}]}
                        except Exception:
                            # Ignore malformed chunks; continue
                            continue
                # No explicit final aggregation here; ChatCompletionsView handles [DONE]
                return
            else:
                # Non-streaming single-shot
                resp = await client.chat.completions.create(model=model_name, messages=messages, stream=False)
                text = (resp.choices[0].message.content or "").strip()
                yield {"messages": [{"role": "assistant", "content": text}]}
        except Exception as e:
            logger.exception("Dynamic team LLM call failed: %s", e)
            yield {"messages": [{"role": "assistant", "content": f"[DynamicTeam Error] {e}"}]}
