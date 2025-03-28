"""Integration test for the mcp_demo blueprint.
This test runs the blueprint in non-interactive mode with the instruction "list your tools"
and asserts that the output contains an expected tool listing.
"""
import subprocess
import pytest

def test_mcp_demo_list_tools():
    command = ["uv", "run", "blueprints/mcp_demo/blueprint_mcp_demo.py", "--instruction", "list your tools"]
    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout + result.stderr
    # Check that the output contains expected strings indicating that tools are listed
    assert "Here are the tools available" in output or "Explorer" in output

if __name__ == "__main__":
    pytest.main([__file__])