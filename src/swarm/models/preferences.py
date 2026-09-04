"""Per-user UI preferences (REQ-144 / #540).

First-party Preferences model — not django-dynamic-preferences — so we stay
dependency-light, work on SQLite and Postgres without Neon, and keep a single
JSON bag for later knobs (theme, …) without a table per setting.

Rows are keyed by Django User when the caller is logged in, otherwise by a
stable auth principal (Bearer token or guest session). That is multi-user-ready
even while most installs are still single-user.
"""

from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """One preferences bag per user / token / guest session."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ui_preference",
    )
    principal = models.CharField(max_length=255, unique=True, db_index=True)
    values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "swarm"
        verbose_name = "User preference"
        verbose_name_plural = "User preferences"
        ordering = ["principal"]

    def __str__(self) -> str:
        return f"UserPreference({self.principal})"
