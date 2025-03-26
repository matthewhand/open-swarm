"""
Initializes the views package and exposes key view modules and viewsets.
"""
# Import the view modules to make them accessible via swarm.views.*
# Use try-except for robustness during development/refactoring
try:
    from . import core_views
except ImportError as e:
    print(f"Warning: Could not import swarm.views.core_views: {e}")
    core_views = None

try:
    from . import chat_views
except ImportError as e:
    print(f"Warning: Could not import swarm.views.chat_views: {e}")
    chat_views = None

try:
    from . import model_views
except ImportError as e:
    print(f"Warning: Could not import swarm.views.model_views: {e}")
    model_views = None

try:
    from . import message_views
    from .message_views import ChatMessageViewSet
except ImportError as e:
    print(f"Warning: Could not import swarm.views.message_views: {e}")
    message_views = None
    ChatMessageViewSet = None # Ensure it's None if import fails

try:
    from . import utils
except ImportError as e:
    print(f"Warning: Could not import swarm.views.utils: {e}")
    utils = None


# Expose only successfully imported components
__all__ = [name for name, obj in globals().items() if obj is not None and not name.startswith('_')]

