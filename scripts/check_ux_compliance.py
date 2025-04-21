import os
import sys
import importlib
from pathlib import Path
import subprocess
import re
import json

BLUEPRINTS = [
    'family_ties', 'omniplex', 'zeus', 'chatbot', 'monkai_magic', 'poets', 'jeeves', 'suggestion', 'codey', 'gaggle', 'geese', 'hello_world'
]

BLUEPRINTS_DIR = Path(__file__).parent.parent / "src" / "swarm" / "blueprints"
REQUIRED_FIELDS = ["agentic", "ux_ansi_emoji", "spinner", "fallback"]
noncompliant = []

SPINNER_PHRASES = [
    "Generating.", "Generating..", "Generating...", "Running...", "Generating... Taking longer than expected"
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
        cmd = [sys.executable, "-m", f"swarm.blueprints.{bp_name}.blueprint_{bp_name}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
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
        return f"{' '.join(status)}\n--- Output ---\n{output.strip()[:400]}{'...' if len(output)>400 else ''}"
    except Exception as e:
        return f"[ERROR] Could not check {bp_name}: {e}"

def check_compliance(bp_name):
    meta_path = BLUEPRINTS_DIR / bp_name / "metadata.json"
    if not meta_path.exists():
        return f"[NONCOMPLIANT] {bp_name}: missing metadata.json"
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        compliance = meta.get("compliance", {})
        missing = [field for field in REQUIRED_FIELDS if field not in compliance or not compliance.get(field)]
        if missing:
            return f"[NONCOMPLIANT] {bp_name}: missing {', '.join(missing)}"
        else:
            return f"[COMPLIANT] {bp_name}"
    except Exception as e:
        return f"[ERROR] Could not check {bp_name}: {e}"

def main():
    print("Blueprint UX Compliance Report:\n")
    for bp in BLUEPRINTS:
        print(f"--- {bp} ---")
        compliance_result = check_compliance(bp)
        print(compliance_result)
        result = check_blueprint(bp)
        print(result)
        print()
    print("\nReview test logs or run pytest for full compliance details.")

if __name__ == "__main__":
    main()
