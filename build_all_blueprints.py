#!/usr/bin/env python3
import os
import subprocess

# List all blueprint directories
blueprint_root = os.path.join(os.path.dirname(__file__), "src", "swarm", "blueprints")

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
                "--distpath", "bin",
                "--name", output_name,
                "--runtime-hook", "swarm_cli_hook.py",
                blueprint_file
            ]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            subprocess.run(command, check=True, env=env)
            print(f"Executable for {output_name} built successfully.")
