"""Support — onboarding guide (role=support).

A single discoverable blueprint. The coordinator uses openai-agents
``as_tool`` specialists (product guide + blueprint coder). It does **not**
spawn extra Grok / OMB / Rakazo CLI seats.
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as fusion
from swarm.blueprints.common.support_blueprint import (
    CLICK_BUBBLE_TO_EDIT,
    resolve_session_kind,
    support_turn_context,
    support_turn_reply,
)
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.support_context import (
    create_paths_markdown,
    live_context,
    model_context_block,
    quickstart_section,
)

logger = logging.getLogger(__name__)

SUPPORT_INSTRUCTIONS = """
You are Support, Open Swarm's onboarding guide (role=support).

Goals:
- Help the user understand the product using the existing docs/QUICKSTART.md
  (do not invent a second quickstart).
- Encourage them to build their first agent team.
- Help them code a blueprint in Python. Always show Python in a fenced
  ```python code block.
- When inference is not configured, point at QUICKSTART §4 and /settings/,
  /profiles/ — never invent credentials or call a live Qwen/Comfy path.

Tools:
- get_live_context: current agents + inference status.
- get_quickstart: existing quickstart excerpts (inference / team / blueprint / run).
- list_create_paths: in-product paths to create agents, blueprints, and teams.
- consult_product_guide: specialist (as_tool) for product Q&A.
- consult_blueprint_coder: specialist (as_tool) for drafting blueprint Python.

Do not shell out to grok, omb, or rakazo. Stay on this Support seat.
"""

PRODUCT_GUIDE_INSTRUCTIONS = """
You are the Support product guide. Answer from Open Swarm's existing
quickstart and in-product routes (/settings/, /profiles/, /teams/launch/,
/blueprint-library/, /agent-creator/). Prefer quoting QUICKSTART.md over
inventing steps. Encourage building a first team.
"""

BLUEPRINT_CODER_INSTRUCTIONS = """
You are the Support blueprint coder. Help the user write a BlueprintBase
subclass. Always return a complete, copy-pasteable ```python fenced block.
Use openai-agents Agent + function_tool / as_tool (handoff-as-tool), not
extra CLI seats. Keep the example small and honest.
"""

STARTER_BLUEPRINT_PYTHON = '''```python
from typing import Any, ClassVar

from agents import Agent, function_tool

from swarm.core.blueprint_base import BlueprintBase


class FirstTeamBlueprint(BlueprintBase):
    """Minimal coordinator + specialist via Agent.as_tool (no extra CLI seats)."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "first_team",
        "title": "First Team",
        "description": "A starter coordinator that delegates to one specialist.",
        "version": "0.1.0",
        "tags": ["team", "starter"],
    }

    def create_starting_agent(self, mcp_servers):
        specialist = Agent(
            name="Specialist",
            instructions="Do the concrete work the coordinator delegates.",
        )
        coordinator = Agent(
            name="Coordinator",
            instructions="Plan the work, then call consult_specialist.",
            tools=[],
        )
        if hasattr(specialist, "as_tool"):
            coordinator.tools.append(
                specialist.as_tool(
                    tool_name="consult_specialist",
                    tool_description="Delegate implementation to the specialist.",
                )
            )
        return coordinator
```'''


def _function_tool(fn):
    """Decorate when openai-agents is available; keep a callable otherwise."""
    try:
        from agents import function_tool as _ft

        return _ft(fn)
    except Exception:
        fn.name = getattr(fn, "__name__", "tool")
        return fn


@_function_tool
def get_live_context() -> str:
    """Current agents list and whether inference is configured. No secrets."""
    import json

    return json.dumps(live_context(), indent=2, default=str)


@_function_tool
def get_quickstart(section: str = "inference") -> str:
    """Return an excerpt from docs/QUICKSTART.md (inference, team, blueprint, run)."""
    excerpt = quickstart_section(section)
    if excerpt:
        return excerpt
    return (
        f"No QUICKSTART.md excerpt for '{section}'. "
        "Valid sections: inference, team, blueprint, run. "
        "See docs/QUICKSTART.md in the repo."
    )


@_function_tool
def list_create_paths() -> str:
    """In-product paths to create agents, blueprints, and teams."""
    return create_paths_markdown()


class SupportBlueprint(BlueprintBase):
    """Onboarding Support agent. Discoverable; metadata.role = support."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "support",
        "title": "Support",
        "description": "Onboarding. First team.",
        "version": "1.0.0",
        "author": "Open Swarm Team",
        "tags": ["support", "onboarding", "quickstart"],
        "role": "support",
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    def system_prompt(self, messages: list[dict[str, Any]] | None = None) -> str:
        """Skill-injected system/prompt for this turn (includes the fixture)."""
        params = getattr(self, "_params", {}) or {}
        session_kind = resolve_session_kind(params, messages)
        live = model_context_block(live_context())
        return support_turn_context(session_kind, live)

    def create_starting_agent(self, mcp_servers=None):  # noqa: ARG002
        """Coordinator + as_tool specialists (no Grok/OMB/Rakazo seats)."""
        try:
            from agents import Agent
        except ImportError as exc:  # pragma: no cover - env without SDK
            raise RuntimeError("openai-agents is required for Support") from exc

        product_guide = Agent(
            name="ProductGuide",
            instructions=PRODUCT_GUIDE_INSTRUCTIONS.strip(),
        )
        blueprint_coder = Agent(
            name="BlueprintCoder",
            instructions=BLUEPRINT_CODER_INSTRUCTIONS.strip(),
        )
        tools: list[Any] = [get_live_context, get_quickstart, list_create_paths]
        coordinator = Agent(
            name="Support",
            instructions=SUPPORT_INSTRUCTIONS.strip(),
            tools=list(tools),
        )
        try:
            coordinator.tools = list(coordinator.tools or [])
            if hasattr(product_guide, "as_tool"):
                coordinator.tools.append(
                    product_guide.as_tool(
                        tool_name="consult_product_guide",
                        tool_description=(
                            "Ask the product-guide specialist about Open Swarm, "
                            "quickstarts, and in-product paths."
                        ),
                    )
                )
            if hasattr(blueprint_coder, "as_tool"):
                coordinator.tools.append(
                    blueprint_coder.as_tool(
                        tool_name="consult_blueprint_coder",
                        tool_description=(
                            "Ask the blueprint-coder specialist to draft Python "
                            "for a BlueprintBase team."
                        ),
                    )
                )
        except Exception as exc:  # pragma: no cover
            logger.debug("Support as_tool wiring skipped: %s", exc)
        return coordinator

    def _deterministic_reply(self, user_text: str, session_kind: str = "api") -> str:
        if session_kind in ("cli", "remote"):
            return support_turn_reply(None, session_kind)
        if not user_text:
            return create_paths_markdown()
        lowered = user_text.lower()
        parts = [user_text]
        if any(word in lowered for word in ("blueprint", "code", "python", "agent team", "write")):
            parts.extend(["", STARTER_BLUEPRINT_PYTHON])
        parts.extend(["", create_paths_markdown()])
        return "\n".join(parts)

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        params = getattr(self, "_params", {}) or {}
        session_kind = resolve_session_kind(params, messages)
        user_text = fusion.render_prompt(messages).strip()
        # Chat-load / empty turn and test mode never hit a live model.
        if os.environ.get("SWARM_TEST_MODE") or not user_text:
            yield fusion.message_chunk(
                self._deterministic_reply(user_text, session_kind), final=True
            )
            return

        injected = [
            {"role": "system", "content": self.system_prompt(messages)},
            *list(messages or []),
        ]
        try:
            from agents import Runner

            agent = self.create_starting_agent(kwargs.get("mcp_servers") or [])
            result = await Runner.run(agent, fusion.render_prompt(injected))
            response = getattr(result, "final_output", None) or str(result)
            text = str(response)
            if session_kind in ("cli", "remote") and CLICK_BUBBLE_TO_EDIT in text.lower():
                text = support_turn_reply(messages, session_kind)
            yield fusion.message_chunk(text, final=True)
        except Exception as exc:
            logger.warning("Support LLM path failed; falling back to welcome: %s", exc)
            fallback = self._deterministic_reply(user_text, session_kind)
            yield fusion.message_chunk(fallback, final=True)
