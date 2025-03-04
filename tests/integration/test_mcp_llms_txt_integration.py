import asyncio
import json
import unittest
from mcp.client.session import ClientSession
import mcp.types as types

def create_memory_streams():
    import anyio
    # Create two channels:
    # client_send: client writes request; server receives on server_recv.
    # server_send: server writes response; client receives on client_recv.
    client_send, server_recv = anyio.create_memory_object_stream(10)
    server_send, client_recv = anyio.create_memory_object_stream(10)
    return client_send, client_recv, server_recv, server_send

async def fake_server_handler(server_recv, server_send):
    """
    Fake server that waits briefly and then sends a pre-defined response on server_send.
    This avoids hanging if no request is received.
    """
    await asyncio.sleep(0.1)  # simulate processing delay
    # Use a fixed request id since we're not receiving a request.
    request_id = 1
    response = {
        "jsonrpc": "2.0",
        "result": {
            "resources": [
                {
                    "uri": "dummy://resource",
                    "name": "Dummy Resource",
                    "description": "A dummy resource for testing",
                    "mimeType": "text/plain"
                }
            ]
        },
        "id": request_id
    }
    await server_send.send(response)

class TestMcpClientResourceIntegration(unittest.TestCase):
    def test_list_resources(self):
        async def run_test():
            # Create in-memory streams for simulating transport.
            client_send, client_recv, server_recv, server_send = create_memory_streams()
            
            # Instantiate ClientSession with in-memory streams.
            session = ClientSession(
                read_stream=client_recv,
                write_stream=client_send,
                read_timeout_seconds=None
            )
            
            # Run fake_server_handler concurrently.
            server_task = asyncio.create_task(fake_server_handler(server_recv, server_send))
            
            # Call the client's list_resources method.
            result = await session.list_resources()
            
            # Wait for the server task to complete.
            await server_task
            
            # Assert the result contains the dummy resource.
            self.assertIn("resources", result)
            self.assertGreater(len(result["resources"]), 0)
            dummy_resource = result["resources"][0]
            self.assertEqual(dummy_resource["uri"], "dummy://resource")
            self.assertEqual(dummy_resource["name"], "Dummy Resource")
            self.assertEqual(dummy_resource["mimeType"], "text/plain")
        
        asyncio.run(asyncio.wait_for(run_test(), timeout=10))

if __name__ == "__main__":
    unittest.main()