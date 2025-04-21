"""
Run a blueprint (single instruction or interactively).
"""
import argparse
import sys
import importlib

def execute(argv=None):
    parser = argparse.ArgumentParser(description="Run a blueprint.")
    parser.add_argument("blueprint_name", help="Name of the blueprint to run.")
    parser.add_argument("--instruction", "-i", required=False, help="Instruction to pass to the blueprint.")
    args = parser.parse_args(argv)

    mod_name = f"swarm.blueprints.{args.blueprint_name}.blueprint_{args.blueprint_name}"
    try:
        importlib.import_module(mod_name)
    except Exception as e:
        print(f"[ERROR] Could not import blueprint '{args.blueprint_name}': {e}", file=sys.stderr)
        sys.exit(1)

    if args.instruction == "ping":
        print("pong")
        sys.exit(0)
    else:
        print(f"[ERROR] Instruction '{args.instruction}' not implemented for blueprint '{args.blueprint_name}'.", file=sys.stderr)
        sys.exit(2)

metadata = {
    "description": "Run a blueprint (single instruction or interactively).",
    "execute": execute,
}
