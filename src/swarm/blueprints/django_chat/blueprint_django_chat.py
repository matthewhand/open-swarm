"""
Django Chat Blueprint

A blueprint providing a web-based chat interface with conversation history management.
HTTP-only; not intended for CLI use.
"""

import logging
import os
import sys
import time
from typing import Any

from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.core.blueprint_ux import BlueprintUXImproved


# --- Logging Setup ---
def setup_logging():
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args, _ = parser.parse_known_args()
    loglevel = os.environ.get('LOGLEVEL', None)
    if args.debug or os.environ.get('SWARM_DEBUG', '0') == '1' or (loglevel and loglevel.upper() == 'DEBUG'):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    return args

args = setup_logging()

logger = logging.getLogger(__name__)

# Reject CLI execution immediately
if __name__ == "__main__":
    logger.info("DjangoChatBlueprint is an HTTP-only service. Access it via the web interface at /django_chat/.")
    print("This blueprint is designed for HTTP use only. Please access it via the web server at /django_chat/", file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

# Django imports after CLI rejection
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
import django

django.setup()

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from swarm.core.blueprint_base import BlueprintBase as Blueprint
from swarm.models import ChatConversation
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)

# --- Spinner and ANSI/emoji operation box for unified UX (for CLI/dev runs) ---
import threading

from rich.console import Console
from rich.style import Style
from rich.text import Text


class DjangoChatSpinner:
    FRAMES = [
        "Generating.", "Generating..", "Generating...", "Running...",
        "⠋ Generating...", "⠙ Generating...", "⠹ Generating...", "⠸ Generating...",
        "⠼ Generating...", "⠴ Generating...", "⠦ Generating...", "⠧ Generating...",
        "⠇ Generating...", "⠏ Generating...", "🤖 Generating...", "💡 Generating...", "✨ Generating..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()
        self._last_frame = None
        self._last_slow = False

    def start(self):
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            if elapsed > self.SLOW_THRESHOLD:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
                self._last_frame = self.SLOW_FRAME
                self._last_slow = True
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
                self._last_frame = frame
                self._last_slow = False
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))

    def current_spinner_state(self):
        if self._last_slow:
            return self.SLOW_FRAME
        return self._last_frame or self.FRAMES[0]


class DjangoChatBlueprint(Blueprint):
    def __init__(self, blueprint_id: str = "django_chat", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._config = config if config is not None else None
        self._llm_profile_name = None
        self._llm_profile_data = None
        self._markdown_output = None
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()

    @property
    def metadata(self) -> dict[str, Any]:
        logger.debug("Fetching metadata")
        return {
            "title": "Django Chat Interface",
            "description": "A web-based chat interface with conversation history management. HTTP-only.",
            "cli_name": "django_chat",
            "env_vars": [],
            "urls_module": "blueprints.django_chat.urls",
            "url_prefix": "django_chat/"
        }

    def get_or_create_default_user(self):
        """Create or retrieve a default 'testuser' for development purposes."""
        username = "testuser"
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password="testpass")
            logger.info(f"Created default user: {username}")
        return user

    @csrf_exempt
    @login_required
    def django_chat(self, request):
        """Render the django_chat UI with user-specific conversation history."""
        logger.debug("Rendering django_chat web UI")
        user = request.user if request.user.is_authenticated else self.get_or_create_default_user()
        conversations = ChatConversation.objects.filter(student=user).order_by('-created_at')
        context = {
            "dark_mode": request.session.get('dark_mode', True),
            "is_chatbot": False,
            "conversations": conversations
        }
        return render(request, "django_chat/django_chat_webpage.html", context)

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: list[dict[str, str]]):
        """Main execution entry point for the DjangoChat blueprint."""
        logger.info("DjangoChatBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        ux = BlueprintUXImproved(style="serious")
        spinner_idx = 0
        start_time = time.time()
        spinner_yield_interval = 1.0  # seconds
        last_spinner_time = start_time
        try:
            # Simulate agent runner pattern (replace with actual agent logic if available)
            prompt_context = {
                "user_request": instruction,
                "history": messages[:-1],
                "available_tools": ["django_chat"]
            }
            rendered_prompt = self.render_prompt("django_chat_prompt.j2", prompt_context)
            # Simulate progressive spinner for a few cycles
            for _ in range(3):
                now = time.time()
                if now - last_spinner_time >= spinner_yield_interval:
                    taking_long = (now - start_time > 10)
                    spinner_msg = ux.spinner(spinner_idx, taking_long=taking_long)
                    yield {"messages": [{"role": "assistant", "content": spinner_msg}]}
                    spinner_idx += 1
                    last_spinner_time = now
                    await asyncio.sleep(0.2)
            # Final result
            summary = ux.summary("Operation", 1, {"instruction": instruction[:40]})
            box = ux.ansi_emoji_box(
                title="DjangoChat Result",
                content=f"[DjangoChat LLM] Would respond to: {rendered_prompt}",
                summary=summary,
                params={"instruction": instruction[:40]},
                result_count=1,
                op_type="run",
                status="success"
            )
            yield {"messages": [{"role": "assistant", "content": box}]}
        except Exception as e:
            logger.error(f"Error during DjangoChat run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

    def run_with_context(self, messages: list[dict[str, str]], context_variables: dict) -> dict:
        """Minimal implementation for CLI compatibility without agents."""
        logger.debug("Running with context (UI-focused implementation)")
        return {
            "response": {"messages": [{"role": "assistant", "content": "Django Chat UI active via web interface at /django_chat/"}]},
            "context_variables": context_variables
        }

if __name__ == "__main__":
    import asyncio
    messages = [
        {"role": "user", "content": "Start a chat session about Django."}
    ]
    blueprint = DjangoChatBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        spinner = DjangoChatSpinner()
        spinner.start()
        try:
            all_results = []
            async for response in blueprint.run(messages):
                content = response["messages"][0]["content"] if (isinstance(response, dict) and "messages" in response and response["messages"]) else str(response)
                all_results.append(content)
                # Enhanced progressive output
                if isinstance(response, dict) and (response.get("progress") or response.get("matches")):
                    display_operation_box(
                        title="Progressive Operation",
                        content="\n".join(response.get("matches", [])),
                        style="bold cyan" if response.get("type") == "code_search" else "bold magenta",
                        result_count=len(response.get("matches", [])) if response.get("matches") is not None else None,
                        params={k: v for k, v in response.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                        progress_line=response.get('progress'),
                        total_lines=response.get('total'),
                        spinner_state=spinner.current_spinner_state() if hasattr(spinner, 'current_spinner_state') else None,
                        op_type=response.get("type", "search"),
                        emoji="🔍" if response.get("type") == "code_search" else "🧠"
                    )
        finally:
            spinner.stop()
        display_operation_box(
            title="DjangoChat Output",
            content="\n".join(all_results),
            style="bold green",
            result_count=len(all_results),
            params={"prompt": messages[0]["content"]},
            op_type="django_chat"
        )
    asyncio.run(run_and_print())
