import os
import re
import subprocess
import sys

BLUEPRINTS = [
    'family_ties', 'omniplex', 'zeus', 'chatbot', 'monkai_magic', 'poets', 'jeeves', 'suggestion', 'codey', 'gaggle', 'geese', 'hello_world'
]

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
