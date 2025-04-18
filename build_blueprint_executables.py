#!/usr/bin/env python3
import os
import glob
import subprocess

def main():
    blueprint_dir = "blueprints"
    # Only build the 'codey' blueprint for now to avoid Django-related failures
    codey_dir = os.path.join(blueprint_dir, "codey")
    if os.path.isdir(codey_dir):
        files = glob.glob(os.path.join(codey_dir, "blueprint_*.py"))
        if files:
            blueprint_file = files[0]
            output_name = "codey"
            print(f"Building executable for {blueprint_file} as {output_name}")
            command = [
                "pyinstaller",
                "--onefile",
                "--distpath", ".",
                "--name", output_name,
                "--runtime-hook", "swarm_cli_hook.py",
                blueprint_file
            ]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            subprocess.run(command, check=True, env=env)
            print(f"Executable for {output_name} built successfully.")
    else:
        print("Codey blueprint directory not found.")
    return

if __name__ == "__main__":
    main()