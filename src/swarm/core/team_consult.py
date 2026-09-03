"""Cross-team consult / handoff tools (REQ-28).

Default: **no** cross-team consult tools. A Chief of Staff gets consult +
handoff to **every** team id. A parent-team member gets consult + handoff
only to each **direct child** team (send-to-all on that child — not
automatic grandchildren).

Tools are plain callables with ``name`` / ``description`` so they can be
wrapped as openai-agents function tools later. Isolation is re-checked at
invoke time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from swarm.core.team_isolation import (
    IsolationDecision,
    assert_talk_allowed,
    can_talk,
    consultable_team_ids,
    send_to_all_targets,
)

ToolKind = Literal["consult", "handoff"]


@dataclass
class TeamConsultTool:
    """Consult or handoff to one team id (send-to-all on that team)."""

    name: str
    description: str
    kind: ToolKind
    target_team_id: str
    caller_id: str
    caller_role: str | None = None
    rosters: dict[str, Any] | None = field(default=None, repr=False)

    def decide(self) -> IsolationDecision:
        return can_talk(
            caller_id=self.caller_id,
            target_id=self.target_team_id,
            channel="consult" if self.kind == "consult" else "handoff",
            caller_role=self.caller_role,
            target_kind="team",
            rosters=self.rosters,
        )

    def __call__(self, message: str = "") -> dict[str, Any]:
        decision = self.decide()
        if not decision.allowed:
            assert_talk_allowed(decision)
        recipients = send_to_all_targets(self.target_team_id, self.rosters)
        return {
            "ok": True,
            "kind": self.kind,
            "team_id": self.target_team_id,
            "message": message,
            "send_to_all": True,
            "recipients": recipients,
            "note": (
                "Parent talks to the child team as one member (send-to-all "
                "on the child), not automatically every grandchild."
            ),
            "isolation": decision.reason,
        }


def _tool_name(kind: ToolKind, team_id: str) -> str:
    prefix = "consult_team" if kind == "consult" else "handoff_team"
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in team_id)
    return f"{prefix}_{safe}"


def build_cross_team_tools(
    caller_id: str,
    *,
    caller_role: Any = None,
    rosters: dict[str, Any] | None = None,
    channels: tuple[ToolKind, ...] = ("consult", "handoff"),
) -> list[TeamConsultTool]:
    """Tools the caller may use to reach other teams.

    Empty for an ordinary teammate with no nested children. CoS receives
    one consult and one handoff tool per roster id.
    """
    tools: list[TeamConsultTool] = []
    for team_id in consultable_team_ids(caller_id, caller_role=caller_role, rosters=rosters):
        for kind in channels:
            verb = "Consult" if kind == "consult" else "Hand off to"
            tools.append(
                TeamConsultTool(
                    name=_tool_name(kind, team_id),
                    description=(
                        f"{verb} team `{team_id}` as a unit (send-to-all on "
                        "that team's direct members; not grandchildren)."
                    ),
                    kind=kind,
                    target_team_id=team_id,
                    caller_id=caller_id,
                    caller_role=caller_role,
                    rosters=rosters,
                )
            )
    return tools
