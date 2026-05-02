from django.views.generic import TemplateView
from django.conf import settings
from django.http import HttpResponseNotFound
import os

class WebUIView(TemplateView):
    template_name = "webui/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Any context variables for the React app
        return context

    def get(self, request, *args, **kwargs):
        # Fallback if index.html is missing
        template_path = os.path.join(settings.BASE_DIR.parent, "staticfiles", "webui", "index.html")
        if not getattr(settings, "DEBUG", False) and not os.path.exists(template_path):
             return HttpResponseNotFound("Web UI build not found. Please run Vite build.")
        return super().get(request, *args, **kwargs)
