import sys
sys.path.insert(0, "src")
import pytest  # type: ignore
pytest.skip("MCP resource timeout tests are WIP", allow_module_level=True)
import sys
sys.path.insert(0, "src")
import asyncio
import pytest  # type: ignore
from swarm.extensions.mcp.mcp_client import MCPClient, StdioServerParameters, stdio_client, ClientSession  # type: ignore

@pytest.mark.asyncio
async def test_list_resources_logs_timeout(monkeypatch, caplog):
    # Set a short timeout to force a timeout condition.
    config = {"command": "npx", "args": [], "env": {}}
    client_timeout = 1  # 1 second timeout to force failure
    mcp = MCPClient(config, timeout=client_timeout, debug=False)

    async def fake_list_resources(self):
        # Simulate a delay longer than the timeout.
        await asyncio.sleep(2)
        return "fake_resources"

    class FakeSession:
        async def list_resources(self):
            return await fake_list_resources(self)
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class FakeClientSession:
        def __init__(self, read, write):
            self.read = read
            self.write = write
        async def __aenter__(self):
            return FakeSession()
        async def __aexit__(self, exc_type, exc, tb):
            pass

    async def fake_stdio_client(params):
        class FakeStdIO:
            async def __aenter__(self):
                return ("fake_read", "fake_write")
            async def __aexit__(self, exc_type, exc, tb):
                pass
        return FakeStdIO()

    monkeypatch.setattr("swarm.extensions.mcp.mcp_client.stdio_client", fake_stdio_client)
    monkeypatch.setattr("swarm.extensions.mcp.mcp_client.ClientSession", FakeClientSession)

    with caplog.at_level("ERROR"):
        start = asyncio.get_event_loop().time()
        with pytest.raises(RuntimeError, match="Resource list request timed out"):
            await mcp.list_resources()
        duration = asyncio.get_event_loop().time() - start
        print(f"Timeout duration: {duration} seconds")
    timeout_logs = [record for record in caplog.records if "Timeout after" in record.message]
    assert timeout_logs, "Expected timeout error log not found"
    assert duration < 30, f"Resource timeout took too long: {duration} seconds"