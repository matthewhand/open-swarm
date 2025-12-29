import importlib.resources as pkg_resources
import os
import subprocess
from pathlib import Path

import typer

import swarm
from swarm.core import paths
from swarm.extensions.cli.commands.compile_blueprint import (
    CompileBlueprintError,
    compile_all_available_blueprints,
    compile_blueprint_executable,
)

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
    for item in blueprint_dir.glob("*.py"):
        if item.is_file() and not item.name.startswith("_"):
            return item.name
    return None


@app.command(name="install-executable")
def install_executable(
    blueprint_name: str | None = typer.Argument(
        None, help="Name of the blueprint directory to install as an executable."
    ),
    all: bool = typer.Option(
        False,
        "--all",
        help="Compile all available blueprint sources (user preferred, then bundled).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing executables when compiling.",
    ),
):
    if all and blueprint_name:
        typer.echo("Error: --all cannot be combined with a specific blueprint name")
        raise typer.Exit(code=2)

    try:
        if all:
            result = compile_all_available_blueprints(force=force)
            if result.failed:
                typer.echo("Some blueprints failed to compile:")
                for name, reason in result.failed.items():
                    typer.echo(f"- {name}: {reason}")
                raise typer.Exit(code=1)
            return

        if not blueprint_name:
            typer.echo("Error: provide a blueprint name or use --all")
            raise typer.Exit(code=2)

        compile_blueprint_executable(blueprint_name, force=force)
    except CompileBlueprintError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc


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
        raise typer.Exit(code=1) from e

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


if __name__ == "__main__":
    app()
