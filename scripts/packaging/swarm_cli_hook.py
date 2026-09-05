# Runtime hook for PyInstaller to set SWARM_CLI environment variable and redirect stderr.
import os
import sys

# Set SWARM_CLI environment variable for CLI mode
os.environ["SWARM_CLI"] = "1"

# Determine stderr redirection target.
# If the environment variable SWARM_STDERR_LOG is set, use its value as the log file.
# Otherwise, default to os.devnull to discard stderr output.
stderr_target = os.getenv("SWARM_STDERR_LOG")

if stderr_target:
    try:
        sys.stderr = open(stderr_target, "a")
    except Exception as e:
        print("Failed to redirect stderr to specified file:", e, file=sys.__stderr__)
else:
    try:
        sys.stderr = open(os.devnull, "w")
    except Exception as e:
        print("Failed to redirect stderr to os.devnull:", e, file=sys.__stderr__)
