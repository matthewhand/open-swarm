#!/usr/bin/env python3
"""Legacy bulk PyInstaller build (make build-all-pyinstaller).

Preferred path today is ``swarm-cli install-executable``. This helper walks
bundled blueprints and writes one-file binaries under ``bin/``.
"""
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
HOOK = os.path.join(SCRIPT_DIR, "swarm_cli_hook.py")
blueprint_root = os.path.join(REPO_ROOT, "src", "swarm", "blueprints")

for dirpath, _dirnames, filenames in os.walk(blueprint_root):
    for filename in filenames:
        if filename.startswith("blueprint_") and filename.endswith(".py"):
            blueprint_file = os.path.join(dirpath, filename)
            blueprint_name = filename.replace("blueprint_", "").replace(".py", "")
            output_name = blueprint_name
            print(f"Building executable for {blueprint_file} as {output_name}")
            command = [
                "pyinstaller",
                "--onefile",
                "--distpath", os.path.join(REPO_ROOT, "bin"),
                "--name",
                output_name,
                "--runtime-hook",
                HOOK,
                blueprint_file,
            ]
            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT
            subprocess.run(command, check=True, env=env, cwd=REPO_ROOT)
            print(f"Executable for {output_name} built successfully.")
