"""
Swarm API entry point for installation via PyPI or local dev.
"""
from swarm.core.swarm_api import main


def main_entry():
    main()

if __name__ == "__main__":
    main_entry()
