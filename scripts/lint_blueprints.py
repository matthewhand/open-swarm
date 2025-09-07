import sys
from pathlib import Path


def check_blueprint_file(path):
    text = Path(path).read_text()
    errors = []
    if "print_search_progress_box" not in text:
        errors.append("Missing print_search_progress_box usage.")
    if "'code'" not in text or "'semantic'" not in text:
        errors.append("Missing code/semantic search mode distinction.")
    for spinner in ["Generating.", "Generating..", "Generating...", "Running..."]:
        if spinner not in text:
            errors.append(f"Missing spinner message: {spinner}")
    if errors:
        print(f"{path}:")
        for err in errors:
            print(f"  - {err}")
        return False
    return True

if __name__ == "__main__":
    root = Path("src/swarm/blueprints")
    ok = True
    for f in root.glob("blueprint_*.py"):
        if not check_blueprint_file(f):
            ok = False
    if not ok:
        sys.exit(1)
