"""
Shared tool utilities for blueprints to reduce code duplication.

Provides PatchedFunctionTool (for wrapping plain funcs for Agent/tools compat and test access to .func),
DummyTool (for SWARM_TEST_MODE no-op placeholders),
and canonical implementations of common file/shell operations.

Prefer using @function_tool from 'agents' where possible for new code (see suggestion.py, chatbot.py).
These patches are legacy compat for blueprints that pre-date full migration or need .func exposure for tests.

Usage:
    from swarm.blueprints.common.tool_utils import (
        PatchedFunctionTool,
        DummyTool,
        read_file, write_file, list_files, execute_shell_command,
        read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool,
    )
    # Then: read_file_tool = ... (or use the pre-created _tool instances)
"""

import os
import subprocess
from typing import Any, Callable

# --- Tool Wrappers ---

class PatchedFunctionTool:
    """
    Wrapper to expose plain python functions as tools compatible with openai-agents Agent/tools.
    Exposes .func (original) and .name for direct test access (e.g. unit tests call tool.func()).
    Also callable.
    """
    def __init__(self, func: Callable, name: str):
        self.func = func
        self.name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<PatchedFunctionTool {self.name}>"


class DummyTool:
    """
    Placeholder tool for SWARM_TEST_MODE (avoids real side effects in tests/compliance).
    Returns dummy string on call. Used e.g. in codey blueprint.
    """
    def __init__(self, name: str):
        self.name = name

    def __call__(self, *_args: Any, **_kwargs: Any) -> str:
        return f"[DummyTool: {self.name} called]"

    def __repr__(self) -> str:
        return f"<DummyTool {self.name}>"


# --- Common file / shell operation implementations (used by many blueprints) ---

def read_file(path: str) -> str:
    """Read file contents safely. Returns error string on failure."""
    try:
        with open(path) as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to file safely. Returns status string."""
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"


def list_files(directory: str = ".") -> str:
    """List directory contents. Returns error string on failure."""
    try:
        return "\n".join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"


def execute_shell_command(command: str, timeout: int | None = None) -> str:
    """Execute a shell command safely using shlex.split (no shell injection)."""
    import shlex
    timeout = timeout or int(os.getenv("SWARM_COMMAND_TIMEOUT", "60"))
    try:
        args = shlex.split(command)
        result = subprocess.run(
            args,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output.strip()
    except ValueError as e:
        return f"Error: invalid command syntax: {e}"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing command: {e}"


# Pre-instantiated tool wrappers for convenience (import and use directly or rebind)
read_file_tool = PatchedFunctionTool(read_file, "read_file")
write_file_tool = PatchedFunctionTool(write_file, "write_file")
list_files_tool = PatchedFunctionTool(list_files, "list_files")
execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, "execute_shell_command")
