# Operating Swarm

Operating Swarm runs Python agent workflows and connects model APIs, local agent CLIs and external harnesses through a shared service. Use its terminal commands, OpenAI-style HTTP endpoints or React WebUI.

**Experimental alpha.** Source is ahead of the published package. A model-and-tool workflow has been exercised through the CLI, API and WebUI. This does not establish that every bundled recipe or remote integration works. See the dated [verification report](docs/verification-2026-10-20.md).

Operating Swarm began as **Open Swarm**, a derivative of OpenAI's experimental [Swarm](https://github.com/openai/swarm). It now uses the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) for agents, tools and handoffs. This is an independent project, not an OpenAI product. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Architecture

The Python import is `swarm`. Django provides configuration, authentication and persisted conversations. Blueprint classes implement workflows: `ApiKindBase` runs an Agents SDK graph, CLI adapters launch host processes, and remote adapters call an external harness's protocol. Team rosters compose these capabilities. The API and WebUI share this backend.

Blueprints run through the CLI and API; they do not ship separate webpages. The WebUI is shared product chrome.

Terminology is still being consolidated: code uses `api`, `cli`, `remote` and `team` bases, while older documents call programmatic workflows “blueprints.” A model profile selects an inference endpoint. Wrapping a CLI or remote does not inject the SDK into that external process. Context transfer and resume depend on the adapter; universal cross-harness continuity is not established.

## Install current source

Use **Python 3.12 or 3.13**, [uv](https://docs.astral.sh/uv/), and **Node.js 24+** for the WebUI. Linux/WSL is the reference environment for the full backend suite. The local workflow below was also exercised on Windows. Bash syntax:

```bash
git clone https://github.com/matthewhand/operating-swarm.git
cd operating-swarm
uv sync --locked --extra tui
export SWARM_CONFIG_DIR="$PWD/.runtime/config"
export SWARM_USER_DATA_DIR="$PWD/.runtime/data"
export SWARM_CONFIG_PATH="$PWD/.runtime/swarm_config.json"
mkdir -p "$SWARM_CONFIG_DIR"
cp docs/examples/inventory-config.json "$SWARM_CONFIG_PATH"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="YOUR_MODEL_ID"
read -rsp 'Model API key: ' OPENAI_API_KEY; echo
export OPENAI_API_KEY
export API_AUTH_TOKEN="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DJANGO_DEBUG=true
```

Choose a model accessible to your account. For an already running Ollama server, use `OPENAI_BASE_URL=http://127.0.0.1:11434/v1`, an installed tool-capable model's exact name, and `OPENAI_API_KEY=ollama` (a local placeholder). Support varies by model. This review used an existing OpenAI-compatible gateway; discovering an Ollama model was not a completed Ollama workflow test.

PowerShell environment setup after cloning and syncing:

```powershell
$env:SWARM_CONFIG_DIR = "$PWD/.runtime/config"
$env:SWARM_USER_DATA_DIR = "$PWD/.runtime/data"
$env:SWARM_CONFIG_PATH = "$PWD/.runtime/swarm_config.json"
New-Item -ItemType Directory -Force $env:SWARM_CONFIG_DIR | Out-Null
Copy-Item docs/examples/inventory-config.json $env:SWARM_CONFIG_PATH
$env:OPENAI_BASE_URL = 'https://api.openai.com/v1'
$env:OPENAI_MODEL = 'YOUR_MODEL_ID'
$key = Read-Host 'Model API key' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $key).Password
$env:API_AUTH_TOKEN = uv run python -c 'import secrets; print(secrets.token_urlsafe(32))'
$env:DJANGO_DEBUG = 'true'
```

All state stays in Git-ignored `.runtime/`. These are localhost development settings. Shared deployment needs production Django settings, a secret key, allowed hosts, authentication and a database plan: [deployment](docs/DEPLOYMENT.md), [auth](docs/AUTH.md), [databases](docs/DATABASE.md). Native development defaults to SQLite; Compose provisions Postgres. Docker, Pinokio and desktop installers were not exercised in this review.

## A practical model-and-tool workflow

The bundled `inventory_demo` calculates a reorder plan from fictional stock. Its `stock_report` tool computes quantities and cost locally; the model calls it and explains the result. It does not place orders or require shell access.

```bash
uv run os-cli launch inventory_demo --message "What should we reorder, and what will it cost?"
```

Expected: **9 notebooks (36) and 6 folders (18), total 54**. A plausible answer alone is not tool-execution evidence. The WebUI displays `stock_report` when it completes. [Blueprint source](src/swarm/blueprints/inventory_demo/blueprint_inventory_demo.py).

`os-cli` and `os` are the same command. Bare invocation opens the optional TUI (`--extra tui`). `os-api` starts the server. There is no `os-webui` executable: the server serves the built React application.

## API and WebUI

From the same configured terminal:

```bash
uv run python -m django migrate --settings=swarm.settings --noinput
npm --prefix webui/frontend ci
npm --prefix webui/frontend run build
uv run os-api --host 127.0.0.1 --port 8000
```

Open [localhost:8000](http://127.0.0.1:8000), select `inventory_demo`, and ask the reorder question. The local development preview establishes a browser session; websocket authentication uses a session cookie, not an HTTP bearer header. Follow [AUTH.md](docs/AUTH.md) for shared deployment.

In another terminal with the same `API_AUTH_TOKEN`:

```bash
curl -fsS http://127.0.0.1:8000/v1/models \
  -H "Authorization: Bearer $API_AUTH_TOKEN"
curl -fsS http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"inventory_demo","messages":[{"role":"user","content":"What should we reorder, and what will it cost?"}]}'
```

`model` selects a Swarm recipe/seat, not the upstream model. Chat completions supports SSE with `stream:true`. `/v1/responses` accepts `model` and `input`. These are compatibility surfaces, not full OpenAI API parity. Unknown models return 404; malformed messages return 400. With a token configured, missing/incorrect HTTP credentials are rejected. Stop with Ctrl+C; preserve operator data when resetting a demo.

## Integration limits

Adapters require a separately installed, reachable and authenticated service. `os-cli remotes` lists configured instances. [Remote protocols](docs/REMOTE_HARNESSES.md). Health, listing and completed inference are different verification levels.

| Integration | Review finding |
|---|---|
| AnythingLLM, OpenMousBot, TrueForge | Configured instances answered health/list calls. Send results are in the report. |
| Hermes | Primary passed health, discovery and a real model turn in the optional live suite on 21 October; secondary failed. An earlier primary turn timed out. |
| Rakazo, Herdr, nested Swarm | Configured targets unavailable; no working inference claim. |
| Open WebUI | Service alive; listing rejected credentials (401). Another instance was down. |
| Flowise, n8n, Tencent Octop, OpenMuse | No configured instance exercised. Tests/catalog entries are not live proof. |
| Letta | Dedicated remote removed. An old local config still contains it; API-profile compatibility not verified here. |

MCP client/server modes, memory backends, sandbox browsers, desktop/tray surfaces, TUI interaction, all CLI providers, cross-kind context transfer and installers have not all been exercised. Historical GIFs and design diagrams are not live evidence. See [FEATURE_STATUS.md](FEATURE_STATUS.md) and the [verification report](docs/verification-2026-10-20.md).

## Package and release status

| Source | Meaning |
|---|---|
| This tree: `os-core 0.6.0a1` | Unreleased alpha preparation. Clone for the demonstrated workflow/WebUI. |
| GitHub Release `v0.5.4` (19 June 2026) | Historical title: “django_chat resolves its LLM profile”; predates the current UI and architecture. |
| PyPI `open-swarm==0.5.4` | Historical package, Python >=3.10; not current `os-core`. |
| PyPI `os-core` | Not available when checked on 20 October 2026. |
| `packaging/open-swarm-alias` | Unpublished migration alias; publish only after its `os-core` dependency is available. |

Main no longer reuses 0.5.4. The publish workflow recognizes this repository name and checks tag/version consistency. Index upload still needs publisher credentials or trusted-publisher setup and a deliberate release. The Python wheel does not bundle the React build: use a source checkout for WebUI. Merging a PR does not publish to PyPI. Publication work is listed in the report.

## Development

```bash
uv sync --locked --extra dev --extra test
uv run pytest tests/core/ tests/views/ -x -q
npm --prefix webui/frontend test
npm --prefix webui/frontend run type-check
npm --prefix webui/frontend run build
```

Some backend tests use Unix executable scripts; use Linux/WSL for the full gate. Windows regressions separately cover config isolation, process locks, safe failures and CLI exit status. [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) define contribution requirements.

Optional real-service checks live in [tests/live](tests/live/README.md). Set private `SWARM_LIVE_<INSTANCE>_URL` and credential variables on your development host, then run `uv run pytest tests/live -m live_remote --no-cov -q --tb=no --show-capture=no`. Unconfigured instances skip; configured failures fail. The summary distinguishes health/discovery from a completed model answer and counts working integrations. OMB, Rakazo and AnythingLLM need dedicated test targets.

Optional [physical-device UI checks](docs/verification/physical-device-ui.md) use explicit device-browser URL variables and skip when unconfigured. Android Chrome was exercised on a real phone; native ChromeOS rendering remains unverified because the available ADB connection only exposed its Android runtime.

Further reference: [minimal workflow configuration](docs/examples/inventory-config.json), [full example configuration](swarm_config.example.json), [configuration guide](CONFIGURATION.md), [developer map](docs/DEVELOPER.md), and [handoff graph examples](docs/examples/openai-agents-handoff-graphs/README.md).

Historical storyboards and GIFs remain in [ANNOUNCE](docs/ANNOUNCE.md) and [the showoff guide](docs/SHOWOFF_DEMO_AGENTS.md). They are historical media, not current integration verification.
