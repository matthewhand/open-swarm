"""Shared copy: what a blueprint is, the Python contract, and how it is consumed.

Used by the library creator UI and by agent instructions so humans and agents
see the same interface spec.
"""

from __future__ import annotations

# Short product sentence for headers / library lead.
BLUEPRINT_ONE_LINER = (
    "A blueprint is a coded agent team: a Python kind-base subclass "
    "(ApiKindBase / CliKindBase / RemoteKindBase) the framework discovers and runs."
)

# What authors (and coding agents) must implement.
BLUEPRINT_INTERFACE = """\
from swarm.core.kind_bases import ApiKindBase

class MyTeamBlueprint(ApiKindBase):
    metadata = {
        "name": "my_team",           # id used as the API model name
        "title": "My Team",
        "description": "What this team does",
        "version": "1.0.0",
    }

    async def run(self, messages, **kwargs):
        # messages: OpenAI-style [{role, content}, ...]
        # yield chunks the web Chat UI and /v1/chat/completions stream
        yield {"messages": [{"role": "assistant", "content": "..."}]}
"""

BLUEPRINT_CONSUMPTION = """\
Web
  • Blueprint Library — browse, install, create
  • Agents sidebar — listed as a coded team (click to talk, no dropdown)
  • Chat — same list in the side pane; POST model=<id> still works
  • POST /v1/chat/completions  {"model": "<blueprint id>", "messages": [...]}

CLI
  • swarm-cli list
  • swarm-cli launch <blueprint id> --message "..."
"""

# Compact prompt injected into coding agents that author blueprints.
BLUEPRINT_AGENT_BRIEF = (
    "Blueprints are coded agent teams. Prefer subclassing a kind base from "
    "swarm.core.kind_bases: ApiKindBase (openai-agents handoff / as-tool graphs), "
    "CliKindBase (native grok/agy session), or RemoteKindBase (Hermes / "
    "OpenMousBot / Herdr). BlueprintBase is the low-level parent — do not "
    "invent a fourth harness from the raw base in the common case. Required: "
    "class-level metadata (name/title/description/version) and "
    "`async def run(self, messages, **kwargs)` yielding "
    '`{"messages": [{"role": "assistant", "content": "..."}]}` chunks. '
    "The framework discovers them and serves them as the API `model` id "
    "on /v1/chat/completions, in the web Chat/Library UI, and via "
    "`swarm-cli launch <id> --message ...`. ADR-005 / REQ-159."
)
