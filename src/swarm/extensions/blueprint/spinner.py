"""DEPRECATED shim: use ``swarm.core.spinner`` instead.

Re-exports the canonical spinner implementations for backwards compatibility.
Will be removed in a future release (see ROADMAP.md for the sunset plan).
"""

import warnings

from swarm.core.spinner import Spinner, SwarmSpinner  # noqa: F401

warnings.warn(
    "swarm.extensions.blueprint.spinner is deprecated; "
    "import from swarm.core.spinner instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Spinner", "SwarmSpinner"]
