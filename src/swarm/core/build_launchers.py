#!/usr/bin/env python3
import PyInstaller.__main__

def build_executable(script, output_name):
    PyInstaller.__main__.run([
        script,
        "--onefile",
        "--name", output_name,
        "--add-data", "swarm_config.json:."  # Adjust if additional data is needed
    ])

if __name__ == "__main__":
    build_executable("launchers/swarm_cli.py", "swarm-cli")
    build_executable("launchers/swarm_rest.py", "swarm-rest")