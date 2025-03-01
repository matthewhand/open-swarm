"""
Chatbot Blueprint

A blueprint providing a web-based chatbot interface with conversation history management.
HTTP-only; not intended for CLI use.
"""

import logging
import uuid
import sys
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))
logger.addHandler(handler)

# Reject CLI execution immediately
if __name__ == "__main__":
    logger.info("ChatbotBlueprint is an HTTP-only service. Access it via the web interface at /chatbot/.")
    print("This blueprint is designed for HTTP use only. Please access it via the web server at /chatbot/", file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

# Django imports after CLI rejection
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
import django
django.setup()

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from swarm.models import ChatConversation, ChatMessage
from swarm.extensions.blueprint.blueprint_base import BlueprintBase as Blueprint
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)

class ChatbotBlueprint(Blueprint):
    @property
    def metadata(self) -> Dict[str, Any]:
        logger.debug("Fetching metadata")
        return {
            "title": "Chatbot Interface",
            "description": "A web-based chatbot interface with conversation history management. HTTP-only.",
            "cli_name": "chatbot",
            "env_vars": [],
            "urls_module": "blueprints.chatbot.urls",
            "url_prefix": "chatbot/"
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
    def chatbot_view(self, request):
        """Render the chatbot UI with user-specific conversation history."""
        logger.debug("Rendering chatbot web UI")
        user = request.user if request.user.is_authenticated else self.get_or_create_default_user()
        conversations = ChatConversation.objects.filter(student=user).order_by('-created_at')
        context = {
            "dark_mode": request.session.get('dark_mode', True),
            "is_chatbot": True,
            "conversations": conversations
        }
        return render(request, "chatbot/chatbot.html", context)

    @csrf_exempt
    @login_required
    def create_chat(self, request):
        """Create a new chat conversation and redirect to chatbot view."""
        user = request.user if request.user.is_authenticated else self.get_or_create_default_user()
        new_convo = ChatConversation.objects.create(
            conversation_id=str(uuid.uuid4()),
            student=user
        )
        return redirect('chatbot:chatbot_view')

    @csrf_exempt
    @login_required
    def delete_chat(self, request, conversation_id):
        """Delete a specific chat conversation and redirect to chatbot view."""
        user = request.user if request.user.is_authenticated else self.get_or_create_default_user()
        try:
            chat = ChatConversation.objects.get(conversation_id=conversation_id, student=user)
            chat.delete()
        except ChatConversation.DoesNotExist:
            logger.warning(f"Attempted to delete non-existent chat: {conversation_id}")
        return redirect('chatbot:chatbot_view')

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        """Minimal implementation for CLI compatibility without agents."""
        logger.debug("Running with context (UI-focused implementation)")
        return {
            "response": {"messages": [{"role": "assistant", "content": "Chatbot UI active via web interface at /chatbot/"}]},
            "context_variables": context_variables
        }
