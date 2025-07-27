#!/usr/bin/env python3
import PyInstaller.__main__


def build_executable(script, output_name):
    PyInstaller.__main__.run([
        script,
        "--onefile",
        "--name", output_name,
    ])

if __name__ == "__main__":
    # build echocraft first (already done), now build rue_code
    build_executable("src/swarm/blueprints/rue_code/blueprint_rue_code.py", "ruecode-blueprint")
    # Uncomment below to build suggestion after verifying disk space
    # build_executable("src/swarm/blueprints/suggestion/blueprint_suggestion.py", "suggestion-blueprint")
