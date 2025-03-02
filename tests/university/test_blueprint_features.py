import os
import pytest
import subprocess
import tempfile
import asyncio
from django.test import Client
from unittest.mock import patch, Mock
from blueprints.university.blueprint_university import UniversitySupportBlueprint
from blueprints.chatbot.blueprint_chatbot import ChatbotBlueprint
from blueprints.messenger.blueprint_messenger import MessengerBlueprint
from blueprints.django_chat.blueprint_django_chat import DjangoChatBlueprint

# Base environment setup
BASE_ENV = {
    "UNIT_TESTING": "true",
    "ENABLE_API_AUTH": "false",
    "SUPPORT_EMAIL": "test@example.com",
    "PYTHONPATH": os.path.abspath("."),
    "DJANGO_SETTINGS_MODULE": "swarm.settings"
}

# Dummy config path
CONFIG_PATH = os.path.abspath("swarm_config.json")

# Patch UniversityBaseViewSet.initial to skip authentication enforcement
@pytest.fixture(scope="module")
def bypass_auth():
    from blueprints.university.views import UniversityBaseViewSet
    original_initial = UniversityBaseViewSet.initial
    def mock_initial(self, request, *args, **kwargs):
        request.user = type('User', (), {'is_authenticated': True, 'is_anonymous': False})()
        super(UniversityBaseViewSet, self).initial(request, *args, **kwargs)
    UniversityBaseViewSet.initial = mock_initial
    yield
    UniversityBaseViewSet.initial = original_initial

@pytest.fixture(scope="module", autouse=True)
def setup_blueprint_urls(bypass_auth):
    for blueprint_cls in [UniversitySupportBlueprint, ChatbotBlueprint, MessengerBlueprint, DjangoChatBlueprint]:
        blueprint = blueprint_cls(config={"llm": {"default": {"provider": "openai", "model": "gpt-4o", "base_url": "https://api.openai.com/v1", "api_key": "dummy"}}})
        blueprint.register_blueprint_urls()
    yield

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

async def run_cli_async(blueprint_path, args, temp_db_path):
    env = BASE_ENV.copy()
    env["SQLITE_DB_PATH"] = temp_db_path
    cmd = ["python", blueprint_path] + args
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        cwd=os.path.abspath("."),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if "--instruction" not in args else None
    )
    input_data = "exit\n".encode() if "--instruction" not in args else None
    stdout, stderr = await process.communicate(input=input_data)
    return subprocess.CompletedProcess(cmd, process.returncode, stdout.decode(), stderr.decode())

@pytest.mark.asyncio
async def test_non_interactive_mode_university(temp_db):
    blueprint_path = "blueprints/university/blueprint_university.py"
    instruction = "List all courses"
    args = ["--config", CONFIG_PATH, "--instruction", instruction]
    
    # Mock the OpenAI API call directly
    with patch('openai.resources.chat.completions.AsyncCompletions.create') as mock_create:
        mock_create.return_value = Mock(
            choices=[Mock(message={"role": "assistant", "content": "Course list"})]
        )
        result = await run_cli_async(blueprint_path, args, temp_db)
    
    output = result.stdout
    assert result.returncode == 0, f"Non-interactive mode failed: output={output}, stderr={result.stderr}"
    assert "University Support System Non-Interactive Mode" in output, f"Mode header missing: {output}"
    assert "Execution completed. Exiting." in output, f"Exit message missing: {output}"

@pytest.mark.asyncio
async def test_interactive_mode_university(temp_db):
    blueprint_path = "blueprints/university/blueprint_university.py"
    args = ["--config", CONFIG_PATH]
    result = await run_cli_async(blueprint_path, args, temp_db)
    output = result.stdout
    assert result.returncode == 0, f"Interactive mode failed: output={output}, stderr={result.stderr}"
    assert "University Support System Interactive Mode" in output, f"Mode header missing: {output}"
    assert "Exiting interactive mode." in output, f"Exit message missing: {output}"

@pytest.mark.asyncio
async def test_http_only_chatbot(temp_db):
    blueprint_path = "blueprints/chatbot/blueprint_chatbot.py"
    args = ["--config", CONFIG_PATH]
    result = await run_cli_async(blueprint_path, args, temp_db)
    output = result.stderr
    assert result.returncode == 1, f"Chatbot CLI execution should fail: output={output}"
    assert "This blueprint is designed for HTTP use only" in output, f"HTTP-only message missing: {output}"
    assert "/chatbot/" in output, f"URL missing: {output}"

@pytest.mark.asyncio
async def test_http_only_messenger(temp_db):
    blueprint_path = "blueprints/messenger/blueprint_messenger.py"
    args = ["--config", CONFIG_PATH]
    result = await run_cli_async(blueprint_path, args, temp_db)
    output = result.stderr
    assert result.returncode == 1, f"Messenger CLI execution should fail: output={output}"
    assert "This blueprint is designed for HTTP use only" in output, f"HTTP-only message missing: {output}"
    assert "/messenger/" in output, f"URL missing: {output}"

@pytest.mark.asyncio
async def test_http_only_django_chat(temp_db):
    blueprint_path = "blueprints/django_chat/blueprint_django_chat.py"
    args = ["--config", CONFIG_PATH]
    result = await run_cli_async(blueprint_path, args, temp_db)
    output = result.stderr
    assert result.returncode == 1, f"Django Chat CLI execution should fail: output={output}"
    assert "This blueprint is designed for HTTP use only" in output, f"HTTP-only message missing: {output}"
    assert "/django_chat/" in output, f"URL missing: {output}"

@pytest.mark.django_db
def test_http_endpoints_accessible():
    client = Client()
    endpoints = [
        "/chatbot/",
        "/messenger/",
        "/django_chat/",
        "/v1/university/teaching-units/"
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in (200, 302, 404), f"Endpoint {endpoint} returned {response.status_code}: {response.content}"
        assert response.status_code != 401, f"Endpoint {endpoint} unauthorized: {response.content}"
