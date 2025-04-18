import os
import subprocess
import sys
from pathlib import Path

BLUEPRINTS_DIR = Path(__file__).parent / "src" / "swarm" / "blueprints"

# Discover blueprint files
blueprint_files = []
for root, dirs, files in os.walk(BLUEPRINTS_DIR):
    for file in files:
        if file.startswith("blueprint_") and file.endswith(".py"):
            blueprint_files.append(Path(root) / file)

def run_blueprint(blueprint_path):
    print(f"\033[1;36m\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║   🚀 TESTING: {blueprint_path.name:<48} ║")
    print(f"╚══════════════════════════════════════════════════════════════╝\033[0m")
    proc = subprocess.run([sys.executable, str(blueprint_path)], capture_output=True, text=True)
    print(proc.stdout)
    if proc.returncode == 0:
        print(f"\033[1;32m✅ {blueprint_path.name} PASSED\033[0m")
    else:
        print(f"\033[1;31m❌ {blueprint_path.name} FAILED\033[0m")
        print(proc.stderr)
    return proc.returncode

def main():
    print("\033[1;35m\n╔══════════════════════════════════════════════════════════════╗")
    print("║         🏆 SWARM ARMY: COVERAGE & VALUE-ADD REPORT         ║")
    print("╚══════════════════════════════════════════════════════════════╝\033[0m")
    failed = []
    for blueprint_path in blueprint_files:
        ret = run_blueprint(blueprint_path)
        if ret != 0:
            failed.append(blueprint_path)
    print("\n\033[1;35m╔══════════════════════════════════════════════════════════════╗")
    if not failed:
        print("║   🎉 ALL BLUEPRINTS PASSED! SWARM IS STRONG & COVERED!     ║")
    else:
        print("║   ⚠️  SOME BLUEPRINTS FAILED. SEE ABOVE FOR DETAILS.        ║")
    print("╚══════════════════════════════════════════════════════════════╝\033[0m")

if __name__ == "__main__":
    main()
