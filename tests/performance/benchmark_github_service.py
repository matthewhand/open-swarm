
import sys
import time
import base64
import json
from unittest.mock import MagicMock, patch

# Mock all dependencies that are missing in the environment
mock_httpx = MagicMock()
sys.modules["httpx"] = mock_httpx
sys.modules["asgiref"] = MagicMock()
sys.modules["asgiref.sync"] = MagicMock()
sys.modules["django"] = MagicMock()
sys.modules["django.conf"] = MagicMock()
sys.modules["django.db"] = MagicMock()
sys.modules["django.db.models"] = MagicMock()
sys.modules["swarm.models.core_models"] = MagicMock()
sys.modules["swarm.settings"] = MagicMock()
sys.modules["swarm.utils.env_utils"] = MagicMock()

# Now we can import the service
sys.path.insert(0, 'src')

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data
    def json(self):
        return self.json_data

class MockClient:
    def __init__(self, *args, **kwargs):
        self.latency = 0.05
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def get(self, url, **kwargs):
        # print(f"Mock GET: {url}")
        time.sleep(self.latency)
        if url.endswith('contents/open-swarm.json'):
            return MockResponse(404, {})
        if url.endswith('contents/swarm/blueprints') or url.endswith('contents/swarm/mcp'):
            base = "swarm/blueprints" if "blueprints" in url else "swarm/mcp"
            return MockResponse(200, [{'type': 'dir', 'path': f'{base}/item-{i}'} for i in range(3)])
        if url.endswith('manifest.json'):
            content = base64.b64encode(json.dumps({'name': 'test'}).encode()).decode()
            return MockResponse(200, {'type': 'file', 'content': content, 'path': url})

        # Enrichment listing
        if any(f'/contents/swarm/blueprints/item-{i}' in url for i in range(3)) or any(f'/contents/swarm/mcp/item-{i}' in url for i in range(3)):
             if not url.endswith('.py') and not url.endswith('manifest.json'):
                return MockResponse(200, [{'type': 'file', 'path': f'{url.split("/")[-1]}/file-0.py', 'size': 1000, 'name': 'file-0.py'}])

        if url.endswith('.py'):
             content = base64.b64encode(b'print(\"hello\")\n' * 5).decode()
             return MockResponse(200, {'content': content})

        return MockResponse(404, {})

# Inject MockClient into github_service module after import
from swarm.marketplace import github_service
github_service.httpx.Client = MockClient

def benchmark():
    # Use full_name that will satisfy the logic
    repo = {'full_name': 'owner/repo'}
    print("Starting benchmark...")

    start = time.perf_counter()
    results = github_service.fetch_repo_manifests(repo)
    end = time.perf_counter()
    duration = end - start
    print(f"Fetched {len(results)} items")
    print(f"Time taken: {duration:.4f}s")
    return duration

if __name__ == "__main__":
    benchmark()
