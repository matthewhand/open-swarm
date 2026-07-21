"""Shared types for Mixture of Agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionMode(str, Enum):
    """Permission posture for a backend invocation."""

    APPROVE_READS = "approve-reads"
    DENY_ALL = "deny-all"
    APPROVE_ALL = "approve-all"  # never valid for MoA participants


@dataclass
class ParticipantOpinion:
    """One participant's read-only response to a question."""

    name: str
    text: str
    ok: bool
    permission_mode: str
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Determination:
    """Orchestrator-owned consensus determination."""

    answer: str
    rationale: str = ""
    participant_names: list[str] = field(default_factory=list)
    analysis: dict[str, Any] | None = None


@dataclass
class ActResult:
    """Outcome of an orchestrator-owned write/impactful operation."""

    ok: bool
    detail: str = ""
    side_effects: list[str] = field(default_factory=list)
