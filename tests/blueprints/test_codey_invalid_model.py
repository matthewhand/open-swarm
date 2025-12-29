import json
import os
import subprocess
import sys

import pytest


def strip_ansi(text):
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def test_codey_invalid_model(tmp_path):
    """Test that codey CLI fails gracefully with an invalid model and surfaces the provider error."""
    codey_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../.venv/bin/codey')
    )
    if not os.path.exists(codey_path):
        pytest.skip("codey CLI utility not found. Please enable codey blueprint.")

    # Create a temp config with a bogus model
    config = {
        "llm": {
            "bad_model": {
                "provider": "openai",
                "model": "hf-qwen2.5-coder-32b",  # non-existent or not accessible
                "base_url": "https://api.openai.com/v1",
                "api_key": os.environ.get("OPENAI_API_KEY", "sk-fake")
            }
        },
        "profiles": {
            "default": {"llm": "bad_model"}
        }
    }
    config_path = tmp_path / "swarm_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f)

    env = os.environ.copy()
    env["SWARM_CONFIG_PATH"] = str(config_path)
    # Use a simple prompt
    result = subprocess.run(
        [sys.executable, codey_path, "Say hello"],
        capture_output=True, text=True, env=env
    )
    out = strip_ansi(result.stdout + result.stderr)
    # Should fail and mention model not found or invalid_request_error
    assert result.returncode != 0
    assert (
        "model_not_found" in out
        or "invalid_request_error" in out
        or "does not exist" in out
        or "NotFoundError" in out
    ), f"Output did not contain provider/model error. Output: {out}"
