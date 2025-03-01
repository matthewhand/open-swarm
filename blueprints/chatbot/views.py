from django.shortcuts import render, redirect
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
def chatbot_view(request):
    """Render the chatbot UI with user-specific conversation history."""
    logger.debug("Rendering chatbot web UI")
    user = request.user if request.user.is_authenticated else get_or_create_default_user()
    conversations = ChatConversation.objects.filter(student=user).order_by('-created_at')
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "is_chatbot": True,
        "conversations": conversations
    }
    return render(request, "chatbot/chatbot.html", context)

@csrf_exempt
@login_required
def create_chat(request):
    """Create a new chat conversation and redirect to chatbot view."""
    user = request.user if request.user.is_authenticated else get_or_create_default_user()
    new_convo = ChatConversation.objects.create(
        conversation_id=str(uuid.uuid4()),
        student=user
    )
    return redirect('chatbot:chatbot_view')

@csrf_exempt
@login_required
def delete_chat(request, conversation_id):
    """Delete a specific chat conversation and redirect to chatbot view."""
    user = request.user if request.user.is_authenticated else get_or_create_default_user()
    try:
        chat = ChatConversation.objects.get(conversation_id=conversation_id, student=user)
        chat.delete()
    except ChatConversation.DoesNotExist:
        logger.warning(f"Attempted to delete non-existent chat: {conversation_id}")
    return redirect('chatbot:chatbot_view')
