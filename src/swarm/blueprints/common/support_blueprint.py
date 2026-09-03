"""Support seat — always attaches the session-ownership skill.

Not a discoverable ``blueprints/support/`` package (that would churn the
locked catalog counts). Instantiated by ``get_blueprint_instance("support")``
and the chat consumer so every Support turn gets ``skill=support-session-ownership``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as fusion
from swarm.core.blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)

SUPPORT_SKILL_NAME = "support-session-ownership"
SUPPORT_SKILL_FIXTURE = "SESSION_OWNERSHIP_API_CLI_REMOTE"
CLICK_BUBBLE_TO_EDIT = "click the bubble to edit"

SESSION_KINDS = ("api", "cli", "remote")
PARAM_SESSION_KIND = "session_kind"


def is_support_id(blueprint_id: str | None) -> bool:
    return (blueprint_id or "").strip().lower() == "support"


def normalize_session_kind(value: Any) -> str:
    kind = str(value or "").strip().lower()
    return kind if kind in SESSION_KINDS else "api"


def resolve_session_kind(
    params: dict[str, Any] | None,
    messages: list[dict[str, Any]] | None = None,
) -> str:
    """Resolve api/cli/remote for this Support turn.

    Explicit ``session_kind`` wins. Otherwise a coarse heuristic on the latest
    user text (so "my grok/cli session" is treated as external).
    """
    params = params or {}
    explicit = params.get(PARAM_SESSION_KIND)
    if explicit:
        return normalize_session_kind(explicit)

    text = ""
    for msg in reversed(messages or []):
        if (msg.get("role") or "user") == "user" and msg.get("content"):
            text = str(msg["content"]).lower()
            break
    if any(token in text for token in (" remote ", "remote agent", "remote session")):
        return "remote"
    if any(
        token in text
        for token in (
            "cli ",
            "cli.",
            "cli?",
            "cli agent",
            "cli session",
            "grok",
            "claude",
            "gemini",
            "codex",
            "opencode",
        )
    ):
        return "cli"
    return "api"


def support_turn_context(session_kind: str = "api", task: str = "") -> str:
    """System/prompt Support sees this turn (skill attach + session kind)."""
    kind = normalize_session_kind(session_kind)
    note = (
        "Current session kind: API. Open Swarm owns this thread; bubbles are editable."
        if kind == "api"
        else (
            f"Current session kind: {kind}. The live session is outside Open Swarm. "
            "Do not tell the user to click the bubble to edit."
        )
    )
    body = f"{note}\n{task}".strip() if task else note
    prompt, applied = fusion.apply_skill_to_prompt(
        body, {fusion.PARAM_SKILL: SUPPORT_SKILL_NAME}
    )
    if applied != SUPPORT_SKILL_NAME:
        logger.warning("Support skill %s was not applied", SUPPORT_SKILL_NAME)
    return prompt


def support_turn_reply(
    messages: list[dict[str, Any]] | None,
    session_kind: str = "api",
) -> str:
    """Laconic Socratic reply used in tests and when no LLM is available.

    CLI/remote must never claim the user can click the bubble to edit.
    """
    kind = normalize_session_kind(session_kind)
    if kind in ("cli", "remote"):
        return (
            "That session lives outside Open Swarm — I cannot edit those bubbles. "
            "What are you trying to change?"
        )
    return (
        "This thread is owned here, so you can edit a user or assistant bubble. "
        "Which message needs a rewrite?"
    )


class SupportBlueprint(BlueprintBase):
    """Onboarding Support agent. Skill-injected every turn; not catalog-listed."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "support",
        "title": "Support",
        "description": "Talk about the other agents.",
        "version": "1.0.0",
        "author": "Open Swarm Team",
        "tags": ["support", "onboarding"],
        "role": "support",
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "support", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    def system_prompt(self, messages: list[dict[str, Any]] | None = None) -> str:
        """Skill-injected system/prompt for this turn (includes the fixture)."""
        params = dict(self._params)
        if not params.get(fusion.PARAM_SKILL):
            params[fusion.PARAM_SKILL] = SUPPORT_SKILL_NAME
        session_kind = resolve_session_kind(params, messages)
        task = fusion.render_prompt(messages or [])
        return support_turn_context(session_kind, task)

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        params = dict(self._params)
        if not params.get(fusion.PARAM_SKILL):
            params[fusion.PARAM_SKILL] = SUPPORT_SKILL_NAME
        session_kind = resolve_session_kind(params, messages)
        system = self.system_prompt(messages)

        # Tests and empty turns never hit a live model.
        if os.environ.get("SWARM_TEST_MODE") or params.get("deterministic"):
            yield fusion.message_chunk(support_turn_reply(messages, session_kind), final=True)
            return

        injected = [{"role": "system", "content": system}, *list(messages or [])]
        try:
            from openai import AsyncOpenAI

            from swarm.utils.env_utils import get_llm_base_url, openai_client_kwargs

            model = (
                os.environ.get("LITELLM_MODEL")
                or os.environ.get("OPENAI_MODEL")
                or os.environ.get("DEFAULT_LLM")
            )
            if not model:
                raise RuntimeError("no model configured")
            client = AsyncOpenAI(**openai_client_kwargs())
            if get_llm_base_url() and "openai.com" in str(getattr(client, "base_url", "") or ""):
                raise RuntimeError("refusing openai.com fallback")
            result = await client.chat.completions.create(
                model=model,
                messages=injected,
            )
            text = (result.choices[0].message.content or "").strip()
            if session_kind in ("cli", "remote") and CLICK_BUBBLE_TO_EDIT in text.lower():
                text = support_turn_reply(messages, session_kind)
            yield fusion.message_chunk(text or support_turn_reply(messages, session_kind), final=True)
        except Exception as exc:
            logger.warning("Support LLM path failed; using deterministic reply: %s", exc)
            yield fusion.message_chunk(support_turn_reply(messages, session_kind), final=True)
