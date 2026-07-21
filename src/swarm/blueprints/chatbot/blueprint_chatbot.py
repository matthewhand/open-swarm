"""Chatbot Blueprint — the minimal single-agent REST blueprint.

Path: src/swarm/blueprints/chatbot/blueprint_chatbot.py
Discovered as blueprint_id "chatbot" (the directory name).

This is the simplest discoverable REST template: one agent, one endpoint
(``POST /v1/chat/completions`` with ``model: "chatbot"``). It runs a single
``openai-agents`` Agent and streams that agent's text answer back as a normal
chat completion.

Under ``SWARM_TEST_MODE`` it returns a deterministic, network-free answer so the
per-blueprint API smoke matrix (tests/api/test_blueprint_api_smoke.py) and the
unit tests in tests/blueprints/test_chatbot.py pass without a live LLM or API
key.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any, ClassVar

from swarm.core.blueprint_base import BlueprintBase


def _latest_user_text(messages: list[dict[str, Any]] | None) -> str:
    """Return the trimmed content of the most recent message, or ""."""
    if not messages:
        return ""
    last = messages[-1]
    if not isinstance(last, dict):
        return ""
    return (last.get("content") or "").strip()


class ChatbotBlueprint(BlueprintBase):
    """A minimal single-agent REST blueprint: one Agent, one answer."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "chatbot",
        "title": "Chatbot (single agent)",
        "description": (
            "Minimal single-agent REST blueprint. Runs one openai-agents Agent "
            "and returns its text answer over the OpenAI-compatible API."
        ),
        "version": "1.0.0",
        "author": "Open Swarm Team",
        "tags": ["minimal", "chatbot", "single-agent", "rest", "example"],
        # Suggested inference: a balanced all-rounder. The framework scores this
        # against the tagged profiles in swarm_config.json's `llm` section and
        # picks the closest match (see core/inference_profile.py). A hint only —
        # explicit llm_profile / DEFAULT_LLM / LITELLM_MODEL still take priority.
        "inference_profile": {"intelligence": 0.6, "speed": 0.6, "cost": 0.6},
        "required_mcp_servers": [],
        "env_vars": [],  # OPENAI_API_KEY implicitly needed by the model
    }

    def __init__(self, blueprint_id: str = "chatbot", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)

    def create_starting_agent(self, mcp_servers=None):
        """Build the single chat agent wired to the configured model.

        ``make_agent()`` resolves the model (provider/model/api_key/base_url)
        from swarm_config.json via ``_get_model_instance`` + ``_resolve_llm_profile``.
        """
        return self.make_agent(
            name="ChatbotAgent",
            instructions=(
                "You are a concise, friendly assistant. "
                "Answer the user directly and helpfully."
            ),
            tools=[],
            mcp_servers=mcp_servers or [],
        )

    async def run(self, messages, **kwargs) -> AsyncGenerator[dict, None]:
        user_text = _latest_user_text(messages)

        # --- SWARM_TEST_MODE: canned answer, NO model call / network / API key ---
        if os.environ.get("SWARM_TEST_MODE"):
            answer = f"You said: {user_text}" if user_text else "Hello! How can I help you?"
            yield {
                "messages": [{"role": "assistant", "content": answer}],
                "final": True,
            }
            return

        # --- Real path: build one Agent, run it, read its text answer ---
        # Imported lazily so test mode never requires the agents SDK / a model.
        from agents import Runner

        agent = self.create_starting_agent(mcp_servers=kwargs.get("mcp_servers", []))
        try:
            result = await Runner.run(agent, user_text)
            # .final_output is the answer; do NOT use str(result) (it serializes
            # the whole RunResult wrapper).
            answer = result.final_output
        except Exception as e:  # noqa: BLE001 - surface any failure to the caller
            answer = f"An error occurred: {e}"

        yield {
            "messages": [{"role": "assistant", "content": str(answer)}],
            "final": True,
        }


if __name__ == "__main__":
    import asyncio
    import json

    async def _demo():
        bp = ChatbotBlueprint(blueprint_id="chatbot")
        async for chunk in bp.run([{"role": "user", "content": "hello"}]):
            print(json.dumps(chunk, indent=2))

    asyncio.run(_demo())
