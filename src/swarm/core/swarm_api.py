#!/usr/bin/env python3
import argparse
import subprocess
import sys
from os import path, listdir, makedirs

def main():
    parser = argparse.ArgumentParser(description="Swarm REST Launcher")
    parser.add_argument("--blueprint", required=True, help="Comma-separated blueprint file paths or names for configuration purposes")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the REST server")
    parser.add_argument("--config", default="~/.swarm/swarm_config.json", help="Configuration file path")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode and print process id")
    args = parser.parse_args()

    # Split blueprints by comma and strip whitespace
    bp_list = [bp.strip() for bp in args.blueprint.split(",") if bp.strip()]
    blueprint_paths = []
    for bp_arg in bp_list:
        resolved = None
        if path.exists(bp_arg):
            if path.isdir(bp_arg):
                resolved = bp_arg
                print(f"Using blueprint directory: {resolved}")
            else:
                resolved = bp_arg
                print(f"Using blueprint file: {resolved}")
        else:
            managed_path = path.expanduser("~/.swarm/blueprints/" + bp_arg)
            if path.isdir(managed_path):
                matches = [f for f in listdir(managed_path) if f.startswith("blueprint_") and f.endswith(".py")]
                if not matches:
                    print("Error: No blueprint file found in managed directory:", managed_path)
                    sys.exit(1)
                resolved = path.join(managed_path, matches[0])
                print(f"Using managed blueprint: {resolved}")
            else:
                print("Warning: Blueprint not found:", bp_arg, "- skipping.")
                continue
        if resolved:
            blueprint_paths.append(resolved)

    if not blueprint_paths:
        print("Error: No valid blueprints found.")
        sys.exit(1)
    print("Blueprints to be configured:")
    for bp in blueprint_paths:
        print(" -", bp)

    config_path = path.expanduser(args.config)
    if not path.exists(config_path):
        makedirs(path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write("{}")
        print("Default config file created at:", config_path)

    print("Launching Django server on port 0.0.0.0:{}".format(args.port))
    try:
        if args.daemon:
            proc = subprocess.Popen(["python", "manage.py", "runserver", f"0.0.0.0:{args.port}"])
            print("Running in daemon mode. Process ID:", proc.pid)
        else:
            subprocess.run(["python", "manage.py", "runserver", f"0.0.0.0:{args.port}"], check=True)
    except subprocess.CalledProcessError as e:
        print("Error launching Django server:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()