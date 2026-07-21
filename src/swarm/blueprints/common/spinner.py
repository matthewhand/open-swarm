"""DEPRECATED shim: ``SwarmSpinner`` moved to ``swarm.core.spinner``.

This module re-exports it for backwards compatibility and will be removed in
a future release (see ROADMAP.md for the sunset plan).
"""

import warnings

from swarm.core.spinner import SwarmSpinner  # noqa: F401

warnings.warn(
    "swarm.blueprints.common.spinner is deprecated; "
    "import SwarmSpinner from swarm.core.spinner instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SwarmSpinner"]
