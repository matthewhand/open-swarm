# Technical Guide: BlueprintBase

How to define and run blueprints against the live `BlueprintBase` / discovery /
sandbox stack. Prefer this over older notes that pointed at
`swarm.extensions.blueprint` (that package has been removed).

## Core concept

A blueprint is a coded team the framework discovers and runs. Blueprints are
**CLI/API only** — they do not ship a webpage or a second chat shell. The
Grok-like WebUI (`/` + `/chat`) is the product chrome. New work should
subclass a **kind base** (`ApiKindBase` / `CliKindBase` / `RemoteKindBase` —
[ADR-005](../adr/005-kind-bases.md)), not raw `BlueprintBase` in the common
case. Each recipe still needs an async `run` loop. The framework loads config, resolves LLM profiles, discovers
blueprint modules under known roots, and exposes them via `swarm-cli` and the
API (`/v1/models`, chat completions). Do not add a blueprint Django app,
`templates/`, or `kind=webui`.

## Key components

### 1. `BlueprintBase` (abstract base)

**Location:** `src/swarm/core/blueprint_base.py`

Import:

```python
from swarm.core.blueprint_base import BlueprintBase
```

- **Inheritance:** Subclass `BlueprintBase`.
- **Required method:** `async def run(self, messages: list[dict], **kwargs) -> AsyncGenerator[dict, None]`. This is the only `@abstractmethod`.
- **`metadata`:** Conventionally a class-level `ClassVar[dict]` (name/title/description/version, optional `required_mcp_servers`, `env_vars`, `inference_profile`, …). Discovery reads it; it is not an abstract method.
- **`__init__(blueprint_id, config=None, config_path=None, **kwargs)`:** Stores id, loads/merges config (Django AppConfig → explicit path → `find_config_file()` → optional `OPENAI_API_KEY` bootstrap), applies `${VAR}` substitution, optional memory backend (no-op unless configured).
- **`get_llm_profile(profile_name)`:** Resolved profile via `config_loader` (API keys / env overrides).
- **`make_agent(...)`:** Helper to build an `agents.Agent` with tools / MCP servers / optional inference-profile suggestion.
- **Markdown:** Controlled by blueprint/`settings` config keys (`output_markdown` / `default_markdown_output`), exposed as `should_output_markdown`.

There is no framework `create_agents` / `_run_non_interactive` / classmethod
`main()` contract on the current base class. Individual blueprints may still
ship a `__main__` block for direct execution.

### 2. Configuration (`swarm_config.json`)

- **`.env` / process env:** Secrets (`OPENAI_API_KEY`, MCP keys, …).
- **`swarm_config.json`:** Located via `SWARM_CONFIG_PATH` → XDG → CWD (see `CONFIGURATION.md` / `SWARM_CONFIG.md`). Typical sections: `"llm"`, `"blueprints"`, `"mcpServers"`, `"settings"`.
- **CLI:** Prefer `swarm-cli launch <name> [--message "..."]` (and related `swarm-cli list` / `install`). Legacy `--instruction` / `swarm-cli run` examples in older docs are superseded; some blueprint `__main__` blocks still accept `--instruction`.

### 3. Agents & tools

- Use `agents.Agent`, `@agents.function_tool`, and agent-as-tool patterns as needed.
- Profile names in config map to models; env overrides such as `LITELLM_MODEL` / `LITELLM_BASE_URL` can reshape the client.
- Structured output: pass `output_type=...` where the openai-agents `Agent` API supports it (see the `suggestion` blueprint).
- List env vars the blueprint itself needs in `metadata["env_vars"]` when relevant; LLM/MCP secrets belong in env / config, not hard-coded.

### 4. Discovery

**Location:** `src/swarm/core/blueprint_discovery.py`

- `discover_blueprints(blueprint_dir, namespace=None, *, sandboxed=None)` walks **subdirectories** of `blueprint_dir` and loads `blueprint_<dir>.py` or `<dir>.py` that define a `BlueprintBase` subclass.
- Return value: `dict[str, DiscoveredBlueprintInfo]` keyed primarily by directory name (plus any in-module aliases the loader registers).
- `discover_all_blueprints(blueprint_dir, extra_dirs=None)` = bundled discovery + `merge_community_blueprints` + `apply_blueprint_aliases` (canonical `swarm_*` aliases for several `cli_*` pattern blueprints).
- Bundled root: `src/swarm/blueprints` (Django `BLUEPRINT_DIRECTORY`).
- Extra roots: `BLUEPRINT_EXTRA_DIRS` from settings — user data blueprints dir **only when** `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY=true` (default **off**), plus paths in `SWARM_BLUEPRINT_PATHS` (os.pathsep-separated). Bundled names win on collision.
- Empty leftover directories (no `.py` entry module) are skipped with a warning — e.g. dirs that retain only `__pycache__` after source removal.

### 5. User / community sandbox

**Location:** `src/swarm/core/blueprint_sandbox.py`

- Bundled tree under `src/swarm/blueprints` is trusted and **not** AST-scanned.
- User/community roots run `assert_safe_blueprint_source` before `exec_module` when the sandbox is enabled (default). Creator save paths also validate through the same gate.
- Default on; opt out with `SWARM_USER_BLUEPRINT_SANDBOX=false`.
- Auto-enable when `sandboxed is None` and the scan root is under `get_user_blueprints_dir()`; `merge_community_blueprints` passes `sandboxed=True` for extra roots.
- The gate bans obvious escapes (e.g. `subprocess`, dynamic import/`runpy`, write-mode `open` / `Path.open`, selected network clients). It is a static filter, not a full OS sandbox.

### 6. Running a blueprint

```bash
uv run swarm-cli list
uv run swarm-cli launch <name> --message "..."
```

Direct module execution still exists for some blueprints
(`uv run python src/swarm/blueprints/<name>/blueprint_<name>.py --instruction "..."`),
but CLI launch is the supported path for docs and tests.

## Currently discoverable bundled blueprints

As of a live `discover_blueprints` pass over `src/swarm/blueprints`, loadable
directory/alias keys include (aliases indented conceptually under their source):

| Directory / key | Notes |
|-----------------|--------|
| `chatbot` | Minimal single-agent REST template |
| `chucks_angels` | Themed coordination |
| `cli_agent` | Single external CLI behind the API |
| `cli_ensemble`, `cli_fusion` | CLI consensus / fusion variants (distinct modules) |
| `cli_map`, `cli_orchestrator`, `cli_pipeline`, `cli_planner`, `cli_recurse`, `cli_roundtable` | Orchestration patterns (`swarm_*` aliases applied by `discover_all_blueprints`) |
| `codey` | Coding workflow |
| `dynamic_team` (alias `dynamic-team`) | Dynamic team from config profile |
| `fs_introspect` | Filesystem introspection demo |
| `gawd` | Present and discovered |
| `geese` | Multi-agent research/write team |
| `hybrid_moa` (aliases `moa_hybrid`, `hybrid-consensus`) | Hybrid MoA |
| `hybrid_swarm`, `hybrid_team` | REST + CLI hybrids |
| `jeeves` | Search / home-automation themed |
| `moa` (aliases `ensemble`, `fusion`, `mixture_of_agents`) | Mixture-of-agents |
| `moa_orchestrator` (aliases `moa-orch`, `agents_moa`) | MoA orchestrator |
| `persona_council` | Persona panel |
| `poets` | Collaborative writing |
| `rue_code` | Code execution / filesystem workflow |
| `stewie` | MCP WordPress-oriented demo (`blueprint_stewie.py`) |
| `suggestion` | Structured `output_type` demo |
| `whiskeytango_foxtrot` | Hierarchical REST team |
| `zeus` | Large software-dev coordination |

Directories that exist on disk but have **no** loadable `blueprint_*.py` (skipped
at discovery — often `__pycache__`-only leftovers) include: `digitalbutlers`,
`echocraft`, `family_ties`, `flock`, `mcp_demo`, `mission_improbable`,
`monkai_magic`, `nebula_shellz`, `omniplex`, `whinge_surf`. `gaggle` is gone
entirely. Do not document those as runnable until sources are restored.

For feature-matrix status and curated demos, see `docs/BLUEPRINT_LIBRARY.md`
(treat any row that names a deleted blueprint as stale until that doc is
updated separately).

## Tests

Pytest is the supported suite (`uv run pytest`, see `CONTRIBUTING.md` /
`DEVELOPMENT.md`). Core coverage includes
`tests/core/test_blueprint_base.py`,
`tests/core/test_blueprint_discovery_*.py`, sandbox/API tests under
`tests/api/` and `tests/unit/`. Do **not** ignore pytest based on older
environment-mismatch notes in this guide.

## Related docs

- `docs/DEVELOPER_GUIDE.md` — CLI surface and metadata conventions
- `docs/BLUEPRINT_LIBRARY.md` — library menu / permutation matrix
- `CONFIGURATION.md` — `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY`, `SWARM_USER_BLUEPRINT_SANDBOX`, `SWARM_BLUEPRINT_PATHS`
- `src/swarm/blueprints/README.md` — in-tree blueprint overview (may lag discovery)
