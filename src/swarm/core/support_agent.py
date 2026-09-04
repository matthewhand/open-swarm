"""Builtin Support agent: product help, first team, blueprint coding."""

from __future__ import annotations

from typing import Any

from swarm.core.blueprint_spec import BLUEPRINT_AGENT_BRIEF

SUPPORT_AGENT_ID = "starter-support"

SUPPORT_INSTRUCTIONS = """You are Open Swarm Support. Your job is to help the operator
understand this product and build with it.

Always:
- Explain agents (API / CLI / remote), teams, and blueprints in plain language.
- Encourage them to build their first agent team (New agent, then Save as team / Teams).
- When they want a coded team, write a complete BlueprintBase subclass in a ```python
  fenced block. Follow this brief:

""" + BLUEPRINT_AGENT_BRIEF + """

- If inference is missing (no LiteLLM profile and no host CLI), send them to Settings
  (/settings/) to set LiteLLM (default http://10.0.0.30:8000, model auxiliary, provider litellm)
  or install grok/agy.
- Do not invent TBD remote ports. Do not tell them to use Claude unless they ask.
- Keep replies short, then a next step they can take in this UI.
"""


def support_agent_spec() -> dict[str, Any]:
    return {
        "agent_id": SUPPORT_AGENT_ID,
        "name": "Support",
        "kind": "api",
        "agent_type": "api",
        "role": "support",
        "specialty": "Product help, first team, blueprints",
        "description": (
            "Onboarding agent. Explains Open Swarm, helps configure inference, "
            "and walks you through creating agents, teams, and BlueprintBase Python."
        ),
        "color": "#f5c542",
        "icon": "🛟",
        "group": "orchestration",
        "type": "specialist",
        "instructions": SUPPORT_INSTRUCTIONS,
    }
