# TODO

> **Project status and priorities now live in [ROADMAP.md](ROADMAP.md).**
> This file previously held a large phase-based plan; most of it was either
> completed, superseded, or promoted to the roadmap. Only genuinely-current,
> fine-grained engineering tasks are kept below. Add new strategic items to
> `ROADMAP.md`, not here.

## CLI blueprint lifecycle (gaps in `swarm-cli`)

- [ ] `swarm-cli compile <blueprint_name>` — PyInstaller compile of an installed blueprint to `get_user_bin_dir()` (see `src/swarm/core/build_launchers.py` for the invocation pattern), plus tests.
- [ ] `swarm-cli launch` should prefer the compiled binary in `get_user_bin_dir()` and fall back to (or offer to compile from) installed source.
- [ ] `delete`/`uninstall` should handle removing source, compiled binary, or both.
- [ ] `swarm-cli session list` / `session show` to inspect past sessions in `~/.cache/swarm/sessions`.

## Blueprint metadata

- [ ] Add `abbreviation: Optional[str]` to `BlueprintBase` metadata and extract it in `blueprint_discovery.py`.
- [ ] Verify/document docstring fallback for `description` metadata.
- [ ] Remove any remaining legacy `metadata.json` files from blueprints.

## Tests still missing (config/core)

- [ ] Per-blueprint and per-agent model override logic.
- [ ] Fallback to default model/profile with warning when requested profile is missing.
- [ ] MCP server config add/remove/parse.
- [ ] Redaction of secrets in logs and config dumps.
- [ ] CRUD tests for `/v1/blueprints/custom/` endpoints (create, read, update, delete, filters).

## Docs

- [ ] USERGUIDE.md: document XDG file locations and full `swarm-cli` command reference with examples.
- [ ] DEVELOPMENT.md: document blueprint-management internals, PyInstaller usage, `abbreviation` metadata, XDG path management.
- [ ] Document `--pre`, `--listen`, `--post` hook flags and slash-command REPL behavior.

---

Superseded content (web UI, MCP server mode, SAML IdP, marketplace, blueprint
rationalization, spinner/config-loader consolidation, dual-CLI split) is
tracked in [ROADMAP.md](ROADMAP.md).
