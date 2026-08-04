"""DEPRECATED shim: use ``swarm.core.slash_commands`` instead.

Documentation/examples historically referenced
``swarm.extensions.blueprint.slash_commands``; the live implementation is
``swarm.core.slash_commands``. Will be removed in a future release (see
ROADMAP.md for the sunset plan).
"""

import warnings

from swarm.core.slash_commands import SlashCommandRegistry, slash_registry  # noqa: F401

warnings.warn(
    "swarm.extensions.blueprint.slash_commands is deprecated; "
    "import from swarm.core.slash_commands instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SlashCommandRegistry", "slash_registry"]
