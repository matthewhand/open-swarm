# Agent roles: support, gate, skeptic, engineer

Users assign a first-class **role** on each agent so the AGENTS sidepane can
highlight them and so a team can relate one agent's output to another's input
via openai-agents **`as_tool` / handoff** — not extra concurrent Grok / OMB /
Rakazo seats.

| Role | Sidepane classes | What it does |
|---|---|---|
| `default` / `none` | (no badge) | Ordinary worker. No special wiring. |
| `support` | `os-agent-role-support` `data-role="support"` | Support seat (REQ-7). Introduces the concept; copy below. |
| `gate` (`tool_gate`) | `os-agent-role-gate` `data-role="gate"` | Classifies a **pending tool call** as dangerous or not (single-token YES/NO). |
| `skeptic` | `os-agent-role-skeptic` `data-role="skeptic"` | Reviews whether the original prompt was accomplished. |
| `chief_of_staff` (`cos`) | `os-agent-role-chief_of_staff` `data-role="chief_of_staff"` | Talks to any team. Badge only (`CoS`). |
| `engineer` | `os-agent-role-engineer` `data-role="engineer"` | Implementer seat (software-dev / Chatty). Badge only. |
| `suggestions` | `os-agent-role-suggestions` `data-role="suggestions"` | Prepares 2–5 quick-select chips after a turn (REQ-85). |

Chrome stays **badge-only** (REQ-67 / #396): no row fill or left-border accent.

## Blueprint default role (REQ-75)

Python blueprints remain the source. A recipe may declare:

```python
metadata = {
    "role": "gate",          # gate / skeptic / cos / engineer / support / none
    "workflow": "as_tool",   # optional: handoff | as_tool (hint only)
}
```

Creating an agent from that blueprint (or re-picking it in the agent editor)
assigns that default role. Catalog / picker show the role as a badge.

**Override rule:** changing Role in the agent editor is agent-scoped and wins
over the blueprint default. Re-picking a blueprint re-applies that recipe's
default role **unless** the operator has explicitly overridden Role. `none`
and a missing `role` mean no badge.

v1 `workflow` is metadata + apply-on-create — not a new orchestration engine.
There is no `webui` blueprint kind; pickers hide leftover `django_chat` /
`kind=webui` rows (#419 already retired that recipe).

Also: `.os-agent-role-badge` for the optional label chip; `.os-agent-dot[data-role=…]`
for the accent. Support should **reuse these class names**, not invent a parallel set.

## How Support should talk about it

* **Roles are seats, not models.** Assigning `gate` or `skeptic` does not add
  another Grok / LiteLLM / OMB seat. It wires an openai-agents specialist.
* **Gate is default-open.** If no gate is wired to the team, every tool call is
  approved and the user is never asked. The gate only applies when a `gate`
  (or `tool_gate`) role is actually on the roster.
* **Dangerous ≠ denied.** A wired gate that says YES (dangerous) **elicits**
  the user. Safe calls go through without a prompt.
* **Skeptic is a bounded retry, not a nag.** On failure, findings are handed
  back to the original agent (max 2 retries). On success, stop. Do not surface
  extra critique to the user.

## Wiring

```
User prompt
    │
    ▼
Original agent  ──pending tool──►  gate.as_tool  ──YES/NO──►  elicit if dangerous
    │
    ▼
output
    │
    ▼
skeptic.as_tool(original prompt + output)
    ├── YES → stop (do not nag)
    └── NO  → findings → original agent (retry ≤ 2)
```

Code:

* `swarm.core.agent_roles` — normalize, roster, CSS class names, API payload
* `swarm.core.tool_gate` — `approve_pending_tool_call` (fail-open when unwired)
* `swarm.core.skeptic` — `run_with_skeptic` (bounded as-tool loop)
* Team Creator select **Agent role** → generated `AGENT_SPECS[].role` + metadata
  `gate_agent` / `skeptic_agent` / `agents[{name,role}]`
* `GET /v1/blueprints/` includes `role`, `agents`, `gate_agent`, `skeptic_agent`, `suggestions_agent`, `workflow`, `webui`
* Consumer **Use suggestions** toggle (`use_suggestions` on `/v1/agents/<id>/settings/`) wires the role as-tool. Chips are chrome, not LLM context.

Unwired gate proof: `tests/core/test_tool_gate.py` asserts `elicit_fn` is never
called when no gate is on the team.
