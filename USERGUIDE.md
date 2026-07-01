# Open Swarm User Guide: `swarm-cli`

This guide is the task-oriented reference for the `swarm-cli` command-line
tool: managing blueprints and configuration in your Open Swarm environment.
It assumes you have installed `open-swarm` (from source: `uv sync
--all-extras`; from PyPI: `pip install open-swarm`). Every command documented
here is verified against `swarm-cli --help`.

> **Documentation map:** this file is the `swarm-cli` reference;
> [docs/USER_JOURNEY.md](./docs/USER_JOURNEY.md) is the end-to-end story
> (install → CLI → web UI → API) with real transcripts;
> [docs/GUIDED_TOUR.md](./docs/GUIDED_TOUR.md) is the screenshot tour of the
> web UI; [docs/SCREENSHOTS.md](./docs/SCREENSHOTS.md) is the capture
> registry.

---

## Overview

`swarm-cli` currently ships **four commands**:

| Command | Purpose |
| --- | --- |
| `list` | List installed executables, bundled blueprints, and user blueprint sources |
| `install-executable <name>` | Build a standalone executable for a blueprint (PyInstaller) |
| `install <name>` | Alias for `install-executable` |
| `launch <name> [options]` | Run an installed blueprint executable, optionally with pre/listen/post hooks |

> **Note:** older versions of this guide documented `add`, `delete`,
> `uninstall`, and `config` subcommands. Those are **not in the current CLI**
> (restoring or formally retiring them is tracked in
> [ROADMAP.md](./ROADMAP.md)). The equivalent manual workflows are described
> below: copy blueprint sources into the user blueprints directory, and edit
> `swarm_config.json` directly.

Run `swarm-cli --help` or `swarm-cli <command> --help` for the authoritative
usage text.

---

## File Locations (XDG Compliance)

`swarm-cli` follows the XDG Base Directory Specification (via
`platformdirs`), keeping your home directory clean. Linux paths shown;
macOS/Windows vary per `platformdirs` conventions.

*   **Configuration File (`swarm_config.json`):**
    *   **Location:** searched upward from the current directory first, then
        `~/.config/swarm/swarm_config.json` (or `$XDG_CONFIG_HOME/swarm/`).
        Override with `SWARM_CONFIG_PATH`.
    *   **Purpose:** stores LLM profiles and MCP server definitions.
    *   **Creation:** create it yourself (see
        [Managing Configuration](#managing-configuration) below) — it is not
        auto-created.
*   **User Blueprint Sources:**
    *   **Location:** `~/.local/share/swarm/blueprints/` (or
        `$XDG_DATA_HOME/swarm/blueprints/`; override the data dir with
        `SWARM_USER_DATA_DIR`).
    *   **Purpose:** blueprint source folders you add manually; `install` and
        `list` pick them up from here.
*   **Installed CLI Binaries (Executables):**
    *   **Location:** `~/.local/share/swarm/bin/`
    *   **Purpose:** standalone executables created by `swarm-cli install`.
    *   **Note:** add this directory to your `PATH` to run installed
        blueprints directly by name.
*   **Build Cache (PyInstaller):**
    *   **Location:** `~/.cache/swarm/`
    *   **Purpose:** temporary files generated during `swarm-cli install`.

---

## Managing Blueprints

### Listing Blueprints (`swarm-cli list`)

Shows three groups: installed executables, blueprints bundled with the
package, and user blueprint sources.

```bash
swarm-cli list                # all three groups
swarm-cli list --installed    # -i: only installed executables
swarm-cli list --available    # -a: only blueprint source directories
```

Example output (fresh environment):

```text
--- Installed Blueprint Executables (in /home/user/.local/share/swarm/bin) ---
(No installed blueprint executables found in /home/user/.local/share/swarm/bin)
Try 'swarm-cli install-executable <blueprint_name>' or see 'swarm-cli list --available'.

--- Bundled Blueprints (available from package) ---
- jeeves (entry: blueprint_jeeves.py)
- codey (entry: blueprint_codey.py)
- suggestion (entry: suggestion_cli.py)
...

--- User Blueprint Sources (in /home/user/.local/share/swarm/blueprints) ---
(No user blueprint sources found in /home/user/.local/share/swarm/blueprints)
You can add blueprints by copying their source folders to this directory.
```

### Adding Your Own Blueprints (manual copy)

There is no `add` command in the current CLI; copy the blueprint's source
folder into the user blueprints directory instead:

```bash
mkdir -p ~/.local/share/swarm/blueprints
cp -r ./my_blueprints/cool_agent ~/.local/share/swarm/blueprints/cool_agent
swarm-cli list --available    # it now appears as a user blueprint source
```

### Installing Blueprints as Commands (`swarm-cli install`)

Builds a standalone executable (PyInstaller) from a user blueprint source or
a bundled blueprint, and places it in `~/.local/share/swarm/bin/`.
`install` and `install-executable` are the same command.

```bash
swarm-cli install jeeves
# Installing blueprint 'jeeves' as executable...
#   Source: .../src/swarm/blueprints/jeeves
#   Entry Point: blueprint_jeeves.py
#   Output Executable: /home/user/.local/share/swarm/bin/jeeves
```

*   **After installation:** (with `~/.local/share/swarm/bin/` in your `PATH`)
    ```bash
    jeeves --message "Now I'm a command!"
    ```
*   **Fast test-mode install:** with `SWARM_TEST_MODE=1`, `install` writes a
    quick shell shim instead of compiling a PyInstaller binary, and launched
    blueprints emit deterministic canned output — useful for trying the CLI
    without an API key (see
    [docs/USER_JOURNEY.md](./docs/USER_JOURNEY.md#try-a-blueprint-without-an-api-key-swarm_test_mode)).

### Launching Blueprints (`swarm-cli launch`)

Runs a **previously installed** blueprint executable from
`~/.local/share/swarm/bin/`. If the executable is missing, `launch` exits
with an error telling you to `swarm-cli install-executable <name>` first.

*   **Single message run:**
    ```bash
    swarm-cli launch jeeves --message "What time is it?"
    ```
*   **Interactive mode:** (omit `--message`; behavior depends on the
    blueprint)
    ```bash
    swarm-cli launch jeeves
    ```
*   **Hooks — chain other installed blueprints around the main run:**
    ```bash
    swarm-cli launch codey \
      --pre lint_team \
      --listen observer \
      --post verifier \
      --message "Refactor the parser"
    ```
    *   `--pre` / `-p`: comma-separated blueprint names to run **before** the
        main task
    *   `--listen` / `-L`: comma-separated blueprint names to invoke **on the
        same inputs**
    *   `--post` / `-o`: comma-separated blueprint names to run **after** the
        main task

    Hook blueprints must also be installed executables; missing ones are
    skipped with a warning.

These are the only `launch` options. To select a different LLM profile, set `llm_profile` in your `swarm_config.json` (or per-blueprint in the `blueprints` section). For the absolute simplest case (no config file), just export `OPENAI_API_KEY` + `OPENAI_BASE_URL` (the app will synthesize a minimal "default" profile). Blueprint-specific flags can be passed when running the blueprint executable directly.

### Removing Blueprints (manual)

There are no `delete`/`uninstall` commands in the current CLI. Remove files
directly:

```bash
rm ~/.local/share/swarm/bin/jeeves                      # installed executable
rm -r ~/.local/share/swarm/blueprints/cool_agent        # user blueprint source
```

---

## Managing Configuration

`swarm_config.json` holds your LLM profiles and MCP server definitions. The
current CLI has **no `config` subcommands** — create and edit the file with
your editor. The loader searches upward from the current directory, then
falls back to `~/.config/swarm/swarm_config.json`; `SWARM_CONFIG_PATH`
overrides both.

### Example configuration

```json
{
    "llm": {
        "default": {
            "provider": "openai",
            "model": "qwen3.5",
            "base_url": "${LITELLM_BASE_URL}",
            "api_key": "${LITELLM_API_KEY}",
            "description": "Default profile (OpenAI-compatible gateway). Requires LITELLM_API_KEY env var."
        },
        "ollama_example": {
            "provider": "ollama",
            "model": "llama3",
            "api_key": "ollama",
            "base_url": "http://localhost:11434",
            "description": "Example for local Ollama Llama 3 model."
        }
    },
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "${ALLOWED_PATH}"],
            "env": { "ALLOWED_PATH": "${ALLOWED_PATH}" }
        }
    },
    "settings": {
        "default_markdown_output": true
    }
}
```

**Important:** placeholders like `${LITELLM_API_KEY}` are substituted from the
environment at load time. You **must** set the corresponding environment
variables — `export` them or put them in a `.env` file in your working
directory.

### Selecting an LLM profile

The active profile is resolved from your `swarm_config.json` (see `_resolve_llm_profile` logic and the `llm_profile` key). 

For the simplest possible setup with no `swarm_config.json` at all, just set:

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1   # or your gateway
```

A minimal `default` profile using `gpt-5.5` will be synthesized automatically.

See the example in `swarm_config.json.example` and [CONFIGURATION.md](./CONFIGURATION.md) for advanced multi-profile setups (different models/endpoints per "role").

---

## Troubleshooting

*   **Command Not Found (`swarm-cli` or installed blueprint):**
    *   Ensure the install completed (`uv sync --all-extras` from source, or
        `pip install open-swarm`); with `uv`, prefix commands with `uv run`.
    *   Verify Python's user script directory (e.g. `~/.local/bin`) is in
        your `PATH`.
    *   For installed blueprints, check that `~/.local/share/swarm/bin/` is
        also in your `PATH`.
*   **`Blueprint executable not found` from `swarm-cli launch`:** `launch`
    only runs installed executables — run
    `swarm-cli install <name>` first, and check spelling against
    `swarm-cli list`.
*   **Configuration Errors:**
    *   Verify your `swarm_config.json` exists (working directory or
        `~/.config/swarm/`) and is valid JSON.
    *   Ensure environment variables referenced in the config (like
        `LITELLM_API_KEY`) are set in your current shell session.
*   **Permissions:** ensure you have read/write permission for the XDG
    directories (`~/.config/swarm`, `~/.local/share/swarm`,
    `~/.cache/swarm`).
