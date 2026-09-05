# Team rosters (composition contract)

REQ-20. A **team roster** is the composition abstraction: a named roster of
members that can see/talk via openai-agents `handoff` / `as_tool`.

This is **not** the Django `/teams/` LLM-profile alias admin.

## Live vs intended

| Store / surface | What it is | Schema |
|---|---|---|
| **Live aliases** — `teams.json`, `/v1/teams/`, Django `/teams/` (Launcher, Admin, Swarm Creator) | Named **LLM-profile alias** (`id` / `description` / `llm_profile`) exposed as a model id via `DynamicTeamBlueprint` | Unchanged. Do not overwrite. |
| **Intended composition** — `team_rosters.json`, `/v1/team-rosters/`, SPA `+` overlay | Roster of members (`api` from a blueprint, `cli`, or `remote` harness) plus per-team wire toggles | `members[{id, kind, role, source}]` + `wires{handoff, as_tool}` |

Django `/teams/` remains aliases. The SPA does **not** add a top-nav Teams tab
or restore Home/Chat chrome. Entry is the chat-header **Compose team** `+`
control (DaisyUI `modal-end` Settings sheet is not in this tree).

## File

`team_rosters.json` lives next to `teams.json` under the user config dir
(XDG `…/swarm/`). Example:

```json
{
  "research-squad": {
    "id": "research-squad",
    "name": "Research Squad",
    "members": [
      {"id": "jeeves", "kind": "api", "role": "default", "source": "blueprint:jeeves"},
      {"id": "grok", "kind": "cli", "role": "skeptic", "source": "cli:grok"},
      {"id": "acp", "kind": "remote", "role": "support", "source": "placeholder:remote:acp"}
    ],
    "wires": {"handoff": true, "as_tool": true}
  }
}
```

- `kind`: `api` | `cli` | `remote`
- `role`: `support` | `gate` | `skeptic` | `default`
- `wires.handoff` / `wires.as_tool`: default **both on**. These are roster
  toggles, not a per-seat edge list. Forced / circular **handoff graphs**
  live on API blueprints (`sdlc_handoff`); CLI/remote members stay native.
  See [openai-agents-handoff-graphs](./examples/openai-agents-handoff-graphs/README.md).
- Gate runtime (REQ-314) is **not** in this tree. Unwired gate = all tools
  approved (UI copy only). Do not reimplement a gate here.

Remotes and missing CLIs are **placeholders**. They are not Blueprint classes.

## API

- `GET/POST /v1/team-rosters/` — list / create
- `GET/PUT/DELETE /v1/team-rosters/<id>/` — read / replace / delete
- Optional `blueprint_id` on a roster assigns a catalog recipe. `GET /v1/blueprints/<id>/personas`
  returns the declared openai-agents roster (static parse; never exec).
- `GET /v1/team-agents/` — available palette (API from blueprints, CLI catalog
  or placeholders, remote placeholders)

Auth matches `/v1/teams/`: `HasValidTokenOrSession` when API auth is on.

## UI

First-launch overlay: two panes. Left = grey dashed drop zone (“drop agents
here”). Right = available agents (API / CLI / remote), each row HTML5-draggable.
Context menu Add/Remove for keyboard / pointer a11y. No `@dnd-kit`.
