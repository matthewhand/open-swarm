# REQ-14

Intent: the Agent Router sidebar groups visible agents by run type `api` / `cli` / `remote` (not Orchestration / Specialists / Tools / Blueprints). Selecting an agent shows only that type's header extra. Favourites stay a top pin grid; Hidden stays Hidden.

Success:
1. Sidebar sections are **API**, **CLI**, **Remote** (labels from `agent_type` / kind). Starters land under their type: API agent → API; CLI agent → CLI; Remote agent → Remote.
2. Header extras are exclusive: CLI selected → CLI model dropdown (catalog + custom). API → blueprint dropdown. Remote → remote member dropdown. Never all three at once.
3. Persist grouping is derived from type, not a new storage key. Custom drag-to-section may still exist, but default grouping is by type.
4. Django chrome sidepane matches if it lists agents in groups.
5. Tests cover frontend grouping and AgentRouterPage type-gated dropdowns.

Constraints: No extra UI frameworks. Do not invent Rakazo/OMB ports. Hide-all keeps the three typed starters (REQ-6). Match existing daisyUI.

Related: Hybrid Team must not auto-use host `claude` as orchestrator — operator default is LiteLLM + grok (honesty, not grouping).

Owner: open-swarm engineer.
