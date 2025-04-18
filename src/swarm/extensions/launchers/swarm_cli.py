"""
Swarm CLI entry point for installation via PyPI or local dev.
"""
import sys
import os
from swarm.extensions.cli.main import main

def app():
    main()

if __name__ == "__main__":
    app()
