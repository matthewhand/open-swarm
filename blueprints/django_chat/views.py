from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from swarm.models import ChatConversation, ChatMessage
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)

def get_or_create_default_user():
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
