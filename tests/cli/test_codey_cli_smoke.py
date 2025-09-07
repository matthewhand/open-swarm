import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTEST_ROOT = Path(__file__).resolve().parents[2]


def _run_codey_cli(env_overrides: dict, args: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.update(env_overrides)
    cmd = [sys.executable, "-m", "src.swarm.blueprints.codey.codey_cli"] + args
    proc = subprocess.run(
        cmd,
        cwd=str(PYTEST_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


@pytest.mark.timeout(60)
def test_codey_cli_basic_message_testmode():
    """
    Smoke test the Codey CLI in SWARM_TEST_MODE.
    Expects deterministic answer text for a simple, non-search message.
    """
    rc, out, err = _run_codey_cli(
        {
            "SWARM_TEST_MODE": "1",  # force deterministic test-mode paths
            "OPENAI_API_KEY": "sk-test-123",  # satisfy validate_env()
        },
        ["--message", "What is a Python function?"],
    )
    if rc != 0:
        sys.stdout.write("\n[codey stdout]\n" + out)
        sys.stderr.write("\n[codey stderr]\n" + err)
    assert rc == 0, "CLI should exit cleanly in test mode"
    assert "function" in out.lower() or "def" in out.lower(), "Expected deterministic test-mode answer"


@pytest.mark.timeout(60)
def test_codey_cli_semantic_search_testmode():
    """
    Smoke test the Semantic Search branch in SWARM_TEST_MODE.
    Validates that the CLI prints search UX output.
    """
    rc, out, err = _run_codey_cli(
        {
            "SWARM_TEST_MODE": "1",
            "OPENAI_API_KEY": "sk-test-123",
        },
        ["--message", "semantic search for asyncio"],
    )
    if rc != 0:
        sys.stdout.write("\n[codey stdout]\n" + out)
        sys.stderr.write("\n[codey stderr]\n" + err)
    assert rc == 0, "CLI should exit cleanly in test mode"
    # The CLI prints a Semantic Search operation box in test-mode search path
    assert "semantic search" in out.lower(), "Expected Semantic Search UX output in stdout"

