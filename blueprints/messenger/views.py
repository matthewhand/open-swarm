from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)

@csrf_exempt
def messenger(request):
    """Render the messenger UI."""
    logger.debug("Rendering messenger web UI")
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "is_chatbot": False
    }
    return render(request, "messenger/messenger.html", context)
