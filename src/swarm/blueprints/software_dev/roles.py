"""Software-dev seat rules (Matthew's shared Grok role skills, encoded here).

Skill text lives in the shared skills ``coding-requirements-gate``,
``engineering-agent``, and ``skeptic-agent``. This module is the in-tree
copy used by the ``software_dev`` blueprint so openai-agents seats follow
the same rules without a parallel ``docs/requirements/`` source of truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# --- Issue quote (Issue-first REQ) ----------------------------------------- #

ISSUE_SECTIONS: tuple[str, ...] = ("Intent", "Success", "Constraints", "Owner")

_SECTION_RE = re.compile(
    r"(?is)(?:^|\n)\s*(?:[-*]\s*)?(?:\*\*)?(Intent|Success|Constraints|Owner)"
    r"(?:\*\*)?\s*:?\s*(.*?)"
    r"(?=(?:^|\n)\s*(?:[-*]\s*)?(?:\*\*)?(?:Intent|Success|Constraints|Owner)"
    r"(?:\*\*)?\s*:|\Z)"
)
_ISSUE_NUM_RE = re.compile(r"(?:Fixes|Closes)?\s*#(\d+)", re.IGNORECASE)
_FEASIBILITY_RE = re.compile(r"feasibil", re.IGNORECASE)


@dataclass(frozen=True)
class QuotedIssue:
    """A quoted GitHub Issue with the four required REQ sections."""

    number: int | None
    intent: str
    success: str
    constraints: str
    owner: str
    raw: str

    def is_complete(self) -> bool:
        return all(
            part.strip()
            for part in (self.intent, self.success, self.constraints, self.owner)
        )


def extract_quoted_issue(text: str | None) -> QuotedIssue | None:
    """Parse Intent/Success/Constraints/Owner from a quoted Issue body."""
    if not text or not str(text).strip():
        return None
    raw = str(text)
    found = {name.lower(): "" for name in ISSUE_SECTIONS}
    for match in _SECTION_RE.finditer(raw):
        found[match.group(1).lower()] = match.group(2).strip()
    if not all(found[name.lower()].strip() for name in ISSUE_SECTIONS):
        return None
    num_match = _ISSUE_NUM_RE.search(raw)
    return QuotedIssue(
        number=int(num_match.group(1)) if num_match else None,
        intent=found["intent"],
        success=found["success"],
        constraints=found["constraints"],
        owner=found["owner"],
        raw=raw,
    )


def has_feasibility(text: str | None) -> bool:
    """True when the engineer stated feasibility before writing."""
    return bool(text and _FEASIBILITY_RE.search(str(text)))


def engineer_may_start(
    text: str | None, *, feasibility: str | None = None
) -> tuple[bool, str]:
    """Hard gate: engineer cannot start without a quoted Issue + feasibility.

    Returns ``(ok, reason)``. Reason is the BLOCKED line when ``ok`` is False.
    """
    quoted = extract_quoted_issue(text)
    if quoted is None or not quoted.is_complete():
        return (
            False,
            "BLOCKED: engineer cannot start without a quoted Issue "
            "(Intent/Success/Constraints/Owner).",
        )
    combined = f"{text or ''}\n{feasibility or ''}"
    if not has_feasibility(combined):
        return (
            False,
            "BLOCKED: engineer must quote the Issue and state feasibility before write.",
        )
    return True, "ok"


def pr_fixes_clause(quoted: QuotedIssue | None) -> str:
    """PR must say Fixes/Closes #N — never a docs-only close."""
    if quoted is None or quoted.number is None:
        return "PR must say Fixes #N or Closes #N for the quoted Issue."
    return f"Fixes #{quoted.number}"


# --- Seat isolation -------------------------------------------------------- #

SEAT_COS = "cos"
SEAT_ENGINEER = "engineer"
SEAT_SKEPTIC = "skeptic"
SEATS: tuple[str, ...] = (SEAT_COS, SEAT_ENGINEER, SEAT_SKEPTIC)

WRITE_TOOLS: frozenset[str] = frozenset({"write_file", "implement", "apply_patch"})
LOOK_TOOLS: frozenset[str] = frozenset({"read_file", "list_files", "review"})

COS_INSTRUCTIONS = """You are the talk-to Chief of Staff for the software-dev team.
You follow the coding-requirements-gate skill.

Issue-first REQ:
- The GitHub Issue is the source of truth. Quote Intent, Success, Constraints, Owner.
- PRs must say Fixes #N or Closes #N. Do not close via docs-only PRs.
- Do not create a parallel docs/requirements/ source of truth. Pointers only.

Seats (openai-agents handoff / as-tool — not concurrent Grok Bot seats):
- You are the talk-to seat. Use consult_engineer / consult_skeptic (agent-as-tool)
  or hand off. Do not spawn three concurrent harness seats.
- Engineer implements only after quoting the Issue and stating feasibility.
- Skeptic is look-only and does not write code until you invoke them for review.
  Unblock the skeptic when the engineer claims Success; keep them look-only otherwise.

Do not implement. Do not write application code. Route work.
"""

ENGINEER_INSTRUCTIONS = """You are the engineer seat. You follow the engineering-agent skill.

Before any write:
1. Quote the GitHub Issue in full: Intent, Success, Constraints, Owner.
2. State feasibility against this tree (what you will change, what you will not).
3. If you cannot quote the Issue, STOP. You are blocked.

Then implement to Success with real tests (not stubs). PRs must say Fixes #N.
Do not invent a parallel docs/requirements/ SoT. Do not enable Neon/oracle,
LiteLLM catalog edits, OMB :8802, extra Grok trio seats, or :8001 deploys
unless the quoted Issue says so.

You are isolated from the skeptic: do not review your own work as skeptic.
"""

SKEPTIC_INSTRUCTIONS = """You are the skeptic seat. You follow the skeptic-agent skill.

You do NOT implement. You do NOT write code, patches, or tests. Look-only
until the CoS unblocks you for review.

When reviewing, run four checks PLUS test interrogation (not diff-only):
1. REQ captured — Intent/Success/Constraints/Owner quoted from the Issue.
2. Match — the change meets Success.
3. Deviations — Constraints honored; no extra scope.
4. Visual — UI/UX honestly assessed. Open-swarm standing order: text-only
   PASS/FAIL in chat. No screenshot attachments to CoS unless Matthew lifts it.
5. Tests — interrogate coverage, depth, and quality. A green run of a shallow
   test is not enough.

Reply with a text-only verdict: PASS or FAIL, then the five checks.
"""

SKEPTIC_NO_WRITE = (
    "BLOCKED: skeptic does not write code (look-only until CoS unblocks)."
)
SKEPTIC_LOOK_ONLY = (
    "LOOK-ONLY: skeptic is not unblocked. CoS must invoke consult_skeptic "
    "before a verdict."
)


@dataclass
class SoftwareDevContext:
    """Per-run isolation: quoted Issue, feasibility, write traces, CoS unblock."""

    quoted_issue: QuotedIssue | None = None
    feasibility: str = ""
    skeptic_unblocked: bool = False
    writes: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    source_text: str = ""

    def refresh_from_text(self, text: str | None, feasibility: str | None = None) -> None:
        if text:
            self.source_text = text
            self.quoted_issue = extract_quoted_issue(text)
        if feasibility:
            self.feasibility = feasibility

    def engineer_gate(self) -> tuple[bool, str]:
        return engineer_may_start(
            self.source_text or (self.quoted_issue.raw if self.quoted_issue else ""),
            feasibility=self.feasibility,
        )


def seat_tool_policy(seat: str) -> dict[str, Any]:
    """Declared tool policy per seat (used by wiring + isolation tests)."""
    seat = (seat or "").strip().lower()
    if seat in (SEAT_COS, "chief_of_staff", "coding-requirements-gate", "gate"):
        return {
            "seat": SEAT_COS,
            "role": "chief_of_staff",
            "skill": "coding-requirements-gate",
            "may_write": False,
            "tools": ("consult_engineer", "consult_skeptic", "unblock_skeptic", "quote_issue"),
            "as_tool": True,
        }
    if seat == SEAT_ENGINEER or seat == "engineering-agent":
        return {
            "seat": SEAT_ENGINEER,
            "role": "engineer",
            "skill": "engineering-agent",
            "may_write": True,
            "tools": ("read_file", "list_files", "write_file", "implement"),
            "as_tool": True,
        }
    if seat == SEAT_SKEPTIC or seat == "skeptic-agent":
        return {
            "seat": SEAT_SKEPTIC,
            "role": "skeptic",
            "skill": "skeptic-agent",
            "may_write": False,
            "tools": ("read_file", "list_files", "review"),
            "as_tool": True,
        }
    raise ValueError(f"unknown software-dev seat: {seat}")


def skeptic_verdict(
    *,
    quoted: QuotedIssue | None,
    work: str,
    tests_note: str = "",
    visual_note: str = "",
    deviations: str = "",
) -> str:
    """Text-only PASS/FAIL with the four checks + test interrogation."""
    checks: list[tuple[str, bool, str]] = []
    captured = quoted is not None and quoted.is_complete()
    checks.append(
        (
            "REQ captured",
            captured,
            "Issue Intent/Success/Constraints/Owner quoted"
            if captured
            else "missing quoted Issue sections",
        )
    )
    match = bool(work.strip()) and captured
    checks.append(
        (
            "match",
            match,
            "work described against Success" if match else "no work matched to Success",
        )
    )
    clean = "scope creep" not in (deviations or "").lower()
    checks.append(
        (
            "deviations",
            clean,
            deviations.strip() or "none noted",
        )
    )
    visual_ok = "fail" not in (visual_note or "").lower()
    checks.append(
        (
            "visual",
            visual_ok,
            visual_note.strip() or "text-only (no screenshot attachments to CoS)",
        )
    )
    tests_ok = bool(tests_note.strip()) and "shallow" not in tests_note.lower()
    checks.append(
        (
            "tests",
            tests_ok,
            tests_note.strip() or "test coverage/depth/quality not interrogated",
        )
    )
    passed = all(ok for _, ok, _ in checks)
    lines = [f"{'PASS' if passed else 'FAIL'} (text-only; no screenshot attachments)"]
    for name, ok, detail in checks:
        lines.append(f"- {'PASS' if ok else 'FAIL'} {name}: {detail}")
    return "\n".join(lines)
