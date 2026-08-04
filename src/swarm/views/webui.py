"""Legacy /webui/ endpoint.

Historically this rendered a dedicated ``webui/index.html`` template, but that
template no longer ships with the project, so the view raised
``TemplateDoesNotExist`` (HTTP 500) whenever it was hit.

Decision (ROADMAP §2 "Login routing"): keep the route for backward
compatibility with old bookmarks/links and redirect to ``/``, which serves the
built SPA when ``webui/frontend/dist`` exists or the Django template index
otherwise (see ``swarm.views.web_views.index``).
"""
from django.views.generic import RedirectView


class WebUIView(RedirectView):
    """Redirect the legacy /webui/ URL to the root index."""

    permanent = False  # temporary redirect: behaviour may change again
    url = "/"
