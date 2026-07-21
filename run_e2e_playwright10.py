import subprocess
import os

env = os.environ.copy()
env["RUN_E2E_VISUAL"] = "1"

result = subprocess.run(
    ["uv", "run", "pytest", "tests/e2e_visual/test_golden_journey.py::test_dark_mode_toggle", "-v"],
    env=env,
    capture_output=True,
    text=True
)
print("--- STDOUT ---")
print(result.stdout)
print("--- STDERR ---")
print(result.stderr)
