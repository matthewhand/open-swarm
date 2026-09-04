# Agent roles: support, gate, skeptic

Users assign a first-class **role** on each agent so the AGENTS sidepane can
highlight them and so a team can relate one agent's output to another's input
via openai-agents **`as_tool` / handoff** — not extra concurrent Grok / OMB /
Rakazo seats.

| Role | Sidepane classes | What it does |
|---|---|---|
| `default` | `os-agent-role-default` `data-role="default"` | Ordinary worker. No special wiring. |
| `support` | `os-agent-role-support` `data-role="support"` | Support seat (REQ-7). Introduces the concept; copy below. |
| `gate` (`tool_gate`) | `os-agent-role-gate` `data-role="gate"` | Classifies a **pending tool call** as dangerous or not (single-token YES/NO). |
| `skeptic` | `os-agent-role-skeptic` `data-role="skeptic"` | Reviews whether the original prompt was accomplished. |

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
* `GET /v1/blueprints/` includes `role`, `agents`, `gate_agent`, `skeptic_agent`

Unwired gate proof: `tests/core/test_tool_gate.py` asserts `elicit_fn` is never
called when no gate is on the team.
