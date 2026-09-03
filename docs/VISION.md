# Open Swarm — Vision

> **One sentence:** Open Swarm is becoming a **harness for other agent
> harnesses** — Hermes, OpenMausBot, Rakazo, and the agentic CLIs you already
> run — composed with openai-agents **handoff / `as_tool`**, not by adding extra
> concurrent Grok / Rakazo / OMB seats.

This is the front door. It states the intended product, then an honest
**live vs intended** table. Mechanics of today's in-process patterns:
[ORCHESTRATION_PATTERNS.md](./ORCHESTRATION_PATTERNS.md). Workflow A vs B:
[SWARM_WORKFLOWS.md](./SWARM_WORKFLOWS.md). Vocabulary:
[GLOSSARY.md](./GLOSSARY.md).

A separate generic docs-vs-reality audit lives on
[PR #297](https://github.com/matthewhand/open-swarm/pull/297) (review-only).
This page is the **direction write**, not that audit.

---

## Thesis

The field now has several **agent harnesses** — Grok Bot (vendor), Hermes
(Nous), OpenMausBot, Rakazo — each a roster of named bots, usually **poly-agent
concurrent**: many seats run in parallel on a computer (shared or per-bot).

Open Swarm used to compete in that shape: wrap CLIs, fan a prompt to a panel,
judge, synthesize. That line still **runs** (CLI fusion / MoA). The product is
turning: **stop being another concurrent-seat harness; become the layer that
invokes the ones you already chose.**

Composition is the openai-agents primitives we already depend on:

- **handoff** — control moves to another agent
- **`as_tool()`** — a specialist (or, later, a remote harness) is called as a
  tool, then returns

That is **not** “spin another Grok / LiteLLM / OMB worker.” Roles are seats in
a graph, not extra concurrent subscriptions.

```
intended (not all live)

  OpenAI client / Chat
           │
           ▼
     Open Swarm coordinator
           │  handoff / as_tool
           ├──► Hermes
           ├──► OpenMausBot
           └──► Rakazo
```

---

## Differentiator

| | **Open Swarm (direction)** | **Grok Bot / Rakazo / OpenMausBot** |
|---|---|---|
| Unit of work | A **tool call or handoff** into another harness | A **concurrent seat** (another bot on a computer) |
| How many run at once | Coordinator invokes specialists; no extra poly-agent seats | Many bots in parallel (the product) |
| What you bring | Harnesses and CLIs you already run | A roster inside that product |
| openai-agents | Native: `handoff` / `as_tool` | Not the composition model |

Existing **MoA / `cli_fusion` concurrent panels** stay as a *pattern you can
pick* (workflow A). They are not the intended differentiator, and they are not
a claim that remotes or Grok-Bot chrome exist.

---

## Live vs intended

Short and dated. Do not treat “intended” as shipped.

| Surface | Status | Honesty |
|---|---|---|
| **Running today** | OpenAI-compatible `/v1/chat/completions` + `/v1/responses`, blueprint discovery, `swarm-cli`, Django operator UI + SPA `/` + `/chat` ([ADR-001](./ADR-001-primary-ui.md)), CLI fusion / MoA, in-process persona / `as_tool` specialists, `harness_fleet` **LAN health probes** | This is the live product. |
| **Teams (`/teams/`, `/v1/teams`)** | **Live:** LLM-profile alias registry (`id` / `description` / `llm_profile` in `teams.json`). Admin/launcher CRUD that proxy chat through `DynamicTeamBlueprint`. **Intended:** a Team wires API / CLI / remote agents so they can **see and talk to each other** (handoff / `as_tool`). | **Collision.** Multi-agent talk today is **Blueprints / MoA**, not Teams Admin. Do not claim `/teams/` already does inter-agent talk. |
| **Dark chrome** | REQ-5 / REQ-5d on `main` — near-black operator shell, large home cards, AGENTS sidepane on Django too | Colour/chrome only. **Not** a Grok-Bot UI. |
| **Grok-Bot-like UI** | Intended look (roster, remotes, Bot chrome) | **Not live. Not shipping.** Do not demo or document it as current. |
| **Support / gate / skeptic** | openai-agents roles via `as_tool` / handoff (Support talks about the roster; gate classifies dangerous tool calls; skeptic reviews then bounded retry) | **In flight** (open PRs; not on `main`). Until those land, there is no Support landing agent and no live gate/skeptic engine. |
| **Remotes (REQ-11)** | First-class connection to Hermes / OpenMausBot / Rakazo (and similar) as handoff / `as_tool` backends | **Not landed.** Chat has no Remote selector. `harness_fleet` is TCP/HTTP inventory, not remotes. **Do not claim remotes work.** |

---

## What is running (so we do not erase it)

Verified capabilities — still true, still not the new headline:

- OpenAI-compatible API, OpenAPI at `/api/schema/`
- Blueprints as `model` ids (`cli_agent`, `cli_fusion` / MoA, `cli_orchestrator`,
  `cli_map`, pipeline / roundtable / planner, persona councils, …)
- `swarm-cli cli-agents` autodiscovery; Skills (`SKILL.md`); inference profiles
- Web: Django trailing-slash operator pages; SPA dashboard + websocket chat
- `/teams/` — LLM-profile **aliases** only (not inter-agent talk)
- `harness_fleet` — LLM-free probe of configured LAN endpoints (placeholders
  for Rakazo / OpenMausBot ports are **UNKNOWN** until configured)

Proof transcripts for *cross-CLI* fusion (not remotes) remain under
[`docs/proofs/`](./proofs/).

---

## What we will not claim

- Remotes work, or Chat can target Hermes / OpenMausBot / Rakazo.
- Grok-Bot chrome is shipping (dark theme ≠ Bot product).
- Support, gate, or skeptic are on `main`.
- **Teams Admin / `/teams/` already lets agents see and talk to each other.**
  Live Teams is an LLM-profile alias registry. Multi-agent talk is Blueprints
  / MoA until the intended Team lands.
- Extra concurrent Grok / Rakazo / OMB seats are the differentiator.
- Neon / Oracle / Fly are part of this direction. They are ops; they are not
  enabled or resumed here.

---

## Design principles (direction)

1. **Handoff / `as_tool`, not another seat.** If a design adds a concurrent
   poly-agent worker to look like Grok/OMB/Rakazo, it is the wrong axis.
2. **Harnesses stay themselves.** Auth, tools, and computers stay with Hermes /
   OMB / Rakazo / the CLI. Open Swarm invokes; it does not re-implement.
3. **OpenAI-compatible or it does not exist.** A capability that cannot be a
   `model` id or a tool on one is not shipped.
4. **Honest status.** Partial is partial; in-flight is in-flight; remotes are
   absent until REQ-11 lands.
5. **Graceful degradation.** A missing remote or unwired gate must not pretend
   to have run. (Today: unwired gate = all tools approved — once that code
   exists. Until then, do not document the gate as live.)

---

## See also

- [GLOSSARY.md](./GLOSSARY.md) — Blueprint, Team (live alias vs intended wiring), Remote, Role
- [SWARM_WORKFLOWS.md](./SWARM_WORKFLOWS.md) — MoA vs persona / `as_tool`
- [ORCHESTRATION_PATTERNS.md](./ORCHESTRATION_PATTERNS.md) — today's patterns
- [ADR-001](./ADR-001-primary-ui.md) — Django operator UI; SPA `/` + `/chat`
- [CLI_FUSION.md](./CLI_FUSION.md) — wrapping *CLIs* (not remotes)
- [ROADMAP.md](../ROADMAP.md) · [FEATURE_STATUS.md](../FEATURE_STATUS.md)
- [PR #297](https://github.com/matthewhand/open-swarm/pull/297) — generic honesty audit (separate)
