import os
import re
import subprocess
import sys
from pathlib import Path

# Dynamically discover ~21 blueprints (instead of hardcoded subset); support ~all
BLUEPRINT_DIR = Path(__file__).parent.parent / "src" / "swarm" / "blueprints"
SKIP_BPS = {"common", "__pycache__", "messenger", "dynamic_team", "flock", "digitalbutlers", "gaggle"}  # gaggle alias of geese; messenger stub
BLUEPRINTS = sorted([
    d.name for d in BLUEPRINT_DIR.iterdir()
    if d.is_dir() and not d.name.startswith('.') and d.name not in SKIP_BPS
    and ( (d / f"{d.name}.py").exists() or (d / f"blueprint_{d.name}.py").exists() or d.name in ("family_ties", "stewie") )
])
# Map/override for compat
if 'geese' not in BLUEPRINTS:
    BLUEPRINTS.append('geese')
BLUEPRINTS = sorted(set(BLUEPRINTS))

SPINNER_PHRASES = [
    "Generating.", "Generating..", "Generating...", "Running...",
    "Generating... Taking longer than expected"
]

SUMMARY_PHRASES = ["Results:", "Processed"]

EMOJI_PATTERN = re.compile('[\U0001F300-\U0001FAFF]')


def check_output(output):
    spinner = any(phrase in output for phrase in SPINNER_PHRASES)
    emoji = EMOJI_PATTERN.search(output) is not None
    summary = any(phrase in output for phrase in SUMMARY_PHRASES)
    return spinner, emoji, summary

def check_blueprint(bp_name):
    os.environ["SWARM_TEST_MODE"] = "1"
    try:
        # Run blueprint as a subprocess to capture stdout
        # Use blueprint_ prefix or key; increase timeout for geese etc compliance
        mod_name = bp_name
        py_stem = f"blueprint_{bp_name}"
        # Special: geese may use blueprint_geese.py
        cmd = [sys.executable, "-m", f"swarm.blueprints.{bp_name}.{py_stem}"]
        timeout = 45 if bp_name in ("geese", "stewie", "mission_improbable", "omniplex", "whinge_surf") else 20
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            # fallback cmd variant for bps using non blueprint_ stem
            alt_cmd = [sys.executable, "-m", f"swarm.blueprints.{bp_name}.{bp_name}"]
            proc = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=timeout)
        output = proc.stdout + proc.stderr
        spinner, emoji, summary = check_output(output)
        status = []
        if spinner:
            status.append("SPINNER=PASS")
        else:
            status.append("SPINNER=WARNING")
        if emoji:
            status.append("EMOJI=PASS")
        else:
            status.append("EMOJI=WARNING")
        if summary:
            status.append("SUMMARY=PASS")
        else:
            status.append("SUMMARY=WARNING")
        return (
            f"{' '.join(status)}\n--- Output ---\n"
            f"{output.strip()[:40]}{'...' if len(output)>400 else ''}"
        )
    except Exception as e:
        return f"[ERROR] Could not check {bp_name}: {e}"

def main():
    print("Blueprint UX Compliance Report:\n")
    for bp in BLUEPRINTS:
        print(f"--- {bp} ---")
        result = check_blueprint(bp)
        print(result)
        print()
    print("\nReview test logs or run pytest for full compliance details.")

if __name__ == "__main__":
    main()
