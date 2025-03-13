import pytest  # type: ignore
import logging
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import shutil
if not shutil.which("uvx"):
    pytest.skip("uvx command not found in PATH")
@pytest.mark.asyncio
async def test_mcp_raw_jsonrpc():
    """Test MCP server integration with raw JSON-RPC commands."""
    import shutil
    if not shutil.which("uvx"):
         pytest.skip("uvx command not found in PATH")

    from mcp.client.stdio import stdio_client  # type: ignore
    from mcp import ClientSession, StdioServerParameters  # type: ignore
    server_config = {"command": "uvx", "args": ["--from", "git+https://github.com/SecretiveShell/MCP-llms-txt", "mcp-llms-txt"], "env": dict(os.environ)}
    server_params = StdioServerParameters(command=server_config["command"], args=server_config["args"], env=server_config["env"])
    try:
         import sys
         old_stderr = sys.stderr
         sys.stderr = open(os.devnull, "w")
         try:
             async with stdio_client(server_params) as (read, write):
                 async with ClientSession(read, write) as session:
                     resources_response = await session.list_resources()
                     resources = getattr(resources_response, "resources", None)
                     assert resources is not None, "Expected 'resources' in response"
                     assert isinstance(resources, list), "'resources' should be a list"
                     assert len(resources) > 0, "Expected at least one resource"
         finally:
             sys.stderr = old_stderr
    except FileNotFoundError as e:
         pytest.skip(f"uvx command not available: {e}")
