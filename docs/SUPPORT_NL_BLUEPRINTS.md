# Support builds blueprints in natural language (REQ-158)

Issue SoT: [REQ-158 #567](https://github.com/matthewhand/open-swarm/issues/567).

**Intent:** Sell the power-user Python path **and** the NL path. Open Swarm
bootstraps more of itself via **Support**.

**Name:** the onboarder is **Support** (same seat as REQ-137 / #530). Not a
second bot.

---

## Two paths (same seat)

| Path | Who writes Python? | What you see |
|------|--------------------|--------------|
| **Happy path** | Nobody. Ask Support. | A usable team/workflow. Code hidden. Optional **View / edit code**. |
| **Power user** | You, or Support when you ask to see it. | An `ApiKindBase` (or CLI/remote kind base) Python class. |

**Under the hood** a blueprint/team is a Python class — usually
`ApiKindBase` (ADR-005). That is how openai-agents handoff / as-tool graphs
are defined. You do not need to look at that class to get a working team.

---

## Guided path (GitHub-only — no live preview host)

This is the announce / GIF story. GitHub-only. No preview host. No secrets.

1. Open Chat on **Support** (empty thread).
2. Click **Create a BA → Engineer → Tester workflow** (or type that sentence).
3. Support persists a rail-visible custom blueprint. Reply says the team is
   **usable** and that you did **not** write Python.
4. The card shows the graph (`BA → Engineer → Tester`) and **Open in chat**.
5. Python is **hidden**. Click **View / edit code** only if you want the
   generated `ApiKindBase` class (ties to #564 / `sdlc_handoff`).

Recorded checklist (source-locked by `tests/unit/test_req158_nl_blueprints.py`
and the Vitest card):

- [x] User message is natural language — no `class`, no `def`, no fenced Python.
- [x] Support create tool / deterministic path calls `create_blueprint_from_nl`.
- [x] Result `userWrotePython` is false.
- [x] Default UI has no `<textarea>` / `pre` of the generated module.
- [x] **View / edit code** reveals the generated class.
- [x] Graph edges are BA → Engineer, Engineer → Tester (REQ-156 example).
- [x] No live preview host, no secrets, no Neon.

---

## Example: Support creates the #564 handoff

User:

> Create a BA → Engineer → Tester workflow

Support (abridged):

> Created **BA → Engineer → Tester**. The team is usable in chat — you did
> not write Python.
>
> Open: `/chat?blueprint=ba_eng_tester`
> Graph: BA → Engineer → Tester
>
> Under the hood this is a Python `ApiKindBase` blueprint class. Code stays
> hidden unless you choose **View / edit code**.

That is the same topology as
[`docs/examples/openai-agents-handoff-graphs/sdlc-pipeline.json`](./examples/openai-agents-handoff-graphs/sdlc-pipeline.json)
and the `sdlc_handoff` recipe. Support copies the idea into a **new**
custom seat so the product builds more of itself.

```mermaid
flowchart LR
  User[User NL] --> Support[Support]
  Support --> Seat[Custom ApiKindBase seat]
  BA[BA] --> Eng[Engineer]
  Eng --> Test[Tester]
```

---

## Deviation vs #562 (REQ-154)

#562 (Support/CoS **create + archive** agents, ~30d purge) is still open.
This slice ships **Support-only NL blueprint/team create** on the existing
custom-library + `rail: true` path (`POST`-equivalent via
`create_blueprint_from_nl` → `build_custom_rail_item`).

Not in this slice: CoS create parity, archive / soft-delete, purge job.
Those stay on #562.

---

## Related

- Support onboarder: [REQ-137 #530](https://github.com/matthewhand/open-swarm/issues/530)
- openai-agents graphs: [REQ-156 #564](https://github.com/matthewhand/open-swarm/issues/564)
- Kind bases: [ADR-005](./adr/005-kind-bases.md) (REQ-159)
