import pytest  # type: ignore
pytest.skip("MCP integration tests are WIP", allow_module_level=True)
import logging
import os
import asyncio
import signal

pytestmark = pytest.mark.timeout(60)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import shutil
if not shutil.which("uvx"):
    pytest.skip("uvx command not found in PATH")

# A context manager to enforce a hard timeout using SIGALRM.
class Timeout:
    def __init__(self, seconds, message="Test timed out"):
        self.seconds = seconds
        self.message = message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_value, traceback):
        signal.alarm(0)

@pytest.mark.asyncio
async def test_mcp_raw_jsonrpc():
    """Test MCP server integration with raw JSON-RPC commands with a 60-second timeout."""
    async def run_test():
        import shutil
        if not shutil.which("uvx"):
            pytest.skip("uvx command not found in PATH")

        from mcp.client.stdio import stdio_client  # type: ignore
        from mcp import ClientSession, StdioServerParameters  # type: ignore
        server_config = {
            "command": "uvx",
            "args": ["--from", "git+https://github.com/SecretiveShell/MCP-llms-txt", "mcp-llms-txt"],
            "env": dict(os.environ)
        }
        server_params = StdioServerParameters(command=server_config["command"], args=server_config["args"], env=server_config["env"])
        try:
            import sys
            old_stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        logger.debug("Requesting resource list from MCP server...")
                        resources_response = await session.list_resources()
                        resources = getattr(resources_response, "resources", None)
                        logger.debug(f"Resources received: {resources}")
                        assert resources is not None, "Expected 'resources' in response"
                        assert isinstance(resources, list), "'resources' should be a list"
                        assert len(resources) > 0, "Expected at least one resource"
            finally:
                sys.stderr = old_stderr
        except FileNotFoundError as e:
            pytest.skip(f"uvx command not available: {e}")

    with Timeout(60, "Test timed out (hard timeout via SIGALRM)"):
        await asyncio.wait_for(run_test(), timeout=60)
