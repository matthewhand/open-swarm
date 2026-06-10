from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from swarm.models import ChatConversation
from swarm.utils.env_utils import get_testuser_password, is_django_debug
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)

def get_or_create_default_user():
    """Create or retrieve a default 'testuser' (DEBUG mode only).

    The fallback user is a development-only convenience. Outside debug mode
    (DJANGO_DEBUG=true) it is refused outright, and the account is never
    created with a hardcoded password (random per-process unless
    TESTUSER_PASSWORD is set).
    """
    if not is_django_debug():
        raise PermissionDenied(
            "The default 'testuser' fallback is a development-only convenience "
            "and is disabled because DJANGO_DEBUG is not enabled."
        )
    username = "testuser"
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username, password=get_testuser_password())
        logger.info(f"Created default user: {username}")
    return user

@csrf_exempt
@login_required
def django_chat(request):
    """Render the django_chat UI with user-specific conversation history."""
    logger.debug("Rendering django_chat web UI")
    user = request.user if request.user.is_authenticated else get_or_create_default_user()
    conversations = ChatConversation.objects.filter(student=user).order_by('-created_at')
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "is_chatbot": False,
        "conversations": conversations
    }
    return render(request, "django_chat/django_chat_webpage.html", context)
