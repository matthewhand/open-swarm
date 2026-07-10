import importlib.resources as pkg_resources
import os
import subprocess
from pathlib import Path

import typer

import swarm
from swarm.core import paths

paths.ensure_swarm_directories_exist()

# Workaround for Click/Typer signature mismatch in Parameter.make_metavar
try:
    import click
    _orig_mm = click.core.Parameter.make_metavar
    def _mm_shim(self, *args, **kwargs):
        """Compat shim: supports both (self) and (self, ctx)."""
        try:
            return _orig_mm(self, *args, **kwargs)
        except TypeError:
            try:
                return _orig_mm(self)
            except Exception:
                # Fallback: derive from name/metavar
                mv = getattr(self, 'metavar', None)
                if mv:
                    return mv
                name = getattr(self, 'name', None)
                return (name or 'VALUE').upper()
    click.core.Parameter.make_metavar = _mm_shim  # type: ignore[assignment]
except Exception:
    pass

app = typer.Typer(help="Swarm CLI tool", add_completion=False)


def find_entry_point(blueprint_dir: Path) -> str | None:
    """Find entry point with deterministic priority for CLI compatibility.
    Prefers {name}_cli.py, then {name}.py, then blueprint_{name}.py.
    """
    name = blueprint_dir.name
    candidates = [
        f"{name}_cli.py",
        f"{name}.py",
        f"blueprint_{name}.py",
    ]
    for cand in candidates:
        p = blueprint_dir / cand
        if p.is_file() and not p.name.startswith("_"):
            return p.name
    for item in blueprint_dir.glob("*.py"):
        if item.is_file() and not item.name.startswith("_"):
            return item.name
    return None


@app.command(name="install-executable")
def install_executable(
    blueprint_name: str = typer.Argument(..., help="Name of the blueprint directory to install as an executable."),
):
    source_dir_user = paths.get_user_blueprints_dir() / blueprint_name
    if source_dir_user.is_dir():
        source_dir = source_dir_user
    else:
        bundled_base = Path(__file__).resolve().parent.parent / "blueprints"
        bundled_dir = bundled_base / blueprint_name
        if bundled_dir.is_dir():
            source_dir = bundled_dir
            typer.echo(f"Using bundled blueprint directory: {bundled_dir}")
        else:
            typer.echo(
                f"Error: Blueprint '{blueprint_name}' not found in user blueprints directory ({paths.get_user_blueprints_dir()}) or bundled blueprints."
            )
            raise typer.Exit(code=1)

    entry_point = find_entry_point(source_dir)
    if not entry_point:
        typer.echo(f"Error: Could not find entry point script in {source_dir}")
        raise typer.Exit(code=1)

    entry_point_path = source_dir / entry_point
    output_bin_name = blueprint_name
    output_bin_dir = paths.get_user_bin_dir()
    output_bin_path = output_bin_dir / output_bin_name
    pyinstaller_workpath = paths.get_user_cache_dir_for_swarm() / "build" / blueprint_name
    pyinstaller_specpath = paths.get_user_cache_dir_for_swarm() / "specs"
    pyinstaller_workpath.mkdir(parents=True, exist_ok=True)
    (paths.get_user_cache_dir_for_swarm() / "specs").mkdir(parents=True, exist_ok=True)

    typer.echo(f"Installing blueprint '{blueprint_name}' as executable...")
    typer.echo(f"  Source: {source_dir}")
    typer.echo(f"  Entry Point: {entry_point}")
    typer.echo(f"  Output Executable: {output_bin_path}")

    if os.environ.get("SWARM_TEST_MODE"):
        # In test mode, skip PyInstaller and create a stub executable
        output_bin_dir.mkdir(parents=True, exist_ok=True)
        output_bin_path.write_text(f"#!/bin/sh\nexec python3 {entry_point_path} \"$@\"\n")
        output_bin_path.chmod(0o755)
        typer.echo(f"Installed stub executable: {output_bin_path}")
        raise typer.Exit(code=0)

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        str(output_bin_name),
        "--distpath",
        str(output_bin_dir),
        "--workpath",
        str(pyinstaller_workpath),
        "--specpath",
        str(pyinstaller_specpath),
        str(entry_point_path),
    ]

    if os.environ.get("SWARM_TEST_MODE"):
        shim = f"#!/usr/bin/env bash\npython3 {entry_point_path} \"$@\"\n"
        try:
            with open(output_bin_path, "w") as f:
                f.write(shim)
            os.chmod(output_bin_path, 0o755)
            typer.echo(f"Test-mode shim installed at: {output_bin_path}")
            return
        except Exception as e:
            typer.echo(f"Error installing test-mode shim: {e}")
            raise typer.Exit(code=1)

    typer.echo(f"Running PyInstaller: {' '.join(map(str, pyinstaller_cmd))}")
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        typer.echo("PyInstaller output:")
        typer.echo(result.stdout)
        typer.echo(f"Successfully installed '{blueprint_name}' to {output_bin_path}")
    except FileNotFoundError:
        typer.echo("Error: PyInstaller command not found. Is PyInstaller installed?")
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error during PyInstaller execution (Return Code: {e.returncode}):")
        typer.echo(e.stderr)
        typer.echo("Check the output above for details.")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}")
        raise typer.Exit(code=1)


@app.command(name="install")
def install(
    blueprint_name: str = typer.Argument(..., help="Name of the blueprint directory to install as an executable."),
):
    """Alias for install-executable to match README quickstart."""
    install_executable(blueprint_name)


@app.command()
def launch(
    blueprint_name: str = typer.Argument(..., help="Name of the installed blueprint executable to launch."),
    pre: str = typer.Option(None, "--pre", "-p", help="Comma-separated blueprint names to run before main task"),
    listen: str = typer.Option(None, "--listen", "-L", help="Comma-separated blueprint names to invoke on the same inputs"),
    post: str = typer.Option(None, "--post", "-o", help="Comma-separated blueprint names to run after main task"),
    message: str = typer.Option(None, "--message", help="Message or prompt to pass through to the blueprint executable"),
):
    user_bin_dir = paths.get_user_bin_dir()
    executable_path = user_bin_dir / blueprint_name
    if not executable_path.is_file() or not os.access(executable_path, os.X_OK):
        typer.echo(f"Error: Blueprint executable not found or not executable: {executable_path}")
        typer.echo(
            f"Ensure '{blueprint_name}' is installed using 'swarm-cli install-executable {blueprint_name}'."
        )
        raise typer.Exit(code=1)

    extra: list[str] = []
    if pre:
        for bp_pre_name in [bp.strip() for bp in pre.split(",") if bp.strip()]:
            pre_exe_path = user_bin_dir / bp_pre_name
            if pre_exe_path.is_file() and os.access(pre_exe_path, os.X_OK):
                cmd_pre = [str(pre_exe_path)] + extra
                typer.echo(f"Invoking pre-hook '{bp_pre_name}' with: {' '.join(cmd_pre)}")
                subprocess.run(cmd_pre)
            else:
                typer.echo(
                    f"Pre-hook executable '{bp_pre_name}' not found in {user_bin_dir}; skipping."
                )

    cmd = [str(executable_path)]
    if message is not None:
        cmd.extend(["--message", message])
    typer.echo(f"Launching '{blueprint_name}' with: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        typer.echo(f"--- {blueprint_name} Output ---")
        typer.echo(result.stdout)
        if result.stderr:
            typer.echo("--- Errors/Warnings ---")
            typer.echo(result.stderr)
        typer.echo(f"--- '{blueprint_name}' finished (Return Code: {result.returncode}) ---")
    except Exception as e:
        typer.echo(f"Error launching blueprint: {e}")
        raise typer.Exit(code=1)

    if listen:
        for listener_name in [bp.strip() for bp in listen.split(",") if bp.strip()]:
            listener_exe_path = user_bin_dir / listener_name
            if listener_exe_path.is_file() and os.access(listener_exe_path, os.X_OK):
                listener_cmd = [str(listener_exe_path)]
                typer.echo(f"Invoking listener '{listener_name}' with: {' '.join(listener_cmd)}")
                subprocess.run(listener_cmd)
            else:
                typer.echo(
                    f"Listener executable '{listener_name}' not found in {user_bin_dir}; skipping."
                )

    if post:
        for bp_post_name in [bp.strip() for bp in post.split(",") if bp.strip()]:
            post_exe_path = user_bin_dir / bp_post_name
            if post_exe_path.is_file() and os.access(post_exe_path, os.X_OK):
                cmd_post = [str(post_exe_path)]
                typer.echo(f"Invoking post-hook '{bp_post_name}' with: {' '.join(cmd_post)}")
                subprocess.run(cmd_post)
            else:
                typer.echo(
                    f"Post-hook executable '{bp_post_name}' not found in {user_bin_dir}; skipping."
                )


@app.command(name="moa")
def moa(
    question: str = typer.Argument(..., help="Question for the Mixture of Agents panel."),
    participants: str = typer.Option(
        "analyst,critic",
        "--participants",
        "-p",
        help=(
            "Comma-separated read-only seat names. With --backend grok each seat "
            "is a separate grok -p one-shot. Codex is not required."
        ),
    ),
    backend: str = typer.Option(
        "fake",
        "--backend",
        "-b",
        help=(
            "Participant backend: fake (demo/CI, default), grok (live consensus via "
            "local grok CLI), or acpx (optional multi-vendor; Codex not required)."
        ),
    ),
    fake_responses: str = typer.Option(
        None,
        "--fake-responses",
        help="For --backend fake: JSON object or name=text||name=text pairs.",
    ),
    cwd: str = typer.Option(None, "--cwd", help="Working directory for participants."),
    permission: str = typer.Option(
        "approve-reads",
        "--permission",
        help="Participant permission: approve-reads or deny-all (never approve-all).",
    ),
    timeout: float = typer.Option(300.0, "--timeout", help="Per-participant timeout seconds."),
    act: bool = typer.Option(
        False,
        "--act",
        help="After determination, let the orchestrator perform a write (never participants).",
    ),
    action: str = typer.Option(None, "--action", help="Description of orchestrator act."),
    act_write: str = typer.Option(
        None,
        "--act-write",
        help="If --act, path to write the determination markdown (orchestrator only).",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    trace: str = typer.Option(
        None,
        "--trace",
        help="Write full MoA telemetry JSON (opinions, scores, determination) to this path.",
    ),
):
    """Mixture of Agents: read-only CLI opinions → orchestrator determination.

    Participants never write. Use --act for orchestrator-owned impact after consensus.
    Primary product name is MoA (not fusion/ensemble).
    """
    import asyncio

    from swarm.core.moa.cli import format_moa_text, parse_fake_responses, run_moa_cli
    from swarm.core.moa.policy import WriteDeniedError

    names = [n.strip() for n in participants.split(",") if n.strip()]
    if not names:
        typer.echo("Error: provide at least one --participants name.", err=True)
        raise typer.Exit(code=2)

    try:
        fakes = parse_fake_responses(fake_responses) if fake_responses else None
        if backend == "fake" and not fakes:
            # Sensible demo defaults so `swarm-cli moa "…"` works out of the box.
            default_texts = [
                "Prefer a simple, well-tested approach with clear rollback.",
                "Prefer explicit validation and structured logging at the boundary.",
                "Prefer least privilege and deny-by-default for side effects.",
            ]
            fakes = {
                name: default_texts[i % len(default_texts)]
                for i, name in enumerate(names)
            }
        payload = asyncio.run(
            run_moa_cli(
                question,
                names,
                backend=backend,
                fake_responses=fakes,
                cwd=cwd,
                permission=permission,
                timeout=timeout,
                act=act,
                action=action,
                act_write_path=act_write,
                trace_path=trace,
            )
        )
    except WriteDeniedError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=5) from e
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=2) from e
    except Exception as e:
        typer.echo(f"MoA failed: {e}", err=True)
        raise typer.Exit(code=1) from e

    if as_json:
        import json

        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(format_moa_text(payload))


@app.command(name="list")
def list_blueprints(
    installed: bool = typer.Option(False, "--installed", "-i", help="List only installed blueprint executables."),
    available: bool = typer.Option(False, "--available", "-a", help="List only available blueprints (source dirs)."),
):
    list_installed = not available or installed
    list_available = not installed or available

    user_bin_dir = paths.get_user_bin_dir()
    user_blueprints_src_dir = paths.get_user_blueprints_dir()

    if list_installed:
        typer.echo(f"--- Installed Blueprint Executables (in {user_bin_dir}) ---")
        found_installed = False
        if user_bin_dir.exists():
            try:
                for item in user_bin_dir.iterdir():
                    if item.is_file() and os.access(item, os.X_OK):
                        typer.echo(f"- {item.name}")
                        found_installed = True
            except OSError as e:
                typer.echo(f"(Warning: Could not read installed directory: {e})")
        if not found_installed:
            typer.echo(f"(No installed blueprint executables found in {user_bin_dir})")
            typer.echo(
                "Try 'swarm-cli install-executable <blueprint_name>' or see 'swarm-cli list --available'."
            )
        typer.echo("")

    if list_available:
        typer.echo("--- Bundled Blueprints (available from package) ---")
        bundled_found = False
        try:
            bundled_blueprints_path = pkg_resources.files(swarm) / "blueprints"
            if bundled_blueprints_path.is_dir():
                for item in bundled_blueprints_path.iterdir():
                    if item.is_dir() and not item.name.startswith("__"):
                        entry_point = find_entry_point(item)
                        if entry_point:
                            typer.echo(f"- {item.name} (entry: {entry_point})")
                            bundled_found = True
        except Exception as e:
            typer.echo(f"(Error accessing bundled blueprints: {e})")

        if not bundled_found:
            typer.echo("(No bundled blueprints found or accessible)")
        typer.echo("")

        typer.echo(f"--- User Blueprint Sources (in {user_blueprints_src_dir}) ---")
        user_found = False
        if user_blueprints_src_dir.is_dir():
            try:
                for item in user_blueprints_src_dir.iterdir():
                    if item.is_dir():
                        entry_point = find_entry_point(item)
                        if entry_point:
                            typer.echo(f"- {item.name} (entry: {entry_point})")
                            user_found = True
            except OSError as e:
                typer.echo(f"(Warning: Could not read user blueprints directory: {e})")

        if not user_found:
            typer.echo(f"(No user blueprint sources found in {user_blueprints_src_dir})")
            typer.echo("You can add blueprints by copying their source folders to this directory.")
        typer.echo("")


@app.command(name="cli-agents")
def cli_agents(
    config_path: str = typer.Option(None, "--config", "-c", help="Path to swarm_config.json (defaults to the usual search)."),
    check_auth: bool = typer.Option(False, "--check-auth", "-a", help="Also probe each installed CLI's authentication (runs its configured auth_check)."),
    suggest: bool = typer.Option(False, "--suggest", "-S", help="Suggest ready-to-paste config blocks for supported CLIs that are installed but not yet configured."),
    smoke: bool = typer.Option(False, "--smoke", "-s", help="Run one trivial one-shot per installed CLI to confirm it returns in non-interactive mode. NOTE: invokes each CLI's model once (small quota cost)."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Emit a single machine-readable JSON object instead of tables (honors --check-auth/--smoke/--suggest)."),
    init: bool = typer.Option(False, "--init", "-i", help="Print a complete, ready-to-run swarm_config wiring every mode (cli_fusion/cli_orchestrator/cli_map) over the CLIs installed on this host."),
    write: bool = typer.Option(False, "--write", "-w", help="With --init, write the config to your swarm config path (backs up any existing file)."),
):
    """Autodiscover configured CLI agents: which are installed (and optionally authenticated)."""
    import asyncio
    import json

    from swarm.core.cli_adapter import CliAdapterRegistry
    from swarm.core import cli_catalog
    from swarm.core.config_loader import find_config_file, load_config

    if init:
        installed = cli_catalog.installed_catalog_clis()
        blob = json.dumps(cli_catalog.build_starter_config(installed), indent=2)
        if write:
            from swarm.core import paths
            dest = Path(config_path) if config_path else (paths.get_user_config_dir_for_swarm() / "swarm_config.json")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                backup = dest.with_suffix(dest.suffix + ".bak")
                dest.replace(backup)
                typer.echo(f"Backed up existing config to {backup}")
            dest.write_text(blob)
            typer.echo(f"Wrote starter config for {len(installed)} CLI(s) [{', '.join(installed) or 'none'}] to {dest}")
            typer.echo("Next: export OPENAI_API_KEY, then `swarm-cli cli-agents` to verify.")
        else:
            if not installed:
                typer.echo("# No catalog CLIs (claude/gemini/codex/opencode) found on this host.")
            typer.echo(blob)
        raise typer.Exit(code=0)

    cfg_file = find_config_file(specific_path=config_path)
    config = load_config(cfg_file) if cfg_file else {}
    registry = CliAdapterRegistry.from_config(config)
    rows = asyncio.run(registry.discover_auth()) if check_auth else registry.discover()

    if output_json:
        payload: dict = {"agents": [d.as_dict() for d in rows]}
        # Native (built-in) consensus capability per configured CLI, so a UI can
        # offer a "use this CLI's own consensus mode" toggle only where available.
        payload["native_consensus"] = {
            d.name: cli_catalog.NATIVE_CONSENSUS[d.name]
            for d in rows
            if cli_catalog.has_native_consensus(d.name)
        }
        if smoke:
            smoke_names = [d.name for d in rows if d.installed]
            payload["smoke"] = [
                s.as_dict() for s in asyncio.run(registry.smoke_check_all(names=smoke_names))
            ]
        if suggest:
            payload["suggestions"] = cli_catalog.suggest_unconfigured(registry.names())
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(code=0)

    if not rows:
        typer.echo("No CLI agents configured. Add a 'cli_agents' block to your swarm config (see docs/CLI_FUSION.md).")
    elif check_auth:
        typer.echo(f"{'AGENT':16} {'STATUS':10} {'AUTH':16} {'MODE':10} EXECUTABLE")
        for d in rows:
            status = "installed" if d.installed else "missing"
            typer.echo(f"{d.name:16} {status:10} {d.authenticated:16} {d.mode:10} {d.executable or '-'}")
    else:
        typer.echo(f"{'AGENT':16} {'STATUS':10} {'MODE':10} EXECUTABLE")
        for d in rows:
            status = "installed" if d.installed else "missing"
            typer.echo(f"{d.name:16} {status:10} {d.mode:10} {d.executable or '-'}")
    if rows:
        installed = sum(1 for d in rows if d.installed)
        typer.echo(f"\n{installed}/{len(rows)} configured CLI agents installed on this host.")

    if smoke:
        installed = [d.name for d in rows if d.installed]
        typer.echo("")
        if not installed:
            typer.echo("No installed CLI agents to smoke-test.")
        else:
            typer.echo(f"Smoke-testing {len(installed)} installed CLI(s) (one trivial one-shot each)…")
            results = asyncio.run(registry.smoke_check_all(names=installed))
            typer.echo(f"\n{'AGENT':16} {'SMOKE':6} {'TIME':>7}  DETAIL")
            for s in results:
                typer.echo(f"{s.name:16} {s.status:6} {s.duration:6.1f}s  {s.detail}")

    if suggest:
        suggestions = cli_catalog.suggest_unconfigured(registry.names())
        typer.echo("")
        if not suggestions:
            typer.echo("No suggestions: every supported CLI installed on this host is already configured.")
        else:
            names = ", ".join(sorted(suggestions))
            typer.echo(f"Suggested cli_agents for installed-but-unconfigured CLIs ({names}):")
            typer.echo("Verify each CLI's flags with --help before use; see docs/CLI_FUSION.md.\n")
            typer.echo(json.dumps({"cli_agents": suggestions}, indent=2))


# Laconic alias: `swarm-cli agents` == `swarm-cli cli-agents`.
app.command(name="agents", help="Alias for cli-agents.")(cli_agents)


@app.command(name="skills")
def skills_command(
    show: str = typer.Option(None, "--show", "-s", help="Print the full SKILL.md instructions for one skill."),
    skills_dir: str = typer.Option(None, "--dir", "-d", help="Skills directory to scan (defaults to <project>/skills)."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Emit a machine-readable JSON object instead of a table."),
):
    """List discoverable skills (reusable capabilities applied via the cli_agent `skill=` param)."""
    import json

    from swarm.core import skills as skills_mod

    catalog = skills_mod.discover_skills(skills_dir)

    if show:
        skill = catalog.get(show)
        if skill is None:
            typer.echo(f"No skill named '{show}'. Available: {', '.join(sorted(catalog)) or 'none'}")
            raise typer.Exit(code=1)
        if output_json:
            typer.echo(json.dumps(
                {"name": skill.name, "description": skill.description,
                 "assets": skill.assets, "instructions": skill.instructions}, indent=2))
        else:
            typer.echo(f"# {skill.name}\n{skill.description}\n")
            if skill.assets:
                typer.echo(f"Bundled assets: {', '.join(skill.assets)}\n")
            typer.echo(skill.instructions)
        raise typer.Exit(code=0)

    if output_json:
        typer.echo(json.dumps(
            {"skills": [{"name": s.name, "description": s.description, "assets": s.assets}
                        for s in catalog.values()]}, indent=2))
        raise typer.Exit(code=0)

    if not catalog:
        typer.echo("No skills found. Add a SKILL.md under the skills/ directory (see docs/CLI_FUSION.md).")
        raise typer.Exit(code=0)
    typer.echo(f"{'SKILL':22} {'ASSETS':>6}  DESCRIPTION")
    for s in sorted(catalog.values(), key=lambda x: x.name):
        typer.echo(f"{s.name:22} {len(s.assets):>6}  {s.description[:70]}")
    typer.echo(f"\n{len(catalog)} skill(s). Apply one: `model=cli_agent`, param `skill=<name>`.")


import json as _json
import shutil as _shutil
from pathlib import Path as _Path


@app.command(name="config")
def config_cmd(
    action: str = typer.Argument(..., help="list | add | remove"),
    section: str = typer.Option(None, "--section", help="llm or mcpServers"),
    name: str = typer.Option(None, "--name", help="profile or server name"),
    json_str: str = typer.Option(None, "--json", help="JSON string for add"),
    config: str = typer.Option(None, "--config", help="path to swarm_config.json"),
):
    """Manage LLM profiles and MCP servers."""
    from swarm.core.config_loader import find_config_file, load_config
    from swarm.core import paths as _paths
    if config:
        cfg_path = _Path(config)
    else:
        found = find_config_file()
        cfg_path = found if found else (_paths.get_user_config_dir_for_swarm() / "swarm_config.json")
    try:
        cfg = _json.loads(cfg_path.read_text()) if cfg_path.is_file() else {"llm": {}, "mcpServers": {}}
    except Exception:
        cfg = {"llm": {}, "mcpServers": {}}

    if action == "list":
        if section in ("llm", None):
            typer.echo("LLM profiles:")
            for k, v in cfg.get("llm", {}).items():
                typer.echo(f"  {k}: {v.get('model', '?')}")
        if section in ("mcpServers", None):
            typer.echo("MCP Servers:")
            for k in cfg.get("mcpServers", {}):
                typer.echo(f"  {k}")
    elif action == "add":
        if not section or not name or not json_str:
            typer.echo("--section, --name, and --json are required for add", err=True)
            raise typer.Exit(code=1)
        try:
            val = _json.loads(json_str)
        except _json.JSONDecodeError as e:
            typer.echo(f"Invalid JSON: {e}", err=True)
            raise typer.Exit(code=1)
        cfg.setdefault(section, {})[name] = val
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(_json.dumps(cfg, indent=2))
        typer.echo(f"Added '{name}' to {section} in {cfg_path}")
    elif action == "remove":
        if not section or not name:
            typer.echo("--section and --name are required for remove", err=True)
            raise typer.Exit(code=1)
        removed = cfg.get(section, {}).pop(name, None)
        if removed is None:
            typer.echo(f"'{name}' not found in {section}")
        else:
            cfg_path.write_text(_json.dumps(cfg, indent=2))
            typer.echo(f"Removed '{name}' from {section}")
    else:
        typer.echo(f"Unknown action '{action}'. Use: list, add, remove", err=True)
        raise typer.Exit(code=1)


@app.command(name="wizard")
def wizard_cmd(
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Skip prompts, use provided options"),
    team_name: str = typer.Option(None, "-n", "--name", help="Team/blueprint name"),
    roles: list[str] = typer.Option([], "-r", "--role", help="Role:description pairs (repeatable)"),
    no_shortcut: bool = typer.Option(False, "--no-shortcut", help="Don't create a CLI shortcut"),
    output_dir: str = typer.Option(None, "--output-dir", help="Where to write the blueprint"),
):
    """Scaffold a new team blueprint (non-interactive mode supported)."""
    import re
    if not team_name:
        typer.echo("--name is required", err=True)
        raise typer.Exit(code=1)
    slug = re.sub(r"[^a-z0-9_]", "", team_name.lower().replace(" ", "_"))
    out = _Path(output_dir) / slug if output_dir else _Path.cwd() / slug
    out.mkdir(parents=True, exist_ok=True)
    agents_code = ""
    for role_spec in roles:
        parts = role_spec.split(":", 1)
        rname, rdesc = (parts[0], parts[1]) if len(parts) == 2 else (parts[0], parts[0])
        agents_code += f"        Agent(name='{rname}', instructions='{rdesc}'),\n"
    bp_file = out / f"blueprint_{slug}.py"
    bp_file.write_text(f'''"""Auto-generated blueprint: {team_name}"""
from agents import Agent
from swarm.core.blueprint_base import BlueprintBase

class {slug.title().replace("_","")}Blueprint(BlueprintBase):
    metadata = {{"name": "{slug}", "description": "Team blueprint: {team_name}"}}
    async def run(self, messages, **kwargs):
        yield {{"messages": [{{"role": "assistant", "content": "Team {team_name} ready."}}]}}
''')
    typer.echo(f"Team blueprint created: {bp_file}")


@app.command(name="add")
def add_cmd(
    source: str = typer.Argument(..., help="Path to blueprint directory to add"),
    name: str = typer.Option(None, "--name", help="Override blueprint name"),
):
    """Add a blueprint to the user blueprint library."""
    from swarm.core import paths as _paths
    src = _Path(source).resolve()
    if not src.is_dir():
        typer.echo(f"Source directory not found: {src}", err=True)
        raise typer.Exit(code=1)
    bp_name = name or src.name
    dest = _Path.home() / ".local" / "share" / "swarm" / "blueprints" / bp_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        _shutil.rmtree(dest)
    _shutil.copytree(src, dest)
    typer.echo(f"Added blueprint '{bp_name}' to {dest}")


@app.command(name="delete")
def delete_cmd(
    blueprint_name: str = typer.Argument(..., help="Blueprint name to delete from user library"),
):
    """Delete a blueprint from the user blueprint library."""
    dest = _Path.home() / ".local" / "share" / "swarm" / "blueprints" / blueprint_name
    if not dest.exists():
        typer.echo(f"Blueprint '{blueprint_name}' not found in user library", err=True)
        raise typer.Exit(code=1)
    _shutil.rmtree(dest)
    typer.echo(f"Deleted blueprint '{blueprint_name}' from {dest}")


@app.command(name="uninstall")
def uninstall_cmd(
    blueprint_name: str = typer.Argument(..., help="Blueprint executable to uninstall"),
):
    """Uninstall a compiled blueprint executable from the user bin directory."""
    from swarm.core import paths as _paths
    bin_dir = _paths.get_user_bin_dir()
    exe = bin_dir / blueprint_name
    if not exe.exists():
        typer.echo(f"Executable '{blueprint_name}' not found in {bin_dir}", err=True)
        raise typer.Exit(code=1)
    exe.unlink()
    typer.echo(f"Uninstalled '{blueprint_name}' from {bin_dir}")


if __name__ == "__main__":
    app()
