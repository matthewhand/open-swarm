"""Compile blueprint source into a standalone executable."""

import argparse
import ast
import importlib.resources as pkg_resources
import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from swarm.core import paths
from swarm.core.blueprint_discovery import BlueprintMetadata, discover_blueprints


class CompileBlueprintError(Exception):
    """Raised when a blueprint cannot be compiled into an executable."""


@dataclass
class CompilationResult:
    """Container for bulk compilation outcomes."""

    succeeded: dict[str, Path]
    failed: dict[str, str]


@dataclass
class BlueprintDetails:
    """Resolved blueprint source, entry point, and metadata."""

    name: str
    source_dir: Path
    entry_point: Path
    metadata: BlueprintMetadata

    @property
    def executable_name(self) -> str:
        return self.metadata.get("abbreviation") or self.metadata.get("name") or self.name


def find_entry_point(blueprint_dir: Path) -> Path | None:
    """Locate a suitable entry-point Python file within a blueprint directory."""

    for item in blueprint_dir.glob("*.py"):
        if item.is_file() and not item.name.startswith("_"):
            return item
    return None


def _discover_blueprint_sources(
    *, include_user: bool = True, include_bundled: bool = True
) -> dict[str, Path]:
    """Return available blueprint source directories, preferring user entries."""

    discovered: dict[str, Path] = {}

    if include_user:
        user_dir = paths.get_user_blueprints_dir()
        if user_dir.is_dir():
            for item in sorted(user_dir.iterdir()):
                if item.is_dir() and not item.name.startswith("__"):
                    discovered[item.name] = item

    if include_bundled:
        bundled_dir = pkg_resources.files("swarm") / "blueprints"
        if bundled_dir.is_dir():
            for item in sorted(bundled_dir.iterdir()):
                if (
                    item.is_dir()
                    and not item.name.startswith("__")
                    and item.name not in discovered
                ):
                    discovered[item.name] = Path(item)

    return discovered


def _resolve_source_dir(blueprint_name: str) -> Path:
    """Find the blueprint source directory in user or bundled locations."""

    discovered = _discover_blueprint_sources()
    if blueprint_name in discovered:
        source_dir = discovered[blueprint_name]
        if paths.get_user_blueprints_dir() in source_dir.parents:
            return source_dir

        print(f"Using bundled blueprint directory: {source_dir}")
        return source_dir

    raise CompileBlueprintError(
        f"Error: Blueprint '{blueprint_name}' not found in user blueprints directory ({paths.get_user_blueprints_dir()}) or bundled blueprints."
    )


def _discover_metadata_and_entry(source_dir: Path, blueprint_name: str) -> BlueprintDetails:
    """Load blueprint metadata and entry point, preferring explicit filenames."""

    explicit_entry = source_dir / f"{blueprint_name}.py"
    alt_entry = source_dir / f"blueprint_{blueprint_name}.py"
    entry_point_path = None
    if explicit_entry.is_file():
        entry_point_path = explicit_entry
    elif alt_entry.is_file():
        entry_point_path = alt_entry
    else:
        entry_point_path = find_entry_point(source_dir)

    if not entry_point_path:
        raise CompileBlueprintError(f"Error: Could not find entry point script in {source_dir}")

    metadata: BlueprintMetadata = {
        "name": blueprint_name,
        "version": None,
        "description": None,
        "author": None,
        "abbreviation": None,
        "required_mcp_servers": None,
        "env_vars": None,
    }

    try:
        discovered = discover_blueprints(str(source_dir.parent))
        metadata = discovered.get(source_dir.name, {}).get("metadata", metadata)
    except Exception:
        # Discovery is best-effort; fallback metadata remains valid.
        pass

    if metadata.get("abbreviation") is None:
        metadata_override = _extract_metadata_from_entry(entry_point_path)
        if metadata_override:
            metadata = {**metadata, **metadata_override}

    return BlueprintDetails(
        name=blueprint_name,
        source_dir=source_dir,
        entry_point=entry_point_path,
        metadata=metadata,
    )


def _extract_metadata_from_entry(entry_point_path: Path) -> BlueprintMetadata | None:
    """Parse class-level metadata without importing blueprint dependencies."""

    try:
        module_ast = ast.parse(entry_point_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None

    for node in module_ast.body:
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "metadata":
                            try:
                                evaluated = ast.literal_eval(stmt.value)
                            except Exception:
                                continue
                            if isinstance(evaluated, dict):
                                return evaluated  # type: ignore[return-value]
    return None


def compile_blueprint_executable(blueprint_name: str, *, force: bool = False) -> Path:
    """Compile the specified blueprint into an executable in the user bin directory."""

    paths.ensure_swarm_directories_exist()

    details = _discover_metadata_and_entry(_resolve_source_dir(blueprint_name), blueprint_name)

    output_bin_dir = paths.get_user_bin_dir()
    output_bin_name = details.executable_name
    output_bin_path = output_bin_dir / output_bin_name
    pyinstaller_workpath = paths.get_user_cache_dir_for_swarm() / "build" / blueprint_name
    pyinstaller_specpath = paths.get_user_cache_dir_for_swarm() / "specs"
    pyinstaller_workpath.mkdir(parents=True, exist_ok=True)
    pyinstaller_specpath.mkdir(parents=True, exist_ok=True)

    print(f"Installing blueprint '{blueprint_name}' as executable...")
    print(f"  Source: {details.source_dir}")
    print(f"  Entry Point: {details.entry_point.name}")
    if details.executable_name != blueprint_name:
        print(f"  Executable Name: {details.executable_name} (from abbreviation)")
    print(f"  Output Executable: {output_bin_path}")

    if output_bin_path.exists() and not force:
        raise CompileBlueprintError(
            f"Error: Executable already exists at {output_bin_path}. Use --force to overwrite."
        )

    if os.environ.get("SWARM_TEST_MODE"):
        shim = f"#!/usr/bin/env bash\npython3 {details.entry_point} \"$@\"\n"
        try:
            with open(output_bin_path, "w", encoding="utf-8") as file:
                file.write(shim)
            os.chmod(output_bin_path, 0o755)
            print(f"Test-mode shim installed at: {output_bin_path}")
            return output_bin_path
        except Exception as exc:
            raise CompileBlueprintError(f"Error installing test-mode shim: {exc}") from exc

    if force and output_bin_path.exists():
        output_bin_path.unlink()

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
        str(details.entry_point),
    ]

    print(f"Running PyInstaller: {' '.join(map(str, pyinstaller_cmd))}")
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print("PyInstaller output:")
        print(result.stdout)
        print(f"Successfully installed '{blueprint_name}' to {output_bin_path}")
    except FileNotFoundError as exc:
        raise CompileBlueprintError("Error: PyInstaller command not found. Is PyInstaller installed?") from exc
    except subprocess.CalledProcessError as exc:
        raise CompileBlueprintError(
            f"Error during PyInstaller execution (Return Code: {exc.returncode}):\n{exc.stderr}\nCheck the output above for details."
        ) from exc
    except Exception as exc:
        raise CompileBlueprintError(f"An unexpected error occurred: {exc}") from exc

    return output_bin_path


def compile_multiple_blueprints(
    blueprint_names: Iterable[str], *, force: bool = False
) -> CompilationResult:
    """Compile multiple blueprints, collecting successes and failures."""

    succeeded: dict[str, Path] = {}
    failed: dict[str, str] = {}

    for name in blueprint_names:
        try:
            succeeded[name] = compile_blueprint_executable(name, force=force)
        except CompileBlueprintError as exc:
            failed[name] = str(exc)

    return CompilationResult(succeeded=succeeded, failed=failed)


def compile_all_available_blueprints(*, force: bool = False) -> CompilationResult:
    """Compile every discovered blueprint source (user first, then bundled)."""

    available = _discover_blueprint_sources()
    if not available:
        raise CompileBlueprintError(
            "No blueprint sources found in user or bundled locations; nothing to compile."
        )

    print(f"Found {len(available)} blueprint(s) to compile: {', '.join(sorted(available))}")
    return compile_multiple_blueprints(available, force=force)


def execute(args: argparse.Namespace) -> int:
    """Argparse entry point for the compile blueprint command."""

    if args.all and args.blueprint_name:
        print("Error: --all cannot be combined with an explicit blueprint name")
        return 2

    try:
        if args.all:
            result = compile_all_available_blueprints(force=args.force)
            if result.failed:
                print("Some blueprints failed to compile:")
                for name, reason in result.failed.items():
                    print(f"- {name}: {reason}")
                return 1
            return 0

        if not args.blueprint_name:
            print("Error: provide a blueprint name or use --all")
            return 2

        compile_blueprint_executable(args.blueprint_name, force=args.force)
    except CompileBlueprintError as exc:
        print(exc)
        return 1
    return 0


def register_args(parser: argparse.ArgumentParser):
    """Register arguments for the compile blueprint command."""

    parser.add_argument(
        "blueprint_name",
        nargs="?",
        help="Name of the blueprint directory to compile into an executable.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compile all available blueprint sources (user first, then bundled).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing executables when compiling.",
    )
