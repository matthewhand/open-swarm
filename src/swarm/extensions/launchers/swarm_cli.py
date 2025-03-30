#!/usr/bin/env python3
import argparse
import importlib.util
import os
import sys
import subprocess
import shutil
import json
import PyInstaller.__main__
from pathlib import Path

# --- XDG Directory Helpers ---
def get_xdg_dir(variable_name: str, default_path: Path) -> Path:
    env_path = os.environ.get(variable_name); return Path(env_path).resolve() if env_path else default_path.resolve()
HOME = Path.home()
XDG_CONFIG_HOME = get_xdg_dir('XDG_CONFIG_HOME', HOME / '.config')
XDG_DATA_HOME = get_xdg_dir('XDG_DATA_HOME', HOME / '.local' / 'share')
XDG_CACHE_HOME = get_xdg_dir('XDG_CACHE_HOME', HOME / '.cache')
USER_BIN_DIR = HOME / '.local' / 'bin'
# Swarm specific paths
SWARM_CONFIG_DIR = XDG_CONFIG_HOME / 'swarm'; SWARM_DATA_DIR = XDG_DATA_HOME / 'swarm'
SWARM_CACHE_DIR = XDG_CACHE_HOME / 'swarm'; MANAGED_DIR = SWARM_DATA_DIR / 'blueprints'
BIN_DIR = USER_BIN_DIR; DEFAULT_CONFIG_PATH = SWARM_CONFIG_DIR / 'swarm_config.json'
BUILD_CACHE_DIR = SWARM_CACHE_DIR / 'build'

# --- Utility Functions ---
def resolve_env_vars(data): # (Unchanged)
    if isinstance(data, dict): return {k: resolve_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list): return [resolve_env_vars(item) for item in data]
    elif isinstance(data, str): return os.path.expandvars(data)
    else: return data

def ensure_swarm_dirs(): # (Unchanged)
    for dir_path in [SWARM_CONFIG_DIR, SWARM_DATA_DIR, MANAGED_DIR, SWARM_CACHE_DIR, BIN_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

def _ensure_default_config(config_path: Path):
    """Creates a default config file if it doesn't exist. Exits on error."""
    print(f"[DEBUG _ensure_default_config] Checking path: {config_path}") # DEBUG
    if not config_path.exists():
        try:
            print(f"[DEBUG _ensure_default_config] Path does not exist. Creating parent: {config_path.parent}") # DEBUG
            config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = {"llm": {}, "mcpServers": {}}
            print(f"[DEBUG _ensure_default_config] Writing default config to: {config_path}") # DEBUG
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Default config file created at: {config_path}")
            # Verify creation immediately
            if not config_path.exists():
                 print(f"[DEBUG _ensure_default_config] ERROR: File still doesn't exist after write attempt!")
                 sys.exit(1) # Exit if write seemed to fail
        except OSError as e:
            print(f"Error creating default config file at {config_path}: {e}")
            sys.exit(1) # Make directory/file creation errors fatal
        except Exception as e: # Catch other potential errors
            print(f"Unexpected error in _ensure_default_config: {e}")
            sys.exit(1)
    else:
         print(f"[DEBUG _ensure_default_config] Path already exists: {config_path}") # DEBUG

# --- CLI Command Functions --- (add, list, delete unchanged)
def add_blueprint(source_path, blueprint_name=None):
    source_path = Path(source_path).resolve();
    if not source_path.exists(): print(f"Error: source does not exist: {source_path}"); sys.exit(1)
    if source_path.is_dir():
        if not blueprint_name: blueprint_name = source_path.name
        target_dir = MANAGED_DIR / blueprint_name
        if target_dir.exists(): print(f"Warning: Overwriting existing blueprint '{blueprint_name}'."); shutil.rmtree(target_dir)
        shutil.copytree(source_path, target_dir, dirs_exist_ok=True)
    else: # File
        blueprint_file = source_path
        if not blueprint_name: blueprint_name = blueprint_file.stem if not blueprint_file.name.startswith("blueprint_") else blueprint_file.name[len("blueprint_"):-3]
        target_dir = MANAGED_DIR / blueprint_name; target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"blueprint_{blueprint_name}.py"; shutil.copy2(blueprint_file, target_file)
    print(f"Blueprint '{blueprint_name}' added to {target_dir}.")

def list_blueprints():
    ensure_swarm_dirs();
    if not MANAGED_DIR.exists(): print("No blueprints registered."); return
    try:
        entries = sorted([d.name for d in MANAGED_DIR.iterdir() if d.is_dir()])
        if entries: print("Registered blueprints:"); [print(" -", bp) for bp in entries]
        else: print("No blueprints registered.")
    except OSError as e: print(f"Error listing {MANAGED_DIR}: {e}")

def delete_blueprint(blueprint_name):
    target_dir = MANAGED_DIR / blueprint_name
    if target_dir.is_dir():
        try: shutil.rmtree(target_dir); print(f"Blueprint '{blueprint_name}' deleted.")
        except OSError as e: print(f"Error deleting {target_dir}: {e}"); sys.exit(1)
    else: print(f"Error: Blueprint '{blueprint_name}' not found."); sys.exit(1)


def run_blueprint(blueprint_name, cli_args, config_path_override=None):
    target_dir = MANAGED_DIR / blueprint_name
    blueprint_file = target_dir / f"blueprint_{blueprint_name}.py"
    if not blueprint_file.exists(): print(f"Error: Blueprint file missing for '{blueprint_name}'."); sys.exit(1)
    config_path_to_use = Path(config_path_override).expanduser() if config_path_override else DEFAULT_CONFIG_PATH
    # Config creation is now handled in main before this is called

    spec = importlib.util.spec_from_file_location(f"swarm_bp_{blueprint_name}", str(blueprint_file))
    if not spec or not spec.loader: print(f"Error: Failed to load spec: {blueprint_file}"); sys.exit(1)
    module = importlib.util.module_from_spec(spec)
    src_path = Path(__file__).resolve().parents[2] / "src"
    if str(src_path) not in sys.path: sys.path.insert(0, str(src_path))
    original_sys_path = list(sys.path); sys.path.insert(0, str(target_dir))
    try:
        spec.loader.exec_module(module)
        bp_class = next((obj for name, obj in module.__dict__.items() if isinstance(obj, type) and hasattr(obj, 'metadata') and issubclass(obj, module.BlueprintBase) and obj is not module.BlueprintBase), None)
        if bp_class and hasattr(bp_class, 'main'):
            original_argv = sys.argv
            # Pass explicit config path to the blueprint's main via argv
            sys.argv = [f"{blueprint_name}.py"] + cli_args + ["--config-path", str(config_path_to_use)]
            try: bp_class.main()
            finally: sys.argv = original_argv
        else: print(f"Error: Valid Blueprint class with main() not found in {blueprint_file}."); sys.exit(1)
    except Exception as e: print(f"Error running blueprint '{blueprint_name}': {e}"); import traceback; traceback.print_exc(); sys.exit(1)
    finally: sys.path = original_sys_path

def install_blueprint(blueprint_name): # (Unchanged)
    target_dir = MANAGED_DIR / blueprint_name; blueprint_file = target_dir / f"blueprint_{blueprint_name}.py"
    if not blueprint_file.exists(): print(f"Error: Blueprint '{blueprint_name}' not registered."); sys.exit(1)
    cli_name = blueprint_name; dist_path = BIN_DIR; work_path = BUILD_CACHE_DIR / blueprint_name; spec_path = target_dir
    print(f"Installing '{blueprint_name}' as '{cli_name}'..."); [print(f"  {k}: {v}") for k,v in locals().items() if k in ['blueprint_file', 'dist_path', 'work_path', 'spec_path']]
    dist_path.mkdir(parents=True, exist_ok=True); work_path.mkdir(parents=True, exist_ok=True)
    project_src_path = Path(__file__).resolve().parents[2] / "src"
    pyinstaller_args = [str(blueprint_file), "--onefile", "--name", cli_name, "--distpath", str(dist_path),
                        "--workpath", str(work_path), "--specpath", str(spec_path), f"--paths={project_src_path}"]
    print(f"  Running PyInstaller: {' '.join(pyinstaller_args)}")
    try:
        PyInstaller.__main__.run(pyinstaller_args)
        final_executable = dist_path / cli_name
        if final_executable.exists():
             final_executable.chmod(final_executable.stat().st_mode | 0o111)
             print(f"\nSuccess! Installed '{cli_name}' to {final_executable}")
             if str(dist_path) not in os.environ.get('PATH', '').split(os.pathsep): print(f"\nWarning: '{dist_path}' is not in your PATH.")
        else: print("\nError: PyInstaller finished but executable not found."); sys.exit(1)
    except Exception as e: print(f"\nError during build: {e}"); import traceback; traceback.print_exc(); sys.exit(1)
    except KeyboardInterrupt: print("\nInstallation aborted."); sys.exit(1)

def uninstall_blueprint(blueprint_name, blueprint_only=False, wrapper_only=False): # (Unchanged)
    target_dir = MANAGED_DIR / blueprint_name; cli_path = BIN_DIR / blueprint_name; removed_bp=False; removed_cli=False
    if blueprint_only or not wrapper_only:
        if target_dir.is_dir():
            try: shutil.rmtree(target_dir); print(f"Blueprint source '{blueprint_name}' removed."); removed_bp=True
            except OSError as e: print(f"Error removing {target_dir}: {e}")
        elif not wrapper_only: print(f"Info: Blueprint source '{blueprint_name}' not found.")
    if wrapper_only or not blueprint_only:
        if cli_path.is_file():
             try: cli_path.unlink(); print(f"CLI wrapper '{blueprint_name}' removed."); removed_cli=True
             except OSError as e: print(f"Error removing {cli_path}: {e}")
        elif not blueprint_only: print(f"Info: CLI wrapper '{blueprint_name}' not found.")
    if not removed_bp and not removed_cli: print(f"Warning: Nothing found to uninstall for '{blueprint_name}'.")

def manage_config(args): # (Unchanged)
    config_path = Path(args.config).expanduser(); _ensure_default_config(config_path)
    try:
        with open(config_path, "r") as f: config = json.load(f)
    except (json.JSONDecodeError, OSError) as e: print(f"Error reading config {config_path}: {e}"); sys.exit(1)
    section = args.section
    if args.action == "list":
        entries = config.get(section, {});
        if entries: print(f"Entries in [{section}]:"); [print(f"  {k}:\n    {json.dumps(v, indent=6).replace(chr(10), chr(10)+'    ')}") for k, v in entries.items()]
        else: print(f"No entries in section '{section}'.")
    elif args.action == "add":
        if not args.name: print("Error: --name required for add."); sys.exit(1)
        if not args.json: print("Error: --json required for add."); sys.exit(1)
        try: entry_data = json.loads(args.json)
        except json.JSONDecodeError as e: print(f"Error: Invalid JSON: {e}"); sys.exit(1)
        config.setdefault(section, {})[args.name] = entry_data
    elif args.action == "remove":
        if not args.name: print("Error: --name required for remove."); sys.exit(1)
        if section in config and args.name in config[section]: del config[section][args.name]
        else: print(f"Error: Entry '{args.name}' not found in section '{section}'."); sys.exit(1)
    if args.action in ["add", "remove"]:
        try:
            with open(config_path, "w") as f: json.dump(config, f, indent=4)
            print(f"Config {config_path} updated.")
        except OSError as e: print(f"Error writing config {config_path}: {e}"); sys.exit(1)

def main():
    os.environ.pop("SWARM_BLUEPRINTS", None)
    parser = argparse.ArgumentParser(description=("Swarm CLI...\n" + f"Config: {SWARM_CONFIG_DIR}\nData: {MANAGED_DIR}\n" + f"Bin: {BIN_DIR}\nCache: {SWARM_CACHE_DIR}"), formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True, metavar='SUBCOMMAND')
    # Add parsers (definitions omitted for brevity)
    parser_add = subparsers.add_parser("add", help="Copy blueprint source."); parser_add.add_argument("source"); parser_add.add_argument("--name")
    parser_list = subparsers.add_parser("list", help="List registered blueprints.")
    parser_delete = subparsers.add_parser("delete", help="Delete blueprint source."); parser_delete.add_argument("name")
    parser_run = subparsers.add_parser("run", help="Run registered blueprint.", add_help=False); parser_run.add_argument("name"); parser_run.add_argument('blueprint_args', nargs=argparse.REMAINDER)
    parser_install = subparsers.add_parser("install", help="Install blueprint as CLI."); parser_install.add_argument("name")
    parser_uninstall = subparsers.add_parser("uninstall", help="Uninstall blueprint/wrapper."); parser_uninstall.add_argument("name"); group = parser_uninstall.add_mutually_exclusive_group(); group.add_argument("--blueprint-only", action="store_true"); group.add_argument("--wrapper-only", action="store_true")
    parser_migrate = subparsers.add_parser("migrate", help="Apply Django migrations.")
    parser_config = subparsers.add_parser("config", help="Manage swarm_config.json."); parser_config.add_argument("action", choices=["add","list","remove"]); parser_config.add_argument("--section", required=True, choices=["llm","mcpServers"]); parser_config.add_argument("--name"); parser_config.add_argument("--json"); parser_config.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))

    args, unknown_args = parser.parse_known_args()
    ensure_swarm_dirs() # Ensure XDG dirs exist

    if args.command == "run":
        # Determine config path specifically for the run command (check args *after* 'run <name>')
        temp_parser = argparse.ArgumentParser(add_help=False); temp_parser.add_argument('--config-path')
        parsed_config_args, remaining_bp_args = temp_parser.parse_known_args(unknown_args)
        run_config_override = parsed_config_args.config_path # Will be None if not provided
        config_path_to_use = Path(run_config_override).expanduser() if run_config_override else DEFAULT_CONFIG_PATH

        # Ensure the config file exists before running the blueprint (FIXED: Call here in main)
        print(f"[DEBUG main] Ensuring config for run command at: {config_path_to_use}") # DEBUG
        _ensure_default_config(config_path_to_use)

        # Pass the override path (or None) and remaining args to run_blueprint
        run_blueprint(args.name, remaining_bp_args, config_path_override=run_config_override)

    elif args.command == "add": add_blueprint(args.source, args.name)
    elif args.command == "list": list_blueprints()
    elif args.command == "delete": delete_blueprint(args.name)
    elif args.command == "install": install_blueprint(args.name)
    elif args.command == "uninstall": uninstall_blueprint(args.name, args.blueprint_only, args.wrapper_only)
    elif args.command == "migrate":
        manage_py = Path(__file__).resolve().parents[2] / "manage.py"
        if not manage_py.exists(): print(f"Error: manage.py not found: {manage_py}"); sys.exit(1)
        if "DJANGO_SETTINGS_MODULE" not in os.environ: os.environ["DJANGO_SETTINGS_MODULE"] = "swarm.settings"; print("Warning: DJANGO_SETTINGS_MODULE not set, using default.")
        try: subprocess.run([sys.executable, str(manage_py), "migrate"], check=True); print("Migrations applied.")
        except Exception as e: print(f"Migration error: {e}"); sys.exit(1)
    elif args.command == "config": manage_config(args)
    else: parser.print_help(); sys.exit(1)

if __name__ == "__main__":
    main()
