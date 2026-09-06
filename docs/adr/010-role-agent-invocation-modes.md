# ADR-010: Role-agent invocation modes — chat configures; as-tool uses caller context

- **Status:** Accepted for the Mode A/B **contract** and the chat-pane tip (2026-09-06). Mode B **runtime wiring** is specified here and deferred to a child Issue.
- **Date:** 2026-09-06
- **Issue:** [#648](https://github.com/matthewhand/open-swarm/issues/648) (REQ-191)
- **Related:** [#356](https://github.com/matthewhand/open-swarm/issues/356) (REQ-42 role-badge / definition pane), [#571](https://github.com/matthewhand/open-swarm/issues/571) / [#577](https://github.com/matthewhand/open-swarm/pull/577) (REQ-160 in-field keybinding tips, not overlay chrome), [#564](https://github.com/matthewhand/open-swarm/issues/564) (REQ-156 openai-agents handoff graphs), [#540](https://github.com/matthewhand/open-swarm/issues/540) (REQ-144 user preferences), [ADR-009](./009-peer-mailbox.md) (peer mailbox ≠ Mode B), [AGENT_ROLES.md](../AGENT_ROLES.md)
- **Supersedes:** none. Complements ADR-009 (mailbox delivery) and REQ-156 (graph topology). This ADR is about **which context a role agent sees**, not how peers discover each other.

**Decision:** A seat with a **role** (`support`, `gate`, `skeptic`, `chief_of_staff`, `engineer`, `suggestions` — anything other than `default` / `none`) has **two invocation modes**. The human must be told; Mode B must not silently reuse the role agent’s private configure thread.

This PR ships the **contract** and a **dismissable chat-pane tip**. It does **not** rewire as-tool / handoff payloads. That work is large (consumers, `as_tool` / `Handoff` input, classifier loops, mailbox vs graph) and belongs on a child Issue.

No secrets. No Neon. No `:8001`.

---

## Issue quote (REQ-191)

**Intent:** Correct context wiring per invocation path; teach the human with a dismissable tip on the chat pane when talking to a role agent.

**Success (this PR — tip + contract):**

1. Clear contract for Mode A vs Mode B (prompt, context window, tool/handoff payload). Mode B code deferred.
2. Dismissable tip on the chat pane when the selected agent has a role. Dismiss persists (localStorage + `GET/PATCH /v1/preferences/` extras bag; #540 is ready).
3. Tip not shown for role-less agents. Esc / dismiss hides the tip; Chat stays mounted.
4. Tests for tip show/dismiss. `Fixes` #648 for tip + contract. Child Issue for Mode B wiring.

**Constraints:** Coordinate tips #571/#577, roles #356, handoff #564. No secrets. Prefer Cursor for Mode B wiring.

---

## Mode A — Human chats with the role agent (configure / discuss)

**Who:** The operator on SPA `/chat` (or Django chat) with that seat selected.

**Prompt:** Role-aware **configure / discuss** instructions. Help the human understand and tune the seat (what the role does, how it is wired on the team, verdict tools, Socratic Support, CoS brief). Do **not** treat a casual chat as a live gate verdict or skeptic pass/fail of some other agent’s hidden run.

**Context window:** The **full conversation thread** for that `(user, agent)` chat — the same JSON `chat_store` / Django thread Chat already hydrates. Compact / cull (REQ-87 / REQ-121) still apply; the point is “this thread,” not “last user line only.”

**Payload:** Ordinary chat WS / `/v1/chat/completions` messages. No caller agent, no handoff input schema.

**Session:** Default one thread per seat. REQ-65 **New chat per task** still mints empty sessions when on; that is scale-out, not Mode B.

Mode A is **already how human chat works** (full thread). This ADR names it so Mode B cannot silently steal that thread.

---

## Mode B — Other agents use the seat as that role (handoff / as-tool)

**Who:** A coordinator, teammate, or runtime loop that invokes the role via openai-agents `Agent.as_tool(...)` or `Handoff` (REQ-156 graphs, gate/skeptic classifier loops, software-dev / persona teams). **Not** ADR-009 `send_message` into the target’s human chat (that is mailbox delivery — it **is** Mode A on the target thread).

**Prompt:** Role-**execution** instructions (classify this pending tool; review whether this prompt was accomplished; emit chips; implement the quoted issue). Verdict roles still finish only via `submit_gate_verdict` / `submit_skeptic_verdict` (REQ-108).

**Context window:** The **caller’s context** plus the **latest message** (the tool/handoff input). Do **not** load the role agent’s private Mode A configure thread. Do **not** re-litigate a human discussion about how the role should behave.

**Payload (contract — implement on the child Issue):**

| Field | Required | Meaning |
|-------|----------|---------|
| `invocation` | yes | `"as_tool"` or `"handoff"` |
| `caller_id` | yes | Invoking agent / blueprint id |
| `role` | yes | Canonical role of the callee |
| `latest_message` | yes | The user/tool turn the role should judge or act on |
| `caller_context` | yes | Compact caller transcript or structured snippet (prompt + relevant output / pending tool). Not the callee’s chat JSON. |
| `callee_thread_id` | no | Must **not** be used as model context in Mode B |

**Session:** Prefer an ephemeral / empty task session (REQ-65 `as_tool` / handoff already mint when new-chat-per-task is on). Never resume the human configure conversation as if it were the caller’s run.

**Today (honest):** Gate and skeptic loops already pass “original prompt + agent output” / “pending tool” into the classifier (`swarm.core.skeptic`, `swarm.core.tool_gate`). Blueprint `as_tool` / `Handoff` graphs still depend on openai-agents defaults and may see the wrong history. There is **no** shared invocation flag that forbids loading the callee’s Mode A thread. That gap is the child Issue.

---

## What is a “role” (tip + contract)

`normalize_agent_role` / SPA `agentRole()` → anything other than `default`. Role-less seats (`none`, worker, Codey, unnamed) get **no** tip and **no** Mode B special case.

Teams (`?team=`) and remotes (`?remote=`) are not a single role seat; the tip stays off.

---

## Chat-pane tip (this PR)

When the selected `/chat` agent has a role and the tip is not dismissed:

* DaisyUI `alert` on the **chat pane** (below the header, above the transcript). Not a modal. Not `first-load-tips` overlay chrome (#571/#577 — those stay composer / Search chips).
* Brief Mode A vs Mode B copy. Dismiss (X) or **Esc** hides it. Chat **stays mounted** (composer, transcript, rail).
* Persist `localStorage.swarm_role_agent_tip_dismissed` immediately; PATCH `/v1/preferences/` extras `role_agent_tip_dismissed: true` (REQ-144). Hydrate: server wins when set; local dismiss imports once if the server bag lacks the key.

Role-badge click (#356) is unchanged. The tip does not open Settings.

---

## Not this ADR

* Peer mailbox `list_agents` / `send_message` (ADR-009) — delivered mail is Mode A on the target chat.
* REQ-156 graph topology / demo names (Mode A kind-clear vs Mode B persona **names** are a different “Mode A/B”).
* Rewriting gate/skeptic verdict tools (REQ-108).
* First-load keybinding overlay (removed; do not bring it back).

---

## Follow-up — file as a child of #648

**Title:** REQ-191B: Role as-tool/handoff uses caller context + latest message (Mode B wiring)

**Intent:** Implement the Mode B payload and session rules in this ADR so a role invoked as a tool or handoff never reads its private configure thread.

**Success:**

1. Shared invocation flag (`as_tool` / `handoff`) on chat WS, `/v1/chat/completions`, and openai-agents tool/handoff wrappers.
2. Model messages = execution prompt + `caller_context` + `latest_message` only.
3. Tests: Mode B run does not include Mode A configure turns; Mode A human chat still gets the full thread. Gate/skeptic/Support/CoS covered.
4. No secrets. No Neon. No `:8001`. Own-diff CI.

**Owner:** Cursor (wiring). Tip + contract already shipped on #648.

---

## Code (this PR)

* SPA: `webui/frontend/src/lib/roleAgentTip.ts`, `webui/frontend/src/components/RoleAgentTip.tsx`, `ChatPage` mount.
* Prefs extras key `role_agent_tip_dismissed` (no new table; #540 bag).
* Tests: `roleAgentTip.test.ts`, `RoleAgentTip.test.tsx`, `ChatPage.roleAgentTip.test.tsx`, `tests/unit/test_req191_role_agent_modes.py`.
* Own-diff: `.github/workflows/req191-role-agent-tip.yml`.
