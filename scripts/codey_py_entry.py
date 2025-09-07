#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


def find_project_root(start_dir: Path, cli_rel_path: str) -> Path:
    """Traverse upward from start_dir to find a directory containing cli_rel_path."""
    current = start_dir.resolve()
    root = Path(current.root)
    while current != root:
        candidate = current / cli_rel_path
        if candidate.exists():
            return current
        current = current.parent
    return None

def main():
    # Set required environment variables
    os.environ["PYTHONPATH"] = os.path.join(os.getcwd(), "src")
    os.environ["SWARM_TEST_MODE"] = "1"
    os.environ["API_KEY"] = "dummy"
    os.environ["MCP_SERVER"] = "dummy"
    # Find the real project root robustly
    script_dir = Path(__file__).resolve().parent
    cli_rel_path = Path("src/swarm/blueprints/codey/codey_cli.py")
    project_root = find_project_root(script_dir, cli_rel_path)
    if not project_root:
        print(f"[ERROR] Could not locate codey_cli.py in any parent directory of {script_dir}", file=sys.stderr)
        sys.exit(2)
    cli_path = project_root / cli_rel_path
    result = subprocess.run([sys.executable, str(cli_path)] + sys.argv[1:])
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
