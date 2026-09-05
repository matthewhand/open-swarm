"""Static parse of openai-agents persona definitions.

Never executes blueprint source. Used by the blueprints API and team visual
roster (REQ-81 / #433) so the UI can show how many agents a team recipe
declares.
"""

from __future__ import annotations

import ast
from typing import Any

PERSONA_CTORS = frozenset({"Agent", "make_agent", "_make_agent"})

UNPARSED: dict[str, Any] = {"count": 1, "personas": [], "parsed": False}


def parse_openai_agent_personas(source: str | None) -> dict[str, Any]:
    """Return declared personas from Python/API source without executing it.

    Detects ``Agent(...)``, ``make_agent(...)``, and ``_make_agent(...)``
    (software-dev / Chatty-style helpers). A name is taken from a string
    ``name=`` keyword or the first positional string. Variable names are
    skipped (not invented). Unknown / unparsable source yields count 1 and
    an empty persona list.
    """
    if not isinstance(source, str) or not source.strip():
        return dict(UNPARSED)
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, TypeError):
        return dict(UNPARSED)

    names: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) not in PERSONA_CTORS:
            continue
        name = _literal_name(node)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)

    if not names:
        return dict(UNPARSED)
    return {
        "count": len(names),
        "personas": [{"name": item} for item in names],
        "parsed": True,
    }


def serialize_personas(parsed: dict[str, Any] | None) -> dict[str, Any]:
    """Public JSON shape for API / SPA."""
    data = parsed if isinstance(parsed, dict) else UNPARSED
    personas = [
        {"name": str(row["name"])}
        for row in (data.get("personas") or [])
        if isinstance(row, dict) and str(row.get("name") or "").strip()
    ]
    if not personas:
        return {"count": 1, "personas": [], "parsed": False}
    return {"count": len(personas), "personas": personas, "parsed": True}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _literal_name(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == "name":
            text = _string_constant(keyword.value)
            if text:
                return text
    if node.args:
        return _string_constant(node.args[0])
    return None


def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value.strip()
        return text or None
    return None
