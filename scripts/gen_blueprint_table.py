#!/usr/bin/env python3
"""
Auto-generates a markdown table of all blueprints and their metadata for the README.
Run this after adding or updating any blueprint metadata.
"""
import os
import sys
import glob
import importlib.util
import inspect

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(REPO_ROOT, "README.md")
BLUEPRINT_MODULES = glob.glob(os.path.join(REPO_ROOT, "src/swarm/blueprints/*/blueprint_*.py"))

# Load blueprint metadata (copied from swarm_cli.py, but standalone)
def get_blueprint_metadata():
    blueprints = []
    for mod_path in BLUEPRINT_MODULES:
        module_name = mod_path.replace("/", ".").rstrip(".py")
        try:
            spec = importlib.util.spec_from_file_location(module_name, mod_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if hasattr(obj, "metadata") and isinstance(getattr(obj, "metadata"), dict):
                    meta = getattr(obj, "metadata").copy()
                    # Docstring fallback for description
                    if not meta.get("description"):
                        doc = inspect.getdoc(obj)
                        if doc:
                            meta["description"] = doc.split("\n")[0]
                    blueprints.append(meta)
        except Exception as e:
            print(f"Warning: Failed to load {mod_path}: {e}", file=sys.stderr)
            continue
    return blueprints

def format_table(blueprints):
    # Table columns: Emoji | Name | Description | Example Commands | Branding
    header = "| Emoji | Name | Description | Example Commands | Branding |\n"
    header += "|-------|------|-------------|------------------|----------|\n"
    rows = []
    for bp in sorted(blueprints, key=lambda b: b.get("name", "")):
        emoji = bp.get("emoji", "")
        name = bp.get("name", "")
        desc = bp.get("description", "")
        examples = "<br>".join(bp.get("examples", []))
        branding = bp.get("branding", "")
        rows.append(f"| {emoji} | `{name}` | {desc} | {examples} | {branding} |")
    return header + "\n".join(rows) + "\n"

def update_readme(table_md):
    with open(README_PATH, "r") as f:
        readme = f.read()
    start = readme.find("<!-- BLUEPRINT_TABLE_START -->")
    end = readme.find("<!-- BLUEPRINT_TABLE_END -->")
    if start == -1 or end == -1:
        print("ERROR: Could not find blueprint table markers in README.md", file=sys.stderr)
        sys.exit(1)
    new_readme = (
        readme[:start]
        + "<!-- BLUEPRINT_TABLE_START -->\n"
        + "<!-- The following table is auto-generated. Do not edit manually. Run scripts/gen_blueprint_table.py to update. -->\n\n"
        + table_md
        + "<!-- BLUEPRINT_TABLE_END -->"
        + readme[end+len("<!-- BLUEPRINT_TABLE_END -->"):]
    )
    with open(README_PATH, "w") as f:
        f.write(new_readme)
    print("Blueprint table updated in README.md")

def main():
    blueprints = get_blueprint_metadata()
    if not blueprints:
        print("No blueprints found!", file=sys.stderr)
        sys.exit(1)
    table_md = format_table(blueprints)
    update_readme(table_md)

if __name__ == "__main__":
    main()
