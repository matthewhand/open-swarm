#!/usr/bin/env python3
import PyInstaller.__main__

PyInstaller.__main__.run([
    "swarm_wrapper.py",
    "--onefile",
    "--name", "swarm-wrapper",
    "--distpath", "~/bin",
    "--workpath", "build",
    "--specpath", "."
])

