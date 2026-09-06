# Agent roles: support, gate, skeptic, engineer

Users assign a first-class **role** on each agent so the AGENTS sidepane can
highlight them and so a team can relate one agent's output to another's input
via openai-agents **`as_tool` / handoff** — not extra concurrent Grok / OMB /
Rakazo seats.

| Role | Sidepane classes | What it does |
|---|---|---|
| `default` / `none` | (no badge) | Ordinary worker. No special wiring. |
| `support` | `os-agent-role-support` `data-role="support"` | Support seat (REQ-7 / REQ-137 / REQ-154). First-run journey onboarder **and** the only global role that can `create_agent` / `archive_agent` (with API CoS). |
| `gate` (`tool_gate`) | `os-agent-role-gate` `data-role="gate"` | Classifies a **pending tool call** as dangerous or not via `submit_gate_verdict` (yes/no). |
| `skeptic` | `os-agent-role-skeptic` `data-role="skeptic"` | Reviews whether the original prompt was accomplished via `submit_skeptic_verdict` (pass/fail). |
| `chief_of_staff` (`cos`) | `os-agent-role-chief_of_staff` `data-role="chief_of_staff"` | Talks to any team. API CoS also gets create/archive tools (REQ-154). CLI CoS does not (v1). |
| `engineer` | `os-agent-role-engineer` `data-role="engineer"` | Implementer seat (software-dev / Chatty). Badge only. |
| `suggestions` | `os-agent-role-suggestions` `data-role="suggestions"` | Prepares 2–5 quick-select chips after a turn (REQ-85). |

Chrome stays **badge-only** (REQ-67 / #396): no row fill or left-border accent.

## Two invocation modes (REQ-191)

A seat with a role runs in two modes. Full contract: [ADR-010](./adr/010-role-agent-invocation-modes.md).

| Mode | Who | Context |
|------|-----|---------|
| **A — Human chat** | Operator on `/chat` | Role-aware configure/discuss prompt + **this thread** (wide context). |
| **B — as-tool / handoff** | Other agents / graph | Execution prompt + **caller context** and the **latest message**. Not the role agent’s private configure thread. |

SPA Chat shows a dismissable tip on the pane when the selected agent has a role. Role-less seats (`default` / `none`) skip it. Mode B payload wiring is a follow-up; mailbox `send_message` (ADR-009) is Mode A on the target chat.

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
* **Dangerous ≠ denied.** A wired gate that says yes (dangerous) via
  `submit_gate_verdict` **elicits** the user. Safe calls go through without a
  prompt. The runtime never parses YES/NO from chat prose. If the model stops
  without the tool, it is nudged (default 3 times) then **fail closed**
  (needs-human / block).
* **Skeptic is a bounded retry, not a nag.** It finishes with
  `submit_skeptic_verdict`. On fail, findings are handed back to the original
  agent (max 2 retries). On pass, stop. Missing tool → nudges, then FAIL.
  Do not surface extra critique to the user. Do not parse PASS/FAIL from prose.

## Wiring

```
User prompt
    │
    ▼
Original agent  ──pending tool──►  gate.as_tool  ──submit_gate_verdict──►  elicit if dangerous
    │
    ▼
output
    │
    ▼
skeptic.as_tool(original prompt + output)
    ├── submit_skeptic_verdict(pass) → stop (do not nag)
    └── submit_skeptic_verdict(fail) → findings → original agent (retry ≤ 2)
```

Code:

Lifecycle (REQ-154 / #562): Support and API CoS share `create_agent` /
`archive_agent` / `restore_agent`. Ordinary roles do not. See
[AGENT_LIFECYCLE.md](./AGENT_LIFECYCLE.md).

* `swarm.core.agent_roles` — normalize, roster, CSS class names, API payload
* `swarm.core.agent_lifecycle` — Support/CoS create + archive + purge
* `swarm.core.classifier_verdict` — verdict tools + continue nudges (REQ-108)
* `swarm.core.tool_gate` — `approve_pending_tool_call` (fail-open when unwired)
* `swarm.core.skeptic` — `run_with_skeptic` (bounded as-tool loop)
* Team Creator select **Agent role** → generated `AGENT_SPECS[].role` + metadata
  `gate_agent` / `skeptic_agent` / `agents[{name,role}]`
* `GET /v1/blueprints/` includes `role`, `agents`, `gate_agent`, `skeptic_agent`, `suggestions_agent`, `workflow`, `webui`
* Consumer **Use suggestions** toggle (`use_suggestions` on `/v1/agents/<id>/settings/`) wires the role as-tool. Chips are chrome, not LLM context.

Unwired gate proof: `tests/core/test_tool_gate.py` asserts `elicit_fn` is never
called when no gate is on the team.
