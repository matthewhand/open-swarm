# Peer mailbox (`list_agents` / `send_message`)

REQ-153 / [#561](https://github.com/matthewhand/open-swarm/issues/561). Graph ADR: [ADR-009](./adr/009-peer-mailbox.md).

This is **not** an openai-agents handoff graph ([REQ-156](./examples/openai-agents-handoff-graphs/README.md)). Handoff enforces a programmed topology. The mailbox lets an **API** agent **list peers** and **send a message** into another API agent’s chat transcript so the user can say “ask X to do Y” without copy-paste.

## Who gets the tools

Eligible in v1: **API-kind** agents (including Support). CLI, remote, and herdr do not get these tools yet.

| Caller | `list_agents` / `send_message` scope |
|--------|--------------------------------------|
| API agent on a team | Other **API** members of that team |
| API agent + relationship edge (team↔agent or team↔team) | Same-kind members across that edge |
| Support / CoS | All same-kind catalogued peers (allow-all) |
| Unteamed, non-Support API agent | Empty (no global roster dump) |

Hidden Bots are omitted and `send_message` fails with `target_hidden`. Archived seats fail with `target_archived`. Unknown ids, kind mismatch, and out-of-graph targets return those error codes.

## Delivery

`send_message(agent_id, content)` appends a **user** turn on the target’s `chat_store` thread (`name` = sender) plus hop chrome `Message from {sender}`. Scoped to the caller’s user key (no cross-tenant). Opening that agent in Chat shows the message.

Tool logs run through `redact_sensitive_data`. Key-shaped payloads are not stored raw.

## ACL (hooks now, UI later)

Effective discoverability = team ∪ edges ∩ (whitelist / ¬blacklist), with Support/CoS default allow-all. Entry kinds: agent, team, role. Full allow/deny UI is [#573](https://github.com/matthewhand/open-swarm/issues/573).

## Code

`swarm.core.agent_mailbox`, `swarm.core.agent_relationships` (`agent_relationships.json` next to `team_rosters.json`). GitHub-only docs. No Neon. No secrets.
