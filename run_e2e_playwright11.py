import subprocess
import os

env = os.environ.copy()
env["RUN_E2E_VISUAL"] = "1"

result = subprocess.run(
    ["uv", "run", "pytest", "tests/e2e_visual/test_golden_journey.py::test_dark_mode_toggle", "--tb=short", "-v"],
    env=env,
    capture_output=True,
    text=True
)

for line in result.stdout.split('\n'):
    if 'E   ' in line or 'playwright' in line.lower() or 'Error' in line:
        print(line)
