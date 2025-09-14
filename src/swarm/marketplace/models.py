from __future__ import annotations

import re
from typing import Optional

from django.db import models

try:
    from wagtail.models import Page
    from wagtail.fields import RichTextField
    from wagtail.admin.panels import FieldPanel, MultiFieldPanel
    from wagtail.snippets.models import register_snippet
except Exception:  # pragma: no cover - only imported when Wagtail is enabled
    Page = object  # type: ignore
    RichTextField = models.TextField  # type: ignore
    FieldPanel = MultiFieldPanel = object  # type: ignore
    def register_snippet(x):  # type: ignore
        return x


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
]


@register_snippet
class BlueprintCategory(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class MarketplaceIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]


class BlueprintPage(Page):
    summary = models.TextField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(
        BlueprintCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    tags = models.CharField(max_length=250, blank=True, help_text="Comma-separated")
    repository_url = models.URLField(blank=True)
    manifest_json = models.TextField(blank=True, help_text="Optional manifest (no secrets)")
    code_template = models.TextField(blank=True, help_text="Blueprint source template only")

    content_panels = Page.content_panels + [
        FieldPanel("summary"),
        FieldPanel("version"),
        FieldPanel("category"),
        FieldPanel("tags"),
        FieldPanel("repository_url"),
        FieldPanel("manifest_json"),
        FieldPanel("code_template"),
    ]

    def clean(self):  # pragma: no cover - validated by business logic
        super().clean()
        # Simple redaction validation: forbid likely secrets
        blob = f"{self.manifest_json}\n{self.code_template}"
        for pat in SECRET_PATTERNS:
            if pat.search(blob or ""):
                raise models.ValidationError("Potential secret detected in content. Remove credentials.")


class MCPConfigPage(Page):
    summary = models.TextField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    server_name = models.CharField(max_length=100)
    config_template = models.TextField(
        blank=True, help_text="Template JSON/YAML only. Do not include secrets."
    )

    content_panels = Page.content_panels + [
        FieldPanel("summary"),
        FieldPanel("version"),
        FieldPanel("server_name"),
        FieldPanel("config_template"),
    ]

    def clean(self):  # pragma: no cover
        super().clean()
        for pat in SECRET_PATTERNS:
            if pat.search(self.config_template or ""):
                raise models.ValidationError("Potential secret detected in MCP config template.")

