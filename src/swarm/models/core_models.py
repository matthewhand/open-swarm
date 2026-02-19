"""
Core models for the refactored marketplace structure.

This module contains the core data models for marketplace items, including
blueprints and MCP configurations with enhanced metadata and validation.
"""

from __future__ import annotations

import re

from django.db import models


class MarketplaceItem(models.Model):
    """
    Abstract base model for marketplace items (blueprints and MCP configs).
    """
    name = models.CharField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0.0')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    repository_url = models.URLField(blank=True)
    source = models.CharField(max_length=50, default='github')  # github, wagtail, local
    manifest_data = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True

    def clean(self) -> None:
        """Validate that no secrets are present in the model fields."""
        super().clean()
        # Check for potential secrets in description and other fields
        blob = f"{self.description}\n{self.manifest_data}"
        if self._contains_secrets(blob):
            raise models.ValidationError("Potential secret detected in content. Remove credentials.")

    @staticmethod
    def _contains_secrets(text: str) -> bool:
        """Check if the text contains potential secret patterns."""
        secret_patterns = [
            re.compile(r"sk-[A-Za-z0-9]{10,}", re.IGNORECASE),  # OpenAI keys
            re.compile(r"api[_-]?key", re.IGNORECASE),  # API key
            re.compile(r"secret", re.IGNORECASE),  # Generic secret
            re.compile(r"password", re.IGNORECASE),  # Password
            re.compile(r"token", re.IGNORECASE),  # Token
            re.compile(r"bearer[_-]?\w+", re.IGNORECASE),  # Bearer tokens
        ]

        return any(pattern.search(text or "") for pattern in secret_patterns)

    @property
    def tag_list(self) -> list[str]:
        """Return tags as a list."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []


class Blueprint(models.Model):
    """
    Model representing a blueprint item in the marketplace.
    """
    name = models.CharField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0.0')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    repository_url = models.URLField(blank=True)
    source = models.CharField(max_length=50, default='github')  # github, wagtail, local
    manifest_data = models.JSONField(default=dict, blank=True)
    code_template = models.TextField(blank=True, help_text="Blueprint source template only")
    required_mcp_servers = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'marketplace_blueprint'
        ordering = ['-created_at']

    def clean(self) -> None:
        """Validate that no secrets are present in the model fields."""
        super().clean()
        # Check for potential secrets in all fields
        blob = f"{self.description}\n{self.code_template}\n{self.manifest_data}"
        if self._contains_secrets(blob):
            raise models.ValidationError("Potential secret detected in content. Remove credentials.")

    @staticmethod
    def _contains_secrets(text: str) -> bool:
        """Check if the text contains potential secret patterns."""
        secret_patterns = [
            re.compile(r"sk-[A-Za-z0-9]{10,}", re.IGNORECASE),  # OpenAI keys
            re.compile(r"api[_-]?key", re.IGNORECASE),  # API key
            re.compile(r"secret", re.IGNORECASE),  # Generic secret
            re.compile(r"password", re.IGNORECASE),  # Password
            re.compile(r"token", re.IGNORECASE),  # Token
            re.compile(r"bearer[_-]?\w+", re.IGNORECASE),  # Bearer tokens
        ]

        return any(pattern.search(text or "") for pattern in secret_patterns)

    @property
    def tag_list(self) -> list[str]:
        """Return tags as a list."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []


class MCPConfig(models.Model):
    """
    Model representing an MCP configuration template in the marketplace.
    """
    name = models.CharField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0.0')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    repository_url = models.URLField(blank=True)
    source = models.CharField(max_length=50, default='github')  # github, wagtail, local
    manifest_data = models.JSONField(default=dict, blank=True)
    config_template = models.TextField(
        blank=True,
        help_text="Template JSON/YAML only. Do not include secrets."
    )
    server_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'marketplace_mcp_config'
        ordering = ['-created_at']

    def clean(self) -> None:
        """Validate that no secrets are present in the config template."""
        super().clean()
        if self._contains_secrets(self.config_template or ""):
            raise models.ValidationError("Potential secret detected in MCP config template.")

    @staticmethod
    def _contains_secrets(text: str) -> bool:
        """Check if the text contains potential secret patterns."""
        secret_patterns = [
            re.compile(r"sk-[A-Za-z0-9]{10,}", re.IGNORECASE),  # OpenAI keys
            re.compile(r"api[_-]?key", re.IGNORECASE),  # API key
            re.compile(r"secret", re.IGNORECASE),  # Generic secret
            re.compile(r"password", re.IGNORECASE),  # Password
            re.compile(r"token", re.IGNORECASE),  # Token
            re.compile(r"bearer[_-]?\w+", re.IGNORECASE),  # Bearer tokens
        ]

        return any(pattern.search(text or "") for pattern in secret_patterns)

    @property
    def tag_list(self) -> list[str]:
        """Return tags as a list."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []


class MarketplaceIndex(models.Model):
    """
    Index model for marketplace items to enable search and categorization.
    """
    name = models.CharField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0.0')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    repository_url = models.URLField(blank=True)
    source = models.CharField(max_length=50, default='github')  # github, wagtail, local
    manifest_data = models.JSONField(default=dict, blank=True)

    # Foreign key to the actual item (either Blueprint or MCPConfig)
    item_type = models.CharField(max_length=20, choices=[
        ('blueprint', 'Blueprint'),
        ('mcp_config', 'MCP Config'),
    ])
    item_id = models.IntegerField()

    class Meta:
        db_table = 'marketplace_index'
        ordering = ['-created_at']

    @property
    def tag_list(self) -> list[str]:
        """Return tags as a list."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []

    @property
    def item(self) -> models.Model | None:
        """Get the associated item (either Blueprint or MCPConfig)."""
        if self.item_type == 'blueprint':
            try:
                return Blueprint.objects.get(id=self.item_id)
            except Blueprint.DoesNotExist:
                return None
        elif self.item_type == 'mcp_config':
            try:
                return MCPConfig.objects.get(id=self.item_id)
            except MCPConfig.DoesNotExist:
                return None
        return None
